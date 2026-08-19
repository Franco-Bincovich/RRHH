"""
El import de Formación de punta a punta, por HTTP: preview → confirmar → reportes.

## El fixture es SINTÉTICO con la MISMA FORMA que el archivo real
El Excel real no va al repo (nombres de personas reales). El builder de abajo reproduce su
forma exacta: los 13 encabezados literales + las 13 columnas fantasma "Columna 14..26", meses
con caja mezclada ("marzo"/"Marzo"), un par de nombres invertidos con una letra distinta
(Ponce Morela / Morella Ponce), un apellido solo (Iturbe), filas con solo el Año, un estado
fuera del diccionario ("En pausa") y una duración distinta para el mismo título.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. **El doble APLICA las dos unicidades de la tabla** — la UNIQUE (capacitacion_id,
     empleado_id) y la parcial de nombre libre con año y mes — levantando el MISMO APIError
     23505 que PostgREST. Un doble que aceptara el segundo insert haría pasar el test de
     reimport con la traducción borrada, que es justo el 500 que A4.1 dejó inventariado.
  2. **Las filas insertadas son las que el service ARMÓ, nunca prefabricadas**: si `save()` deja
     de escribir una fecha, el reporte deja de encontrar la fila y el test (d) rojea.
  3. **`gte`/`lte` EXCLUYEN el NULL**, como Postgres: sin eso, la fila sin fecha derivable
     aparecería igual en los reportes y el test que fija su invisibilidad pasaría al revés.
  4. Los tests de rechazo llevan su CONTRASTE en el mismo archivo (el lote importa 8 y rechaza
     3, con los números exactos): un doble o un parser que rechace todo no puede dar esos dos
     números a la vez.

Se falsea la autenticación, no la autorización: el gate de `Seccion.IMPORTACION` corre de
verdad (rol `admin_rrhh`). Molde del montaje: `test_capacitacion_columnas_http.py`.
"""
import io
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

from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from postgrest.exceptions import APIError  # noqa: E402

import main as main_mod  # noqa: E402
import middleware.auth as auth_mod  # noqa: E402
import repositories._asignacion_row as asig_row_mod  # noqa: E402
import repositories._capacitacion_row as cap_row_mod  # noqa: E402
import repositories.asignacion_repo as asig_repo_mod  # noqa: E402
import repositories.capacitacion_repo as cap_repo_mod  # noqa: E402
import services._reporte_anual_metricas as anual_mod  # noqa: E402
import services.formacion_import_service as svc_mod  # noqa: E402
import services.reportes._reporte_capacitacion as reporte_mod  # noqa: E402
from services._reporte_anual_metricas import actividad  # noqa: E402
from services.reportes._reporte_capacitacion import generate_capacitacion  # noqa: E402
from utils.rate_limit import limiter  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

_PREVIEW = "/api/importacion/formacion/preview"
_CONFIRMAR = "/api/importacion/formacion/confirmar"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_EMPRESA = str(uuid4())
_E1, _E2, _E3, _E4 = (str(uuid4()) for _ in range(4))

# Los 13 encabezados literales del archivo real + las 13 columnas fantasma.
_HEADERS = ["Año", "Fecha", "Proyecto", "Área / Equipo", "Colaborador", "Puesto",
            "Tipo de capacitación", "Título", "Entidad capacitadora", "Modalidad",
            "Duración (hs)", "Estado", "Observaciones"] + [f"Columna {n}" for n in range(14, 27)]


def _r(colaborador, mes, titulo, entidad, duracion, estado, anio=2026.0):
    """Una fila con la forma del archivo real (Año como float, que es como lo da Excel)."""
    return [anio, mes, "Elinpar", "Desarrollo", colaborador, "Desarrollador",
            "Capacitación", titulo, entidad, "Virtual", duracion, estado, None] + [None] * 13

