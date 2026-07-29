"""
Tests de la RECUPERABILIDAD del import de nómina — sin red.

El problema que cubren: hoy, si el request muere por timeout, quedan N empleados cargados, el
resto no, y el reporte por fila (qué falló y por qué) muere con el request. RRHH ve un error
genérico y no sabe dónde quedó. La solución es un presupuesto de tiempo: el import para ENTRE
FILAS y devuelve el reporte de lo que hizo.

  1. Presupuesto amplio → todas las filas, comportamiento idéntico a antes.
  2. Presupuesto chico → corta, y dice hasta qué fila llegó y cuántas quedaron.
  3. El corte NUNCA parte una fila al medio.
  4. El evento de lote se emite TAMBIÉN en el corte, marcado parcial, con los ids de las altas.
  5. Reintentar continúa donde quedó, y el resultado final iguala a un import completo.
  6. Reimportar lo mismo NO genera eventos de auditoría (diff vacío).
  7. El tiempo se loguea siempre, no solo en el corte.

⚠️ EL RELOJ ES INYECTADO (`LoteNomina(reloj=...)`), no un `sleep`. Un test que durmiera de
verdad sería lento y, peor, dependería de la velocidad de la máquina: en un CI lento cortaría en
otra fila y el test sería flakeante. Con un reloj falso el corte es DETERMINÍSTICO — la fila
exacta en la que corta es parte de la aserción.

¿Qué tendría que ser distinto en el fake para que cada test pueda fallar? En cada docstring.
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

from schemas.empleado import EmpleadoResponse
from services._nomina_lote import LoteNomina
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


def _csv(n_filas: int) -> str:
    """CSV de `n_filas` filas válidas, con DNI distinto cada una."""
    out = [";".join(_COLUMNAS)]
    for i in range(n_filas):
        fila = {
            "Apellido": f"Ap{i}", "Nombre": f"No{i}", "DNI": f"3000000{i:02d}",
            "Organismo": "ACME", "Sector": "SISTEMAS", "Rol": "Analista",
            "Fecha Ingreso": "1/3/2024", "Email": f"e{i}@k.com",
        }
        out.append(";".join(str(fila.get(c, "")) for c in _COLUMNAS))
    return "\r\n".join(out) + "\r\n"


def _empleado(id_: str, dni: str) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": id_, "nombre": "N", "apellido": "A", "email_corporativo": f"{dni}@k.com",
        "empresa_id": EMPRESA_A, "area_id": AREA_A, "roles": ["Analista"], "dni": dni,
        "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


class _RelojFalso:
    """Reloj determinístico: la PRIMERA lectura da 0 y cada siguiente avanza `paso` segundos.

    La primera lectura no avanza a propósito: es la que `LoteNomina.__init__` usa como línea de
    base (`_inicio`). Si contara como un paso, "1 s por fila" daría una fila menos que lo que
    dice el nombre y el cálculo esperado del test sería un off-by-one difícil de leer.

    Con `paso=1` y `presupuesto=P`, la fila k ve k-1 segundos consumidos, así que se procesan
    exactamente P filas. Determinístico: el corte cae siempre en la misma fila, sin depender de
    la velocidad de la máquina (un `sleep` real haría el test lento y flakeante en CI).
    """

    def __init__(self, paso: float = 1.0) -> None:
        self.paso = paso
        self.ahora = 0.0
        self._primera = True

    def __call__(self) -> float:
        if self._primera:
            self._primera = False
            return 0.0
        valor = self.ahora
        self.ahora += self.paso
        return valor


class _EmpleadoRepo:
    """Base falsa que PERSISTE entre corridas: es lo que permite probar el reintento.

    HONRA empresa_id (devuelve None si no coincide) y construye la respuesta a partir del dni
    recibido, no de una constante.
    """

    def __init__(self) -> None:
        self.por_dni: dict[str, EmpleadoResponse] = {}
        self.updates: list[str] = []

    def find_by_dni(self, dni, empresa_id=None):
        emp = self.por_dni.get(str(dni))
        if emp and empresa_id and emp.empresa_id != str(empresa_id):
            return None
        return emp

    def find_by_legajo(self, legajo, empresa_id=None):
        return None

    def find_by_id(self, id, empresa_id=None):
        return next((e for e in self.por_dni.values() if e.id == str(id)), None)

    def save(self, data, empresa_id):
        emp = _empleado(str(uuid4()), data.dni or "")
        self.por_dni[data.dni or ""] = emp        # ← persiste: el reintento lo va a encontrar
        return emp

    def update(self, id, data, empresa_id=None):
        emp = next(e for e in self.por_dni.values() if e.id == str(id))
        self.updates.append(emp.dni or "")
        return emp                                # mismos valores → diff vacío

    def dar_de_baja(self, empleado_id, fecha_egreso, empresa_id=None):
        return True


class _AreaRepo:
    def find_by_id(self, id, empresa_id=None):
        return {"id": str(id), "empresa_id": empresa_id}


class _Audit:
    """Fake de AuditService que delega en el REAL para decidir si registra.

    🔴 Es la única forma de que el test de "un update sin cambios no audita" pueda fallar: si
    este fake solo apilara lo que recibe, estaría probando el fake y no la regla de
    `AuditService.registrar`.
    """

    def __init__(self) -> None:
        self.eventos: list[dict] = []
        from services.audit_service import _es_update_sin_cambios
        self._omitir = _es_update_sin_cambios

    def registrar(self, **kw) -> None:
        if self._omitir(kw.get("accion", ""), kw.get("datos_anteriores"), kw.get("datos_nuevos")):
            return
        self.eventos.append(kw)


class _Catalogos:
    def empresa_id(self, nombre):
        return EMPRESA_A

    def area_id(self, empresa_id, nombre):
        return AREA_A

    def areas_validadas(self):
        return frozenset({AREA_A})


class _Noop:
    def resolver_y_asignar(self, *a, **k):
        pass

    def crear_si_falta(self, *a, **k):
        pass


def _servicio(emp_repo=None, audit=None):
    """Service con colaboradores falsos. `emp_repo` y `audit` se pueden reusar entre corridas
    para simular un reintento contra la misma base."""
    from services import empleado_service as es

    emp_repo = emp_repo or _EmpleadoRepo()
    audit = audit or _Audit()
    svc = NominaEmpleadosImportService.__new__(NominaEmpleadosImportService)
    svc._usuario_id = "u1"
    svc._catalogos = _Catalogos()
    svc._empleados = es.EmpleadoService(repo=emp_repo, audit=audit, area_repo=_AreaRepo())
    svc._emp_repo = emp_repo
    svc._audit = audit
    svc._seen_dni = set()
    svc._seen_legajo = set()
    svc._proyectos = _Noop()
    svc._cesiones = _Noop()
    return svc, emp_repo, audit


class TestPresupuestoAmplio:
    def test_se_procesan_todas_las_filas(self):
        """Con presupuesto de sobra el comportamiento es IDÉNTICO al de antes: nada de parcial.

        Para que falle: que `hay_margen` devuelva False de más (p. ej. comparando con <= en vez
        de <, o midiendo mal el inicio)."""
        svc, _, _ = _servicio()
        r = svc.importar(_csv(10), "n.csv", presupuesto=10_000)
        assert (r.total, r.creados) == (10, 10)
        assert r.parcial is False
        assert r.filas_sin_procesar == 0
        assert r.ultima_fila_procesada == 11        # header=1, 10 filas → la última es la 11

    def test_por_default_HAY_presupuesto(self):
        """🔴 El default de la env var tiene que ENFORZAR un presupuesto, no ser 0 (sin límite).

        No es restatear la constante: la propiedad que importa es que la protección exista sin
        configurar nada. Verificado por mutación: con el default en 0 la suite entera pasaba, o
        sea que un cambio a 0 —que apaga la recuperabilidad en silencio— no lo veía nadie."""
        from config.settings import settings

        assert settings.import_presupuesto_segundos > 0
        assert LoteNomina()._presupuesto == settings.import_presupuesto_segundos

    def test_una_fila_rechazada_cuenta_como_procesada(self):
        """Una fila que va a `no_cargados` YA SE MIRÓ: cuenta para "hasta dónde llegué".

        Importa para el mensaje del reintento: si una fila rechazada no avanzara
        `ultima_fila_procesada`, el reporte diría que se llegó más atrás de lo real y RRHH
        buscaría el corte en el lugar equivocado. Y el reintento la va a rechazar igual, así que
        no es trabajo pendiente. Verificado por mutación: sin la línea que la registra, la suite
        entera pasaba."""
        svc, _, _ = _servicio()
        # 🔴 La fila que falla tiene que ser la ÚLTIMA. Si fallara una del medio, la siguiente
        # fila exitosa sobreescribiría `ultima_fila_procesada` y el test pasaría igual con la
        # línea borrada — verificado por mutación.
        # El DNI se recalcula con la misma fórmula que `_csv` en vez de hardcodearlo: si esa
        # fórmula cambia, el reemplazo sigue funcionando en vez de quedar sin efecto en silencio.
        original = _csv(3).split("\r\n")
        filas = list(original)
        filas[3] = filas[3].replace(f"3000000{2:02d}", "", 1)   # fila 4 del archivo, sin DNI
        assert filas[3] != original[3], "el reemplazo no tuvo efecto"
        r = svc.importar("\r\n".join(filas), "n.csv", presupuesto=10_000)

        assert len(r.no_cargados) == 1 and r.no_cargados[0].fila == 4
        assert r.total == 3 and r.creados == 2
        assert r.ultima_fila_procesada == 4   # la 4 falló, y aun así cuenta como procesada

    def test_presupuesto_cero_significa_sin_limite(self):
        """Un presupuesto <= 0 procesa TODO, no corta en la fila 1.

        Es el degradado seguro: si alguien configura la env var en 0 por error, el import se
        comporta como antes en vez de no cargar nada. Para que falle: quitar el guard de
        `_presupuesto <= 0` — ahí `segundos() < 0` sería False y cortaría de entrada."""
        svc, _, _ = _servicio()
        r = svc.importar(_csv(5), "n.csv", presupuesto=0)
        assert r.total == 5 and r.parcial is False


class TestPresupuestoChico:
    def test_corta_y_dice_hasta_donde_llego(self):
        """Reloj que avanza 1 s por consulta, presupuesto 3 s → procesa 3 filas de 10.

        El reloj se consulta una vez por `hay_margen` (t=0,1,2,3...): en la cuarta vuelta
        `segundos()` da 3, que ya NO es < 3, así que corta. Para que falle: que el corte no
        marque `parcial`, o que `filas_sin_procesar` no descuente las procesadas."""
        svc, emp_repo, _ = _servicio()
        lote = LoteNomina(presupuesto=3, reloj=_RelojFalso(1.0))
        r = self._importar_con_lote(svc, _csv(10), lote)

        assert r.parcial is True
        assert r.total == 3
        assert r.creados == 3
        assert r.ultima_fila_procesada == 4          # header=1 → filas 2, 3 y 4
        assert r.filas_sin_procesar == 7             # 10 - 3
        assert len(emp_repo.por_dni) == 3            # y en la base quedaron esas 3

    def test_el_corte_no_parte_una_fila_al_medio(self):
        """Toda fila contada está COMPLETA: nada a mitad de camino.

        La invariante que se afirma: `total` (filas contadas) == filas efectivamente clasificadas
        en alguno de los tres grupos, y == empleados escritos. Si el chequeo de presupuesto
        estuviera DENTRO de `_procesar_fila`, una fila quedaría contada sin empleado escrito y
        esta igualdad se rompería.

        ⚠️ Lo que este test NO fija, verificado por mutación: que el chequeo esté ANTES y no
        DESPUÉS de la fila. Mover `hay_margen` después tampoco parte una fila —solo procesa una
        más— así que estas invariantes siguen valiendo. Eso lo pinnea el conteo exacto de
        `test_corta_y_dice_hasta_donde_llego`, que sí falla con la mutación."""
        svc, emp_repo, _ = _servicio()
        lote = LoteNomina(presupuesto=4, reloj=_RelojFalso(1.0))
        r = self._importar_con_lote(svc, _csv(12), lote)

        clasificadas = r.cargados_ok + len(r.con_faltantes) + len(r.no_cargados)
        assert r.total == clasificadas
        assert r.total == len(emp_repo.por_dni)
        assert r.total + r.filas_sin_procesar == 12   # ninguna fila se pierde de la cuenta

    def test_el_evento_de_lote_se_emite_en_el_corte_marcado_parcial(self):
        """🔴 El evento es el ÚNICO rastro de las altas (ya no emiten evento individual).

        Si se emitiera solo al terminar el archivo, un corte dejaría N empleados creados sin una
        línea en `auditoria`. Para que falle: mover el `registrar` adentro del `for`, o ponerlo
        detrás de un `if not lote.parcial`."""
        svc, _, audit = _servicio()
        lote = LoteNomina(presupuesto=3, reloj=_RelojFalso(1.0))
        r = self._importar_con_lote(svc, _csv(10), lote)

        lotes = [e for e in audit.eventos if e["evento"] == "importacion_nomina"]
        assert len(lotes) == 1
        datos = lotes[0]["datos_nuevos"]
        assert datos["parcial"] is True
        assert datos["creados"] == 3
        assert len(datos["empleado_ids_creados"]) == 3   # las altas hechas, nominadas
        assert r.creados == 3

    def test_el_evento_de_un_import_completo_dice_parcial_false(self):
        """El flag va SIEMPRE, no solo en el corte: un evento sin el campo sería ambiguo."""
        svc, _, audit = _servicio()
        svc.importar(_csv(3), "n.csv", presupuesto=10_000)
        lote_ev = next(e for e in audit.eventos if e["evento"] == "importacion_nomina")
        assert lote_ev["datos_nuevos"]["parcial"] is False

    @staticmethod
    def _importar_con_lote(svc, contenido, lote):
        """Corre `importar` forzando un LoteNomina con reloj falso.

        Se parchea la clase en el módulo del service (no se pasa el lote por parámetro) para no
        ensanchar la firma pública solo por los tests."""
        import services.nomina_empleados_service as mod
        original = mod.LoteNomina
        mod.LoteNomina = lambda _presupuesto=None: lote
        try:
            return svc.importar(contenido, "n.csv")
        finally:
            mod.LoteNomina = original


class TestReintento:
    def test_reimportar_continua_donde_quedo_y_el_final_es_identico(self):
        """🔴 El reintento se apoya SOLO en el dedup por DNI — no hay estado de progreso.

        Corte en la fila 3 de 10 → reintento con el mismo archivo → las 3 ya cargadas van por
        UPDATE y las 7 que faltaban por ALTA. El total final iguala a un import completo.

        Para que falle: que `_EmpleadoRepo.save` no persistiera en `por_dni`. Ahí el reintento
        no encontraría nada y crearía 10 empleados nuevos, duplicando los 3 primeros."""
        svc, emp_repo, audit = _servicio()
        lote = LoteNomina(presupuesto=3, reloj=_RelojFalso(1.0))
        primero = TestPresupuestoChico._importar_con_lote(svc, _csv(10), lote)
        assert primero.parcial is True and primero.creados == 3

        # Reintento: MISMO archivo, MISMA base, servicio nuevo (como un request nuevo).
        svc2, emp_repo2, _ = _servicio(emp_repo=emp_repo, audit=audit)
        segundo = svc2.importar(_csv(10), "n.csv", presupuesto=10_000)

        assert segundo.parcial is False
        assert segundo.total == 10
        assert segundo.actualizados == 3     # las del primer tramo
        assert segundo.creados == 7          # las que faltaban
        assert len(emp_repo2.por_dni) == 10  # ni un duplicado
        assert sorted(emp_repo2.updates) == sorted(["300000000", "300000001", "300000002"])

    def test_reimportar_lo_mismo_no_genera_eventos_de_auditoria(self):
        """🔴 Un update cuyo diff sale vacío no se registra: 73 eventos con `{}` no registran nada.

        Para que falle: que `_Audit` apile todo sin consultar `_es_update_sin_cambios` — ahí el
        test pasaría con la regla borrada del service real. El fake delega en la función REAL
        justamente para que no pueda mentir."""
        svc, emp_repo, audit = _servicio()
        svc.importar(_csv(5), "n.csv", presupuesto=10_000)
        eventos_primera = len(audit.eventos)
        assert eventos_primera == 1           # solo el de lote (las altas van consolidadas)

        svc2, _, _ = _servicio(emp_repo=emp_repo, audit=audit)
        r = svc2.importar(_csv(5), "n.csv", presupuesto=10_000)

        assert r.actualizados == 5
        nuevos = audit.eventos[eventos_primera:]
        assert [e["evento"] for e in nuevos] == ["importacion_nomina"]   # cero update_empleado

    def test_un_update_que_si_cambia_algo_sigue_auditando(self):
        """La contracara: la regla solo omite el diff VACÍO, no todos los updates.

        Sin este test, "no auditar updates vacíos" podría implementarse como "no auditar updates"
        y nadie se enteraría. El fake de `update` devuelve una fila con el apellido cambiado, así
        que el diff tiene contenido real."""
        from schemas.empleado import EmpleadoUpdate
        from services import empleado_service as es

        emp_repo, audit = _EmpleadoRepo(), _Audit()
        emp = _empleado(str(uuid4()), "300000000")
        emp_repo.por_dni["300000000"] = emp

        def _update_con_cambio(id, data, empresa_id=None):
            return emp.model_copy(update={"apellido": "CAMBIADO"})

        emp_repo.update = _update_con_cambio            # type: ignore[method-assign]
        svc = es.EmpleadoService(repo=emp_repo, audit=audit, area_repo=_AreaRepo())
        svc.update_empleado(emp.id, EmpleadoUpdate(apellido="CAMBIADO"), None, "u1", prior=emp)

        updates = [e for e in audit.eventos if e["evento"] == "update_empleado"]
        assert len(updates) == 1
        assert updates[0]["datos_nuevos"]["apellido"] == "CAMBIADO"


class TestLaReglaDelUpdateVacio:
    """🔴 `{}` vs `None` en un evento de auditoría: la distinción que hace segura la omisión.

    Se prueba sobre `AuditService.registrar` con un repo falso —no sobre la función pura— porque
    lo que importa es si el evento LLEGA a la base. Sin esta clase, cambiar `== {}` por un chequeo
    de "falsy" pasaba la suite entera: verificado por mutación, sobrevivía a los 1094 tests.
    """

    @staticmethod
    def _service():
        from services.audit_service import AuditService

        class _Repo:
            def __init__(self):
                self.insertados: list[dict] = []

            def registrar(self, payload):
                self.insertados.append(payload)

        repo = _Repo()
        return AuditService(repo=repo), repo

    def test_un_update_con_diff_vacio_no_llega_a_la_base(self):
        """`{}` = "difeé y no hubo cambios" → el evento no dice nada y se omite."""
        svc, repo = self._service()
        svc.registrar(usuario_id="u1", entidad="empleado", registro_id=str(uuid4()),
                      accion="UPDATE", evento="update_empleado",
                      datos_anteriores={}, datos_nuevos={})
        assert repo.insertados == []

    def test_un_update_sin_datos_A_PROPOSITO_si_llega(self):
        """🔴 `None` = "acá no se guarda dato, a propósito" → el evento SÍ significa algo.

        Es la forma exacta de `payload_cambio_password`: un UPDATE con los dos campos en None,
        porque nunca puede incluir contraseñas, cuyo valor está entero en el `evento`. Para que
        falle: cambiar `antes == {}` por `not antes` en `_es_update_sin_cambios` — ahí este
        evento se omitiría y se perdería el registro de que alguien cambió su clave."""
        from services._audit_payloads_usuarios import payload_cambio_password

        svc, repo = self._service()
        svc.registrar(**payload_cambio_password(str(uuid4())))
        assert len(repo.insertados) == 1
        assert repo.insertados[0]["evento"] == "cambio_password"

    def test_un_update_con_solo_datos_nuevos_si_llega(self):
        """La forma de `payload_toggle_empresa`: `datos_anteriores=None` + `datos_nuevos` con algo.
        Un chequeo de "falsy" sobre `antes` solo no lo omitiría, pero se afirma igual para fijar
        que la regla exige que los DOS estén vacíos."""
        from services._audit_payloads_rrhh import payload_toggle_empresa

        svc, repo = self._service()
        svc.registrar(**payload_toggle_empresa(str(uuid4()), activa=False, usuario_id="u1"))
        assert len(repo.insertados) == 1

    def test_la_regla_es_solo_para_update(self):
        """Un INSERT o un DELETE con los dos campos vacíos SÍ se registra: no son un diff.

        Los dos `{}` son una forma artificial para un INSERT (ningún payload real la produce),
        y es a propósito: es la ÚNICA combinación que aísla la condición `accion == "UPDATE"`.
        Con `datos_anteriores=None` la mutación que borra esa guarda pasaría igual, porque
        `None == {}` ya es False — verificado por mutación."""
        for accion, evento in (("INSERT", "alta_empleado"), ("DELETE", "baja_empleado")):
            svc, repo = self._service()
            svc.registrar(usuario_id="u1", entidad="empleado", registro_id=str(uuid4()),
                          accion=accion, evento=evento, datos_anteriores={}, datos_nuevos={})
            assert len(repo.insertados) == 1, accion


class TestMedicionDeTiempo:
    def test_el_tiempo_se_reporta_tambien_cuando_termina_completo(self):
        """🔴 `segundos` viaja SIEMPRE, no solo en el corte: es la única medición de duración del
        repo y sin ella el presupuesto se calibra a ojo.

        Para que falle: que `resultado()` no incluya `segundos`, o que solo lo llene si parcial."""
        svc, _, _ = _servicio()
        lote = LoteNomina(presupuesto=10_000, reloj=_RelojFalso(2.0))
        r = TestPresupuestoChico._importar_con_lote(svc, _csv(3), lote)
        assert r.parcial is False
        assert r.segundos is not None and r.segundos > 0

    def test_el_reloj_es_monotonico_por_default(self):
        """`time.monotonic`, no `time.time`: un ajuste de hora del sistema no puede alterar el
        presupuesto ni hacer que un import se corte solo."""
        import time as _t
        lote = LoteNomina(presupuesto=5)
        assert lote._reloj is _t.monotonic
