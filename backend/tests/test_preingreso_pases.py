"""
El CICLO de vida de un preingreso: cómo nace, cómo pasa a activo, y las tres puertas que se le
cierran mientras no haya entrado.

Hermano de `test_estado_preingreso_padron.py`, que cubre las LECTURAS (contadores, listados).
Acá van las ESCRITURAS y las guardas. Son archivos separados porque aquel ya está en 358 líneas
y porque responden preguntas distintas: allá "¿este preingreso cuenta?", acá "¿se puede?".

═══════════════════════════════════════════════════════════════════════════════════════════
🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
═══════════════════════════════════════════════════════════════════════════════════════════
Cada guarda se prueba contra **las dos filas que la rodean**, no solo contra el preingreso: si
el test solo mirara el rechazo, un `raise` incondicional lo pasaría en verde y rompería la
operación para todo el mundo. Por eso cada clase de guarda tiene su caso de CONTRASTE con un
empleado en plantilla, que tiene que seguir pasando.

El motor de query (`_Q`/`_DB`) se IMPORTA de `test_estado_preingreso_padron` en vez de
copiarse: es el mismo motor —aplica de verdad eq/neq/in_/gte/lte y calcula el `count` sobre lo
que sobrevive al WHERE— y dos copias divergirían sin avisar, que es el modo de falla que este
repo documenta. Lo que sí es propio de este archivo es el PADRÓN: acá hace falta un preingreso
con fecha futura y otro con fecha ya cumplida, que allá no tenían sentido.
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

import json  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from pydantic import ValidationError as PydanticValidationError  # noqa: E402
from starlette.requests import Request  # noqa: E402

import services.reportes._reporte_dotacion as dot_mod  # noqa: E402
from middleware.error_handler import validation_error_handler  # noqa: E402
from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate  # noqa: E402
from services._asignacion_precargada import AsignacionPrecargada  # noqa: E402
from services._empleado_activar import activar  # noqa: E402
from services._identificacion_resolver import decidir  # noqa: E402
from services._offboarding_efectivizar import efectivizar  # noqa: E402
from services.asignaciones_service import AsignacionesService  # noqa: E402
from tests.test_estado_preingreso_padron import _DB, EMPRESA  # noqa: E402
from utils.errors import AppError  # noqa: E402

AREA = "11111111-1111-1111-1111-111111111111"
_HOY = date.today()
_AYER = (_HOY - timedelta(days=1)).isoformat()
_MANANA = (_HOY + timedelta(days=30)).isoformat()

_BASE_FILA = {
    "empresa_id": EMPRESA, "area_id": AREA, "roles": ["Analista"],
    "modalidad_trabajo": "presencial", "tipo_contrato": "Full time",
    "created_at": "2026-01-01T00:00:00+00:00", "fecha_egreso": None,
}


def _fila(id_: str, estado: str, fecha_ingreso: str, **extra) -> dict:
    return {**_BASE_FILA, "id": id_, "estado": estado, "nombre": id_.title(),
            "apellido": "Test", "fecha_ingreso": fecha_ingreso, **extra}


class _RepoEmpleados:
    """Repo fake con estado REAL: el update muta la fila, así que el segundo `activar` ve lo que
    dejó el primero. Un fake que devolviera siempre la fila original haría que el test de
    'activar dos veces' pasara aunque la guarda no existiera."""

    def __init__(self, filas: list) -> None:
        self.filas = {f["id"]: dict(f) for f in filas}

    def find_by_id(self, id: str, empresa_id=None):
        fila = self.filas.get(id)
        # Honra empresa_id: sin esto la barrera de empresa del service no se puede desmentir.
        if not fila or (empresa_id and fila["empresa_id"] != str(empresa_id)):
            return None
        return EmpleadoResponse.model_validate(fila)

    def update(self, id: str, data, empresa_id=None):
        fila = self.filas.get(id)
        if not fila or (empresa_id and fila["empresa_id"] != str(empresa_id)):
            return None
        # Construye la respuesta A PARTIR de lo recibido, nunca de un objeto prefabricado.
        fila.update(data.model_dump(exclude_none=True))
        return EmpleadoResponse.model_validate(fila)

    def dar_de_baja(self, empleado_id: str, fecha_egreso, empresa_id=None) -> bool:
        """Calca la escritura real: estado Y fecha juntos, siempre. Un fake que solo pusiera el
        estado dejaría pasar la regresión que `_empleado_write_repo` documenta (una baja sin
        fecha se cae del headcount y del conteo de bajas de todos los meses a la vez)."""
        fila = self.filas.get(empleado_id)
        if not fila or (empresa_id and fila["empresa_id"] != str(empresa_id)):
            return False
        fila.update({"estado": "baja", "fecha_egreso": str(fecha_egreso)})
        return True

    def save(self, data: EmpleadoCreate, empresa_id: UUID) -> EmpleadoResponse:
        """Calca `_empleado_write_repo.guardar`: el payload sale del model_dump, o sea que el
        `estado` que persiste es el del SCHEMA. Si alguien reinstalara el hardcodeo que se sacó
        en A3.2, este fake seguiría mostrando lo que manda el schema y el test de alta en
        preingreso no podría fallar — por eso NO se fuerza ningún estado acá."""
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        fila = {**_BASE_FILA, **payload, "id": str(uuid4()),
                "empresa_id": str(empresa_id), "fecha_ingreso": str(data.fecha_ingreso),
                "area_id": str(data.area_id), "created_at": "2026-01-01T00:00:00+00:00"}
        self.filas[fila["id"]] = fila
        return EmpleadoResponse.model_validate(fila)


class _Audit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _request_dummy() -> Request:
    """El handler solo necesita un Request para la firma; no lee nada de él."""
    return Request({"type": "http", "path": "/api/empleados/x", "headers": [],
                    "client": ("6.6.6.6", 1), "method": "PUT"})


def _alta(estado: str, fecha_ingreso: str) -> EmpleadoCreate:
    return EmpleadoCreate(
        nombre="Nueva", apellido="Persona", email_corporativo="n@p.com", area_id=AREA,
        roles=["Analista"], modalidad_trabajo="presencial", tipo_contrato="Full time",
        fecha_ingreso=fecha_ingreso, empresa_id=EMPRESA, estado=estado,
    )


# ── El tipo del campo: un estado inválido sale 422 y NUNCA 500 ──────────────────────────────

class TestUnEstadoInvalidoNoLlegaAPostgres:
    """🔴 ESTA CLASE EXISTE PORQUE SU AUSENCIA SE NOTÓ EN UNA REVERSIÓN.
    Al revertir los dos `Literal` a `str` para comprobar que los tests podían fallar, **no rojeó
    ninguno**: el resto del archivo usa solo valores válidos, así que el tipado no estaba
    cubierto por nada. Se verificaba a mano y eso no cuenta.

    Lo que se prueba es la cadena entera de dos piezas: el schema RECHAZA el valor, y el handler
    de la app convierte ese rechazo en un **422 con el contrato {error, message, code}**. Sin el
    Literal, el valor viajaba hasta Postgres, chocaba contra `empleados_estado_check` y volvía
    como un 23514 que ningún `except` mapea — o sea un **500**."""

    @pytest.mark.parametrize("valor", ["cualquier_cosa", "ACTIVO", "", "activo "])
    def test_el_put_rechaza_un_estado_fuera_del_check(self, valor: str) -> None:
        with pytest.raises(PydanticValidationError):
            EmpleadoUpdate(estado=valor)

    @pytest.mark.parametrize("valor", ["activo", "baja", "licencia", "suspendido", "preingreso"])
    def test_el_put_acepta_los_CINCO_del_check(self, valor: str) -> None:
        """La contracara. `suspendido` está aunque sea valor muerto: el Literal es el espejo del
        CHECK, y angostarlo es una decisión propia (ver `utils/estados_empleado.py`)."""
        assert EmpleadoUpdate(estado=valor).estado == valor

    @pytest.mark.parametrize("valor", ["baja", "licencia", "suspendido"])
    def test_el_alta_rechaza_los_estados_que_no_son_de_alta(self, valor: str) -> None:
        """Nadie se da de alta como dado de baja ni en licencia: describen algo que le pasó a
        alguien que YA estaba."""
        with pytest.raises(PydanticValidationError):
            _alta(valor, _AYER)

    async def test_el_rechazo_sale_422_con_el_contrato_y_no_500(self) -> None:
        """La segunda mitad de la cadena: que el rechazo del schema se convierta en la respuesta
        que el front entiende. Sin este handler FastAPI devuelve `{"detail": [...]}` y el front
        lo muestra como 'Error del servidor' — ver el docstring de `validation_error_handler`."""
        try:
            EmpleadoUpdate(estado="cualquier_cosa")
            raise AssertionError("el schema tenía que rechazar")
        except PydanticValidationError as exc:
            errores = exc.errors()
        respuesta = await validation_error_handler(
            _request_dummy(), RequestValidationError(errores))
        assert respuesta.status_code == 422
        cuerpo = json.loads(bytes(respuesta.body))
        assert set(cuerpo) >= {"error", "message", "code"}


# ── a) El alta puede nacer en preingreso, y no cuenta como alta del mes ──────────────────────

class TestElAltaEnPreingreso:
    def test_el_estado_del_schema_es_el_que_persiste(self) -> None:
        repo = _RepoEmpleados([])
        assert repo.save(_alta("preingreso", _AYER), UUID(EMPRESA)).estado == "preingreso"
        assert repo.save(_alta("activo", _AYER), UUID(EMPRESA)).estado == "activo"

    def test_sin_estado_explicito_el_alta_nace_activa(self) -> None:
        """El default vive en el schema desde A3.2 (antes estaba hardcodeado en el repo)."""
        data = EmpleadoCreate(
            nombre="N", apellido="P", email_corporativo="n@p.com", area_id=AREA,
            roles=["A"], modalidad_trabajo="presencial", tipo_contrato="FT",
            fecha_ingreso=_AYER, empresa_id=EMPRESA)
        assert data.estado == "activo"

    def test_un_alta_en_preingreso_no_cuenta_como_alta_del_mes(self, monkeypatch) -> None:
        """🔑 CIERRA EL CÍRCULO CON A3.1. Allá se probó que un preingreso YA CARGADO no cuenta;
        acá que uno recién dado de alta tampoco — que es el caso que la feature crea de verdad."""
        dentro = date(_HOY.year, _HOY.month, 10).isoformat()
        filas = [_fila("act1", "activo", dentro), _fila("pre1", "preingreso", dentro)]
        monkeypatch.setattr(dot_mod, "supabase_admin",
                            _DB({"empleados": filas, "areas": []}))
        assert dot_mod.generate_headcount(
            _HOY.month, _HOY.year, UUID(EMPRESA))["ingresos_periodo"] == 1


# ── b), c), d) El pase a activo ──────────────────────────────────────────────────────────────

class TestElPaseAActivo:
    def _activar(self, repo, id_="pre1"):
        return activar(repo, _Audit(), id_, UUID(EMPRESA), "u1")

    def test_activar_deja_al_empleado_activo(self) -> None:
        """(b) Y el pase NO toca `fecha_ingreso`: la prevista es la que se cumplió."""
        repo = _RepoEmpleados([_fila("pre1", "preingreso", _AYER)])
        resultado = self._activar(repo)
        assert resultado.estado == "activo"
        assert str(resultado.fecha_ingreso) == _AYER
        assert repo.filas["pre1"]["estado"] == "activo"

    def test_y_ahi_si_empieza_a_contar(self, monkeypatch) -> None:
        """(b, la mitad que importa) El mismo empleado, antes y después del pase, contra el
        MISMO contador. Sin esto 'quedó activo' sería una afirmación sobre un string."""
        dentro = date(_HOY.year, _HOY.month, 10).isoformat()
        repo = _RepoEmpleados([_fila("pre1", "preingreso", dentro)])

        def altas() -> int:
            monkeypatch.setattr(dot_mod, "supabase_admin",
                                _DB({"empleados": list(repo.filas.values()), "areas": []}))
            return dot_mod.generate_headcount(
                _HOY.month, _HOY.year, UUID(EMPRESA))["ingresos_periodo"]

        assert altas() == 0
        self._activar(repo)
        assert altas() == 1

    def test_activar_dos_veces_da_409(self) -> None:
        """(c) El segundo pase ya no encuentra un preingreso: encuentra al activo que dejó el
        primero. Es la guarda haciendo de idempotencia explícita."""
        repo = _RepoEmpleados([_fila("pre1", "preingreso", _AYER)])
        self._activar(repo)
        with pytest.raises(AppError) as e:
            self._activar(repo)
        assert e.value.code == "EMPLEADO_NO_ES_PREINGRESO" and e.value.status_code == 409

    def test_activar_con_fecha_de_ingreso_futura_da_400(self) -> None:
        """(d) 🔴 LA GUARDA QUE ES EL CORAZÓN DEL MÓDULO. Activar a alguien que todavía no entró
        reinstala el bug de la efectivización de bajas por el eje contrario: la persona
        aparecería en el headcount y en los denominadores antes de trabajar un solo día."""
        repo = _RepoEmpleados([_fila("pre1", "preingreso", _MANANA)])
        with pytest.raises(AppError) as e:
            self._activar(repo)
        assert e.value.code == "INGRESO_AUN_NO_OCURRIO" and e.value.status_code == 400
        assert repo.filas["pre1"]["estado"] == "preingreso", "no tiene que haber escrito nada"

    def test_un_empleado_de_otra_empresa_da_404_y_no_409(self) -> None:
        """La barrera de empresa va ANTES del chequeo de estado: al revés, el 409 confirmaría
        que ese id existe en otra empresa (oráculo de enumeración)."""
        repo = _RepoEmpleados([_fila("pre1", "preingreso", _AYER, empresa_id=str(uuid4()))])
        with pytest.raises(AppError) as e:
            self._activar(repo)
        assert e.value.code == "EMPLEADO_NOT_FOUND" and e.value.status_code == 404

    def test_el_pase_se_audita_con_la_empresa_del_empleado(self) -> None:
        repo, audit = _RepoEmpleados([_fila("pre1", "preingreso", _AYER)]), _Audit()
        activar(repo, audit, "pre1", UUID(EMPRESA), "u1")
        evento = audit.eventos[0]
        assert evento["evento"] == "activacion_empleado"
        assert evento["empresa_id"] == EMPRESA, "con None quedaría fuera del filtro de /auditoria"
        assert evento["datos_nuevos"]["estado"] == "activo"


# ── e) Asignar a un proyecto ─────────────────────────────────────────────────────────────────

class TestAsignarUnPreingresoAUnProyecto:
    def _asignar(self, estado: str):
        return AsignacionesService()._asignar_uno(
            uuid4(), uuid4(), "Dev", None, None, None,
            precargado=AsignacionPrecargada(True, EMPRESA, estado))

    def test_un_preingreso_es_rechazado_con_su_codigo_propio(self) -> None:
        """(e) Código PROPIO y no el genérico de baja: los dos rechazos se arreglan distinto —a
        un preingreso se lo activa, a una baja no— y sin horas imputadas de por medio, porque
        una carga sobre alguien que no entró es dato falso en el reporte de horas por cliente."""
        with pytest.raises(AppError) as e:
            self._asignar("preingreso")
        assert e.value.code == "EMPLEADO_PREINGRESO" and e.value.status_code == 422

    def test_una_baja_sigue_dando_el_codigo_de_siempre(self) -> None:
        """CONTRASTE 1: el contrato viejo no se movió al cambiar el predicado."""
        with pytest.raises(AppError) as e:
            self._asignar("baja")
        assert e.value.code == "EMPLEADO_INACTIVO"

    def test_alguien_en_licencia_SI_se_puede_asignar(self) -> None:
        """CONTRASTE 2, y es el que hace falsable el cambio de '¿es baja?' a '¿está en
        plantilla?': si la guarda se hubiera pasado a `!= 'activo'`, esto rojearía. Alguien de
        licencia sigue siendo dotación y puede estar asignado a un proyecto."""
        with pytest.raises(Exception) as e:   # falla más adelante (repo real), NO en la guarda
            self._asignar("licencia")
        assert getattr(e.value, "code", None) not in ("EMPLEADO_PREINGRESO", "EMPLEADO_INACTIVO")


# ── f) Offboarding sobre un preingreso ───────────────────────────────────────────────────────

class _RepoOffboarding:
    def __init__(self, empleado_id: str) -> None:
        self.completados: list = []
        self._inst = {"id": "i1", "empleado_id": empleado_id, "estado": "iniciado",
                      "empresa_id": EMPRESA}

    def find_instancia_min(self, instancia_id: str, empresa_id=None):
        return dict(self._inst)

    def marcar_completado(self, instancia_id: str, empresa_id=None) -> None:
        self.completados.append(instancia_id)


class TestOffboardingSobreUnPreingreso:
    def _efectivizar(self, estado: str, fecha_ingreso: str):
        repo_emp = _RepoEmpleados([_fila("e1", estado, fecha_ingreso)])
        off = _RepoOffboarding("e1")
        efectivizar(off, repo_emp, _Audit(), uuid4(), _HOY, UUID(EMPRESA), "u1")
        return repo_emp, off

    def test_rechaza_con_codigo_propio_y_no_con_el_de_la_fecha(self) -> None:
        """(f) 🔴 EL PUNTO DEL TEST ES EL CÓDIGO, NO EL RECHAZO. Antes de A3.2 este caso lo
        cortaba `_validar_fecha` POR ACCIDENTE (un preingreso tiene fecha futura, así que
        `fecha_egreso < fecha_ingreso`) y salía FECHA_EGRESO_INVALIDA, que le dice a RRHH que
        corrija la fecha cuando el problema es que esa persona nunca entró."""
        with pytest.raises(AppError) as e:
            self._efectivizar("preingreso", _MANANA)
        assert e.value.code == "EMPLEADO_PREINGRESO" and e.value.status_code == 409
        assert e.value.code != "FECHA_EGRESO_INVALIDA"

    def test_tambien_rechaza_al_preingreso_cuya_fecha_ya_paso(self) -> None:
        """🔑 EL CASO QUE LA GUARDA VIEJA NO CUBRÍA EN ABSOLUTO. Con la fecha prevista ya pasada,
        `_validar_fecha` no se quejaba de nada y el offboarding se COMPLETABA: dejaba a alguien
        que nunca trabajó contando como una baja del mes, o sea rotación inventada."""
        with pytest.raises(AppError) as e:
            self._efectivizar("preingreso", _AYER)
        assert e.value.code == "EMPLEADO_PREINGRESO"

    def test_un_activo_sigue_pudiendo_darse_de_baja(self) -> None:
        """CONTRASTE: la guarda nueva no rompió el camino normal."""
        repo_emp, off = self._efectivizar("activo", _AYER)
        assert repo_emp.filas["e1"]["estado"] == "baja" and off.completados


# ── g) Link público de carga de horas ────────────────────────────────────────────────────────

class _RepoIdentificacion:
    def __init__(self, filas: list) -> None:
        self._filas = filas

    def buscar_por_dni(self, dni: str) -> list:
        return [f for f in self._filas if f.get("dni") == dni]

    def hay_clientes_activos(self) -> bool:
        return True


class TestElLinkPublicoConUnPreingreso:
    def _decidir(self, estado: str) -> tuple:
        repo = _RepoIdentificacion([
            {"id": "e1", "dni": "30111222", "nombre": "Ana", "estado": estado,
             "empresa_id": EMPRESA}])
        return decidir(repo, lambda _d: True, "30111222")

    def test_un_preingreso_es_rechazado(self) -> None:
        """(g) No puede cargar horas quien todavía no entró: sus horas serían de días que no
        trabajó, y el reporte por cliente es lo que se factura."""
        resultado, _ = self._decidir("preingreso")
        assert resultado != "ok"

    def test_el_motivo_que_se_loguea_es_preingreso_no_inactivo(self) -> None:
        """✅ CERRADO EN A3.3 (migración 121) — este test fijaba la limitación conocida
        ("el forense no distingue 'se fue' de 'todavía no entró': los dos quedan como
        `inactivo`") y ahora fija lo contrario: el motivo propio.
        ⚠️ El valor nuevo exige el CHECK de la 121 corrido — `registrar_intento` se traga todo
        error a propósito, así que sin la migración la fila del log DESAPARECERÍA en silencio.
        Ver `services/_identificacion_resolver.py` y `docs/DEUDA-TECNICA.md`."""
        assert self._decidir("preingreso")[0] == "preingreso"

    def test_un_activo_pasa(self) -> None:
        """CONTRASTE: sin esto, un `return "inactivo"` incondicional pasaría los dos de arriba."""
        assert self._decidir("activo")[0] == "ok"
