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
import services.horas_cliente_service as svc_mod  # noqa: E402
from services.export import Descarga  # noqa: E402
from services.horas_cliente_service import HorasClienteService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
ACME, GLOBEX = uuid4(), uuid4()
ANA, BRUNO, CARLA, DIEGO = uuid4(), uuid4(), uuid4(), uuid4()
AHORA = "2026-08-01T00:00:00+00:00"
# Lo que devuelve el motor de export falseado. El contenido no importa: lo que se mira es lo que
# el service le PASA, no lo que el motor produce (eso lo prueba `services/export/`).
_DESCARGA = Descarga(content=b"x", media_type="text/csv", filename="x.csv")


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
    """Filtra DE VERDAD por rango. Ver los puntos 2 y 3 del encabezado.

    🔴 `find_por_periodo` NO acepta `empresa_id`: sigue la firma real, que dejó de aceptarlo (L8).
    Si el fake lo siguiera aceptando, un service que volviera a pasarlo NO fallaría acá y el test
    de los tres modos pasaría con el recorte puesto."""

    def __init__(self) -> None:
        self.borradas: list = []

    def find_por_periodo(self, desde: str, hasta: str):
        return [h for h in _FILAS if desde <= h.fecha.isoformat() <= hasta]

    def find_por_empleado(self, empleado_id: str, desde: str, hasta: str):
        return [h for h in self.find_por_periodo(desde, hasta)
                if str(h.empleado_id or "") == str(empleado_id)]

    def find_by_id(self, hora_id: str):
        return next((h for h in _FILAS if str(h.id) == str(hora_id)), None)

    def delete(self, hora_id: str) -> bool:
        """🔴 Ninguno de los tres acepta ya `empresa_id`: siguen la firma real (L9). Si el fake lo
        siguiera aceptando, un service que volviera a pasarlo NO fallaría acá y los tests del
        detalle y del borrado cruzados pasarían con el recorte puesto."""
        if not self.find_by_id(hora_id):
            return False
        self.borradas.append(str(hora_id))
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
        vista = svc.get_vista(8, 2026)
        assert [c.cliente_nombre for c in vista.clientes] == ["Globex", "Acme", SIN_CLIENTE]
        # Globex pasó al frente: son sus 5 h de Karstec + 7 de Dosuba (L8). Ordenado por desc.
        assert [c.horas for c in vista.clientes] == [12.0, 9.0, 6.0]

    def test_las_lineas_separan_empleados_dentro_del_cliente(self, svc) -> None:
        acme = _cliente(svc.get_vista(8, 2026), "Acme")
        assert {ln.empleado_nombre for ln in acme.lineas} == {"Ana Pérez", "Bruno Gómez"}

    def test_dos_cargas_de_la_misma_linea_se_suman_en_un_renglon(self, svc) -> None:
        """4 + 2 de Ana con la misma tarea y modalidad tienen que ser UN renglón de 6, no dos."""
        acme = _cliente(svc.get_vista(8, 2026), "Acme")
        ana = next(ln for ln in acme.lineas if ln.empleado_nombre == "Ana Pérez")
        assert (ana.horas, ana.registros) == (6.0, 2)

    def test_la_linea_lleva_tarea_y_modalidad(self, svc) -> None:
        acme = _cliente(svc.get_vista(8, 2026), "Acme")
        bruno = next(ln for ln in acme.lineas if ln.empleado_nombre == "Bruno Gómez")
        assert (bruno.tarea_texto, bruno.modalidad) == ("Soporte", "home_office")

    def test_las_cargas_del_camino_viejo_no_desaparecen(self, svc) -> None:
        """🔴 No tienen cliente. Descartarlas era lo cómodo en una pantalla que agrupa por
        cliente, y habría hecho que 6 horas cargadas y válidas se esfumen sin aviso."""
        sin = _cliente(svc.get_vista(8, 2026), SIN_CLIENTE)
        assert sin.cliente_id is None and sin.horas == 6.0
        assert sin.lineas[0].empleado_nombre == "Diego Sosa"


