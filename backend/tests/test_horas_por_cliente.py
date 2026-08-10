"""
La vista interna "Horas por cliente": KPIs, agrupamiento, filtro de mes, consolidado y baja.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 El fake tendría que traer UN cliente y UN empleado.** Es el punto entero del bloque de
agrupación: con un solo cliente, "agrupa por cliente" y "devuelve todo junto" dan el mismo árbol
de un elemento, y con un solo empleado pasa lo mismo con las líneas. `_FILAS` trae **tres
clientes (uno de ellos ausente), cuatro empleados y dos empresas**, y cada aserción compara los
grupos ENTRE SÍ, no contra un total.

**2. 🔴 El repo tendría que ignorar el rango de fechas.** `_RepoFalso` filtra de VERDAD por
`desde`/`hasta`, así que el borde del primer y del último día se puede desmentir: un service que
pida el mes equivocado —o que no filtre— trae filas de más y los KPIs cambian.

**3. 🔴 El repo tendría que ignorar `empresa_id`.** Filtra, y el padrón tiene filas de DOS
empresas: sin eso, "consolidado y empresa elegida dan conjuntos distintos" pasaría con la barrera
borrada. Es el caso #1 de la doctrina del repo.

**4. El fake de baja tendría que devolver una fila prefabricada.** `find_by_id` la busca en el
mismo padrón que el listado, así que el evento de auditoría se arma con datos REALES de la fila y
un service que audite con la empresa del header en vez de la de la entidad se ve.
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

from datetime import date  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.horas import HoraResponse  # noqa: E402
from services._horas_cliente_agrupacion import SIN_CLIENTE, agrupar  # noqa: E402
from services._horas_cliente_export import construir_filas_export  # noqa: E402
from services.horas_cliente_service import HorasClienteService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
ACME, GLOBEX = uuid4(), uuid4()
ANA, BRUNO, CARLA, DIEGO = uuid4(), uuid4(), uuid4(), uuid4()
AHORA = "2026-08-01T00:00:00+00:00"


def _h(**kw) -> HoraResponse:
    base = dict(id=uuid4(), empresa_id=EMPRESA_A, fecha=date(2026, 8, 10), horas=4.0,
                cliente_id=ACME, cliente_nombre="Acme", empleado_id=ANA,
                empleado_nombre="Ana Pérez", empleado_empresa_nombre="Karstec",
                modalidad="home_office", proyecto_texto=None, tarea_texto=None,
                descripcion=None, created_at=AHORA)
    return HoraResponse.model_validate({**base, **kw})


# TRES clientes (uno ausente), CUATRO empleados, DOS empresas, y fechas en los dos bordes del mes.
_FILAS = [
    _h(horas=4.0, tarea_texto="Reunión"),
    _h(horas=2.0, tarea_texto="Reunión"),                       # misma línea que la anterior
    _h(horas=3.0, empleado_id=BRUNO, empleado_nombre="Bruno Gómez", tarea_texto="Soporte"),
    _h(horas=5.0, cliente_id=GLOBEX, cliente_nombre="Globex", empleado_id=CARLA,
       empleado_nombre="Carla Ruiz", modalidad="on_site", fecha=date(2026, 8, 1)),
    # Camino VIEJO: sin cliente. `_hora_row.build` le resolvió el empleado por la asignación.
    _h(horas=6.0, cliente_id=None, cliente_nombre=None, empleado_id=DIEGO,
       empleado_nombre="Diego Sosa", fecha=date(2026, 8, 31), proyecto_texto="Interno"),
    # Otra empresa: solo tiene que aparecer en el consolidado.
    _h(horas=7.0, empresa_id=EMPRESA_B, cliente_id=GLOBEX, cliente_nombre="Globex",
       empleado_id=CARLA, empleado_nombre="Carla Ruiz", empleado_empresa_nombre="Dosuba"),
    # Fuera del mes: ningún filtro correcto la trae.
    _h(horas=99.0, fecha=date(2026, 7, 31)),
    _h(horas=88.0, fecha=date(2026, 9, 1)),
]


class _RepoFalso:
    """Filtra DE VERDAD por rango y por empresa. Ver los puntos 2 y 3 del encabezado."""

    def __init__(self) -> None:
        self.borradas: list = []

    def find_por_periodo(self, desde: str, hasta: str, empresa_id=None):
        return [h for h in _FILAS
                if desde <= h.fecha.isoformat() <= hasta
                and (empresa_id is None or str(h.empresa_id) == str(empresa_id))]

    def find_por_empleado(self, empleado_id: str, desde: str, hasta: str, empresa_id=None):
        return [h for h in self.find_por_periodo(desde, hasta, empresa_id)
                if str(h.empleado_id or "") == str(empleado_id)]

    def find_by_id(self, hora_id: str, empresa_id=None):
        for h in _FILAS:
            if str(h.id) == str(hora_id) and (empresa_id is None
                                              or str(h.empresa_id) == str(empresa_id)):
                return h
        return None

    def delete(self, hora_id: str, empresa_id=None) -> bool:
        if not self.find_by_id(hora_id, empresa_id):
            return False
        self.borradas.append((hora_id, str(empresa_id) if empresa_id else None))
        return True


class _AuditoriaFalsa:
    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


@pytest.fixture
def repo() -> _RepoFalso:
    return _RepoFalso()


@pytest.fixture
def auditoria() -> _AuditoriaFalsa:
    return _AuditoriaFalsa()


@pytest.fixture
def svc(repo, auditoria) -> HorasClienteService:
    return HorasClienteService(repo=repo, audit=auditoria)


def _cliente(vista, nombre: str):
    return next(c for c in vista.clientes if c.cliente_nombre == nombre)


# ── Agrupamiento y KPIs ───────────────────────────────────────────────────────


class TestAgrupamiento:
    def test_agrupa_por_cliente_y_no_devuelve_todo_junto(self, svc) -> None:
        """Tres grupos distintos. Con UN cliente esto pasaría sin agrupar nada."""
        vista = svc.get_vista(8, 2026, EMPRESA_A)
        assert [c.cliente_nombre for c in vista.clientes] == ["Acme", SIN_CLIENTE, "Globex"]
        assert [c.horas for c in vista.clientes] == [9.0, 6.0, 5.0]   # ordenado por horas desc

    def test_las_lineas_separan_empleados_dentro_del_cliente(self, svc) -> None:
        acme = _cliente(svc.get_vista(8, 2026, EMPRESA_A), "Acme")
        assert {ln.empleado_nombre for ln in acme.lineas} == {"Ana Pérez", "Bruno Gómez"}

    def test_dos_cargas_de_la_misma_linea_se_suman_en_un_renglon(self, svc) -> None:
        """4 + 2 de Ana con la misma tarea y modalidad tienen que ser UN renglón de 6, no dos."""
        acme = _cliente(svc.get_vista(8, 2026, EMPRESA_A), "Acme")
        ana = next(ln for ln in acme.lineas if ln.empleado_nombre == "Ana Pérez")
        assert (ana.horas, ana.registros) == (6.0, 2)

    def test_la_linea_lleva_tarea_y_modalidad(self, svc) -> None:
        acme = _cliente(svc.get_vista(8, 2026, EMPRESA_A), "Acme")
        bruno = next(ln for ln in acme.lineas if ln.empleado_nombre == "Bruno Gómez")
        assert (bruno.tarea_texto, bruno.modalidad) == ("Soporte", "home_office")

    def test_las_cargas_del_camino_viejo_no_desaparecen(self, svc) -> None:
        """🔴 No tienen cliente. Descartarlas era lo cómodo en una pantalla que agrupa por
        cliente, y habría hecho que 6 horas cargadas y válidas se esfumen sin aviso."""
        sin = _cliente(svc.get_vista(8, 2026, EMPRESA_A), SIN_CLIENTE)
        assert sin.cliente_id is None and sin.horas == 6.0
        assert sin.lineas[0].empleado_nombre == "Diego Sosa"


class TestKPIs:
    def test_los_cuatro_salen_del_mismo_conjunto_que_la_tabla(self, svc) -> None:
        vista = svc.get_vista(8, 2026, EMPRESA_A)
        assert vista.kpis.horas_totales == 20.0          # 4+2+3+5+6
        assert vista.kpis.registros == 5
        assert vista.kpis.empleados_que_cargaron == 4    # Ana, Bruno, Carla, Diego
        assert vista.kpis.horas_totales == sum(c.horas for c in vista.clientes)

    def test_clientes_con_carga_no_cuenta_el_grupo_sin_cliente(self, svc) -> None:
        """Sumarlo daría un KPI que dice que hay un cliente más de los que RRHH tiene cargados."""
        vista = svc.get_vista(8, 2026, EMPRESA_A)
        assert vista.kpis.clientes_con_carga == 2        # Acme y Globex, no el bucket
        assert len(vista.clientes) == 3

    def test_un_mes_sin_cargas_da_ceros_y_no_un_error(self, svc) -> None:
        vista = svc.get_vista(1, 2026, EMPRESA_A)
        assert (vista.kpis.horas_totales, vista.kpis.registros) == (0.0, 0)
        assert vista.clientes == []

    def test_si_la_agrupacion_falla_los_kpis_salen_en_cero_y_no_revienta(self, repo) -> None:
        """Patrón `_safe` del dashboard: una pantalla que ya tenía los datos no puede dar 500."""
        class _Roto(_RepoFalso):
            def find_por_periodo(self, *a, **k):
                return [object()]        # rompe `agrupar` al leer .horas
        vista = HorasClienteService(repo=_Roto(), audit=_AuditoriaFalsa()).get_vista(8, 2026)
        assert vista.kpis.horas_totales == 0.0 and vista.clientes == []


# ── El filtro de mes ──────────────────────────────────────────────────────────


class TestFiltroDeMes:
    def test_el_primer_dia_del_mes_entra(self, svc) -> None:
        """La carga del 1/8 es de Globex: si el borde estuviera mal, ese cliente desaparecería."""
        assert "Globex" in [c.cliente_nombre for c in svc.get_vista(8, 2026, EMPRESA_A).clientes]

    def test_el_ultimo_dia_del_mes_entra(self, svc) -> None:
        """La del 31/8 es la del camino viejo. Un `<` en vez de `<=` la dejaría afuera."""
        assert SIN_CLIENTE in [c.cliente_nombre for c in svc.get_vista(8, 2026, EMPRESA_A).clientes]

    def test_los_dias_de_los_meses_vecinos_no_entran(self, svc) -> None:
        """El 31/7 (99 h) y el 1/9 (88 h) están en el padrón a propósito: si el rango se
        desbordara un día para cualquier lado, el total lo gritaría."""
        assert svc.get_vista(8, 2026, EMPRESA_A).kpis.horas_totales == 20.0

    def test_el_mes_vecino_ve_sus_filas_y_no_las_de_agosto(self, svc) -> None:
        assert svc.get_vista(7, 2026, EMPRESA_A).kpis.horas_totales == 99.0
        assert svc.get_vista(9, 2026, EMPRESA_A).kpis.horas_totales == 88.0


# ── Consolidado vs empresa ────────────────────────────────────────────────────


class TestBarreraDeEmpresa:
    def test_consolidado_y_empresa_elegida_dan_conjuntos_distintos(self, svc) -> None:
        """🔴 Con un padrón de una sola empresa esto pasaría con la barrera borrada."""
        consolidado = svc.get_vista(8, 2026, None)
        propia = svc.get_vista(8, 2026, EMPRESA_A)
        assert consolidado.kpis.horas_totales == 27.0    # 20 + las 7 de la otra empresa
        assert propia.kpis.horas_totales == 20.0
        assert consolidado.kpis.registros != propia.kpis.registros

    def test_la_otra_empresa_ve_solo_lo_suyo(self, svc) -> None:
        assert svc.get_vista(8, 2026, EMPRESA_B).kpis.horas_totales == 7.0


# ── Listado y export: el MISMO conjunto ───────────────────────────────────────


class TestParidadListadoExport:
    def test_el_export_trae_exactamente_las_filas_del_listado(self, repo, svc) -> None:
        """Invariante 1 del bloque B: los dos entran por `_filas`, así que el archivo no puede
        traer filas que la pantalla no muestre. Se compara el CONTEO de registros del KPI contra
        las filas proyectadas al Excel."""
        vista = svc.get_vista(8, 2026, EMPRESA_A)
        filas = construir_filas_export(repo.find_por_periodo("2026-08-01", "2026-08-31", EMPRESA_A))
        assert len(filas) == vista.kpis.registros
        assert sum(f["Horas"] for f in filas) == vista.kpis.horas_totales

    def test_el_export_respeta_el_mismo_filtro_de_empresa(self, repo) -> None:
        consolidado = construir_filas_export(repo.find_por_periodo("2026-08-01", "2026-08-31"))
        propia = construir_filas_export(
            repo.find_por_periodo("2026-08-01", "2026-08-31", EMPRESA_A))
        assert len(consolidado) > len(propia)

    def test_el_export_es_plano_y_nombra_el_grupo_sin_cliente(self, repo) -> None:
        """Una celda vacía se lee como un dato que falta; acá significa algo concreto."""
        filas = construir_filas_export(repo.find_por_periodo("2026-08-01", "2026-08-31", EMPRESA_A))
        assert any(f["Cliente"] == "Sin cliente" for f in filas)
        assert all(isinstance(f["Horas"], float) for f in filas)   # escalares, no árboles


# ── El detalle día por día y la baja ──────────────────────────────────────────


class TestDetalleYBaja:
    def test_el_detalle_trae_las_cargas_del_empleado_con_su_id(self, svc) -> None:
        """El `id` es lo que la pantalla necesita para poder borrar."""
        det = svc.get_detalle(ANA, 8, 2026, EMPRESA_A)
        assert det.total_horas == 6.0 and len(det.items) == 2
        assert all(i.id for i in det.items)

    def test_el_detalle_no_trae_las_de_otro_empleado(self, svc) -> None:
        assert svc.get_detalle(BRUNO, 8, 2026, EMPRESA_A).total_horas == 3.0

    def test_borra_y_audita_con_la_empresa_de_la_entidad(self, svc, repo, auditoria) -> None:
        """🔴 Se llama en modo CONSOLIDADO (empresa_id=None) sobre una fila de EMPRESA_A: el
        header vale None y la entidad vale A, así que solo un payload que lea la ENTIDAD puede
        dar A. Con las dos coincidiendo, el test no podría desmentir de dónde salió."""
        fila = _FILAS[0]
        svc.eliminar(fila.id, None, "usuario-1")
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"], ev["entidad"]) == ("DELETE", "baja_hora", "hora")
        assert ev["empresa_id"] is not None, "se etiquetó con el header (None)"
        assert str(ev["empresa_id"]) == str(EMPRESA_A)
        assert ev["usuario_id"] == "usuario-1"

    def test_el_evento_no_lleva_campos_derivados_de_joins(self, svc, auditoria) -> None:
        """`cliente_nombre` y `empleado_nombre` son resultado de CÓMO se leyó la fila, no datos
        del registro. Un diff que los incluya registra cambios que nunca ocurrieron."""
        svc.eliminar(_FILAS[0].id, EMPRESA_A, "usuario-1")
        anteriores = auditoria.eventos[0]["datos_anteriores"]
        assert not {"cliente_nombre", "empleado_nombre", "empleado_empresa_nombre", "costo"} \
            & set(anteriores)
        assert anteriores["horas"] == 4.0

    def test_una_carga_de_otra_empresa_da_404_y_no_borra(self, svc, repo, auditoria) -> None:
        ajena = _FILAS[5]                       # es de EMPRESA_B
        with pytest.raises(AppError) as exc:
            svc.eliminar(ajena.id, EMPRESA_A, "usuario-1")
        assert (exc.value.code, exc.value.status_code) == ("HORA_NOT_FOUND", 404)
        assert repo.borradas == [] and auditoria.eventos == []

    def test_una_inexistente_da_el_mismo_404_que_una_ajena(self, svc) -> None:
        with pytest.raises(AppError) as ajena:
            svc.eliminar(_FILAS[5].id, EMPRESA_A, "u")
        with pytest.raises(AppError) as inexistente:
            svc.eliminar(UUID("11111111-1111-1111-1111-111111111111"), EMPRESA_A, "u")
        assert (ajena.value.code, ajena.value.message) == \
               (inexistente.value.code, inexistente.value.message)

    def test_la_barrera_viaja_en_el_delete_y_no_solo_en_la_lectura(self, svc, repo) -> None:
        """Sin el `.eq` en el delete, la fila ya no estaría cuando la relectura devolviera None."""
        svc.eliminar(_FILAS[0].id, EMPRESA_A, "u")
        assert repo.borradas == [(str(_FILAS[0].id), str(EMPRESA_A))]


class TestEditarNoExiste:
    def test_el_service_no_expone_un_update(self) -> None:
        """`HorasService` declara los registros inmutables por decisión ESCRITA. Agregar un
        update no es sumar una feature: es revocarla. Lo que haría falta está enumerado en
        `_QUE_FALTARIA_PARA_EDITAR`, dentro del service, para poder decidirlo con el costo a la
        vista. Este test es lo que hace que agregarlo sea un acto deliberado."""
        assert not hasattr(HorasClienteService, "actualizar")
        assert not hasattr(HorasClienteService, "update")


class TestAgrupacionPura:
    def test_con_lista_vacia_no_inventa_grupos(self) -> None:
        kpis, clientes = agrupar([])
        assert clientes == []
        assert kpis == {"horas_totales": 0.0, "clientes_con_carga": 0,
                        "empleados_que_cargaron": 0, "registros": 0}


# ── El repo REAL: la barrera que un repo falso no puede desmentir ─────────────


class TestElRepoReal:
    """🔴 Los bloques de arriba usan `_RepoFalso`, así que NO pueden ver si la barrera de empresa
    viaja de verdad en el WHERE. Lo detectó una corrida de mutación: sacarle el `.eq("empresa_id")`
    al DELETE del repo real dejaba los 27 tests en verde.

    Acá corre el repo REAL contra el doble de tabla (`tests/_almacen_tabla.Almacen`), que acumula
    TODOS los `.eq()` y registra las escrituras. Lo que se afirma es lo que VIAJA EN LA QUERY —
    molde: `TestElOrdenLoPoneLaQuery` de `test_historial_salarial`.
    """

    @pytest.fixture
    def almacen(self, monkeypatch):
        from tests._almacen_tabla import Almacen
        import repositories._hora_row as hora_row
        import repositories._horas_vista_repo as repo_mod
        a = Almacen({"horas_proyecto": [
            {"id": "aaaaaaaa-0000-4000-8000-000000000001", "empresa_id": str(EMPRESA_A),
             "empleado_empresa_id": str(EMPRESA_A), "empleado_id": str(ANA), "cliente_id": None,
             "fecha": "2026-08-10", "horas": 4.0, "valor_hora_snapshot": None,
             "asignacion_id": None, "proyecto_id": None, "modalidad": "home_office",
             "proyecto_texto": None, "tarea_texto": None, "descripcion": None,
             "created_at": AHORA},
            {"id": "bbbbbbbb-0000-4000-8000-000000000002", "empresa_id": str(EMPRESA_B),
             "empleado_empresa_id": str(EMPRESA_B), "empleado_id": str(CARLA), "cliente_id": None,
             "fecha": "2026-08-10", "horas": 7.0, "valor_hora_snapshot": None,
             "asignacion_id": None, "proyecto_id": None, "modalidad": "on_site",
             "proyecto_texto": None, "tarea_texto": None, "descripcion": None,
             "created_at": AHORA},
        ], "empleados": [], "empresas": [], "clientes": [], "proyecto_asignaciones": []})
        monkeypatch.setattr(repo_mod, "supabase_admin", a)
        monkeypatch.setattr(hora_row, "supabase_admin", a)
        return a

    def test_el_listado_filtra_por_empresa_en_la_query(self, almacen) -> None:
        import repositories._horas_vista_repo as repo_mod
        propias = repo_mod.find_por_periodo("2026-08-01", "2026-08-31", EMPRESA_A)
        todas = repo_mod.find_por_periodo("2026-08-01", "2026-08-31", None)
        assert len(propias) == 1 and len(todas) == 2

    def test_el_rango_de_fechas_viaja_en_la_query(self, almacen) -> None:
        import repositories._horas_vista_repo as repo_mod
        assert repo_mod.find_por_periodo("2026-09-01", "2026-09-30", None) == []

    def test_borrar_una_fila_ajena_no_la_borra(self, almacen) -> None:
        """🔴 EL TEST QUE LA MUTACIÓN PEDÍA. Sin el `.eq("empresa_id")` en el DELETE, la fila de
        la otra empresa desaparecería del catálogo y esto rojea."""
        import repositories._horas_vista_repo as repo_mod
        ajena = "bbbbbbbb-0000-4000-8000-000000000002"
        assert repo_mod.delete(ajena, EMPRESA_A) is False
        assert any(f["id"] == ajena for f in almacen.catalogo["horas_proyecto"])
        _, filtros, _ = almacen.escrituras[0]
        assert ("empresa_id", str(EMPRESA_A)) in filtros

    def test_borrar_la_propia_si_la_borra(self, almacen) -> None:
        """El contraste: sin esto, "no borra la ajena" pasaría con un delete que no borra nada."""
        import repositories._horas_vista_repo as repo_mod
        propia = "aaaaaaaa-0000-4000-8000-000000000001"
        assert repo_mod.delete(propia, EMPRESA_A) is True
        assert not any(f["id"] == propia for f in almacen.catalogo["horas_proyecto"])
