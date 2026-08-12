"""
Módulo de objetivos: el comportamiento que hoy NO tenía ninguna red.

🔴 POR QUÉ EXISTE ESTE ARCHIVO. Viene un rediseño del modelo (jerarquía + múltiples
responsables) y el módulo tenía CERO tests propios: nada probaba `cambiar_estado`,
`_validate_responsable`, el filtro combinado ni el 404. Lo único que lo tocaba era cobertura de
barrido (el límite de export, la franja de rate limit, la paridad list↔export y la limpieza de
columnas), que no mira ni una regla de negocio. Estos tests describen lo que el código hace HOY
—no lo que va a hacer— para que el rediseño tenga contra qué chocar.

🔴 SE PRUEBA EN DOS PLANOS, y no es redundancia:

  · **Service, con un repo falso** — las reglas de negocio: validación del responsable, el 404,
    la barrera de empresa, qué filtros se le pasan al repo.
  · **Repo, con el CLIENTE de Supabase falseado** — lo que tiene que viajar EN LA QUERY: los
    `.eq()` de cada filtro y el `.order()`. Un fake de repo que filtre y ordene en Python fija
    el contrato pero NO toca la query real: sacarle el `.order("fecha_entrega")` dejaría todo
    en verde. Es el caso #3 de la regla del repo, y el molde es
    `test_historial_salarial.py::TestElOrdenLoPoneLaQuery`.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL REPO FALSO FILTRA DE VERDAD, sobre 4 objetivos repartidos en 2 empresas, 2
     responsables, 3 estados y 2 prioridades, y NINGÚN filtro devuelve el total. Un repo que
     aceptara los parámetros y devolviera siempre los 4 —el caso #1 de la regla del repo— haría
     que "el filtro llegó" y "el filtro se perdió" dieran el mismo resultado.
  2. 🔴 HAY DOS EMPRESAS y `find_by_id` devuelve None cuando la empresa no coincide. Con una
     sola, la barrera de empresa no se puede verificar: todo pasaría igual.
  3. 🔴 LA TABLA `users` FALSA TIENE TRES RESPUESTAS DISTINTAS —activo, inactivo y desconocido—.
     Con un solo usuario activo, las dos ramas de error de `_validate_responsable`
     (RESPONSABLE_NO_ACTIVO y RESPONSABLE_NO_VALIDO) serían indistinguibles y borrar cualquiera
     de las dos quedaría en verde.
  4. 🔴 EL FAKE DE ESCRITURA CONSTRUYE LA RESPUESTA A PARTIR DE LO QUE RECIBE (`save`, `update`,
     `set_estado`). Devolver un objeto prefabricado haría que el test afirme algo sobre su
     propia constante en vez de sobre el código.
  5. El espía del cliente de Supabase registra los `.eq()` y los `.order()` con sus argumentos:
     así se puede afirmar QUÉ viajó a la base, no solo qué devolvió el repo.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from datetime import date, datetime  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

import services.objetivo_service as svc_mod  # noqa: E402
from repositories._objetivos_arbol import armar_arbol, contar_con_hijos  # noqa: E402
from schemas.objetivo import (  # noqa: E402
    CambiarEstadoRequest, ObjetivoCreate, ObjetivoResponse, ObjetivoUpdate, ResponsableItem,
)
from services._objetivos_export import construir_filas_export  # noqa: E402
from services.objetivo_service import ObjetivoService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A = uuid4()
EMPRESA_B = uuid4()
USER_ACTIVO = str(uuid4())
USER_INACTIVO = str(uuid4())
USER_FANTASMA = str(uuid4())   # no existe en `users`

# 🔴 Punto 3 del encabezado: tres respuestas distintas. Sin el inactivo y sin el fantasma, las
# dos ramas de error de _validate_responsable son indistinguibles.
_USERS = {
    USER_ACTIVO:   {"activo": True},
    USER_INACTIVO: {"activo": False},
}


def _obj(titulo: str, empresa, responsable: str, estado: str, prioridad: str,
         fecha, parent=None, resp_extra=None, parent_titulo=None) -> ObjetivoResponse:
    """`parent_titulo` va explícito porque en producción lo resuelve `_objetivo_row._build` con
    un lookup batch: es un DERIVADO de otra fila, no una columna. Sin modelarlo acá, el test de
    la columna "Objetivo padre" del export no tendría contra qué comparar."""
    nombre = "Ana Gómez" if responsable == USER_ACTIVO else "Beto Pérez"
    return ObjetivoResponse(
        id=str(uuid4()), empresa_id=str(empresa), empresa_nombre="Karstec",
        responsable_id=responsable, responsable_nombre=nombre,
        titulo=titulo, descripcion=None, prioridad=prioridad, estado=estado,
        fecha_entrega=fecha, created_at=datetime(2026, 1, 5, 9, 0, 0),
        updated_at=datetime(2026, 2, 1, 12, 0, 0),
        parent_id=parent, parent_titulo=parent_titulo,
        responsables=[ResponsableItem(id=responsable, nombre=nombre),
                      *[ResponsableItem(id=u, nombre="Beto Pérez") for u in (resp_extra or [])]],
    )


# 🔴 Punto 1 + jerarquía real: UN PADRE CON DOS HIJOS y DOS RAÍCES SUELTAS, en 2 empresas, 2
# responsables, 3 estados y 2 prioridades. Sin un padre con hijos de verdad en el fake, "cuenta
# solo raíces" y "cuenta todo" darían el MISMO número y las dos serían indistinguibles.
_PADRE = _obj("Migrar nómina", EMPRESA_A, USER_ACTIVO, "por_hacer", "alta", date(2026, 6, 30))
_HIJO_1 = _obj("Relevar proveedores", EMPRESA_A, USER_INACTIVO, "haciendo", "media",
               date(2026, 3, 15), parent=_PADRE.id, parent_titulo=_PADRE.titulo)
_HIJO_2 = _obj("Validar con contable", EMPRESA_A, USER_ACTIVO, "terminado", "media",
               date(2026, 9, 1), parent=_PADRE.id, parent_titulo=_PADRE.titulo)
_RAIZ_A = _obj("Auditar licencias", EMPRESA_A, USER_ACTIVO, "terminado", "media", date(2026, 5, 1))
_RAIZ_B = _obj("Onboarding DOSUBA", EMPRESA_B, USER_ACTIVO, "por_hacer", "alta", None)

# 5 filas planas: 3 raíces (_PADRE, _RAIZ_A, _RAIZ_B) + 2 hijos.
_CATALOGO = [_HIJO_1, _RAIZ_A, _PADRE, _HIJO_2, _RAIZ_B]


class _Repo:
    """🔴 FILTRA DE VERDAD (punto 1), HONRA `empresa_id` (punto 2) y **ARMA EL ÁRBOL CON EL
    MISMO CÓDIGO QUE PRODUCCIÓN**.

    Ese último punto es nuevo y es el que más importa: `find_all` real devuelve RAÍCES con sus
    hijos anidados, no una lista plana. Un fake que siguiera devolviendo plano haría que todo
    test sobre conteos, kanban o export midiera una forma que el código ya no produce — y
    "cuenta raíces" y "cuenta todo" volverían a ser indistinguibles. Por eso llama a
    `armar_arbol`, la misma función del repo, en vez de reimplementar el anidado.

    🔴 EL FILTRO POR RESPONSABLE MIRA LA PUENTE, como el real: un objetivo donde el usuario es
    responsable-acompañante (y NO dueño) tiene que aparecer. Con un fake que solo mirara
    `responsable_id`, borrar la puente del código quedaría en verde.
    """

    def __init__(self, filas=None) -> None:
        self.llamadas: list[dict] = []
        self.escrituras: list[dict] = []
        self._filas = list(_CATALOGO if filas is None else filas)

    def _plano(self, empresa_id=None, estado=None, responsable_id=None, prioridad=None):
        return [
            o for o in self._filas
            if (empresa_id is None or o.empresa_id == str(empresa_id))
            and (estado is None or o.estado == estado)
            and (responsable_id is None
                 or responsable_id in [r.id for r in o.responsables]
                 or o.responsable_id == responsable_id)
            and (prioridad is None or o.prioridad == prioridad)
        ]

    def find_all(self, empresa_id=None, estado=None, responsable_id=None, prioridad=None):
        self.llamadas.append({"empresa_id": empresa_id, "estado": estado,
                              "responsable_id": responsable_id, "prioridad": prioridad})
        planas = [o.model_copy(update={"hijos": []})
                  for o in self._plano(empresa_id, estado, responsable_id, prioridad)]
        return armar_arbol(planas)

    def tiene_hijos(self, id, empresa_id=None) -> bool:
        return any(o.parent_id == id for o in self._filas)

    def find_by_id(self, id, empresa_id=None):
        for o in self._filas:
            if o.id == id and (empresa_id is None or o.empresa_id == str(empresa_id)):
                return o
        return None

    def save(self, data: ObjetivoCreate) -> ObjetivoResponse:
        """Construye la respuesta A PARTIR de lo recibido (punto 4), nunca prefabricada."""
        self.escrituras.append({"op": "save", "data": data})
        return _obj(data.titulo, data.empresa_id, str(data.responsable_id),
                    "por_hacer", data.prioridad, data.fecha_entrega)

    def update(self, id, data: ObjetivoUpdate, empresa_id=None):
        self.escrituras.append({"op": "update", "id": id, "data": data, "empresa_id": empresa_id})
        prev = self.find_by_id(id, empresa_id)
        if not prev:
            return None
        patch = data.model_dump(exclude_none=True)
        if "responsable_id" in patch:
            patch["responsable_id"] = str(patch["responsable_id"])
        return prev.model_copy(update=patch)

    def set_estado(self, id, estado, empresa_id=None):
        self.escrituras.append({"op": "set_estado", "id": id, "estado": estado,
                                "empresa_id": empresa_id})
        prev = self.find_by_id(id, empresa_id)
        return prev.model_copy(update={"estado": estado}) if prev else None

    def delete(self, id, empresa_id=None) -> bool:
        """🔴 MODELA EL `ON DELETE CASCADE` de la migración 095: borrar un padre se lleva a sus
        hijos. Sin esto, el test del cascade estaría verificando el fake y no la base — pero al
        menos deja explícito qué contrato asume el código sobre la FK."""
        self.escrituras.append({"op": "delete", "id": id, "empresa_id": empresa_id})
        antes = len(self._filas)
        objetivo = self.find_by_id(id, empresa_id)
        if objetivo:
            muertos = {id, *(o.id for o in self._filas if o.parent_id == id)}
            self._filas = [o for o in self._filas if o.id not in muertos]
        return len(self._filas) < antes


class _UsersFake:
    """La tabla `users` como la consulta `_validate_responsable`: select→eq→limit→execute.

    🔴 Devuelve TRES cosas distintas según el id (punto 3): la fila de un activo, la de un
    inactivo, y None para un id que no existe.

    ⚠️ **Desde la sesión 0.9 el service NO llega a `users` por `supabase_admin` directo**: pasa
    por `UsuarioRepo.get_estado`, que delega en `_usuario_lookup_repo`. Se faltea AHÍ, que es
    donde quedó la query. La forma cambió con la mudanza —`maybe_single()` devolvía un dict,
    `limit(1)` devuelve una lista— y este fake la sigue: el repo ya usaba `limit(1)` en sus
    otros tres lookups, así que la query se alineó con sus hermanas en vez de al revés.
    Las dos aserciones que este doble sostiene NO cambiaron: que la tabla sea `users` y a qué
    id se consultó.
    """

    def __init__(self) -> None:
        self.consultas: list[str] = []
        self._id = None

    def table(self, nombre: str):
        assert nombre == "users", f"_validate_responsable consultó {nombre!r}, no users"
        return self

    def select(self, *a, **k):
        return self

    def eq(self, col: str, val: str):
        self._id = val
        self.consultas.append(val)
        return self

    def limit(self, n: int):
        return self

    def execute(self):
        fila = _USERS.get(self._id)
        return SimpleNamespace(data=[fila] if fila else [])


@pytest.fixture
def users(monkeypatch) -> _UsersFake:
    """Evita la red en `_validate_responsable` y deja afirmar a QUIÉN se consultó."""
    fake = _UsersFake()
    import repositories._usuario_lookup_repo as lookup_mod
    monkeypatch.setattr(lookup_mod, "supabase_admin", fake)
    return fake


def _svc(filas=None):
    repo = _Repo(filas)
    return ObjetivoService(repo=repo), repo


def _create(**kw) -> ObjetivoCreate:
    base = dict(empresa_id=EMPRESA_A, responsable_id=UUID(USER_ACTIVO), titulo="Nuevo objetivo",
                descripcion=None, prioridad="media", fecha_entrega=date(2026, 12, 1))
    return ObjetivoCreate(**{**base, **kw})


# ── 0. Los guardianes del fake ────────────────────────────────────────────────

def test_el_repo_falso_filtra_y_ningun_filtro_devuelve_el_total() -> None:
    """Sin esto, todo lo de abajo pasa a ser decorativo: un repo que ignore los parámetros
    hace que "filtró" y "no filtró" den el mismo resultado.

    ⚠️ Los números son RAÍCES, no filas: desde la jerarquía `find_all` devuelve el árbol."""
    repo = _Repo()
    assert len(repo.find_all()) == 3                                   # 5 filas, 3 raíces
    assert len(repo.find_all(empresa_id=EMPRESA_A)) == 2
    assert len(repo.find_all(estado="por_hacer")) == 2
    assert len(repo.find_all(responsable_id=USER_ACTIVO)) == 3
    assert len(repo.find_all(prioridad="alta")) == 2
    assert len(repo.find_all(empresa_id=EMPRESA_A, estado="por_hacer")) == 1


def test_el_fake_tiene_un_padre_con_dos_hijos_y_dos_raices_sueltas() -> None:
    """🔴 Sin jerarquía real en el fake, "cuenta solo raíces" y "cuenta todo" son el mismo
    número, y los tests de procesos, del reporte anual y del kanban no prueban nada."""
    assert [o.parent_id for o in _CATALOGO].count(_PADRE.id) == 2
    assert _RAIZ_A.parent_id is None and _RAIZ_B.parent_id is None
    raices = _Repo().find_all()
    assert sorted(len(r.hijos) for r in raices) == [0, 0, 2]
    assert contar_con_hijos(raices) == 5


def test_la_tabla_users_falsa_tiene_las_tres_respuestas() -> None:
    """Activo, inactivo y desconocido. Con una sola, las dos ramas de error son iguales."""
    assert _USERS[USER_ACTIVO]["activo"] is True
    assert _USERS[USER_INACTIVO]["activo"] is False
    assert USER_FANTASMA not in _USERS


# ── 1. create: la validación del responsable ──────────────────────────────────

class TestCreate:

    def test_crea_con_un_responsable_activo(self, users) -> None:
        svc, repo = _svc()

        row = svc.create(_create(), "operador-1")

        assert row.titulo == "Nuevo objetivo"
        assert repo.escrituras[0]["op"] == "save"

    def test_consulta_el_responsable_contra_users(self, users) -> None:
        """🔴 La validación pega a `users`, NO a `empleados`: este tablero es de tareas del
        equipo de RRHH. Si mañana se mudara a empleados, este test rojea."""
        svc, _ = _svc()

        svc.create(_create(), "operador-1")

        assert users.consultas == [USER_ACTIVO]

    def test_un_responsable_INACTIVO_se_rechaza(self, users) -> None:
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(responsable_id=UUID(USER_INACTIVO)), "operador-1")

        assert exc.value.code == "RESPONSABLE_NO_ACTIVO"
        assert exc.value.status_code == 422

    def test_un_responsable_INEXISTENTE_se_rechaza_con_OTRO_code(self, users) -> None:
        """Los dos codes son distintos a propósito: acá no hay oráculo de enumeración que
        cuidar —los usuarios del sistema son 4 y todos se ven en el selector—, así que decir
        cuál de las dos cosas pasó es información útil, no una fuga."""
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(responsable_id=UUID(USER_FANTASMA)), "operador-1")

        assert exc.value.code == "RESPONSABLE_NO_VALIDO"
        assert exc.value.status_code == 422

    def test_no_escribe_nada_si_el_responsable_no_valida(self, users) -> None:
        """🔴 El gate va ANTES del insert. Si fuera después, quedaría un objetivo huérfano."""
        svc, repo = _svc()

        with pytest.raises(AppError):
            svc.create(_create(responsable_id=UUID(USER_INACTIVO)), "operador-1")

        assert repo.escrituras == []

    def test_titulo_vacio_se_rechaza_antes_de_consultar_users(self, users) -> None:
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(titulo="   "), "operador-1")

        assert exc.value.code == "TITULO_REQUERIDO"
        assert users.consultas == [] and repo.escrituras == []

    def test_prioridad_invalida_se_rechaza(self, users) -> None:
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(prioridad="urgentisima"), "operador-1")

        assert exc.value.code == "PRIORIDAD_INVALIDA"


# ── 2. update: revalida el responsable SOLO si viene ──────────────────────────

class TestUpdate:

    def test_revalida_el_responsable_si_viene(self, users) -> None:
        svc, _ = _svc()
        objetivo = _RAIZ_A

        svc.update(UUID(objetivo.id), ObjetivoUpdate(responsable_id=UUID(USER_ACTIVO)), EMPRESA_A)

        assert users.consultas == [USER_ACTIVO]

    def test_NO_consulta_users_si_no_viene_el_responsable(self, users) -> None:
        """Contrapeso del de arriba: sin esto, un `_validate_responsable` llamado siempre
        pasaría igual — y encima cobraría una consulta por cada edición de título."""
        svc, _ = _svc()
        objetivo = _RAIZ_A

        svc.update(UUID(objetivo.id), ObjetivoUpdate(titulo="Otro título"), EMPRESA_A)

        assert users.consultas == []

    def test_un_responsable_inactivo_rechaza_la_edicion(self, users) -> None:
        svc, repo = _svc()
        objetivo = _RAIZ_A

        with pytest.raises(AppError) as exc:
            svc.update(UUID(objetivo.id), ObjetivoUpdate(responsable_id=UUID(USER_INACTIVO)), EMPRESA_A)

        assert exc.value.code == "RESPONSABLE_NO_ACTIVO"
        assert [e["op"] for e in repo.escrituras] == []   # no escribió

    def test_un_objetivo_de_otra_empresa_da_404(self, users) -> None:
        """La barrera de empresa: el objetivo existe, pero no en la empresa del request."""
        svc, _ = _svc()
        de_empresa_b = _RAIZ_B

        with pytest.raises(AppError) as exc:
            svc.update(UUID(de_empresa_b.id), ObjetivoUpdate(titulo="X"), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_NOT_FOUND"
        assert exc.value.status_code == 404

    def test_el_titulo_editado_llega_al_repo(self, users) -> None:
        svc, repo = _svc()
        objetivo = _RAIZ_A

        row = svc.update(UUID(objetivo.id), ObjetivoUpdate(titulo="Título nuevo"), EMPRESA_A)

        assert row.titulo == "Título nuevo"
        assert repo.escrituras[0]["data"].titulo == "Título nuevo"


# ── 3. cambiar_estado: el kanban ──────────────────────────────────────────────

class TestCambiarEstado:

    @pytest.mark.parametrize("estado", ["por_hacer", "haciendo", "terminado"])
    def test_mueve_a_cualquiera_de_los_tres_estados(self, estado: str) -> None:
        svc, repo = _svc()
        objetivo = _RAIZ_A

        row = svc.cambiar_estado(UUID(objetivo.id), CambiarEstadoRequest(estado=estado), EMPRESA_A)

        assert row.estado == estado
        assert repo.escrituras[0] == {"op": "set_estado", "id": objetivo.id,
                                      "estado": estado, "empresa_id": EMPRESA_A}

    def test_un_estado_fuera_del_CHECK_se_rechaza(self) -> None:
        """🔴 Los tres valores son un CHECK en la base: si el service dejara pasar otro, el
        error saldría como un 500 de Postgres en vez de un 422 con mensaje."""
        svc, repo = _svc()
        objetivo = _RAIZ_A

        with pytest.raises(AppError) as exc:
            svc.cambiar_estado(UUID(objetivo.id), CambiarEstadoRequest(estado="archivado"), EMPRESA_A)

        assert exc.value.code == "ESTADO_INVALIDO"
        assert exc.value.status_code == 422
        assert repo.escrituras == []

    def test_el_estado_se_valida_ANTES_de_buscar_el_objetivo(self) -> None:
        """Un estado inválido sobre un id inexistente da ESTADO_INVALIDO, no 404: el orden de
        los dos chequeos está fijado acá porque el rediseño lo va a tocar."""
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.cambiar_estado(uuid4(), CambiarEstadoRequest(estado="archivado"), EMPRESA_A)

        assert exc.value.code == "ESTADO_INVALIDO"

    def test_un_objetivo_inexistente_da_404(self) -> None:
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.cambiar_estado(uuid4(), CambiarEstadoRequest(estado="haciendo"), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_NOT_FOUND"

    def test_un_objetivo_de_otra_empresa_da_el_MISMO_404(self) -> None:
        """🔴 Mismo code y mismo status que "no existe" — nunca un 403. Un status distinto
        confirmaría que el objetivo existe y es de otra empresa."""
        svc, _ = _svc()
        de_empresa_b = _RAIZ_B

        with pytest.raises(AppError) as exc:
            svc.cambiar_estado(UUID(de_empresa_b.id), CambiarEstadoRequest(estado="haciendo"), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_NOT_FOUND"
        assert exc.value.status_code == 404


# ── 4. delete ─────────────────────────────────────────────────────────────────

class TestDelete:

    def test_borra_el_objetivo(self) -> None:
        svc, repo = _svc()
        objetivo = _RAIZ_A

        svc.delete(UUID(objetivo.id), EMPRESA_A)

        assert repo.escrituras[0]["op"] == "delete"
        assert repo.find_by_id(objetivo.id) is None

    def test_un_id_inexistente_da_404_y_no_borra_nada(self) -> None:
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.delete(uuid4(), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_NOT_FOUND"
        assert repo.escrituras == []

    def test_un_objetivo_de_otra_empresa_NO_se_borra(self) -> None:
        """🔴 La barrera de empresa sobre una operación destructiva. El objetivo de la empresa
        B existe: si la barrera no estuviera, este delete se ejecutaría sobre él."""
        svc, repo = _svc()
        de_empresa_b = _RAIZ_B

        with pytest.raises(AppError) as exc:
            svc.delete(UUID(de_empresa_b.id), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_NOT_FOUND"
        assert repo.escrituras == []
        assert repo.find_by_id(de_empresa_b.id) is not None   # sigue vivo

    def test_la_empresa_viaja_al_repo_en_el_borrado(self) -> None:
        """No alcanza con que el service chequee: el DELETE tiene que llevar la empresa en su
        propio WHERE, o una carrera entre el chequeo y el borrado lo deja sin barrera."""
        svc, repo = _svc()
        objetivo = _RAIZ_A

        svc.delete(UUID(objetivo.id), EMPRESA_A)

        assert repo.escrituras[0]["empresa_id"] == EMPRESA_A


# ── 5. find_all: los tres filtros del listado y su composición ────────────────

class TestFiltrosDelListado:

    def test_sin_filtros_trae_todas_las_RAICES(self) -> None:
        """El total del listado cuenta raíces: los hijos viajan anidados dentro de su padre."""
        svc, _ = _svc()
        assert svc.get_all().total == 3

    @pytest.mark.parametrize("filtro,valor,esperado", [
        ("estado", "por_hacer", 2),
        ("estado", "terminado", 2),     # el hijo terminado se promueve: su padre no matchea
        ("estado", "haciendo", 1),
        ("responsable_id", USER_ACTIVO, 3),
        ("responsable_id", USER_INACTIVO, 1),
        ("prioridad", "alta", 2),
        ("prioridad", "media", 3),
    ])
    def test_cada_filtro_acota(self, filtro: str, valor: str, esperado: int) -> None:
        svc, _ = _svc()

        res = svc.get_all(**{filtro: valor})

        assert res.total == esperado, f"el filtro {filtro}={valor} no acotó"

    def test_los_filtros_se_componen_por_AND(self) -> None:
        """🔴 Cada uno por separado da 2 y 3; juntos tienen que dar 1. Si se compusieran por OR
        —o si uno se perdiera— el resultado sería 2, 3 o 4, nunca 1."""
        svc, _ = _svc()

        assert svc.get_all(estado="por_hacer").total == 2
        assert svc.get_all(responsable_id=USER_ACTIVO).total == 3
        assert svc.get_all(estado="por_hacer", responsable_id=USER_ACTIVO).total == 2
        assert svc.get_all(EMPRESA_A, "por_hacer", USER_ACTIVO, "alta").total == 1

    def test_los_cuatro_parametros_llegan_al_repo_en_orden(self) -> None:
        """El service recibe posicionales y los pasa posicionales: un cruce entre `estado` y
        `responsable_id` no daría error, daría el conjunto equivocado."""
        svc, repo = _svc()

        svc.get_all(EMPRESA_A, "haciendo", USER_INACTIVO, "media")

        assert repo.llamadas[0] == {"empresa_id": EMPRESA_A, "estado": "haciendo",
                                    "responsable_id": USER_INACTIVO, "prioridad": "media"}

    def test_en_consolidado_la_empresa_viaja_como_None(self) -> None:
        svc, repo = _svc()

        svc.get_all(None, "por_hacer")

        assert repo.llamadas[0]["empresa_id"] is None
        assert svc.get_all(None, "por_hacer").total == 2   # las dos empresas

    def test_un_filtro_sin_resultados_da_lista_vacia_no_error(self) -> None:
        svc, _ = _svc()

        res = svc.get_all(EMPRESA_B, "terminado")

        assert res.total == 0 and res.items == []


# ── 6. 🔴 Lo que tiene que viajar EN LA QUERY ─────────────────────────────────

class TestLaQueryDelRepo:
    """🔴 EL FAKE DE REPO NO ALCANZA PARA ESTO, y es exactamente lo que el rediseño va a tocar.

    El repo falso de arriba filtra y devuelve en el orden del catálogo: fija el CONTRATO, pero
    no toca la query real. Sacarle el `.order("fecha_entrega")` o un `.eq()` a
    `objetivo_repo.find_all` dejaría todo lo de arriba en verde. Acá se faltea un escalón más
    abajo —el cliente de Supabase— para verificar qué se le pidió a la base.

    Molde: `test_historial_salarial.py::TestElOrdenLoPoneLaQuery`.
    """

    def _repo_con_espia(self, monkeypatch, puente=None):
        """🔴 PARCHEA LOS TRES MÓDULOS QUE TOCAN LA BASE, no solo el repo.

        El filtro por responsable vive en `_objetivo_responsables` y `tiene_hijos` en
        `_objetivos_arbol`, y CADA UNO importa `supabase_admin` por su cuenta. Parchear solo
        `objetivo_repo` dejaba a esos dos pegándole a la red de verdad: el test no fallaba por
        una aserción, fallaba con ConnectError — que es un rojo que no dice nada. Pasó
        exactamente eso al mover el filtro a su satélite.
        """
        import repositories._objetivo_responsables as resp_mod
        import repositories._objetivos_arbol as arbol_mod
        import repositories.objetivo_repo as mod

        registro = {"eq": [], "order": [], "select": [], "or": [], "tablas": []}

        class _Q:
            def __init__(self, tabla):
                self._tabla = tabla
                registro["tablas"].append(tabla)

            def select(self, *a, **k):
                registro["select"].append(a[0] if a else None)
                return self

            def eq(self, col, val):
                registro["eq"].append((col, val))
                return self

            def or_(self, expr):
                registro["or"].append(expr)
                return self

            def in_(self, col, vals):
                return self

            def order(self, col, desc=False):
                registro["order"].append((col, desc))
                return self

            def limit(self, n):
                return self

            def maybe_single(self):
                return self

            def execute(self):
                # La puente devuelve lo que el test le pida; el resto, vacío.
                if self._tabla == "objetivo_responsables":
                    return SimpleNamespace(data=[{"objetivo_id": o} for o in (puente or [])],
                                           count=0)
                return SimpleNamespace(data=[], count=0)

        cliente = type("C", (), {"table": lambda s, t: _Q(t)})()
        for m in (mod, resp_mod, arbol_mod):
            monkeypatch.setattr(m, "supabase_admin", cliente)
        return mod.ObjetivoRepo(), registro

    def test_ordena_por_fecha_entrega_ASCENDENTE(self, monkeypatch) -> None:
        """🔴 ESTE TEST VA A ROJEAR CON LA JERARQUÍA, Y ESTÁ BIEN QUE LO HAGA.

        Hoy el listado sale por fecha de entrega ascendente: lo primero que vence, arriba. Con
        subobjetivos ese orden desarma el árbol —un hijo con fecha temprana saldría por encima
        de su padre—, así que va a haber que cambiarlo. Cuando eso pase, este test falla y
        obliga a decidir el orden nuevo a propósito, en vez de que se cambie de refilón."""
        repo, registro = self._repo_con_espia(monkeypatch)

        repo.find_all()

        assert registro["order"] == [("fecha_entrega", False)]

    def test_el_orden_va_en_la_QUERY_y_no_en_python(self, monkeypatch) -> None:
        """Ordenar en Python depende de haberse traído todas las filas: con paginación futura,
        el orden sería el de la página, no el del conjunto."""
        repo, registro = self._repo_con_espia(monkeypatch)

        repo.find_all(estado="haciendo")

        assert registro["order"], "el .order() desapareció de la query"

    @pytest.mark.parametrize("kwargs,esperado", [
        ({"empresa_id": EMPRESA_A}, ("empresa_id", str(EMPRESA_A))),
        ({"estado": "haciendo"}, ("estado", "haciendo")),
        ({"prioridad": "alta"}, ("prioridad", "alta")),
    ])
    def test_cada_filtro_viaja_como_un_eq_en_la_query(self, monkeypatch, kwargs, esperado) -> None:
        """`responsable_id` NO está acá: dejó de ser un `.eq()` al pasar por la puente. Su
        contrato nuevo se verifica en TestElFiltroPorResponsableUsaLaPuente."""
        repo, registro = self._repo_con_espia(monkeypatch)

        repo.find_all(**kwargs)

        assert esperado in registro["eq"]

    def test_sin_filtros_la_query_no_lleva_ningun_eq(self, monkeypatch) -> None:
        """Contrapeso: con `.eq()` incondicionales, el test de arriba pasaría igual."""
        repo, registro = self._repo_con_espia(monkeypatch)

        repo.find_all()

        assert registro["eq"] == []

    def test_los_cuatro_filtros_juntos_se_encadenan_en_la_query(self, monkeypatch) -> None:
        """La composición por AND del lado de la query. Ya no son cuatro `.eq()`: tres columnas
        planas más el predicado de responsable, que después de la puente es un `.or_()` (o un
        `.eq()` de dueño si la puente está vacía). El AND lo da el encadenado de PostgREST."""
        repo, registro = self._repo_con_espia(monkeypatch, puente=["obj-1"])

        repo.find_all(EMPRESA_A, "haciendo", USER_ACTIVO, "alta")

        planos = [e for e in registro["eq"] if e[0] in ("empresa_id", "estado", "prioridad")]
        assert len(planos) == 3
        assert len(registro["or"]) == 1

    def test_find_by_id_lleva_la_empresa_en_su_propio_WHERE(self, monkeypatch) -> None:
        """🔴 Forma A del patrón de barrera: el filtro va EN LA QUERY, no comparando en Python
        después de traer la fila. Así un id de otra empresa no vuelve nunca."""
        repo, registro = self._repo_con_espia(monkeypatch)

        repo.find_by_id("obj-1", EMPRESA_A)

        assert ("id", "obj-1") in registro["eq"]
        assert ("empresa_id", str(EMPRESA_A)) in registro["eq"]

    def test_find_by_id_en_consolidado_no_filtra_por_empresa(self, monkeypatch) -> None:
        """`empresa_id=None` es la vista consolidada: no restringe. No es un fallo de validación."""
        repo, registro = self._repo_con_espia(monkeypatch)

        repo.find_by_id("obj-1", None)

        assert registro["eq"] == [("id", "obj-1")]

    def test_el_delete_tambien_lleva_la_empresa(self, monkeypatch) -> None:
        import repositories.objetivo_repo as mod

        registro = {"eq": []}

        class _Q:
            def delete(self):
                return self

            def eq(self, col, val):
                registro["eq"].append((col, val))
                return self

            def execute(self):
                return SimpleNamespace(data=[])

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())

        mod.ObjetivoRepo().delete("obj-1", EMPRESA_A)

        assert ("empresa_id", str(EMPRESA_A)) in registro["eq"]


# ── 7. El export ──────────────────────────────────────────────────────────────

class TestExport:

    def test_usa_los_MISMOS_filtros_que_el_listado(self) -> None:
        svc, repo = _svc()

        svc.get_all(EMPRESA_A, "por_hacer", USER_ACTIVO, "alta")
        svc.exportar(EMPRESA_A, "csv", "por_hacer", USER_ACTIVO, "alta")

        assert repo.llamadas[0] == repo.llamadas[1]

    def test_el_archivo_sale_con_el_NOMBRE_del_responsable_y_no_su_uuid(self) -> None:
        """🔴 Lo que esto cubre: `responsable_id` es un uuid de `users` y no le dice nada a
        nadie. El nombre lo resuelve `_objetivo_row._build` con un lookup batch; si esa
        resolución se cayera, la columna saldría con el uuid o vacía."""
        svc, _ = _svc()

        texto = svc.exportar(EMPRESA_A, "csv").content.decode("utf-8-sig")

        assert "Ana Gómez" in texto and "Beto Pérez" in texto
        assert USER_ACTIVO not in texto and USER_INACTIVO not in texto

    def test_la_proyeccion_no_emite_ningun_uuid(self) -> None:
        for original, fila in zip(_CATALOGO, construir_filas_export(_CATALOGO)):
            assert {"id", "empresa_id", "responsable_id"}.isdisjoint(fila.keys())
            assert original.id not in str(fila)
            assert original.responsable_id not in str(fila)

    def test_el_filtro_recorta_el_ARCHIVO(self) -> None:
        """⚠️ Se afirma sobre la COLUMNA "Título", no sobre el texto crudo del CSV. Desde la
        jerarquía, el título de un padre puede aparecer legítimamente en el archivo como valor
        de la columna "Objetivo padre" de un hijo que sí pasó el filtro — un `in texto` daría
        un falso rojo, y peor, un `not in texto` daría un falso verde el día que la columna
        desaparezca. La versión anterior de este test miraba el CSV crudo y rojeó por eso."""
        svc, repo = _svc()

        svc.exportar(EMPRESA_A, "csv", "terminado")
        titulos = [f["Título"] for f in construir_filas_export(repo.find_all(EMPRESA_A, "terminado"))]

        assert "Auditar licencias" in titulos and "Validar con contable" in titulos
        assert "Migrar nómina" not in titulos and "Relevar proveedores" not in titulos

    def test_un_objetivo_sin_fecha_de_entrega_no_rompe(self) -> None:
        """`fecha_entrega` es nullable — el objetivo de la empresa B no la tiene."""
        fila = construir_filas_export([_RAIZ_B])[0]
        assert fila["Fecha entrega"] == "" and "None" not in str(fila["Fecha entrega"])


# ── 8. 🔴 La jerarquía: profundidad 2, cascade y orden del árbol ──────────────

class TestProfundidad:
    """La guarda de las DOS puntas. Molde y limitación declarada: _objetivos_jerarquia.py.

    ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE? El catálogo tiene un padre CON hijos y un hijo
    CON padre. Sin las dos cosas, cada punta de la guarda sería inobservable: sin un hijo real
    no se puede pedir colgar algo de él, y sin un padre con hijos no se lo puede intentar
    colgar de otro.
    """

    def test_no_se_puede_colgar_un_objetivo_de_un_HIJO(self, users) -> None:
        """🔴 El nieto. Es lo único que la profundidad 2 prohíbe, y el CHECK de Postgres no lo
        puede expresar: una constraint no consulta la fila del padre."""
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(parent_id=UUID(_HIJO_1.id)), "operador-1")

        assert exc.value.code == "OBJETIVO_JERARQUIA_PROFUNDA"
        assert exc.value.status_code == 422

    def test_SI_se_puede_colgar_de_una_raiz(self, users) -> None:
        """Contrapeso: sin esto, una guarda que rechazara TODO padre pasaría el test de arriba."""
        svc, repo = _svc()

        svc.create(_create(parent_id=UUID(_PADRE.id)), "operador-1")

        assert repo.escrituras[0]["data"].parent_id == UUID(_PADRE.id)

    def test_un_padre_inexistente_da_404(self, users) -> None:
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(parent_id=uuid4()), "operador-1")

        assert exc.value.code == "OBJETIVO_PADRE_NOT_FOUND"

    def test_un_padre_de_OTRA_empresa_da_el_mismo_404(self, users) -> None:
        """🔴 La jerarquía no puede cruzar la frontera multiempresa por referencia. Y el código
        es el mismo que "no existe": uno distinto confirmaría que el objetivo es de otro."""
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.create(_create(empresa_id=EMPRESA_A, parent_id=UUID(_RAIZ_B.id)), "operador-1")

        assert exc.value.code == "OBJETIVO_PADRE_NOT_FOUND"

    def test_no_se_puede_colgar_un_objetivo_QUE_YA_TIENE_HIJOS(self, users) -> None:
        """🔴 La otra punta, la que se olvida: sin ella, editar el padre para colgarlo de otro
        convertiría a sus dos hijos en nietos de una, sin pasar por la guarda del padre."""
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.update(UUID(_PADRE.id), ObjetivoUpdate(parent_id=UUID(_RAIZ_A.id)), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_JERARQUIA_PROFUNDA"

    def test_un_objetivo_SIN_hijos_si_se_puede_colgar(self, users) -> None:
        """Contrapeso de la punta de arriba."""
        svc, repo = _svc()

        svc.update(UUID(_RAIZ_A.id), ObjetivoUpdate(parent_id=UUID(_PADRE.id)), EMPRESA_A)

        assert repo.escrituras[-1]["data"].parent_id == UUID(_PADRE.id)

    def test_un_objetivo_no_puede_ser_su_propio_padre(self, users) -> None:
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.update(UUID(_RAIZ_A.id), ObjetivoUpdate(parent_id=UUID(_RAIZ_A.id)), EMPRESA_A)

        assert exc.value.code == "OBJETIVO_PADRE_ES_SI_MISMO"


class TestCascade:

    def test_borrar_el_padre_se_lleva_a_los_dos_hijos(self) -> None:
        """🔴 ON DELETE CASCADE (migración 095). El fake lo MODELA —no lo prueba contra la base—,
        así que lo que se fija acá es el contrato que el código asume sobre la FK: después de
        borrar el padre, sus hijos no pueden seguir siendo alcanzables."""
        svc, repo = _svc()
        assert repo.tiene_hijos(_PADRE.id) is True

        svc.delete(UUID(_PADRE.id), EMPRESA_A)

        assert repo.find_by_id(_PADRE.id) is None
        assert repo.find_by_id(_HIJO_1.id) is None
        assert repo.find_by_id(_HIJO_2.id) is None

    def test_borrar_un_hijo_NO_toca_al_padre_ni_al_hermano(self) -> None:
        """Contrapeso: un cascade que borrara de más se vería acá."""
        svc, repo = _svc()

        svc.delete(UUID(_HIJO_1.id), EMPRESA_A)

        assert repo.find_by_id(_PADRE.id) is not None
        assert repo.find_by_id(_HIJO_2.id) is not None

    def test_borrar_una_raiz_suelta_no_arrastra_nada(self) -> None:
        svc, repo = _svc()

        svc.delete(UUID(_RAIZ_A.id), EMPRESA_A)

        assert len(repo._filas) == 4


class TestElOrdenDelArbol:
    """🔴 ACÁ SE MUDÓ `test_ordena_por_fecha_entrega_ASCENDENTE`, que la sesión anterior escribió
    para que rojeara con la jerarquía.

    ⚠️ NO ROJEÓ, y el motivo importa: el diseño elegido **deja el `.order()` donde estaba** —la
    query sigue trayendo todo por fecha ascendente— y cambia solo el ARMADO en Python. Así que
    aquel test sigue siendo cierto y sigue vivo en TestLaQueryDelRepo, verificando la mitad que
    no cambió. Lo que faltaba y se agrega acá es la otra mitad: que el árbol conserve ese orden
    en las raíces y lo repita dentro de cada padre.
    """

    def test_las_raices_salen_por_fecha_ascendente(self) -> None:
        svc, _ = _svc()

        titulos = [r.titulo for r in svc.get_all(EMPRESA_A).items]

        # _RAIZ_A vence el 1/5 y _PADRE el 30/6.
        assert titulos == ["Auditar licencias", "Migrar nómina"]

    def test_los_hijos_van_bajo_su_padre_y_entre_ellos_por_fecha(self) -> None:
        """🔴 El bug que esto cubre: con el orden plano viejo, "Relevar proveedores" (15/3)
        saldría ARRIBA de todo —antes que su propio padre— y la pantalla mostraría la subtarea
        como si fuera un objetivo suelto."""
        svc, _ = _svc()

        padre = [r for r in svc.get_all(EMPRESA_A).items if r.titulo == "Migrar nómina"][0]

        assert [h.titulo for h in padre.hijos] == ["Relevar proveedores", "Validar con contable"]

    def test_ningun_hijo_aparece_en_el_nivel_superior(self) -> None:
        svc, _ = _svc()

        raices = svc.get_all(EMPRESA_A).items

        assert all(r.parent_id is None for r in raices)

    def test_un_hijo_cuyo_padre_NO_pasa_el_filtro_se_promueve_y_no_desaparece(self) -> None:
        """🔴 La invariante que sostiene todo el módulo: la pantalla y el archivo pueden mostrar
        de más, nunca de menos y en silencio. Con estado=haciendo el padre no matchea, y si el
        hijo se descartara por "huérfano" no aparecería en ningún lado."""
        svc, _ = _svc()

        res = svc.get_all(EMPRESA_A, "haciendo")

        assert [r.titulo for r in res.items] == ["Relevar proveedores"]
        assert res.total == 1


# ── 9. 🔴 El filtro por responsable después de la puente ─────────────────────

class TestElFiltroPorResponsableUsaLaPuente:
    """⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE? El catálogo tiene un objetivo donde el
    usuario es responsable-ACOMPAÑANTE y no dueño. Sin esa fila, filtrar por la puente y
    filtrar por `responsable_id` darían el mismo conjunto y borrar la puente del código quedaría
    en verde — que es exactamente el caso #1 de la regla del repo.
    """

    def test_encuentra_un_objetivo_donde_NO_es_el_dueño(self) -> None:
        acompanado = _obj("Revisar convenio", EMPRESA_A, USER_ACTIVO, "por_hacer", "baja",
                          date(2026, 4, 1), resp_extra=[USER_INACTIVO])
        svc, _ = _svc([acompanado])

        res = svc.get_all(EMPRESA_A, None, USER_INACTIVO)

        assert res.total == 1, "el filtro no miró la puente: solo encuentra al dueño"
        assert res.items[0].titulo == "Revisar convenio"

    def test_el_dueño_sigue_encontrando_lo_suyo(self) -> None:
        """Contrapeso: un filtro que mirara SOLO la puente y se olvidara del dueño rompería el
        listado en la ventana entre el deploy y la migración 096."""
        svc, _ = _svc()

        assert svc.get_all(EMPRESA_A, None, USER_ACTIVO).total >= 1

    def test_en_la_query_el_filtro_es_un_OR_entre_la_puente_y_el_dueño(self, monkeypatch) -> None:
        """El plano de la query: con filas en la puente sale un `.or_()` que combina los ids
        encontrados con la columna de dueño."""
        import repositories._objetivo_responsables as resp_mod
        import repositories.objetivo_repo as mod

        registro = {"or": [], "eq": []}

        class _Q:
            def __init__(self, t): self._t = t
            def select(self, *a, **k): return self
            def eq(self, c, v):
                registro["eq"].append((c, v)); return self
            def or_(self, e):
                registro["or"].append(e); return self
            def order(self, *a, **k): return self
            def execute(self):
                data = [{"objetivo_id": "obj-9"}] if self._t == "objetivo_responsables" else []
                return SimpleNamespace(data=data, count=0)

        cliente = type("C", (), {"table": lambda s, t: _Q(t)})()
        for m in (mod, resp_mod):
            monkeypatch.setattr(m, "supabase_admin", cliente)

        mod.ObjetivoRepo().find_all(responsable_id=USER_ACTIVO)

        assert registro["or"] == [f"id.in.(obj-9),responsable_id.eq.{USER_ACTIVO}"]

    def test_con_la_puente_VACIA_cae_al_dueño_y_no_devuelve_cero(self, monkeypatch) -> None:
        """🔴 La ventana entre el deploy y la migración 096: si el filtro mirara solo la puente,
        el listado por responsable se vaciaría entero SIN ningún error."""
        import repositories._objetivo_responsables as resp_mod
        import repositories.objetivo_repo as mod

        registro = {"or": [], "eq": []}

        class _Q:
            def select(self, *a, **k): return self
            def eq(self, c, v):
                registro["eq"].append((c, v)); return self
            def or_(self, e):
                registro["or"].append(e); return self
            def order(self, *a, **k): return self
            def execute(self): return SimpleNamespace(data=[], count=0)

        cliente = type("C", (), {"table": lambda s, t: _Q()})()
        for m in (mod, resp_mod):
            monkeypatch.setattr(m, "supabase_admin", cliente)

        mod.ObjetivoRepo().find_all(responsable_id=USER_ACTIVO)

        assert registro["or"] == []
        assert ("responsable_id", USER_ACTIVO) in registro["eq"]


# ── 10. El export con la jerarquía ───────────────────────────────────────────

class TestExportJerarquia:

    def test_el_archivo_trae_padres_E_HIJOS(self) -> None:
        """🔴 Exportar solo las raíces mentiría por omisión: la fecha de entrega real vive en
        los subobjetivos."""
        svc, _ = _svc()

        texto = svc.exportar(EMPRESA_A, "csv").content.decode("utf-8-sig")

        assert "Migrar nómina" in texto
        assert "Relevar proveedores" in texto and "Validar con contable" in texto

    def test_la_columna_Objetivo_padre_lleva_el_titulo_del_padre(self) -> None:
        filas = construir_filas_export(_Repo().find_all(EMPRESA_A))
        por_titulo = {f["Título"]: f for f in filas}

        assert por_titulo["Relevar proveedores"]["Objetivo padre"] == "Migrar nómina"
        assert por_titulo["Validar con contable"]["Objetivo padre"] == "Migrar nómina"

    def test_la_columna_va_VACIA_en_las_raices(self) -> None:
        """Contrapeso: una columna que copiara el propio título en las raíces se leería como si
        cada objetivo colgara de sí mismo."""
        filas = construir_filas_export(_Repo().find_all(EMPRESA_A))
        por_titulo = {f["Título"]: f for f in filas}

        assert por_titulo["Migrar nómina"]["Objetivo padre"] is None
        assert por_titulo["Auditar licencias"]["Objetivo padre"] is None

    def test_cada_hijo_sale_INMEDIATAMENTE_despues_de_su_padre(self) -> None:
        """El archivo recién bajado se lee como la pantalla. Después de que el usuario lo
        ordene, la columna es lo único que sostiene la relación — para eso está."""
        titulos = [f["Título"] for f in construir_filas_export(_Repo().find_all(EMPRESA_A))]

        i = titulos.index("Migrar nómina")
        assert titulos[i + 1:i + 3] == ["Relevar proveedores", "Validar con contable"]

    def test_los_responsables_salen_como_texto_y_no_como_objetos(self) -> None:
        """Una lista de objetos en una celda saldría como el `repr` de Python."""
        fila = construir_filas_export(_Repo().find_all(EMPRESA_A))[0]

        assert isinstance(fila["Responsables"], str)
        assert "ResponsableItem" not in str(fila)

    def test_el_limite_cuenta_padres_MAS_hijos(self) -> None:
        """🔴 `find_all` devuelve raíces; el archivo escribe raíces + hijos. Con `len(items)` el
        tope se mediría sobre la mitad de lo que se va a escribir."""
        from services._limite_export import LIMITE_FILAS_EXPORT

        padre = _obj("P", EMPRESA_A, USER_ACTIVO, "por_hacer", "alta", None)
        hijos = [_obj(f"H{i}", EMPRESA_A, USER_ACTIVO, "por_hacer", "alta", None, parent=padre.id)
                 for i in range(LIMITE_FILAS_EXPORT)]
        svc, _ = _svc([padre, *hijos])          # 1 raíz, pero 5.001 filas de archivo

        with pytest.raises(AppError) as exc:
            svc.exportar(EMPRESA_A, "excel")

        assert exc.value.code == "EXPORT_DEMASIADAS_FILAS"