class TestKPIs:
    def test_los_cuatro_salen_del_mismo_conjunto_que_la_tabla(self, svc) -> None:
        vista = svc.get_vista(8, 2026)
        assert vista.kpis.horas_totales == 27.0          # 4+2+3+5+6+7, las dos sociedades
        assert vista.kpis.registros == 6
        assert vista.kpis.empleados_que_cargaron == 4    # Ana, Bruno, Carla, Diego
        assert vista.kpis.horas_totales == sum(c.horas for c in vista.clientes)

    def test_clientes_con_carga_no_cuenta_el_grupo_sin_cliente(self, svc) -> None:
        """Sumarlo daría un KPI que dice que hay un cliente más de los que RRHH tiene cargados."""
        vista = svc.get_vista(8, 2026)
        assert vista.kpis.clientes_con_carga == 2        # Acme y Globex, no el bucket
        assert len(vista.clientes) == 3

    def test_un_mes_sin_cargas_da_ceros_y_no_un_error(self, svc) -> None:
        vista = svc.get_vista(1, 2026)
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
        assert "Globex" in [c.cliente_nombre for c in svc.get_vista(8, 2026).clientes]

    def test_el_ultimo_dia_del_mes_entra(self, svc) -> None:
        """La del 31/8 es la del camino viejo. Un `<` en vez de `<=` la dejaría afuera."""
        assert SIN_CLIENTE in [c.cliente_nombre for c in svc.get_vista(8, 2026).clientes]

    def test_los_dias_de_los_meses_vecinos_no_entran(self, svc) -> None:
        """El 31/7 (99 h) y el 1/9 (88 h) están en el padrón a propósito: si el rango se
        desbordara un día para cualquier lado, el total lo gritaría."""
        assert svc.get_vista(8, 2026).kpis.horas_totales == 27.0

    def test_el_mes_vecino_ve_sus_filas_y_no_las_de_agosto(self, svc) -> None:
        assert svc.get_vista(7, 2026).kpis.horas_totales == 99.0
        assert svc.get_vista(9, 2026).kpis.horas_totales == 88.0


# ── El total es del CLIENTE, no de la sociedad ────────────────────────────────


class TestElTotalNoSeRecorta:
    """🔴 EL BLOQUE QUE SOSTIENE LA DECISIÓN DE L8, e INVIERTE al que estaba acá.

    Antes esto era `TestBarreraDeEmpresa` y afirmaba que consolidado y empresa elegida daban
    conjuntos DISTINTOS. Se decidió al revés: las empresas son sociedades de un mismo grupo, así
    que las horas que consume un cliente son las horas del cliente, venga de donde venga el
    empleado que las cargó.

    ¿Qué tendría que ser distinto en el fake para que esto falle? Que `_FILAS` tuviera un cliente
    por empresa. Globex recibe 5 h de Karstec (EMPRESA_A) y 7 h de Dosuba (EMPRESA_B): **el mismo
    cliente, dos sociedades**. Con un cliente por empresa, "recorta" y "no recorta" darían el
    mismo número y no habría nada que desmentir.
    """

    def test_globex_suma_las_dos_sociedades(self, svc) -> None:
        """5 h de Karstec + 7 h de Dosuba = 12. Es el caso concreto del diagnóstico."""
        assert _cliente(svc.get_vista(8, 2026), "Globex").horas == 12.0

    def test_el_total_es_el_mismo_no_importa_el_sidebar(self, svc) -> None:
        """🔴 El service ya no RECIBE la empresa, así que los tres "modos" del sidebar (A, B y
        consolidado) producen exactamente la misma llamada y el mismo número. Se afirma sobre lo
        que ve el usuario: 27 h totales y Globex con 12, en los tres."""
        vista = svc.get_vista(8, 2026)
        assert vista.kpis.horas_totales == 27.0
        assert _cliente(vista, "Globex").horas == 12.0
        import inspect
        params = inspect.signature(svc.get_vista).parameters
        assert "empresa_id" not in params, "volvió a aceptar la empresa: el sidebar podría recortar"

    def test_el_desglose_reparte_las_mismas_horas_por_sociedad(self, svc) -> None:
        """El reparto no se pierde: se muestra adentro del cliente. Y su suma ES el total — sin
        esa igualdad, el desglose podría estar contando cualquier otra cosa."""
        globex = _cliente(svc.get_vista(8, 2026), "Globex")
        reparto = {e.empresa_nombre: e.horas for e in globex.por_empresa}
        assert reparto == {"Dosuba": 7.0, "Karstec": 5.0}
        assert round(sum(reparto.values()), 2) == globex.horas

    def test_el_desglose_ordena_por_horas_desc(self, svc) -> None:
        globex = _cliente(svc.get_vista(8, 2026), "Globex")
        assert [e.empresa_nombre for e in globex.por_empresa] == ["Dosuba", "Karstec"]

    def test_un_cliente_de_una_sola_sociedad_tiene_un_solo_renglon(self, svc) -> None:
        """El contraste: sin esto, un desglose que devolviera SIEMPRE las dos empresas pasaría."""
        acme = _cliente(svc.get_vista(8, 2026), "Acme")
        assert [(e.empresa_nombre, e.horas) for e in acme.por_empresa] == [("Karstec", 9.0)]


