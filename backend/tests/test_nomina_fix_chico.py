"""
Tests del "fix chico" del import de nómina — sin red.

Cubre las cuatro piezas y, sobre todo, la GARANTÍA: sacar lookups redundantes no cambió el
comportamiento observable del import.

  1. El import sigue creando y actualizando igual que antes (dedup por DNI).
  2. Los lookups redundantes YA NO SE INVOCAN — y se cuenta cuántas idas a la base quedan,
     que es la métrica que decide si el batch sigue siendo necesario.
  3. Legajo: columna OPCIONAL (un CSV sin ella importa igual) y duplicado → motivo legible.
  4. Auditoría: UN evento de lote con los ids de las altas; los updates conservan su diff.

⚠️ FAKES: los repos de acá CUENTAN sus invocaciones (`llamadas`). Esa es la única forma de que
un test de "ya no se consulta la base por esto" pueda fallar: un fake que solo devuelve datos
no puede desmentir que se lo llamó de más. Y el fake de empleados HONRA empresa_id (dos
empresas), como exige la regla del repo.

¿Qué tendría que ser distinto en cada fake para que el test pueda fallar? En el docstring de
cada test.
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

from uuid import uuid4

import pytest

from schemas.empleado import EmpleadoResponse
from services import _nomina_empleados_transforms as tx
from services.nomina_empleados_service import NominaEmpleadosImportService

EMPRESA_A = str(uuid4())
AREA_A = str(uuid4())

_COLUMNAS = [
    "Apellido", "Nombre", "DNI", "CUIT", "Sexo", "Edad", "Email", "Fecha Nacimiento",
    "Fecha Ingreso", "Fecha Ingreso Reconocida", "Organismo", "Gerencia", "Sector", "Equipo",
    "Rol", "Seniority", "Categoria", "Modalidad Contratacion", "Co-sourcing",
    "Apellido Superior", "Nombre Superior", "Liderazgo", "Ubicación Física", "Carga Horaria",
    "Product Owner", "Fecha Baja", "Motivo Baja",
]


def _csv(filas: list[dict], con_legajo: bool = False) -> str:
    """Arma un CSV ';' con las 27 columnas requeridas (+ Legajo si se pide)."""
    cols = (["Legajo"] if con_legajo else []) + _COLUMNAS
    out = [";".join(cols)]
    for f in filas:
        out.append(";".join(str(f.get(c, "")) for c in cols))
    return "\r\n".join(out) + "\r\n"


def _fila(apellido="Perez", nombre="Ana", dni="30111222", **extra) -> dict:
    base = {
        "Apellido": apellido, "Nombre": nombre, "DNI": dni, "Organismo": "ACME",
        "Sector": "SISTEMAS", "Rol": "Analista", "Fecha Ingreso": "1/3/2024",
        "Email": f"{dni}@k.com", "Modalidad Contratacion": "RELACION DE DEPENDENCIA",
    }
    base.update(extra)
    return base


def _empleado(id_: str, dni: str, legajo=None) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": id_, "nombre": "N", "apellido": "A", "email_corporativo": f"{dni}@k.com",
        "empresa_id": EMPRESA_A, "area_id": AREA_A, "roles": ["Analista"], "dni": dni,
        "legajo": legajo, "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


class _Contador:
    """Base de los fakes: registra cada invocación para poder contar idas a la base."""

    def __init__(self) -> None:
        self.llamadas: list[str] = []

    def _reg(self, nombre: str) -> None:
        self.llamadas.append(nombre)

    def cuenta(self, nombre: str) -> int:
        return sum(1 for x in self.llamadas if x == nombre)


class _EmpleadoRepo(_Contador):
    """HONRA empresa_id. `existentes` mapea dni → EmpleadoResponse (los que ya están en la base)."""

    def __init__(self, existentes: dict) -> None:
        super().__init__()
        self._por_dni = dict(existentes)
        self._por_legajo = {e.legajo: e for e in existentes.values() if e.legajo}

    def find_by_dni(self, dni, empresa_id=None):
        self._reg("find_by_dni")
        emp = self._por_dni.get(str(dni))
        if emp and empresa_id and emp.empresa_id != str(empresa_id):
            return None   # ← sin esto el fake sería permisivo y no desmentiría nada
        return emp

    def find_by_legajo(self, legajo, empresa_id=None):
        self._reg("find_by_legajo")
        return self._por_legajo.get(str(legajo))

    def find_by_id(self, id, empresa_id=None):
        self._reg("find_by_id")
        return next((e for e in self._por_dni.values() if e.id == str(id)), None)

    def save(self, data, empresa_id):
        self._reg("save")
        return _empleado(str(uuid4()), data.dni or "", getattr(data, "legajo", None))

    def update(self, id, data, empresa_id=None):
        self._reg("update")
        return _empleado(str(id), "30111222")

    def dar_de_baja(self, empleado_id, fecha_egreso, empresa_id=None):
        self._reg("dar_de_baja")
        return True


class _AreaRepo(_Contador):
    def find_by_id(self, id, empresa_id=None):
        self._reg("area_find_by_id")   # ← el lookup que el fix elimina
        return {"id": str(id), "empresa_id": empresa_id}


class _Audit:
    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


class _Catalogos:
    """Resuelve empresa/área sin tocar la base y expone el área como YA VALIDADA — es lo que
    hace el NominaCatalogos real después de primar su cache."""

    def empresa_id(self, nombre):
        return EMPRESA_A

    def area_id(self, empresa_id, nombre):
        return AREA_A

    def areas_validadas(self):
        return frozenset({AREA_A})


class _Noop:
    """Proyectos y cesiones: fuera del alcance de estos tests (son best-effort y no propagan)."""

    def resolver_y_asignar(self, *a, **k):
        pass

    def crear_si_falta(self, *a, **k):
        pass


def _servicio(existentes=None, monkeypatch=None):
    """Arma el service con todos los colaboradores falsos. Devuelve (svc, emp_repo, area_repo, audit)."""
    from services import empleado_service as es

    emp_repo = _EmpleadoRepo(existentes or {})
    area_repo = _AreaRepo()
    audit = _Audit()

    svc = NominaEmpleadosImportService.__new__(NominaEmpleadosImportService)
    svc._usuario_id = "u1"
    svc._catalogos = _Catalogos()
    svc._empleados = es.EmpleadoService(repo=emp_repo, audit=audit, area_repo=area_repo)
    svc._emp_repo = emp_repo
    svc._audit = audit
    svc._seen_dni = set()
    svc._seen_legajo = set()
    svc._proyectos = _Noop()
    svc._cesiones = _Noop()
    return svc, emp_repo, area_repo, audit


class TestElImportSigueHaciendoLoMismo:
    def test_crea_un_empleado_nuevo(self):
        """Garantía de no-regresión: el alta sigue funcionando y se reporta como creada.

        Para que falle: que `save` no se invoque, o que el resultado no clasifique la fila."""
        svc, emp_repo, _, _ = _servicio()
        r = svc.importar(_csv([_fila()]), "n.csv")
        assert (r.total, r.creados, r.actualizados, r.cargados_ok) == (1, 1, 0, 1)
        assert emp_repo.cuenta("save") == 1
        assert emp_repo.cuenta("update") == 0

    def test_actualiza_si_el_dni_ya_existe(self):
        """Dedup por DNI: la segunda corrida actualiza, no duplica.

        Para que falle: que `find_by_dni` del fake devuelva None siempre — ahí el import crearía
        de nuevo y `actualizados` daría 0."""
        existente = _empleado(str(uuid4()), "30111222")
        svc, emp_repo, _, _ = _servicio({"30111222": existente})
        r = svc.importar(_csv([_fila()]), "n.csv")
        assert (r.creados, r.actualizados) == (0, 1)
        assert emp_repo.cuenta("update") == 1
        assert emp_repo.cuenta("save") == 0

    def test_fila_sin_email_va_a_con_faltantes_y_se_carga_igual(self):
        """El éxito parcial no cambió: se crea el empleado y se reporta el faltante."""
        svc, _, _, _ = _servicio()
        r = svc.importar(_csv([_fila(Email="")]), "n.csv")
        assert r.creados == 1 and r.cargados_ok == 0
        assert [f.faltan for f in r.con_faltantes] == [["email"]]

    def test_fila_sin_obligatorio_no_se_carga_y_dice_por_que(self):
        """El reporte por fila sigue nombrando la fila y el motivo, sin abortar el lote."""
        svc, _, _, _ = _servicio()
        r = svc.importar(_csv([_fila(), _fila(dni="", apellido="SinDni")]), "n.csv")
        assert r.creados == 1
        assert len(r.no_cargados) == 1
        assert r.no_cargados[0].fila == 3          # header=1, primera fila=2
        assert "DNI" in r.no_cargados[0].motivo


class TestLosLookupsRedundantesYaNoSeInvocan:
    def test_el_area_no_se_revalida_contra_la_base(self):
        """(a) `ensure_area_valida` recibe el área ya validada por el cache de catálogos.

        🔴 Para que falle: que `_empleados_write` deje de pasar `areas_validadas`, o que
        `ensure_area_valida` ignore el set. El fake de áreas CUENTA sus llamadas — sin ese
        contador, el test no podría distinguir "no se llamó" de "se llamó y devolvió algo"."""
        svc, _, area_repo, _ = _servicio()
        svc.importar(_csv([_fila(), _fila(dni="30111223"), _fila(dni="30111224")]), "n.csv")
        assert area_repo.cuenta("area_find_by_id") == 0

    def test_el_update_no_relee_la_fila_anterior(self):
        """(b) El `prior` del diff viene del `find_by_dni`, no de un segundo `find_by_id`.

        Para que falle: que el import deje de pasar `prior=existente`. Ahí `actualizar` haría su
        propio `find_by_id` y el contador lo delataría."""
        existente = _empleado(str(uuid4()), "30111222")
        svc, emp_repo, _, _ = _servicio({"30111222": existente})
        svc.importar(_csv([_fila()]), "n.csv")
        assert emp_repo.cuenta("find_by_dni") == 1
        assert emp_repo.cuenta("find_by_id") == 0

    def test_el_diff_del_update_usa_la_fila_precargada(self):
        """El `prior` precargado tiene que producir un diff REAL, no uno vacío ni fantasma.

        Es la contracara del test anterior: ahorrar la query no sirve si el evento sale mal.
        `find_by_dni` y `find_by_id` devuelven la misma forma (los dos usan el SELECT con joins
        de _empleado_row), así que no puede aparecer el diff fantasma de campos derivados."""
        existente = _empleado(str(uuid4()), "30111222")
        svc, _, _, audit = _servicio({"30111222": existente})
        svc.importar(_csv([_fila()]), "n.csv")
        updates = [e for e in audit.eventos if e["evento"] == "update_empleado"]
        assert len(updates) == 1
        assert updates[0]["datos_anteriores"] is not None

    def test_precargado_evita_las_tres_queries_de_la_asignacion(self):
        """(c)+(d) AsignacionPrecargada reemplaza proyecto + empresa + estado del empleado.

        Se prueba sobre AsignacionesService directamente: los repos cuentan sus llamadas, así
        que con `precargado` los tres contadores quedan en 0 y sin él en 1. Para que falle:
        que `asignar`/`_asignar_uno` ignoren el argumento."""
        from services import asignaciones_service as asig_mod
        from services.asignaciones_service import AsignacionPrecargada, AsignacionesService
        from schemas.proyectos import AsignacionCreate

        lookups: list[str] = []

        class _ProyRepo:
            def find_by_id(self, id, empresa_id=None):
                lookups.append("proyecto")
                return {"id": id}

        class _AsigRepo:
            def save(self, *a, **k):
                return {"ok": True}

        svc = AsignacionesService(repo=_AsigRepo(), proyectos_repo=_ProyRepo())
        monkey = {"empresa": 0, "estado": 0}
        asig_mod.find_empresa_for_empleado = lambda _e: (monkey.__setitem__("empresa", monkey["empresa"] + 1) or EMPRESA_A)
        asig_mod.get_estado_empleado = lambda _e: (monkey.__setitem__("estado", monkey["estado"] + 1) or "activo")

        data = AsignacionCreate(empleado_id=uuid4(), rol="Analista")
        svc._repo.save = lambda *a, **k: _empleado(str(uuid4()), "1")  # type: ignore[assignment]

        svc.asignar(uuid4(), data, None, precargado=AsignacionPrecargada(True, EMPRESA_A, "activo"))
        assert lookups == [] and monkey == {"empresa": 0, "estado": 0}

        svc.asignar(uuid4(), data, None)   # sin precargado: los tres lookups vuelven
        assert lookups == ["proyecto"] and monkey == {"empresa": 1, "estado": 1}

    def test_una_baja_no_se_asigna_pero_si_se_da_de_baja(self):
        """La fila con Fecha Baja sigue llamando `dar_de_baja` (no se optimizó ese camino)."""
        svc, emp_repo, _, _ = _servicio()
        svc.importar(_csv([_fila(**{"Fecha Baja": "31/12/2025"})]), "n.csv")
        assert emp_repo.cuenta("dar_de_baja") == 1


class TestLegajo:
    def test_un_csv_sin_columna_legajo_se_importa_igual(self):
        """🔴 Legajo es OPCIONAL: sin la columna, el archivo entra completo y sin error.

        Para que falle: que "Legajo" se agregue a HEADERS en vez de a HEADERS_OPCIONALES. Ahí
        `validar_headers` devolvería "Faltan columnas: Legajo" y el import daría 0 empleados."""
        svc, _, _, _ = _servicio()
        r = svc.importar(_csv([_fila()], con_legajo=False), "n.csv")
        assert r.creados == 1 and r.no_cargados == []
        assert "Legajo" not in tx.HEADERS and "Legajo" in tx.HEADERS_OPCIONALES

    def test_el_legajo_se_lee_y_viaja_al_empleado(self):
        """Con la columna presente, el valor llega al payload del alta.

        Para que falle: que `parsear_fila` no extraiga "Legajo" o que `_base_nomina` no lo pase.
        Se mira el objeto que recibió `save`, no una constante del test."""
        recibidos = []

        svc, emp_repo, _, _ = _servicio()
        original = emp_repo.save
        emp_repo.save = lambda data, empresa_id: (recibidos.append(data) or original(data, empresa_id))

        svc.importar(_csv([_fila(Legajo="A-100")], con_legajo=True), "n.csv")
        assert recibidos[0].legajo == "A-100"

    def test_dos_filas_del_mismo_legajo_dan_motivo_legible(self):
        """🔴 El duplicado INTRA-ARCHIVO lo atrapa `_seen_legajo`, no Postgres.

        `ensure_legajo_unico` valida contra la BASE: las dos filas la pasan porque ninguna está
        cargada todavía, y la segunda reventaría en el INSERT con el texto de
        `empleados_legajo_empresa_key`. Para que falle: borrar `_seen_legajo` del service — ahí
        la fila 3 se "cargaría" y `no_cargados` quedaría vacío."""
        svc, _, _, _ = _servicio()
        r = svc.importar(_csv([
            _fila(Legajo="A-100"),
            _fila(Legajo="A-100", dni="30111223", apellido="Otro"),
        ], con_legajo=True), "n.csv")
        assert r.creados == 1
        assert len(r.no_cargados) == 1
        assert r.no_cargados[0].fila == 3
        assert "Legajo duplicado" in r.no_cargados[0].motivo

    def test_legajo_duplicado_contra_la_base_da_409_legible(self):
        """El duplicado contra la BASE lo atrapa `ensure_legajo_unico` (AppError, no error de DB).

        El empleado existente tiene OTRO dni, así que la fila entra por la rama de alta y choca
        con su legajo. Para que falle: que `find_by_legajo` del fake devuelva None siempre."""
        otro = _empleado(str(uuid4()), "99999999", legajo="A-100")
        svc, _, _, _ = _servicio({"99999999": otro})
        r = svc.importar(_csv([_fila(Legajo="A-100")], con_legajo=True), "n.csv")
        assert r.creados == 0
        assert len(r.no_cargados) == 1
        assert "legajo" in r.no_cargados[0].motivo.lower()

    def test_sin_legajo_no_se_consulta_find_by_legajo(self):
        """Un CSV sin legajo no paga la query de unicidad: `ensure_legajo_unico` corta en su guard.

        Es el dato que decide cuánto sube el conteo de round-trips al activar legajo."""
        svc, emp_repo, _, _ = _servicio()
        svc.importar(_csv([_fila()], con_legajo=False), "n.csv")
        assert emp_repo.cuenta("find_by_legajo") == 0

        svc2, emp_repo2, _, _ = _servicio()
        svc2.importar(_csv([_fila(Legajo="A-1")], con_legajo=True), "n.csv")
        assert emp_repo2.cuenta("find_by_legajo") == 1   # +1 por fila CON legajo


class TestAuditoriaConsolidada:
    def test_cinco_altas_dan_un_evento_de_lote_con_los_cinco_ids(self):
        """🔴 La regla del repo: un evento por lote, no uno por fila.

        Para que falle: que `create_empleado` se llame sin `auditar=False` (volverían los 5
        eventos INSERT individuales) o que el payload no lleve `empleado_ids_creados`."""
        svc, _, _, audit = _servicio()
        filas = [_fila(dni=f"3011122{i}", apellido=f"E{i}") for i in range(5)]
        r = svc.importar(_csv(filas), "nomina.csv")
        assert r.creados == 5

        assert [e["evento"] for e in audit.eventos] == ["importacion_nomina"]
        datos = audit.eventos[0]["datos_nuevos"]
        assert datos["creados"] == 5
        assert datos["archivo"] == "nomina.csv"
        assert len(datos["empleado_ids_creados"]) == 5
        assert len(set(datos["empleado_ids_creados"])) == 5   # ids distintos, no el mismo 5 veces

    def test_el_update_conserva_su_evento_individual_con_diff(self):
        """Un UPDATE responde "¿qué cambió?" y eso no se reconstruye desde un id → evento propio.

        Para que falle: que `actualizar` también reciba auditar=False. Ahí quedaría solo el
        evento de lote y se perdería el rastro de que el reimport pisó datos."""
        existente = _empleado(str(uuid4()), "30111222")
        svc, _, _, audit = _servicio({"30111222": existente})
        svc.importar(_csv([_fila(), _fila(dni="30111299", apellido="Nueva")]), "nomina.csv")

        eventos = [e["evento"] for e in audit.eventos]
        assert eventos.count("update_empleado") == 1      # el update conserva el suyo
        assert eventos.count("alta_empleado") == 0        # el alta se consolidó
        assert eventos.count("importacion_nomina") == 1

        lote = next(e for e in audit.eventos if e["evento"] == "importacion_nomina")
        assert lote["datos_nuevos"]["actualizados"] == 1
        assert len(lote["datos_nuevos"]["empleado_ids_creados"]) == 1   # solo la alta

    def test_el_alta_manual_sigue_auditando(self):
        """`auditar=False` es SOLO del import: el default deja el alta desde la ficha intacta.

        Para que falle: que el default de `auditar` en `EmpleadoService.create_empleado` pase a
        False. Ese es el riesgo real de agregar un flag así, y es el default que ven todos los
        callers.

        ⚠️ Verificado por mutación, con un matiz: cambiar el default de la capa de ADENTRO
        (`_empleados_write.crear`) NO hace fallar este test, porque el service pasa su propio
        valor explícito y lo tapa. Los dos defaults en True son defensa en profundidad; este
        test guarda el de arriba, que es el que un caller puede alcanzar."""
        from services import empleado_service as es
        from schemas.empleado import EmpleadoCreate

        emp_repo, area_repo, audit = _EmpleadoRepo({}), _AreaRepo(), _Audit()
        svc = es.EmpleadoService(repo=emp_repo, audit=audit, area_repo=area_repo)
        svc.create_empleado(EmpleadoCreate.model_validate({
            "nombre": "Ana", "apellido": "P", "email_corporativo": "a@k.com", "dni": "1",
            "area_id": AREA_A, "roles": ["Analista"], "fecha_ingreso": "2024-01-01",
            "empresa_id": EMPRESA_A, "tipo_contrato": "efectivo",
        }), "u1", EMPRESA_A)
        assert [e["evento"] for e in audit.eventos] == ["alta_empleado"]
        # Y sin `areas_validadas`, el área SÍ se valida contra la base: el atajo es solo del import.
        assert area_repo.cuenta("area_find_by_id") == 1


class TestModalidadYNivel:
    def test_la_distribucion_sale_de_tipo_contrato(self):
        """🔴 R4 y el KPI leen `tipo_contrato`, la columna que el import realmente escribe.

        Antes leían `modalidad_contratacion`, que ningún camino escribía: el reporte decía
        "Sin especificar" para toda la plantilla teniendo el dato al lado. Para que falle:
        volver el `select` a la columna vieja — estas filas no la tienen y todo caería en
        "Sin especificar"."""
        import inspect

        from services.reportes import _reporte_distribucion as dist
        fuente = inspect.getsource(dist)
        assert "tipo_contrato" in fuente
        assert "modalidad_contratacion" not in fuente.replace("ex `modalidad_contratacion`", "")

    def test_modalidad_contratacion_y_nivel_no_existen_en_los_schemas(self):
        """Las dos columnas se borran en la migración 084 → ningún schema puede pedirlas.

        Si un *Response las declarara, PostgREST devolvería 42703 y el listado entero fallaría.
        Para que falle: dejar la declaración en cualquiera de los tres schemas."""
        from schemas.empleado import EmpleadoCreate, EmpleadoUpdate
        from schemas.empleado_out import EmpleadoResponse as EmpleadoOut

        for modelo in (EmpleadoCreate, EmpleadoUpdate, EmpleadoOut):
            campos = modelo.model_fields
            assert "modalidad_contratacion" not in campos, modelo.__name__
            assert "nivel" not in campos, modelo.__name__

    def test_modalidad_trabajo_no_se_toco(self):
        """⚠️ Es OTRO concepto (dónde trabaja) y sigue vivo, con su default "presencial".

        Ese 19/19 en producción NO es un dato cargado: es el default del schema, porque el CSV
        no trae la columna. Se afirma acá para que quede escrito en un test y no solo en un
        comentario."""
        from schemas.empleado import EmpleadoCreate
        campo = EmpleadoCreate.model_fields["modalidad_trabajo"]
        assert campo.default == "presencial"

    def test_el_autocompletado_ya_no_expone_la_columna_borrada(self):
        """`CAMPOS_AUTOCOMPLETABLES` es la whitelist del endpoint /valores-conocidos: si dejara
        la columna borrada, ese endpoint daría 42703."""
        from services.empleado_catalogos_service import CAMPOS_AUTOCOMPLETABLES
        assert "modalidad_contratacion" not in CAMPOS_AUTOCOMPLETABLES
        assert "tipo_contrato" in CAMPOS_AUTOCOMPLETABLES


class TestRoundTripsPorFila:
    """🔴 La métrica que decide si el batch sigue siendo necesario. Cuenta las idas a la base
    de un alta y de un update, con proyectos/cesiones neutralizados (son otro eje)."""

    def test_conteo_de_un_alta(self):
        """Alta: find_by_dni + save. Nada más — ni área, ni auditoría individual."""
        svc, emp_repo, area_repo, _ = _servicio()
        svc.importar(_csv([_fila()]), "n.csv")
        total = len(emp_repo.llamadas) + len(area_repo.llamadas)
        assert emp_repo.llamadas == ["find_by_dni", "save"]
        assert total == 2, f"un alta debería costar 2 idas a la base, costó {total}"

    def test_conteo_de_un_update(self):
        """Update: find_by_dni + update. El `prior` y el área ya no se consultan."""
        existente = _empleado(str(uuid4()), "30111222")
        svc, emp_repo, area_repo, _ = _servicio({"30111222": existente})
        svc.importar(_csv([_fila()]), "n.csv")
        total = len(emp_repo.llamadas) + len(area_repo.llamadas)
        assert emp_repo.llamadas == ["find_by_dni", "update"]
        assert total == 2, f"un update debería costar 2 idas a la base, costó {total}"

    def test_conteo_de_un_alta_con_legajo(self):
        """Con legajo se suma UNA query (`ensure_legajo_unico` deja de ser no-op)."""
        svc, emp_repo, area_repo, _ = _servicio()
        svc.importar(_csv([_fila(Legajo="A-1")], con_legajo=True), "n.csv")
        total = len(emp_repo.llamadas) + len(area_repo.llamadas)
        assert emp_repo.llamadas == ["find_by_dni", "find_by_legajo", "save"]
        assert total == 3, f"un alta con legajo debería costar 3, costó {total}"