_FILAS = [
    _r("Alcaraz Valeria", "marzo", "Explorando la IA", "Kinetic", 6.0, "Finalizado"),   # fila 2
    _r("Ponce Morela", "Marzo", "Explorando la IA", "Kinetic", 6.0, "Finalizado"),      # fila 3 (typo)
    _r("Morella Ponce", "marzo", "Explorando la IA", "Kinetic", 6.0, "Finalizado"),     # fila 4 (invertido)
    _r("Quiroga Camila", "marzo", "HTML desde Cero", "Udemy", 4.0, "Sin iniciar"),      # fila 5
    _r("Camila Quiroga", "Junio", "Explorando la IA", "Kinetic", 6.0, "Finalizado"),    # fila 6 (invertido OK)
    _r("Iturbe", "marzo", "Explorando la IA", "Kinetic", 6.0, "Finalizado"),            # fila 7 (apellido solo)
    _r("Delgado Nicolas", "", "Explorando la IA", "Kinetic", 6.0, "Finalizado"),        # fila 8 (sin mes)
    _r("Alcaraz Valeria", "marzo", "HTML desde Cero", "Udemy", 5.0, "En pausa"),        # fila 9 (estado ajeno)
    _r("Delgado Nicolas", "Julio", "HTML desde Cero", "Udemy", 5.0, "Sin iniciar"),     # fila 10 (dur 5≠4)
    [2026.0] + [None] * 25,                                                             # fila 11 (solo Año)
    [2026.0] + [None] * 25,                                                             # fila 12 (solo Año)
]
_VALIDAS, _RECHAZADAS = 8, 3


def _xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Registro Capacitaciones"
    ws.append(_HEADERS)
    for fila in _FILAS:
        ws.append(fila)
    wb.create_sheet("Resumen")            # segunda hoja vacía, como el archivo real
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ─── El doble de supabase, con las unicidades puestas ────────────────────────

def _clave_libre(fila: dict):
    return (fila["capacitacion_id"], (fila.get("nombre_libre") or "").lower(),
            fila.get("anio") or "", (fila.get("mes") or "").lower())


class _SupabaseImport:
    def __init__(self, tablas: dict) -> None:
        self.tablas = {t: list(rows) for t, rows in tablas.items()}

    def table(self, t):
        return _Query(self.tablas, t)