# ── Listado y export: el MISMO conjunto ───────────────────────────────────────


class TestParidadListadoExport:
    def test_el_export_trae_exactamente_las_filas_del_listado(self, repo, svc) -> None:
        """Invariante 1 del bloque B: los dos entran por `_filas`, así que el archivo no puede
        traer filas que la pantalla no muestre. Se compara el CONTEO de registros del KPI contra
        las filas proyectadas al Excel."""
        vista = svc.get_vista(8, 2026)
        filas = construir_filas_export(repo.find_por_periodo("2026-08-01", "2026-08-31"))
        assert len(filas) == vista.kpis.registros
        assert sum(f["Horas"] for f in filas) == vista.kpis.horas_totales

    def test_el_export_tampoco_se_recorta_por_empresa(self, repo, monkeypatch) -> None:
        """Invertido junto con el listado (L8): el archivo trae las dos sociedades, y la columna
        "Empresa" permite reconstruir el reparto desde el Excel.

        🔴 VA POR `svc.exportar()`, NO por `construir_filas_export(repo.find_por_periodo(...))`.
        La versión anterior de este test armaba las filas a mano desde el repo y NUNCA entraba al
        service: `exportar` podía recortar por empresa y ningún test se enteraba. Lo detectó la
        corrida de mutación de L8 —recortar el export dejó los 34 en verde—, no la lectura.
        Se captura lo que el service le pasa al motor de export, que es el archivo que sale."""
        capturado: dict = {}
        monkeypatch.setattr(svc_mod, "build_export",
                            lambda **kw: capturado.update(kw) or _DESCARGA)

        HorasClienteService(repo=repo, audit=_AuditoriaFalsa()).exportar(8, 2026)

        filas = capturado["datos"]["Horas"]
        assert {f["Empresa"] for f in filas} == {"Karstec", "Dosuba"}
        assert sum(f["Horas"] for f in filas) == 27.0

    def test_el_export_sale_por_el_motor_comun(self, repo, monkeypatch) -> None:
        """El contraste: sin esto, "el service no recorta" pasaría con un `exportar` que no
        llamara a nada. Verifica que el nombre y el formato llegan al motor."""
        capturado: dict = {}
        monkeypatch.setattr(svc_mod, "build_export",
                            lambda **kw: capturado.update(kw) or _DESCARGA)
        HorasClienteService(repo=repo, audit=_AuditoriaFalsa()).exportar(8, 2026, formato="csv")
        assert capturado["formato"] == "csv"
        assert capturado["filename_base"] == "horas-por-cliente"

    def test_el_export_es_plano_y_nombra_el_grupo_sin_cliente(self, repo) -> None:
        """Una celda vacía se lee como un dato que falta; acá significa algo concreto."""
        filas = construir_filas_export(repo.find_por_periodo("2026-08-01", "2026-08-31"))
        assert any(f["Cliente"] == "Sin cliente" for f in filas)
        assert all(isinstance(f["Horas"], float) for f in filas)   # escalares, no árboles


# ── El detalle día por día y la baja ──────────────────────────────────────────


