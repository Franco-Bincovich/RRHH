"""
Catálogo de perfiles de puesto — CRUD, paginación, permisos y auditoría, POR HTTP.

## 🚨 LAS TRES PREGUNTAS PREVIAS, CONTESTADAS ANTES DE ESCRIBIR NADA

**1. ¿Qué tendría que ser distinto en el fake para que estos tests puedan fallar?**

  · **El almacén tiene 120 filas, no 3.** Con menos de `page_size` ninguna aserción de
    paginación puede fallar: `range(0, 19)` sobre 3 filas devuelve las mismas 3 que sin
    `range`. 120 > 100 (el `le` del router) es lo que hace que "el listado dejó de paginar" se
    vea como un largo distinto Y como un `total_pages` distinto.
  · **`count="exact"` se HONRA y devuelve el total ANTES de recortar.** Un almacén que
    ignorara el kwarg —como hace el fake de Supabase del repo, y es exactamente el bug que dejó
    6 reportes rotos en verde— devolvería `count=None` y el service calcularía sobre 0 sin que
    nada rojee.
  · **`.range()` recorta de verdad y `.ilike()` filtra de verdad**, con `%` como comodín. Si
    cualquiera de los dos fuera un no-op, sacarlo del repo no cambiaría un solo resultado.
  · **La escritura se construye A PARTIR del payload recibido**, nunca devuelve un objeto
    prefabricado: si el repo deja de mandar un campo, la fila no lo tiene y el schema no valida.
  · **🔴 El request llega con un `X-Empresa-Id` REAL y resuelto a una empresa concreta.** Es la
    condición sin la cual el test de auditoría es vacuo: si el middleware falseado devolviera
    `None`, "el evento no toma la empresa del header" pasaría con el bug puesto, porque no
    habría empresa que tomar.

**2. ¿El fake ES lo que estoy probando?** No. Lo falseado es el CLIENTE DE SUPABASE (un
escalón por debajo del repo) y la resolución de identidad del middleware. El repo, el service,
los schemas, los gates de permisos y el ruteo son los REALES: los requests entran por HTTP y
atraviesan `app`. Es deliberado — los 30 tests de clientes pasaban con un bug de 422 vivo
porque empezaban del lado de adentro de la validación de Pydantic.

**3. ¿El test replica adentro lo que dice verificar?** No hay ningún literal de respuesta
esperada copiado del código de producción: los 404 se comparan ENTRE SÍ (dos caminos, un solo
rechazo), la paginación se compara contra el contenido del almacén, y el evento de auditoría se
mira campo por campo sobre lo que el service pasó de verdad.
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

from datetime import UTC, datetime  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402

import middleware.auth as auth_mod  # noqa: E402
import repositories._perfil_puesto_write_repo as write_mod  # noqa: E402
import repositories.perfil_puesto_repo as repo_mod  # noqa: E402
from main import app  # noqa: E402
from routers.perfiles_puesto import _service as _dep_lecturas  # noqa: E402
from routers.perfiles_puesto_escrituras import _service as _dep_escrituras  # noqa: E402
from services.perfil_puesto_service import PerfilPuestoService  # noqa: E402
from utils.usuario_estado import EstadoUsuario  # noqa: E402

BASE = "/api/perfiles-puesto"
USUARIO = str(uuid4())
# 🔴 Una empresa CONCRETA en el header. Ver la pregunta 1 del encabezado: sin esto el test de
# auditoría no tendría nada que desmentir.
EMPRESA_HEADER = str(uuid4())
INEXISTENTE = "33333333-3333-3333-3333-333333333333"
OTRO_INEXISTENTE = "44444444-4444-4444-4444-444444444444"

# 120 > 100 (el `le` del router) > 20 (el page_size por defecto). Los tres escalones importan.
TOTAL_FILAS = 120


# ── El doble del cliente de Supabase ──────────────────────────────────────────


class _Resp:
    def __init__(self, data, count=None) -> None:
        self.data = data
        self.count = count


class _Q:
    """Query encadenable. Cada operador FILTRA DE VERDAD; ninguno es un no-op."""

    def __init__(self, almacen: "Almacen", tabla: str) -> None:
        self._a, self._tabla = almacen, tabla
        self._eq: List[tuple] = []
        self._ilike: Optional[tuple] = None
        self._orden: Optional[str] = None
        self._rango: Optional[tuple] = None
        self._single = False
        self._modo = "select"
        self._payload: Optional[dict] = None
        self._cols = "*"
        self._count = None

    def select(self, cols: str = "*", count=None) -> "_Q":
        """🔴 HONRA `count`. Ignorarlo es el bug que dejó 6 reportes rotos en verde."""
        self._cols, self._count = cols, count
        return self

    def eq(self, col: str, val) -> "_Q":
        self._eq.append((col, val))
        return self

    def ilike(self, col: str, patron: str) -> "_Q":
        self._ilike = (col, patron)
        return self

    def order(self, col: str, **k) -> "_Q":
        self._orden = col
        return self

    def range(self, desde: int, hasta: int) -> "_Q":
        """Inclusivo en los dos extremos, como PostgREST."""
        self._rango = (desde, hasta)
        return self

    def maybe_single(self) -> "_Q":
        self._single = True
        return self

    def insert(self, payload: dict) -> "_Q":
        self._modo, self._payload = "insert", payload
        return self

    def update(self, patch: dict) -> "_Q":
        self._modo, self._payload = "update", patch
        return self

    def _match(self, fila: dict) -> bool:
        if not all(fila.get(c) == v for c, v in self._eq):
            return False
        if self._ilike:
            col, patron = self._ilike
            valor = (fila.get(col) or "").casefold()
            nucleo = patron.strip("%").casefold()
            if patron.startswith("%") and patron.endswith("%"):
                return nucleo in valor
            return valor == nucleo
        return True

    def execute(self) -> _Resp:
        filas = self._a.catalogo.setdefault(self._tabla, [])
        self._a.registrar(self._tabla, self._modo, self._cols, self._count, self._rango)
        if self._modo == "insert":
            nueva = {"id": str(uuid4()), "activo": True,
                     "created_at": self._a.ahora, "updated_at": None,
                     "created_by": None, **self._payload}
            filas.append(nueva)
            return _Resp([nueva])
        if self._modo == "update":
            tocadas = [f for f in filas if self._match(f)]
            for f in tocadas:
                f.update(self._payload)
            return _Resp(tocadas)
        halladas = [f for f in filas if self._match(f)]
        if self._orden:
            halladas = sorted(halladas, key=lambda f: str(f.get(self._orden, "")))
        total = len(halladas)
        if self._rango:
            desde, hasta = self._rango
            halladas = halladas[desde:hasta + 1]
        if self._single:
            return _Resp(halladas[0] if halladas else None)
        # `count` sale del total SIN recortar: es lo que hace PostgREST y lo que permite que
        # "el repo dejó de paginar" y "el repo dejó de contar" fallen por caminos distintos.
        return _Resp(halladas, count=total if self._count == "exact" else None)


class Almacen:
    """`catalogo` es {tabla: [filas]}. `consultas` registra cada ida a la "base"."""

    def __init__(self, filas: List[dict],
                 ahora: str = "2026-08-14T00:00:00+00:00") -> None:
        self.catalogo: Dict[str, List[dict]] = {"perfiles_puesto": filas}
        self.ahora = ahora
        self.consultas: List[dict] = []

    def registrar(self, tabla, modo, cols, count, rango) -> None:
        self.consultas.append({"tabla": tabla, "modo": modo, "cols": cols,
                               "count": count, "rango": rango})

    def table(self, tabla: str) -> _Q:
        return _Q(self, tabla)


def _fila(n: int, activo: bool = True) -> dict:
    """Fila del catálogo. El nombre lleva el índice zero-padded para que el orden alfabético
    y el numérico coincidan: sin eso, "Perfil 10" iría antes que "Perfil 2" y las aserciones
    de paginación estarían comparando contra un orden que nadie eligió."""
    return {
        "id": str(uuid4()), "nombre": f"Perfil {n:03d}", "descripcion": None,
        "funciones": None, "requisitos": None, "formacion": None, "experiencia": None,
        "conocimientos_tecnicos": None, "ofrecemos": None, "modalidad": None,
        "tipo_contrato": None, "nivel": None, "jornada": None, "activo": activo,
        "created_by": None, "created_at": "2026-08-14T00:00:00+00:00", "updated_at": None,
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def almacen(monkeypatch) -> Almacen:
    """120 activos + 2 dados de baja. Los 2 inactivos existen para que
    `incluir_inactivos` pueda fallar: sin ellos, prenderlo y apagarlo da lo mismo."""
    filas = [_fila(n) for n in range(TOTAL_FILAS)]
    filas += [_fila(900, activo=False), _fila(901, activo=False)]
    a = Almacen(filas)
    monkeypatch.setattr(repo_mod, "supabase_admin", a)
    monkeypatch.setattr(write_mod, "supabase_admin", a)
    return a


class _AuditoriaFalsa:
    """Guarda cada llamada ENTERA y cuenta. Un payload al que le falte un campo se ve."""

    def __init__(self) -> None:
        self.eventos: List[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


@pytest.fixture
def auditoria() -> _AuditoriaFalsa:
    return _AuditoriaFalsa()


@pytest.fixture
def como(monkeypatch, almacen, auditoria):
    """Devuelve una fábrica de clientes HTTP autenticados con el rol que se le pida.

    🔴 QUÉ SE FALSEA Y QUÉ NO. Se falsea la RESOLUCIÓN DE IDENTIDAD del middleware (token,
    rol, actividad, sesión) porque eso tiene sus propios tests y montarlo de verdad exigiría
    un JWKS. NO se falsea el gate de permisos, ni el ruteo, ni la validación de Pydantic, ni
    el service, ni el repo: esos son los reales y son lo que se está probando.

    🔴 `resolver_empresa_id` devuelve una EMPRESA CONCRETA, no None. Ver el encabezado.
    """
    def _fabrica(rol: str = "admin_rrhh") -> httpx.AsyncClient:
        monkeypatch.setattr(auth_mod, "_extract_token", lambda r: "token-de-prueba")
        monkeypatch.setattr(auth_mod, "_verificar_token", lambda t, p: USUARIO)
        monkeypatch.setattr(auth_mod, "estado_usuario",
                            lambda uid: EstadoUsuario(rol=rol, activo=True, resuelto=True))
        monkeypatch.setattr(auth_mod, "registrar_actividad", lambda uid: None)
        monkeypatch.setattr(auth_mod, "sesion_expirada", lambda e: False)
        monkeypatch.setattr(auth_mod, "resolver_empresa_id", lambda h, p: EMPRESA_HEADER)

        svc = PerfilPuestoService(audit=auditoria)
        app.dependency_overrides[_dep_lecturas] = lambda: svc
        app.dependency_overrides[_dep_escrituras] = lambda: svc
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test",
            headers={"X-Empresa-Id": EMPRESA_HEADER},
        )

    yield _fabrica
    app.dependency_overrides.clear()


def _alta() -> dict:
    return {"nombre": "Analista SQL", "nivel": "semi_senior", "modalidad": "hibrido",
            "tipo_contrato": "efectivo", "experiencia": "1 a 3 años"}


# ── 1. El listado NACE PAGINADO ───────────────────────────────────────────────


class TestPaginacion:
    """🔴 Si el repo dejara de paginar, TODOS estos rojean — cada uno por un motivo distinto."""

    async def test_el_almacen_tiene_mas_filas_que_una_pagina(self, almacen) -> None:
        """Guarda contra el falso verde: con <= page_size, paginar y no paginar dan lo mismo."""
        assert len(almacen.catalogo["perfiles_puesto"]) > 100

    async def test_la_pagina_por_defecto_trae_20_de_120(self, como) -> None:
        async with como() as c:
            r = await c.get(BASE)
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 20
        assert body["total"] == TOTAL_FILAS
        assert body["page"] == 1 and body["page_size"] == 20
        assert body["total_pages"] == 6

    async def test_la_segunda_pagina_trae_OTRAS_filas(self, como) -> None:
        """No basta con que devuelva 20: tienen que ser 20 DISTINTAS. Un `range` ignorado
        devolvería las mismas y un test de largo pasaría igual."""
        async with como() as c:
            p1 = (await c.get(BASE, params={"page": 1})).json()["items"]
            p2 = (await c.get(BASE, params={"page": 2})).json()["items"]
        assert [i["id"] for i in p1] != [i["id"] for i in p2]
        assert not ({i["id"] for i in p1} & {i["id"] for i in p2})

    async def test_el_total_es_el_del_filtro_y_no_el_de_la_pagina(self, como) -> None:
        """`count="exact"` en la MISMA query. Sin él el total sería 20 (o 0) y el paginador
        del front dibujaría una sola página sobre 120 filas."""
        async with como() as c:
            body = (await c.get(BASE, params={"page_size": 5})).json()
        assert len(body["items"]) == 5
        assert body["total"] == TOTAL_FILAS
        assert body["total_pages"] == 24

    async def test_el_repo_pide_count_exact_y_un_rango(self, almacen, como) -> None:
        """Un escalón más abajo: lo que tiene que viajar EN LA QUERY se verifica en la query.
        Molde: `TestElOrdenLoPoneLaQuery` de test_historial_salarial."""
        async with como() as c:
            await c.get(BASE)
        lecturas = [q for q in almacen.consultas if q["modo"] == "select" and q["rango"]]
        assert lecturas, "el repo no pidió ningún rango: dejó de paginar"
        assert lecturas[-1]["count"] == "exact"
        assert lecturas[-1]["rango"] == (0, 19)

    async def test_page_size_mayor_a_100_lo_rechaza_el_router(self, como) -> None:
        """🔴 El `le=100` es lo que impide que el listado sea un export encubierto que
        esquiva `verificar_limite_export`."""
        async with como() as c:
            r = await c.get(BASE, params={"page_size": 500})
        assert r.status_code == 422

    async def test_page_cero_lo_rechaza_el_router(self, como) -> None:
        """`ge=1`: con page=0 el `range` daría (-20, -1) y PostgREST devolvería cualquier cosa."""
        async with como() as c:
            assert (await c.get(BASE, params={"page": 0})).status_code == 422


# ── 2. Filtros ────────────────────────────────────────────────────────────────


class TestFiltros:
    async def test_los_inactivos_no_salen_por_defecto(self, como) -> None:
        async with como() as c:
            body = (await c.get(BASE, params={"page_size": 100})).json()
        assert body["total"] == TOTAL_FILAS
        assert all(i["activo"] for i in body["items"])

    async def test_incluir_inactivos_los_suma(self, como) -> None:
        """Las DOS direcciones: sin el flag son 120, con el flag 122. Un filtro que se
        ignorara daría el mismo número en los dos casos."""
        async with como() as c:
            sin = (await c.get(BASE)).json()["total"]
            con = (await c.get(BASE, params={"incluir_inactivos": "true"})).json()["total"]
        assert sin == TOTAL_FILAS
        assert con == TOTAL_FILAS + 2

    async def test_search_acota_de_verdad(self, como) -> None:
        """"Perfil 01" matchea 01x → 10 filas de 120. Si `ilike` fuera un no-op darían 120."""
        async with como() as c:
            body = (await c.get(BASE, params={"search": "Perfil 01"})).json()
        assert body["total"] == 10
        assert all("Perfil 01" in i["nombre"] for i in body["items"])

    async def test_search_sin_resultados_no_es_un_error(self, como) -> None:
        async with como() as c:
            body = (await c.get(BASE, params={"search": "no existe"})).json()
        assert body["items"] == [] and body["total"] == 0
        assert body["total_pages"] == 1, "con 0 filas hay UNA página vacía, no cero"


# ── 3. Los IDs se tipan UUID ──────────────────────────────────────────────────


class TestTipadoDeIds:
    """🔴 Error #1 del porteo a asyncpg. Con `id: str` estos dos rojean.

    Van POR HTTP a propósito: instanciar el schema a mano probaría Pydantic, no el endpoint.
    """

    async def test_un_id_mal_formado_da_422_y_no_llega_al_service(self, almacen, como) -> None:
        antes = len(almacen.consultas)
        async with como() as c:
            r = await c.get(f"{BASE}/no-soy-un-uuid")
        assert r.status_code == 422
        assert len(almacen.consultas) == antes, "el id inválido llegó hasta la base"

    async def test_un_id_mal_formado_en_el_delete_tambien_da_422(self, como) -> None:
        async with como() as c:
            assert (await c.delete(f"{BASE}/1234")).status_code == 422

    async def test_el_id_que_sale_es_un_uuid_valido(self, como) -> None:
        async with como() as c:
            body = (await c.post(BASE, json=_alta())).json()
        UUID(body["id"])  # levanta si el schema dejó pasar cualquier string


# ── 4. Vocabularios cerrados ──────────────────────────────────────────────────


class TestVocabulariosCerrados:
    """Los tres `Literal` son copia de los CHECK: un valor fuera de lista tiene que salir como
    422 con el nombre del campo, no como el 23514 crudo convertido en 500."""

    @pytest.mark.parametrize("campo,valor", [
        ("nivel", "semisenior"), ("modalidad", "hibrida"), ("tipo_contrato", "indefinido"),
    ])
    async def test_valor_fuera_del_vocabulario_da_422(self, almacen, como, campo, valor) -> None:
        antes = len(almacen.catalogo["perfiles_puesto"])
        async with como() as c:
            r = await c.post(BASE, json={**_alta(), campo: valor})
        assert r.status_code == 422
        assert len(almacen.catalogo["perfiles_puesto"]) == antes, "se insertó igual"

    @pytest.mark.parametrize("campo,valor", [
        ("nivel", "c_level"), ("modalidad", "remoto"), ("tipo_contrato", "pasantia"),
    ])
    async def test_los_valores_del_vocabulario_entran(self, como, campo, valor) -> None:
        """La contracara: si el `Literal` estuviera mal escrito, rechazaría lo válido."""
        async with como() as c:
            r = await c.post(BASE, json={**_alta(), "nombre": f"P {campo}", campo: valor})
        assert r.status_code == 201
        assert r.json()[campo] == valor


# ── 5. CRUD ───────────────────────────────────────────────────────────────────


class TestAlta:
    async def test_crea_y_persiste_lo_que_se_mandó(self, almacen, como) -> None:
        """La fila se arma A PARTIR del payload: si el repo dejara de mandar `experiencia`,
        esto rojea."""
        async with como() as c:
            r = await c.post(BASE, json=_alta())
        assert r.status_code == 201
        body = r.json()
        assert body["nombre"] == "Analista SQL" and body["experiencia"] == "1 a 3 años"
        assert body["activo"] is True
        guardada = [f for f in almacen.catalogo["perfiles_puesto"] if f["id"] == body["id"]]
        assert guardada and guardada[0]["nivel"] == "semi_senior"

    async def test_persiste_created_by_del_usuario_del_request(self, almacen, como) -> None:
        """🔴 `created_by` sale del usuario autenticado y NUNCA del body."""
        async with como() as c:
            body = (await c.post(BASE, json=_alta())).json()
        fila = next(f for f in almacen.catalogo["perfiles_puesto"] if f["id"] == body["id"])
        assert fila["created_by"] == USUARIO

    async def test_ignora_un_created_by_mandado_por_el_cliente(self, almacen, como) -> None:
        """Aceptarlo permitiría atribuirle el alta a otro usuario."""
        ajeno = str(uuid4())
        async with como() as c:
            body = (await c.post(BASE, json={**_alta(), "created_by": ajeno})).json()
        fila = next(f for f in almacen.catalogo["perfiles_puesto"] if f["id"] == body["id"])
        assert fila["created_by"] == USUARIO != ajeno

    async def test_nombre_duplicado_da_409_sin_importar_el_case(self, como) -> None:
        """El índice único es sobre `lower(nombre)` y es GLOBAL: no hay dedup por empresa."""
        async with como() as c:
            assert (await c.post(BASE, json=_alta())).status_code == 201
            r = await c.post(BASE, json={**_alta(), "nombre": "  analista sql  "})
        assert r.status_code == 409
        assert r.json()["code"] == "PERFIL_DUPLICADO"

    async def test_nombre_de_solo_espacios_da_422(self, como) -> None:
        """Pydantic frena `""` por `min_length`; `"   "` pasa y lo tiene que frenar el service."""
        async with como() as c:
            r = await c.post(BASE, json={**_alta(), "nombre": "     "})
        assert r.status_code == 422
        assert r.json()["code"] == "NOMBRE_REQUERIDO"

    async def test_nombre_vacio_lo_frena_pydantic(self, como) -> None:
        async with como() as c:
            assert (await c.post(BASE, json={**_alta(), "nombre": ""})).status_code == 422


class TestDetalleYRechazo:
    async def test_devuelve_el_perfil(self, almacen, como) -> None:
        fila = almacen.catalogo["perfiles_puesto"][0]
        async with como() as c:
            r = await c.get(f"{BASE}/{fila['id']}")
        assert r.status_code == 200 and r.json()["nombre"] == fila["nombre"]

    async def test_el_rechazo_es_UNO_SOLO(self, como) -> None:
        """🔴 No se compara contra un literal escrito acá: se comparan DOS rechazos REALES
        entre sí. Así el día que el mensaje cambie el test sigue valiendo — lo que no puede
        es que dos caminos den mensajes distintos, que es el oráculo de enumeración."""
        async with como() as c:
            a = await c.get(f"{BASE}/{INEXISTENTE}")
            b = await c.delete(f"{BASE}/{OTRO_INEXISTENTE}")
        assert a.status_code == b.status_code == 404
        assert a.json()["code"] == b.json()["code"] == "PERFIL_PUESTO_NOT_FOUND"
        assert a.json()["message"] == b.json()["message"]


class TestEdicion:
    async def test_edita_solo_lo_que_viaja(self, almacen, como) -> None:
        """`exclude_none`: los campos ausentes quedan intactos."""
        fila = almacen.catalogo["perfiles_puesto"][0]
        fila["descripcion"] = "no me toques"
        async with como() as c:
            r = await c.put(f"{BASE}/{fila['id']}", json={"nombre": "Renombrado"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "Renombrado"
        assert r.json()["descripcion"] == "no me toques"

    async def test_la_cadena_vacia_SI_vacia_el_campo(self, almacen, como) -> None:
        """Contracara del anterior, y el contrato declarado en `PerfilPuestoUpdate`: `null` no
        toca, `""` sí escribe. Sin este test la mitad del contrato no está verificada."""
        fila = almacen.catalogo["perfiles_puesto"][1]
        fila["descripcion"] = "algo"
        async with como() as c:
            r = await c.put(f"{BASE}/{fila['id']}", json={"descripcion": ""})
        assert r.json()["descripcion"] == ""

    async def test_renombrar_a_uno_existente_da_409(self, almacen, como) -> None:
        otro = almacen.catalogo["perfiles_puesto"][5]["nombre"]
        fila = almacen.catalogo["perfiles_puesto"][0]
        async with como() as c:
            r = await c.put(f"{BASE}/{fila['id']}", json={"nombre": otro})
        assert r.status_code == 409

    async def test_dejarse_el_MISMO_nombre_NO_es_duplicado(self, almacen, como) -> None:
        """El `excepto_id` tiene que excluirse a sí mismo, o nadie podría editar otro campo
        mandando el nombre sin cambios."""
        fila = almacen.catalogo["perfiles_puesto"][0]
        async with como() as c:
            r = await c.put(f"{BASE}/{fila['id']}",
                            json={"nombre": fila["nombre"], "jornada": "9 a 18"})
        assert r.status_code == 200 and r.json()["jornada"] == "9 a 18"


class TestBajaLogica:
    async def test_la_baja_no_borra_la_fila(self, almacen, como) -> None:
        """🔴 `vacantes.perfil_puesto_id` es ON DELETE SET NULL: un borrado físico no falla,
        arranca la trazabilidad en silencio. Por eso se verifica que la fila SIGA existiendo."""
        fila = almacen.catalogo["perfiles_puesto"][0]
        antes = len(almacen.catalogo["perfiles_puesto"])
        async with como() as c:
            r = await c.delete(f"{BASE}/{fila['id']}")
        assert r.status_code == 204
        assert len(almacen.catalogo["perfiles_puesto"]) == antes
        assert fila["activo"] is False

    async def test_el_dado_de_baja_sale_del_listado_por_defecto(self, almacen, como) -> None:
        fila = almacen.catalogo["perfiles_puesto"][0]
        async with como() as c:
            await c.delete(f"{BASE}/{fila['id']}")
            body = (await c.get(BASE)).json()
        assert body["total"] == TOTAL_FILAS - 1


# ── 6. Permisos ───────────────────────────────────────────────────────────────


class TestPermisos:
    """El gate es el REAL (`require_permission`), no un fake: lo único falseado es el rol."""

    async def test_gerencia_lectura_puede_leer(self, como) -> None:
        async with como("gerencia_lectura") as c:
            assert (await c.get(BASE)).status_code == 200

    @pytest.mark.parametrize("metodo,ruta,body", [
        ("post", BASE, _alta()),
        ("put", f"{BASE}/{INEXISTENTE}", {"nombre": "x"}),
        ("delete", f"{BASE}/{INEXISTENTE}", None),
    ])
    async def test_gerencia_lectura_no_puede_escribir(self, almacen, como,
                                                      metodo, ruta, body) -> None:
        antes = len(almacen.catalogo["perfiles_puesto"])
        async with como("gerencia_lectura") as c:
            r = await getattr(c, metodo)(ruta, **({"json": body} if body else {}))
        assert r.status_code == 403
        assert len(almacen.catalogo["perfiles_puesto"]) == antes

    @pytest.mark.parametrize("metodo,ruta", [("get", BASE), ("get", f"{BASE}/campos")])
    async def test_mandos_medios_no_llega_ni_a_leer(self, como, metodo, ruta) -> None:
        """`MANDOS_MEDIOS_SECCIONES` son solo vacaciones y ausencias: acá no puede nada."""
        async with como("mandos_medios") as c:
            assert (await getattr(c, metodo)(ruta)).status_code == 403

    async def test_un_rol_desconocido_es_fail_closed(self, como) -> None:
        async with como("rol_inventado") as c:
            assert (await c.get(BASE)).status_code == 403


# ── 7. Auditoría ──────────────────────────────────────────────────────────────


class TestAuditoria:
    """🔴 EL TEST QUE MÁS IMPORTA DE ESTE ARCHIVO.

    El request llega con `X-Empresa-Id` resuelto a `EMPRESA_HEADER`, o sea que **hay una
    empresa concreta a mano**. Que el evento la deje en `None` teniendo dónde copiarla es
    justamente lo que se afirma. Si el middleware falseado devolviera `None`, estos tests
    pasarían con el bug puesto.
    """

    async def test_el_alta_emite_UN_evento(self, como, auditoria) -> None:
        async with como() as c:
            await c.post(BASE, json=_alta())
        assert len(auditoria.eventos) == 1
        ev = auditoria.eventos[0]
        assert ev["evento"] == "alta_perfil_puesto" and ev["accion"] == "INSERT"
        assert ev["entidad"] == "perfil_puesto"
        assert ev["usuario_id"] == USUARIO
        assert ev["datos_nuevos"]["nombre"] == "Analista SQL"
        assert ev["datos_anteriores"] is None

    async def test_la_edicion_emite_un_diff(self, almacen, como, auditoria) -> None:
        fila = almacen.catalogo["perfiles_puesto"][0]
        viejo = fila["nombre"]
        async with como() as c:
            await c.put(f"{BASE}/{fila['id']}", json={"nombre": "Nuevo nombre"})
        ev = auditoria.eventos[-1]
        assert ev["evento"] == "update_perfil_puesto" and ev["accion"] == "UPDATE"
        assert ev["datos_anteriores"]["nombre"] == viejo
        assert ev["datos_nuevos"]["nombre"] == "Nuevo nombre"

    async def test_la_baja_fotografia_el_estado_previo(self, almacen, como, auditoria) -> None:
        fila = almacen.catalogo["perfiles_puesto"][0]
        async with como() as c:
            await c.delete(f"{BASE}/{fila['id']}")
        ev = auditoria.eventos[-1]
        assert ev["evento"] == "baja_perfil_puesto" and ev["accion"] == "DELETE"
        assert ev["datos_anteriores"]["activo"] is True, "fotografió el estado de DESPUÉS"
        assert ev["datos_nuevos"] is None

    @pytest.mark.parametrize("operacion", ["alta", "edicion", "baja"])
    async def test_ningun_evento_toma_la_empresa_del_header(self, almacen, como,
                                                            auditoria, operacion) -> None:
        """🔴 LA MUTACIÓN OBLIGATORIA. Un perfil es del GRUPO y no tiene empresa; el header
        dice `EMPRESA_HEADER`. Etiquetar el evento con eso sería afirmar que el perfil es de
        la empresa A solo porque el usuario tenía A seleccionada en el sidebar."""
        fila = almacen.catalogo["perfiles_puesto"][0]
        async with como() as c:
            if operacion == "alta":
                await c.post(BASE, json=_alta())
            elif operacion == "edicion":
                await c.put(f"{BASE}/{fila['id']}", json={"nombre": "Otro"})
            else:
                await c.delete(f"{BASE}/{fila['id']}")
        assert auditoria.eventos, "no se emitió ningún evento: el test quedaría vacuo"
        ev = auditoria.eventos[-1]
        assert "empresa_id" in ev, "el payload ni siquiera declara empresa_id"
        assert ev["empresa_id"] is None
        assert ev["empresa_id"] != EMPRESA_HEADER

    async def test_una_operacion_fallida_no_audita(self, como, auditoria) -> None:
        """Un 409 no es un hecho de negocio: si auditara, el log contaría ediciones que
        nunca ocurrieron."""
        async with como() as c:
            await c.post(BASE, json=_alta())
            await c.post(BASE, json=_alta())
        assert len(auditoria.eventos) == 1


# ── 8. Export ─────────────────────────────────────────────────────────────────


class TestExport:
    async def test_devuelve_un_archivo(self, como) -> None:
        async with como() as c:
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        assert r.status_code == 200
        assert "attachment" in r.headers["content-disposition"]
        assert "perfiles_puesto" in r.headers["content-disposition"]

    async def test_exportar_no_matchea_como_un_id(self, como) -> None:
        """🔴 El orden de declaración: si `/exportar` estuviera después de `/{id}`, esto sería
        un 422 de "no es un UUID" en vez del archivo."""
        async with como() as c:
            assert (await c.get(f"{BASE}/exportar")).status_code == 200

    async def test_el_export_NO_se_pagina(self, almacen, como) -> None:
        """Las 120 filas entran en el archivo aunque el listado muestre 20."""
        async with como() as c:
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        cuerpo = r.content.decode("utf-8", errors="replace")
        assert cuerpo.count("Perfil ") >= TOTAL_FILAS

    async def test_el_export_respeta_el_search(self, como) -> None:
        """Si el filtro no viajara, el archivo traería MÁS filas de las que se ven en
        pantalla — que es el bug que el barrido de paridad persigue."""
        async with como() as c:
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv", "search": "Perfil 01"})
        cuerpo = r.content.decode("utf-8", errors="replace")
        assert cuerpo.count("Perfil 01") == 10

    async def test_separa_las_cuatro_naturalezas_en_columnas_propias(self, como) -> None:
        """🔴 Experiencia · Formación · Conocimientos técnicos · Otros requisitos salen como
        CUATRO columnas. Concatenarlas desharía en el archivo la única separación que este
        módulo existe para sostener."""
        async with como() as c:
            r = await c.get(f"{BASE}/exportar", params={"formato": "csv"})
        # El CSV abre con el título y el nombre de la hoja; la fila de headers es la primera
        # que trae "Activo". Se la busca en vez de asumir un número de línea, así el test no se
        # rompe si el motor de export cambia su preámbulo.
        lineas = r.content.decode("utf-8", errors="replace").splitlines()
        cabecera = next((ln for ln in lineas if "Activo" in ln), "")
        assert cabecera, "no se encontró la fila de encabezados en el CSV"
        for col in ("Experiencia", "Formaci", "Conocimientos", "Otros requisitos"):
            assert col in cabecera, f"falta la columna {col}"
        assert "Requisitos" not in cabecera.replace("Otros requisitos", ""), \
            "hay una columna 'Requisitos' suelta: las cuatro naturalezas se volvieron a mezclar"


# ── 9. El catálogo de labels ──────────────────────────────────────────────────


class TestCampos:
    async def test_sirve_los_campos_en_orden(self, como) -> None:
        async with como() as c:
            body = (await c.get(f"{BASE}/campos")).json()
        nombres = [c_["campo"] for c_ in body["campos"]]
        assert nombres[0] == "nombre"
        assert nombres.index("requisitos") > nombres.index("conocimientos_tecnicos") > \
            nombres.index("formacion") > nombres.index("experiencia"), \
            "requisitos tiene que ir DESPUÉS de los tres que le sacan contenido"

    async def test_todos_los_campos_tienen_ayuda(self, como) -> None:
        """Un label sin ayuda es exactamente el estado que este módulo vino a evitar."""
        async with como() as c:
            body = (await c.get(f"{BASE}/campos")).json()
        assert len(body["campos"]) >= 12
        sin_ayuda = [c_["campo"] for c_ in body["campos"] if len(c_["ayuda"].strip()) < 20]
        assert not sin_ayuda, f"campos sin texto de ayuda: {sin_ayuda}"
        assert len(body["nota_requisitos"]) > 50

    async def test_los_vocabularios_coinciden_con_los_Literal_del_schema(self, como) -> None:
        """🔴 Las dos direcciones. Si el catálogo ofreciera un valor que el schema rechaza, el
        front pondría en un select algo que devuelve 422; si le faltara uno, la pantalla no
        dejaría elegir un valor válido."""
        from typing import get_args

        from schemas.perfil_puesto import Modalidad, Nivel, TipoContrato
        async with como() as c:
            body = (await c.get(f"{BASE}/campos")).json()
        for clave, tipo in (("modalidades", Modalidad), ("tipos_contrato", TipoContrato),
                            ("niveles", Nivel)):
            assert {o["value"] for o in body[clave]} == set(get_args(tipo)), clave
            assert all(o["label"] for o in body[clave]), clave


# ── 10. Lo que un perfil NO tiene ─────────────────────────────────────────────


class TestLoQueNoExiste:
    """🔴 Un prototipo inventó competencias, ubicación y contadores de ocupantes/vacantes. No
    están en el modelo. Este test es la barrera contra que vuelvan a aparecer, y falla tanto si
    alguien las agrega al schema como si las manda por el body y el backend las acepta."""

    @pytest.mark.parametrize("campo", [
        "competencias", "ubicacion", "ocupantes", "vacantes_abiertas", "empresa_id", "area_id",
    ])
    async def test_no_salen_en_la_respuesta(self, como, campo) -> None:
        async with como() as c:
            body = (await c.post(BASE, json={**_alta(), "nombre": f"P {campo}"})).json()
        assert campo not in body

    async def test_un_campo_inventado_en_el_body_no_se_persiste(self, almacen, como) -> None:
        async with como() as c:
            body = (await c.post(BASE, json={**_alta(), "competencias": ["SQL"]})).json()
        fila = next(f for f in almacen.catalogo["perfiles_puesto"] if f["id"] == body["id"])
        assert "competencias" not in fila