class _Query:
    def __init__(self, tablas, t):
        self._tablas, self._t = tablas, t
        self._rows = list(tablas.get(t, []))
        self._una = False
        self._insertada = None

    def select(self, *a, **k): return self
    def order(self, *a, **k): return self
    def range(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def maybe_single(self):
        self._una = True
        return self

    def insert(self, payload: dict):
        if self._t == "empleado_capacitacion":
            self._chequear_unicidades(payload)
        fila = {"id": str(uuid4()), "created_at": "2026-08-19T10:00:00+00:00",
                "activo": True, **payload}
        self._tablas.setdefault(self._t, []).append(fila)
        self._insertada = fila
        return self

    def _chequear_unicidades(self, payload: dict) -> None:
        """Las DOS unicidades reales de la tabla. Levanta el APIError que PostgREST levanta."""
        for r in self._tablas.get(self._t, []):
            choca_unique = (payload.get("empleado_id") is not None
                            and r.get("empleado_id") == payload["empleado_id"]
                            and r["capacitacion_id"] == payload["capacitacion_id"])
            choca_parcial = (payload.get("empleado_id") is None and payload.get("nombre_libre")
                             and r.get("empleado_id") is None and r.get("nombre_libre")
                             and _clave_libre(r) == _clave_libre(payload))
            if choca_unique or choca_parcial:
                raise APIError({"message": "duplicate key value violates unique constraint",
                                "code": "23505", "hint": None, "details": None})

    def eq(self, campo, valor):
        self._rows = [r for r in self._rows if str(r.get(campo)) == str(valor)]
        return self

    def in_(self, campo, valores):
        self._rows = [r for r in self._rows if str(r.get(campo)) in {str(v) for v in valores}]
        return self

    def gte(self, campo, valor):
        # NULL queda AFUERA, como en Postgres: es lo que vuelve verificable la invisibilidad
        # de la fila sin fecha (punto 3 del encabezado).
        self._rows = [r for r in self._rows if r.get(campo) is not None and r[campo] >= valor]
        return self

    def lte(self, campo, valor):
        self._rows = [r for r in self._rows if r.get(campo) is not None and r[campo] <= valor]
        return self

    def is_(self, campo, valor):
        if valor == "null":
            self._rows = [r for r in self._rows if r.get(campo) is None]
        return self

    def execute(self):
        if self._insertada is not None:
            return SimpleNamespace(data=[self._insertada], count=1)
        if self._una:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        return SimpleNamespace(data=self._rows, count=len(self._rows))


def _emp(eid, nombre, apellido):
    return {"id": eid, "empresa_id": _EMPRESA, "nombre": nombre, "apellido": apellido,
            "area_id": None}


def _tablas() -> dict:
    return {
        "empresas": [{"id": _EMPRESA, "nombre": "Karstec"}],
        "empleados": [_emp(_E1, "Valeria", "Alcaraz"), _emp(_E2, "Morella", "Ponce"),
                      _emp(_E3, "Camila", "Quiroga"), _emp(_E4, "Nicolas", "Delgado")],
        "capacitaciones": [],
        "empleado_capacitacion": [],
        "areas": [],
        "solicitudes_vacaciones": [],
        "objetivos": [],
    }


class _AuditEspia:
    eventos: list = []

    def registrar(self, **kw) -> None:
        _AuditEspia.eventos.append(kw)


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verificar_token", lambda token, path: str(uuid4()))
    monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
    monkeypatch.setattr(auth_mod, "estado_usuario",
                        lambda user_id: EstadoUsuario(rol="admin_rrhh", activo=True))
    limiter.reset()          # la franja "import" es 10/hora compartida: sin esto, la suite
    _AuditEspia.eventos = []  # entera se come el límite entre tests


def _montar(monkeypatch) -> _SupabaseImport:
    """Falsea el ÚNICO punto de contacto con la base en TODOS los módulos que lo importan:
    los dos repos, sus satélites `_row`, y los dos generadores de reporte del test (d)."""
    doble = _SupabaseImport(_tablas())
    for mod in (asig_repo_mod, asig_row_mod, cap_repo_mod, cap_row_mod, reporte_mod, anual_mod):
        monkeypatch.setattr(mod, "supabase_admin", doble)
    monkeypatch.setattr(svc_mod, "AuditService", _AuditEspia)
    return doble


async def _post_preview(contenido: bytes) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                                 base_url="http://test") as c:
        return await c.post(_PREVIEW, files={"file": ("formacion.xlsx", contenido, _XLSX)},
                            data={"empresa_id": _EMPRESA},
                            headers={"Authorization": "Bearer token-valido"})


async def _post_confirmar(body: dict) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main_mod.app),
                                 base_url="http://test") as c:
        return await c.post(_CONFIRMAR, json=body,
                            headers={"Authorization": "Bearer token-valido"})


async def _confirmado(monkeypatch):
    """Preview + confirmar del fixture entero. Devuelve (doble, respuesta del confirmar)."""
    doble = _montar(monkeypatch)
    preview = (await _post_preview(_xlsx())).json()
    r = await _post_confirmar({"empresa_id": _EMPRESA, "filas": preview["filas_validas"]})
    assert r.status_code == 200, r.text
    return doble, r.json()


# ─── (a) el preview no escribe ───────────────────────────────────────────────