class TestDetalleYBaja:
    """🔴 El detalle y la baja tampoco se recortan por empresa (L9).

    ¿Qué tendría que ser distinto en el fake para que estos tests fallen? Que `_FILAS` tuviera
    todas las cargas de una sola sociedad. La fila 5 es de EMPRESA_B (Carla/Dosuba) contra el
    MISMO cliente que la 3: es la única que puede desmentir "cruza empresas". Y `_RepoFalso` ya no
    acepta `empresa_id` en ninguno de los tres métodos, así que un service que volviera a pasarlo
    revienta acá en vez de pasar en silencio.

    ⚠️ Estos tests atraviesan el SERVICE (`svc.get_detalle`, `svc.eliminar`), no arman el
    resultado por su cuenta. Lo que NO atraviesan es el router — ver la nota al pie del archivo."""

    def test_el_detalle_trae_las_cargas_del_empleado_con_su_id(self, svc) -> None:
        """El `id` es lo que la pantalla necesita para poder borrar."""
        det = svc.get_detalle(ANA, 8, 2026)
        assert det.total_horas == 6.0 and len(det.items) == 2
        assert all(i.id for i in det.items)

    def test_el_detalle_no_trae_las_de_otro_empleado(self, svc) -> None:
        assert svc.get_detalle(BRUNO, 8, 2026).total_horas == 3.0

    def test_el_detalle_de_un_empleado_de_otra_sociedad_trae_sus_horas(self, svc) -> None:
        """🔴 EL CASO QUE L9 VIENE A CERRAR. Carla tiene 5 h en EMPRESA_A y 7 h en EMPRESA_B.
        Antes, con el sidebar en A, este modal se abría con las 5 —o vacío si se la miraba desde
        B—. Ahora trae las 12: el detalle es del empleado, no de la sociedad desde la que se mira.
        Si el recorte volviera, este número baja."""
        det = svc.get_detalle(CARLA, 8, 2026)
        assert det.total_horas == 12.0
        assert {str(i.empresa_id) for i in det.items} == {str(EMPRESA_A), str(EMPRESA_B)}

    def test_borra_y_audita_con_la_empresa_de_la_entidad(self, svc, repo, auditoria) -> None:
        """🔴 Se llama en modo CONSOLIDADO (empresa_id=None) sobre una fila de EMPRESA_A: el
        header vale None y la entidad vale A, así que solo un payload que lea la ENTIDAD puede
        dar A. Con las dos coincidiendo, el test no podría desmentir de dónde salió."""
        fila = _FILAS[0]
        svc.eliminar(fila.id, "usuario-1")
        ev = auditoria.eventos[0]
        assert (ev["accion"], ev["evento"], ev["entidad"]) == ("DELETE", "baja_hora", "hora")
        assert ev["empresa_id"] is not None, "se etiquetó con el header (None)"
        assert str(ev["empresa_id"]) == str(EMPRESA_A)
        assert ev["usuario_id"] == "usuario-1"

    def test_el_evento_no_lleva_campos_derivados_de_joins(self, svc, auditoria) -> None:
        """`cliente_nombre` y `empleado_nombre` son resultado de CÓMO se leyó la fila, no datos
        del registro. Un diff que los incluya registra cambios que nunca ocurrieron."""
        svc.eliminar(_FILAS[0].id, "usuario-1")
        anteriores = auditoria.eventos[0]["datos_anteriores"]
        assert not {"cliente_nombre", "empleado_nombre", "empleado_empresa_nombre", "costo"} \
            & set(anteriores)
        assert anteriores["horas"] == 4.0

    def test_una_carga_de_otra_sociedad_se_borra(self, svc, repo, auditoria) -> None:
        """🔴 INVERTIDO. Este test afirmaba que una carga de EMPRESA_B daba 404 mirándola desde A.
        Ahora se borra: la carga es del cliente, y quién la mira no cambia de quién es. El evento
        se sigue etiquetando con la empresa de la ENTIDAD (B), no con la de quien la borró."""
        ajena = _FILAS[5]                       # es de EMPRESA_B
        svc.eliminar(ajena.id, "usuario-1")
        assert repo.borradas == [str(ajena.id)]
        assert str(auditoria.eventos[0]["empresa_id"]) == str(EMPRESA_B)

    def test_una_inexistente_sigue_dando_404(self, svc, repo, auditoria) -> None:
        """🔴 EL CONTRASTE, sin el cual los dos de arriba pasarían con un repo que no filtra NADA.
        Al sacar el recorte por empresa, lo único que separa "esta fila" de "cualquier fila" es el
        id — así que un `find_by_id` que devolviera siempre algo tiene que verse acá."""
        with pytest.raises(AppError) as exc:
            svc.eliminar(UUID("11111111-1111-1111-1111-111111111111"), "u")
        assert (exc.value.code, exc.value.status_code) == ("HORA_NOT_FOUND", 404)
        assert repo.borradas == [] and auditoria.eventos == []

    def test_el_id_viaja_en_el_delete_y_no_solo_en_la_lectura(self, svc, repo) -> None:
        """Sin el `.eq("id")` en el delete, la fila ya no estaría cuando la relectura devolviera
        None. Desde L9 ese `.eq` es la ÚNICA guarda de la query: antes había además un
        `.eq("empresa_id")` que acotaba el daño de un descuido a una sola sociedad."""
        svc.eliminar(_FILAS[0].id, "u")
        assert repo.borradas == [str(_FILAS[0].id)]


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
            # 🔴 CARLA otra vez, pero en EMPRESA_A: es la única forma de que `find_por_empleado`
            # pueda desmentir un recorte por empresa CONTRA LA QUERY REAL. Con Carla en una sola
            # sociedad, "trae las dos" y "trae la suya" darían el mismo resultado.
            {"id": "cccccccc-0000-4000-8000-000000000003", "empresa_id": str(EMPRESA_A),
             "empleado_empresa_id": str(EMPRESA_A), "empleado_id": str(CARLA), "cliente_id": None,
             "fecha": "2026-08-11", "horas": 5.0, "valor_hora_snapshot": None,
             "asignacion_id": None, "proyecto_id": None, "modalidad": "on_site",
             "proyecto_texto": None, "tarea_texto": None, "descripcion": None,
             "created_at": AHORA},
        ], "empleados": [], "empresas": [], "clientes": [], "proyecto_asignaciones": []})
        monkeypatch.setattr(repo_mod, "supabase_admin", a)
        monkeypatch.setattr(hora_row, "supabase_admin", a)
        return a

    def test_el_listado_no_filtra_por_empresa_en_la_query(self, almacen) -> None:
        """🔴 Invertido en L8, y contra la query REAL. El padrón del almacén tiene una fila de
        cada empresa: si el WHERE volviera a llevar `empresa_id`, traería menos."""
        import repositories._horas_vista_repo as repo_mod
        assert len(repo_mod.find_por_periodo("2026-08-01", "2026-08-31")) == 3

    def test_el_rango_de_fechas_viaja_en_la_query(self, almacen) -> None:
        import repositories._horas_vista_repo as repo_mod
        assert repo_mod.find_por_periodo("2026-09-01", "2026-09-30") == []

    def test_find_by_id_alcanza_una_fila_de_otra_sociedad(self, almacen) -> None:
        """🔴 LO DETECTÓ UNA MUTACIÓN, NO LA LECTURA. Volver a filtrar por empresa en el
        `find_by_id` REAL dejaba los 37 tests en verde: los del borrado cruzado van por el
        service, que usa `_RepoFalso`, así que la QUERY real no la miraba nadie. Es el mismo
        agujero que L8 encontró en el export."""
        import repositories._horas_vista_repo as repo_mod
        otra = "bbbbbbbb-0000-4000-8000-000000000002"
        fila = repo_mod.find_by_id(otra)
        assert fila is not None and str(fila.id) == otra

    def test_find_por_empleado_trae_las_cargas_de_las_dos_sociedades(self, almacen) -> None:
        """Ídem: Carla tiene una carga en cada sociedad. Si la query volviera a recortar, trae 1."""
        import repositories._horas_vista_repo as repo_mod
        filas = repo_mod.find_por_empleado(str(CARLA), "2026-08-01", "2026-08-31")
        assert len(filas) == 2
        assert {str(f.empresa_id) for f in filas} == {str(EMPRESA_A), str(EMPRESA_B)}

    def test_el_delete_se_lleva_solo_la_fila_del_id(self, almacen) -> None:
        """🔴 EL TEST QUE MÁS IMPORTA DE L9, y contra la query REAL.

        Al sacar el `.eq("empresa_id")` del DELETE, el `.eq("id")` quedó como ÚNICA guarda de esa
        query: sin él, el DELETE alcanza la tabla entera. Antes un descuido ahí se llevaba una
        sociedad; ahora se lleva todo.

        Las DOS mitades hacen falta: que devuelva True dice que borró algo, que la OTRA fila siga
        en el catálogo dice que no borró de más. Con una sola fila en el almacén no habría con qué
        contrastar — por eso el padrón tiene una de cada sociedad."""
        import repositories._horas_vista_repo as repo_mod
        una = "aaaaaaaa-0000-4000-8000-000000000001"
        otra = "bbbbbbbb-0000-4000-8000-000000000002"

        assert repo_mod.delete(una) is True

        quedan = [f["id"] for f in almacen.catalogo["horas_proyecto"]]
        assert quedan == [otra, "cccccccc-0000-4000-8000-000000000003"], \
            "el DELETE se llevó filas que no eran la del id"
        _, filtros, _ = almacen.escrituras[0]
        assert ("id", una) in filtros, "el id no viajó en la query"

    def test_borrar_una_de_otra_sociedad_ahora_si_la_borra(self, almacen) -> None:
        """🔴 INVERTIDO. Este test afirmaba que la fila de la otra empresa NO se borraba."""
        import repositories._horas_vista_repo as repo_mod
        otra = "bbbbbbbb-0000-4000-8000-000000000002"
        assert repo_mod.delete(otra) is True
        assert not any(f["id"] == otra for f in almacen.catalogo["horas_proyecto"])

    def test_borrar_un_id_inexistente_no_toca_nada(self, almacen) -> None:
        """El contraste: sin esto, "borra la del id" pasaría con un delete que borra siempre."""
        import repositories._horas_vista_repo as repo_mod
        assert repo_mod.delete("dddddddd-0000-4000-8000-000000000009") is False
        assert len(almacen.catalogo["horas_proyecto"]) == 3
