"""
La jerarquía de dos niveles de tipos de ausencia (migración 088) — sin red.

  1. 🔴 Profundidad máxima 2: un subtipo de un subtipo se rechaza.
  2. Anti-ciclos.
  3. 🔴 Filtrar por un PADRE trae las ausencias de sus hijos; por un HIJO, solo las suyas.
  4. El export devuelve el MISMO conjunto que el listado con el mismo filtro.
  5. `cuenta_ausentismo` del hijo se precarga del padre y después es INDEPENDIENTE.
  6. Un tipo desactivado no aparece en los selects y NO rompe las ausencias que lo usan.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · `_TiposRepo.ids_de_familia` resuelve los hijos DE VERDAD contra sus filas, no devuelve una
    constante. Si devolviera siempre `[tipo_id]`, el test de "filtrar por padre trae los hijos"
    pasaría con el `.in_()` puesto o con el `.eq()` viejo — no podría desmentir nada.
  · `_AusRepo` CAPTURA los `tipo_ids` que recibe y filtra sus filas con ellos. Un fake que
    ignorara el parámetro haría que (3) y (4) den verde con el filtro roto: es el caso #1 de la
    regla del repo ("el fake acepta el parámetro y lo ignora").
  · El fake de tipos GUARDA lo que recibe en `create` (incluido `cuenta_ausentismo`): si
    devolviera un objeto prefabricado, (5) estaría afirmando algo sobre el fake.
  · Hay un tipo DESACTIVADO con una ausencia colgando: sin esa fila, (6) no podría distinguir
    "no rompe" de "no había nada que romper".
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from uuid import UUID, uuid4

import pytest

from schemas.ausencias import AusenciaResponse, TipoAusenciaCreate, TipoAusenciaResponse
from schemas.configuracion import TipoAusenciaUpdate
from services._tipos_jerarquia import ensure_no_ciclo_tipo, ensure_padre_valido
from services.ausencias_service import AusenciasService
from services.tipos_ausencia_service import TiposAusenciaService
from utils.errors import AppError

EMPRESA = uuid4()
PADRE, HIJO, OTRO, NIETO = (str(UUID(int=i)) for i in range(1, 5))


def _ausencia(id_: str, tipo_id: str) -> AusenciaResponse:
    """Una ausencia mínima válida. `_ausencia("a1", PADRE)` es el caso que (k) habilita: cargar
    contra un tipo padre QUE TIENE HIJOS — porque no toda enfermedad familiar tiene subtipo, y
    forzar la hoja obligaría a crear un "Otro" debajo de cada padre."""
    return AusenciaResponse.model_validate({
        "id": id_, "empleado_id": "11111111-1111-1111-1111-111111111111",
        "empresa_id": str(EMPRESA), "tipo_id": tipo_id,
        "fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-02", "dias": 2,
        "justificada": True, "created_at": "2026-01-01T00:00:00Z"})


def _fila(id_: str, nombre: str, padre_id=None, activo: bool = True,
          cuenta: bool = True, empresa_id=None) -> dict:
    return {"id": id_, "nombre": nombre, "es_base": False, "activo": activo,
            "empresa_id": empresa_id, "cuenta_ausentismo": cuenta, "padre_id": padre_id,
            "padre_nombre": None}


class _TiposRepo:
    """Catálogo fake. `ids_de_familia` resuelve los hijos DE VERDAD — sin eso, el test del
    filtro por padre no podría fallar."""

    def __init__(self, filas: dict) -> None:
        self.filas = dict(filas)
        self.creados: list = []

    def find_by_id(self, tipo_id):
        return self.filas.get(str(tipo_id))

    def find_all(self, empresa_id=None, incluir_inactivos=False):
        return [TipoAusenciaResponse.model_validate(f) for f in self.filas.values()
                if incluir_inactivos or f["activo"]]

    def ids_de_familia(self, tipo_id):
        tipo_id = str(tipo_id)
        return [tipo_id, *[f["id"] for f in self.filas.values()
                           if str(f.get("padre_id") or "") == tipo_id]]

    def create(self, nombre, empresa_id=None, padre_id=None, cuenta_ausentismo=None):
        fila = _fila(f"nuevo-{nombre}", nombre, str(padre_id) if padre_id else None,
                     cuenta=True if cuenta_ausentismo is None else cuenta_ausentismo,
                     empresa_id=empresa_id)
        self.creados.append((nombre, padre_id, cuenta_ausentismo))
        self.filas[fila["id"]] = fila
        return TipoAusenciaResponse.model_validate(fila)

    def update(self, tipo_id, cambios):
        self.filas[str(tipo_id)].update(cambios)
        return TipoAusenciaResponse.model_validate(self.filas[str(tipo_id)])


def _catalogo() -> _TiposRepo:
    return _TiposRepo({
        PADRE: _fila(PADRE, "Enfermedad familiar"),
        HIJO: _fila(HIJO, "Madre/padre", padre_id=PADRE),
        OTRO: _fila(OTRO, "Personal"),
    })


# ── 1. 🔴 Profundidad máxima 2 ────────────────────────────────────────────────

class TestProfundidadMaxima2:
    def test_un_subtipo_de_un_subtipo_se_rechaza(self) -> None:
        """🔴 EL CASO CENTRAL. Para que falle: borrar el `if padre.get("padre_id")` de
        `ensure_padre_valido`. El árbol de profundidad libre volvería a ser posible y con él la
        UI de árbol que la decisión de producto descartó."""
        with pytest.raises(AppError) as exc:
            ensure_padre_valido(_catalogo(), HIJO)
        assert exc.value.code == "TIPO_JERARQUIA_PROFUNDA" and exc.value.status_code == 422

    def test_colgar_de_un_padre_de_primer_nivel_SI_se_permite(self) -> None:
        """El contrapeso: si esto fallara, no se podría crear ningún subtipo."""
        padre = ensure_padre_valido(_catalogo(), PADRE)
        assert padre is not None and padre["nombre"] == "Enfermedad familiar"

    def test_sin_padre_no_valida_nada(self) -> None:
        """`padre_id=None` es un tipo de primer nivel: el caso normal, sin consultas."""
        assert ensure_padre_valido(_catalogo(), None) is None

    def test_un_padre_inexistente_es_404(self) -> None:
        with pytest.raises(AppError) as exc:
            ensure_padre_valido(_catalogo(), str(uuid4()))
        assert exc.value.code == "TIPO_PADRE_NOT_FOUND" and exc.value.status_code == 404

    def test_un_tipo_no_puede_ser_su_propio_padre(self) -> None:
        with pytest.raises(AppError) as exc:
            ensure_padre_valido(_catalogo(), PADRE, PADRE)
        assert exc.value.code == "TIPO_PADRE_ES_SI_MISMO"

    def test_el_service_aplica_la_guarda_al_crear(self) -> None:
        """La guarda tiene que estar en el CAMINO REAL, no solo disponible."""
        repo = _catalogo()
        with pytest.raises(AppError) as exc:
            TiposAusenciaService(repo=repo).create_tipo(
                TipoAusenciaCreate(nombre="Nieto", padre_id=UUID(HIJO)), EMPRESA)
        assert exc.value.code == "TIPO_JERARQUIA_PROFUNDA"
        assert repo.creados == [], "se creó el tipo pese a la guarda"


# ── 2. Anti-ciclos ────────────────────────────────────────────────────────────

class TestAntiCiclos:
    def test_un_ciclo_directo_se_detecta(self) -> None:
        """PADRE pasaría a ser hijo de HIJO, que ya es hijo de PADRE."""
        with pytest.raises(AppError) as exc:
            ensure_no_ciclo_tipo(_catalogo(), PADRE, HIJO)
        assert exc.value.code == "TIPO_CICLO" and exc.value.status_code == 400

    def test_una_cadena_sin_ciclo_no_molesta(self) -> None:
        """El contrapeso: que la guarda exista no puede volver circular a todo."""
        ensure_no_ciclo_tipo(_catalogo(), OTRO, PADRE)

    def test_sin_padre_no_recorre_nada(self) -> None:
        ensure_no_ciclo_tipo(_catalogo(), PADRE, None)

    def test_una_cadena_corrupta_no_cuelga(self) -> None:
        """🔴 Dato ya roto (un nieto escrito a mano en la base, que el CHECK no puede impedir):
        el recorrido tiene que cortar por `max_saltos`, no entrar en un bucle infinito."""
        repo = _TiposRepo({PADRE: _fila(PADRE, "A", padre_id=HIJO),
                           HIJO: _fila(HIJO, "B", padre_id=PADRE)})
        with pytest.raises(AppError) as exc:
            ensure_no_ciclo_tipo(repo, OTRO, PADRE, max_saltos=5)
        assert exc.value.code == "TIPO_CICLO"


# ── 3 y 4. 🔴 El filtro por familia, y la paridad listado ↔ export ────────────

class _AusRepo:
    """CAPTURA los `tipo_ids` recibidos y filtra con ellos. Un fake que los ignorara dejaría
    pasar el `.eq()` viejo sin que ningún test se entere."""

    def __init__(self) -> None:
        self.recibidos: list = []
        # Se usa el schema REAL y no un SimpleNamespace: el service arma un
        # AusenciaListResponse, así que un doble suelto ni siquiera llegaría a la aserción.
        self._filas = [_ausencia("a1", PADRE),   # cargada directo al PADRE (se permite, ver (k))
                       _ausencia("a2", HIJO),    # cargada al hijo
                       _ausencia("a3", OTRO)]    # otro tipo

    def find_all(self, empresa_id=None, empleado_ids=None, tipo_ids=None, page=1,
                 page_size=20, *, desde=None, hasta=None):
        self.recibidos.append(tipo_ids)
        filas = ([f for f in self._filas if f.tipo_id in set(tipo_ids)] if tipo_ids
                 else list(self._filas))
        return filas, len(filas)


class _Ownership:
    def find_by_user_id(self, user_id):
        return None

    def ids_subordinados(self, emp_id):
        return []


def _svc(aus: _AusRepo, tipos: _TiposRepo) -> AusenciasService:
    return AusenciasService(repo=aus, ownership_repo=_Ownership(), tipos_repo=tipos)


def _ids(pagina) -> set:
    return {i.id for i in pagina.items}


class TestFiltroPorFamilia:
    def test_filtrar_por_el_PADRE_trae_las_de_sus_hijos(self) -> None:
        """🔴 EL CAMBIO DE FONDO. Con el `.eq("tipo_id")` viejo esto devolvía CERO: las ausencias
        apuntan a la hoja, nunca al padre. Sin error y sin aviso."""
        aus, tipos = _AusRepo(), _catalogo()
        pagina = _svc(aus, tipos).get_all("u", "admin_rrhh", tipo_id=UUID(PADRE))
        assert _ids(pagina) == {"a1", "a2"}
        assert set(aus.recibidos[0]) == {PADRE, HIJO}, "no se resolvió la familia"

    def test_filtrar_por_un_HIJO_trae_solo_las_suyas(self) -> None:
        """Un hijo no tiene hijos (profundidad 2): la familia es él solo."""
        aus, tipos = _AusRepo(), _catalogo()
        pagina = _svc(aus, tipos).get_all("u", "admin_rrhh", tipo_id=UUID(HIJO))
        assert _ids(pagina) == {"a2"} and aus.recibidos[0] == [HIJO]

    def test_un_padre_SIN_hijos_se_comporta_como_antes(self) -> None:
        aus, tipos = _AusRepo(), _catalogo()
        pagina = _svc(aus, tipos).get_all("u", "admin_rrhh", tipo_id=UUID(OTRO))
        assert _ids(pagina) == {"a3"} and aus.recibidos[0] == [OTRO]

    def test_sin_filtro_de_tipo_no_se_consulta_la_familia(self) -> None:
        """El contrapeso: el caso normal no puede pagar una query de más."""
        aus, tipos = _AusRepo(), _catalogo()
        pagina = _svc(aus, tipos).get_all("u", "admin_rrhh")
        assert len(pagina.items) == 3 and aus.recibidos[0] is None


def test_el_export_devuelve_el_MISMO_conjunto_que_el_listado() -> None:
    """🔴 La invariante 1 del bloque B: si el filtro afecta al export, va server-side y con UNA
    sola implementación. Acá se verifica el efecto: mismo filtro, mismo conjunto de ausencias.

    Para que falle: resolver la familia dentro de `get_all` pero no en el camino del export —
    o sea, duplicar la resolución en vez de que el export delegue en `get_all`."""
    aus, tipos = _AusRepo(), _catalogo()
    svc = _svc(aus, tipos)
    listado = svc.get_all("u", "admin_rrhh", tipo_id=UUID(PADRE))
    svc.exportar("u", "admin_rrhh", tipo_id=UUID(PADRE), formato="csv")
    # El export llama a get_all con los mismos filtros: los tipo_ids resueltos tienen que coincidir.
    assert aus.recibidos[0] == aus.recibidos[1]
    assert _ids(listado) == {"a1", "a2"}


# ── 5. cuenta_ausentismo: default de alta, NO herencia ────────────────────────

class TestCuentaAusentismo:
    def test_un_subtipo_nace_con_el_valor_del_padre(self) -> None:
        repo = _TiposRepo({PADRE: _fila(PADRE, "Licencia", cuenta=False)})
        TiposAusenciaService(repo=repo).create_tipo(
            TipoAusenciaCreate(nombre="Maternidad", padre_id=UUID(PADRE)), EMPRESA)
        assert repo.creados[0][2] is False, "el subtipo no se precargó con el valor del padre"

    def test_un_tipo_de_primer_nivel_deja_el_default_de_la_tabla(self) -> None:
        repo = _catalogo()
        TiposAusenciaService(repo=repo).create_tipo(TipoAusenciaCreate(nombre="Nuevo"), EMPRESA)
        assert repo.creados[0][2] is None, "se forzó un valor donde debía regir el default"

    def test_despues_el_hijo_es_INDEPENDIENTE_del_padre(self) -> None:
        """🔴 Es un DEFAULT, no una herencia: editar el padre NO toca al hijo. Si fuera herencia,
        habría dos fuentes para el mismo hecho y el conflicto no tendría respuesta correcta."""
        repo = _catalogo()
        svc = TiposAusenciaService(repo=repo)
        svc.update_tipo(UUID(PADRE), TipoAusenciaUpdate(cuenta_ausentismo=False), None)
        assert repo.filas[HIJO]["cuenta_ausentismo"] is True, "el hijo siguió al padre"

    def test_y_el_hijo_puede_diferir_del_padre(self) -> None:
        repo = _catalogo()
        svc = TiposAusenciaService(repo=repo)
        svc.update_tipo(UUID(HIJO), TipoAusenciaUpdate(cuenta_ausentismo=False), None)
        assert repo.filas[HIJO]["cuenta_ausentismo"] is False
        assert repo.filas[PADRE]["cuenta_ausentismo"] is True


# ── 6. Un tipo desactivado ────────────────────────────────────────────────────

class TestTipoDesactivado:
    def test_no_aparece_en_los_selects(self) -> None:
        """`incluir_inactivos=False` es el default justamente porque el consumidor normal es el
        select del formulario, que no debe ofrecer un tipo dado de baja."""
        repo = _TiposRepo({PADRE: _fila(PADRE, "Vigente"),
                           OTRO: _fila(OTRO, "Injustificada", activo=False)})
        nombres = {t.nombre for t in TiposAusenciaService(repo=repo).get_tipos().items}
        assert nombres == {"Vigente"}

    def test_pero_SI_aparece_en_configuracion(self) -> None:
        """Ahí hay que verlos para poder reactivarlos."""
        repo = _TiposRepo({PADRE: _fila(PADRE, "Vigente"),
                           OTRO: _fila(OTRO, "Injustificada", activo=False)})
        items = TiposAusenciaService(repo=repo).get_tipos(incluir_inactivos=True).items
        assert len(items) == 2

    def test_NO_rompe_las_ausencias_que_lo_usan(self) -> None:
        """🔴 Por esto se DESACTIVA y no se borra: `solicitudes_ausencia.tipo_id` es una FK sin
        ON DELETE. Las ausencias cargadas con "Injustificada" siguen listándose y mostrando su
        nombre. Para que falle: que el listado filtre por `activo` — no lo hace ni debe."""
        aus, tipos = _AusRepo(), _catalogo()
        tipos.filas[OTRO]["activo"] = False
        pagina = _svc(aus, tipos).get_all("u", "admin_rrhh", tipo_id=UUID(OTRO))
        assert _ids(pagina) == {"a3"}, "una ausencia desapareció al desactivar su tipo"