class TestPreviewNoEscribe:
    async def test_cero_filas_antes_y_despues(self, auth, monkeypatch) -> None:
        doble = _montar(monkeypatch)
        r = await _post_preview(_xlsx())
        assert r.status_code == 200, r.text
        assert doble.tablas["empleado_capacitacion"] == []
        assert doble.tablas["capacitaciones"] == [], "el preview creó catálogo: eso es del confirmar"

    async def test_el_preview_clasifica_8_y_3(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        cuerpo = (await _post_preview(_xlsx())).json()
        assert len(cuerpo["filas_validas"]) == _VALIDAS
        assert len(cuerpo["errores"]) == _RECHAZADAS


# ─── (b) la traducción de estado, por HTTP ───────────────────────────────────

class TestEstado:
    async def test_finalizado_y_sin_iniciar_se_traducen(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        filas = (await _post_preview(_xlsx())).json()["filas_validas"]
        por_fila = {f["fila"]: f for f in filas}
        assert por_fila[2]["estado"] == "completado"
        assert por_fila[5]["estado"] == "pendiente"

    async def test_en_pausa_rechaza_la_fila_con_motivo(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        errores = (await _post_preview(_xlsx())).json()["errores"]
        de_estado = [e for e in errores if "En pausa" in e["motivo"]]
        assert len(de_estado) == 1 and de_estado[0]["fila"] == 9


# ─── (c) las fechas derivadas ────────────────────────────────────────────────

class TestFechas:
    async def test_primer_dia_del_mes_en_las_dos_fechas(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        por_fila = {f["fila"]: f for f in (await _post_preview(_xlsx())).json()["filas_validas"]}
        assert por_fila[2]["fecha_asignacion"] == "2026-03-01"
        assert por_fila[2]["fecha_completado"] == "2026-03-01"
        assert por_fila[5]["fecha_asignacion"] == "2026-03-01"
        assert por_fila[5]["fecha_completado"] is None, "pendiente no lleva fecha_completado"

    async def test_sin_mes_entra_sin_fecha_y_reportada(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        por_fila = {f["fila"]: f for f in (await _post_preview(_xlsx())).json()["filas_validas"]}
        fila = por_fila[8]
        assert fila["fecha_asignacion"] is None and fila["fecha_completado"] is None
        assert any("sin fecha derivable" in a for a in fila["avisos"])


# ─── (d) 🔴 las filas importadas APARECEN en los reportes ────────────────────

class TestLosReportesVenElImport:
    async def test_reporte_de_formacion_por_area(self, auth, monkeypatch) -> None:
        """El test que dice si el import sirvió para algo: sin fechas derivadas,
        `generate_capacitacion` filtra por fecha_asignacion y esto daría cero."""
        await _confirmado(monkeypatch)
        reporte = generate_capacitacion(3, 2026, None)
        assert reporte["total_asignaciones"] == 5          # las cinco de marzo
        por_area = reporte["por_area"][0]                  # sin área: los empleados no tienen
        assert por_area["completadas"] == 4
        assert por_area["pendientes"] == 1

    async def test_reporte_anual_cuenta_las_completadas(self, auth, monkeypatch) -> None:
        """5 y no 6: la fila sin mes quedó completada pero SIN fecha_completado, y el anual
        filtra por esa fecha. Es la invisibilidad que el aviso del preview anuncia."""
        await _confirmado(monkeypatch)
        datos = actividad(None, "2026-01-01", "2026-12-31",
                          "2026-01-01T00:00:00", "2026-12-31T23:59:59")
        assert datos["cap_completadas"] == 5

    async def test_el_contraste_otro_mes_no_las_ve(self, auth, monkeypatch) -> None:
        """Si `gte/lte` no filtraran, el reporte de febrero mostraría lo de marzo y el de
        arriba pasaría por casualidad."""
        await _confirmado(monkeypatch)
        assert generate_capacitacion(2, 2026, None)["total_asignaciones"] == 0


# ─── (e) y (f) matcheo ───────────────────────────────────────────────────────

class TestMatcheoPorHttp:
    async def test_los_dos_ordenes_resuelven_a_la_misma_persona(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        por_fila = {f["fila"]: f for f in (await _post_preview(_xlsx())).json()["filas_validas"]}
        assert por_fila[5]["empleado_id"] == _E3           # "Quiroga Camila"
        assert por_fila[6]["empleado_id"] == _E3           # "Camila Quiroga"

    async def test_lo_que_no_matchea_va_a_nombre_libre_y_al_reporte(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        cuerpo = (await _post_preview(_xlsx())).json()
        assert sorted(cuerpo["sin_match"]) == ["Iturbe", "Ponce Morela"]
        suelta = {f["fila"]: f for f in cuerpo["filas_validas"]}[3]
        assert suelta["empleado_id"] is None and suelta["nombre_libre"] == "Ponce Morela"
        assert any("nombre suelto" in a for a in suelta["avisos"]), "nunca en silencio"

    async def test_el_par_parecido_se_reporta_sin_decidir(self, auth, monkeypatch) -> None:
        """Ponce Morela (suelta) y Morella Ponce (matcheada a e2): invertidas y con una letra.
        El par con los dos órdenes que SÍ resolvió a la misma persona (filas 5 y 6) NO sale."""
        _montar(monkeypatch)
        pares = (await _post_preview(_xlsx())).json()["pares_parecidos"]
        assert len(pares) == 1
        assert {pares[0]["nombre_a"], pares[0]["nombre_b"]} == {"Ponce Morela", "Morella Ponce"}

    async def test_la_fila_suelta_se_escribe_con_nombre_libre(self, auth, monkeypatch) -> None:
        doble, _ = await _confirmado(monkeypatch)
        sueltas = [r for r in doble.tablas["empleado_capacitacion"] if r["empleado_id"] is None]
        assert {r["nombre_libre"] for r in sueltas} == {"Ponce Morela", "Iturbe"}


# ─── (g) filas con solo el Año ───────────────────────────────────────────────

class TestFilasSoloAnio:
    async def test_rechazadas_con_motivo_y_contadas(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        errores = (await _post_preview(_xlsx())).json()["errores"]
        solo_anio = [e for e in errores if "solo trae el Año" in e["motivo"]]
        assert len(solo_anio) == 2 and {e["fila"] for e in solo_anio} == {11, 12}
        assert len(errores) == _RECHAZADAS, "el contraste: nada más cayó en el rechazo"


# ─── (h) e (i) el catálogo ───────────────────────────────────────────────────

class TestCatalogo:
    async def test_una_capacitacion_por_titulo_no_por_fila(self, auth, monkeypatch) -> None:
        doble, cuerpo = await _confirmado(monkeypatch)
        assert sorted(cuerpo["capacitaciones_creadas"]) == ["Explorando la IA", "HTML desde Cero"]
        assert len(doble.tablas["capacitaciones"]) == 2, "seis filas del mismo título = UNA fila"
        html = next(c for c in doble.tablas["capacitaciones"] if c["nombre"] == "HTML desde Cero")
        assert html["duracion_horas"] == 4.0 and html["entidad_capacitadora"] == "Udemy"

    async def test_duracion_conflictiva_gana_la_primera_y_se_reporta(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        a_crear = (await _post_preview(_xlsx())).json()["capacitaciones_a_crear"]
        html = next(c for c in a_crear if c["nombre"] == "HTML desde Cero")
        assert html["duracion_horas"] == 4.0
        assert any("fila 10" in a and "gana la primera" in a for a in html["avisos"])
        ia = next(c for c in a_crear if c["nombre"] == "Explorando la IA")
        assert ia["avisos"] == [], "el contraste: sin conflicto no hay aviso"

    async def test_un_titulo_ya_existente_no_se_recrea(self, auth, monkeypatch) -> None:
        doble = _montar(monkeypatch)
        doble.tablas["capacitaciones"].append({
            "id": str(uuid4()), "empresa_id": _EMPRESA, "nombre": "Explorando la IA",
            "descripcion": None, "categoria": None, "duracion_horas": 6.0,
            "entidad_capacitadora": "Kinetic", "modalidad": "Virtual", "tipo": "Capacitación",
            "obligatoria": False, "activo": True, "created_at": "2026-01-01T00:00:00+00:00"})
        preview = (await _post_preview(_xlsx())).json()
        assert [c["nombre"] for c in preview["capacitaciones_a_crear"]] == ["HTML desde Cero"]
        r = await _post_confirmar({"empresa_id": _EMPRESA, "filas": preview["filas_validas"]})
        assert r.json()["capacitaciones_creadas"] == ["HTML desde Cero"]
        assert len(doble.tablas["capacitaciones"]) == 2


# ─── (j) reimportar no rompe ni duplica ──────────────────────────────────────

class TestReimport:
    async def test_duplicados_reportados_por_fila_sin_500_y_sin_duplicar(self, auth, monkeypatch) -> None:
        doble, primero = await _confirmado(monkeypatch)
        assert primero["importados"] == _VALIDAS
        preview = (await _post_preview(_xlsx())).json()
        r = await _post_confirmar({"empresa_id": _EMPRESA, "filas": preview["filas_validas"]})
        assert r.status_code == 200, "el reimport no puede ser un 500"
        segundo = r.json()
        assert segundo["importados"] == 0
        assert len(segundo["errores"]) == _VALIDAS
        assert all("ya tiene esta formación" in e["motivo"] for e in segundo["errores"]), \
            "el motivo tiene que ser el traducido, no el texto crudo de Postgres"
        assert len(doble.tablas["empleado_capacitacion"]) == _VALIDAS, "no duplicó nada"


# ─── (k) el evento de auditoría ──────────────────────────────────────────────

class TestAuditoria:
    async def test_un_evento_por_lote(self, auth, monkeypatch) -> None:
        _, cuerpo = await _confirmado(monkeypatch)
        assert len(_AuditEspia.eventos) == 1
        evento = _AuditEspia.eventos[0]
        assert evento["evento"] == "importacion_formacion"
        assert evento["empresa_id"] == _EMPRESA
        assert evento["datos_nuevos"]["filas_creadas"] == cuerpo["importados"]
        assert len(evento["datos_nuevos"]["ids_creados"]) == cuerpo["importados"]
        assert evento["datos_nuevos"]["capacitaciones_creadas"] == cuerpo["capacitaciones_creadas"]

    async def test_se_emite_tambien_con_cero_filas(self, auth, monkeypatch) -> None:
        """🔴 Con lote vacío el evento sale igual: es el ÚNICO registro de que alguien importó
        formación, y este módulo no auditaba nada hasta hoy."""
        _montar(monkeypatch)
        r = await _post_confirmar({"empresa_id": _EMPRESA, "filas": []})
        assert r.status_code == 200
        assert len(_AuditEspia.eventos) == 1
        assert _AuditEspia.eventos[0]["datos_nuevos"]["filas_enviadas"] == 0


# ─── El confirmar revalida (el body viajó por la red) ────────────────────────

class TestConfirmarRevalida:
    async def test_un_empleado_ajeno_cae_como_error_de_fila(self, auth, monkeypatch) -> None:
        _montar(monkeypatch)
        preview = (await _post_preview(_xlsx())).json()
        filas = preview["filas_validas"]
        filas[0]["empleado_id"] = str(uuid4())     # un id que no es de la empresa del lote
        r = await _post_confirmar({"empresa_id": _EMPRESA, "filas": filas})
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["importados"] == _VALIDAS - 1
        assert any("no existe en la empresa" in e["motivo"] for e in cuerpo["errores"])

    async def test_un_estado_alterado_muere_en_el_422(self, auth, monkeypatch) -> None:
        """El Literal del schema: "Finalizado" crudo en el body es el cliente alterándolo —
        muere ANTES de llegar al CHECK de la base."""
        _montar(monkeypatch)
        preview = (await _post_preview(_xlsx())).json()
        filas = preview["filas_validas"]
        filas[0]["estado"] = "Finalizado"
        r = await _post_confirmar({"empresa_id": _EMPRESA, "filas": filas})
        assert r.status_code == 422
