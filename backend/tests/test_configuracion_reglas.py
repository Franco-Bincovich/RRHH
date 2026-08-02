"""
Configuración de reglas de negocio (migración 085): resolución COALESCE, escala y permisos.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

El fake INDEXA POR `empresa_id` y modela TRES alcances a la vez: empresa A (con fila propia),
empresa B (sin fila propia) y la global. Devuelve `None`/`[]` cuando la clave no está.

Un fake que aceptara `empresa_id` y lo ignorara —devolviendo siempre la misma fila— dejaría
pasar los dos casos del COALESCE sin haber resuelto nada, que es exactamente el caso #1 de
"Un test solo prueba lo que el fake puede desmentir". Acá, si el service dejara de consultar
la fila de la empresa y fuera siempre a la global, los tests de la empresa A rojean; si dejara
de caer a la global, los de la empresa B rojean.

Los fakes de ESCRITURA construyen la respuesta A PARTIR de lo que reciben (guardan en el dict
y releen), nunca devuelven un objeto prefabricado: si no, el test afirmaría algo sobre su
propia constante.
"""
import os

# Patch env antes de importar el proyecto (config.settings lee os.environ al instanciar).
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

from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import UUID

import pytest

from schemas.configuracion import EscalaUpdate, ParametrosUpdate, TramoEscala
from services.configuracion_service import ConfiguracionService
from utils.errors import AppError
from utils.permisos import Accion, Seccion, puede

EMPRESA_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
EMPRESA_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

# Los valores que la migración 085 siembra en la fila global.
GLOBAL = {
    "base_dias_habiles": 22, "corte_antiguedad_mes": 10,
    "periodo_vacacional_desde_mes": 10, "periodo_vacacional_hasta_mes": 4,
    "primer_anio_mes_corte": 7, "primer_anio_dias": 5, "vencimiento_anios": 4,
}
ESCALA_GLOBAL = [
    {"antiguedad_anios": 0, "dias": 14},
    {"antiguedad_anios": 5, "dias": 21},
    {"antiguedad_anios": 15, "dias": 28},
]


class _FakeRepo:
    """Modela la fila global (clave None) y las de cada empresa, por separado."""

    def __init__(self, params_propios=None, escala_propia=None, con_global: bool = True) -> None:
        self.parametros: Dict[Optional[str], Dict[str, Any]] = {}
        self.escala: Dict[Optional[str], List[Dict[str, Any]]] = {}
        if con_global:
            self.parametros[None] = dict(GLOBAL)
            self.escala[None] = [dict(t) for t in ESCALA_GLOBAL]
        if params_propios:
            self.parametros[str(EMPRESA_A)] = dict(params_propios)
        if escala_propia:
            self.escala[str(EMPRESA_A)] = [dict(t) for t in escala_propia]
        self.borrados: List[Optional[str]] = []

    def find_parametros(self, empresa_id):
        return self.parametros.get(empresa_id)

    def upsert_parametros(self, empresa_id, data):
        # Construye la respuesta a partir de lo recibido: nada prefabricado.
        self.parametros[empresa_id] = dict(data)
        return {**data, "empresa_id": empresa_id}

    def find_escala(self, empresa_id):
        return sorted(self.escala.get(empresa_id, []), key=lambda t: t["antiguedad_anios"])

    def replace_escala(self, empresa_id, tramos):
        self.borrados.append(empresa_id)
        self.escala[empresa_id] = [dict(t) for t in tramos]


def _svc(**kw) -> ConfiguracionService:
    return ConfiguracionService(_FakeRepo(**kw))


# ── COALESCE ──────────────────────────────────────────────────────────────────────────────

class TestCoalesceParametros:
    def test_empresa_sin_fila_propia_usa_la_global(self) -> None:
        r = _svc().get_parametros(EMPRESA_B)
        assert r.base_dias_habiles == 22
        assert r.es_propia is False

    def test_empresa_con_fila_propia_usa_la_suya(self) -> None:
        propios = {**GLOBAL, "base_dias_habiles": 20, "vencimiento_anios": 2}
        r = _svc(params_propios=propios).get_parametros(EMPRESA_A)
        assert r.base_dias_habiles == 20
        assert r.vencimiento_anios == 2
        assert r.es_propia is True

    def test_la_fila_propia_de_A_no_se_le_aplica_a_B(self) -> None:
        # La barrera entre empresas: sin ella, configurar A cambiaría las reglas de B.
        svc = _svc(params_propios={**GLOBAL, "base_dias_habiles": 20})
        assert svc.get_parametros(EMPRESA_B).base_dias_habiles == 22

    def test_modo_consolidado_devuelve_la_global(self) -> None:
        # empresa_id None no es un fallo de validación: es "todas las empresas", y lo que rige
        # para cualquiera que no configuró nada es justamente la global.
        r = _svc(params_propios={**GLOBAL, "base_dias_habiles": 20}).get_parametros(None)
        assert r.base_dias_habiles == 22 and r.es_propia is False

    def test_sin_fila_global_falla_fuerte(self) -> None:
        # Inventar defaults en Python haría que la pantalla mostrara valores que NO rigen.
        with pytest.raises(AppError) as e:
            _svc(con_global=False).get_parametros(EMPRESA_B)
        assert e.value.code == "CONFIG_GLOBAL_FALTANTE"


class TestCoalesceEscala:
    def test_empresa_sin_tramos_propios_usa_la_global(self) -> None:
        r = _svc().get_escala(EMPRESA_B)
        assert [(t.antiguedad_anios, t.dias) for t in r.tramos] == [(0, 14), (5, 21), (15, 28)]
        assert r.es_propia is False

    def test_empresa_con_tramos_propios_usa_SOLO_los_suyos(self) -> None:
        # No es la unión con la global: unirlas daría dos tramos reclamando la antigüedad 0
        # y cuál gana dependería del orden de la query.
        propia = [{"antiguedad_anios": 0, "dias": 15}]
        r = _svc(escala_propia=propia).get_escala(EMPRESA_A)
        assert [(t.antiguedad_anios, t.dias) for t in r.tramos] == [(0, 15)]
        assert r.es_propia is True

    def test_los_tramos_salen_ordenados_por_antiguedad(self) -> None:
        # El tramo aplicable es el de mayor antigüedad que no supere la del empleado: esa
        # búsqueda se lee sobre una lista ordenada.
        r = _svc(escala_propia=[{"antiguedad_anios": 10, "dias": 25},
                                {"antiguedad_anios": 0, "dias": 14}]).get_escala(EMPRESA_A)
        assert [t.antiguedad_anios for t in r.tramos] == [0, 10]


# ── Escritura ─────────────────────────────────────────────────────────────────────────────

class TestAgregarYQuitarTramos:
    def test_agregar_un_tramo(self) -> None:
        svc = _svc(escala_propia=[{"antiguedad_anios": 0, "dias": 14}])
        nueva = EscalaUpdate(tramos=[TramoEscala(antiguedad_anios=0, dias=14),
                                     TramoEscala(antiguedad_anios=20, dias=35)])
        r = svc.set_escala(EMPRESA_A, nueva)
        assert [(t.antiguedad_anios, t.dias) for t in r.tramos] == [(0, 14), (20, 35)]

    def test_quitar_un_tramo(self) -> None:
        svc = _svc(escala_propia=[{"antiguedad_anios": 0, "dias": 14},
                                  {"antiguedad_anios": 5, "dias": 21}])
        r = svc.set_escala(EMPRESA_A, EscalaUpdate(tramos=[TramoEscala(antiguedad_anios=0, dias=14)]))
        assert [t.antiguedad_anios for t in r.tramos] == [0]

    def test_quitarlos_todos_vuelve_a_heredar_la_global(self) -> None:
        svc = _svc(escala_propia=[{"antiguedad_anios": 0, "dias": 15}])
        r = svc.set_escala(EMPRESA_A, EscalaUpdate(tramos=[]))
        assert [(t.antiguedad_anios, t.dias) for t in r.tramos] == [(0, 14), (5, 21), (15, 28)]
        assert r.es_propia is False

    def test_dos_tramos_con_la_misma_antiguedad_se_rechazan(self) -> None:
        # El índice único de la base también lo rechaza, pero como 500 genérico.
        svc = _svc()
        with pytest.raises(AppError) as e:
            svc.set_escala(EMPRESA_A, EscalaUpdate(tramos=[TramoEscala(antiguedad_anios=5, dias=21),
                                                           TramoEscala(antiguedad_anios=5, dias=28)]))
        assert e.value.code == "ESCALA_TRAMOS_DUPLICADOS" and e.value.status_code == 422

    def test_guardar_la_escala_de_A_no_toca_la_global(self) -> None:
        # 🔴 Un DELETE sin filtro se llevaría la fila global y dejaría sin reglas a TODAS.
        fake = _FakeRepo()
        svc = ConfiguracionService(fake)
        svc.set_escala(EMPRESA_A, EscalaUpdate(tramos=[TramoEscala(antiguedad_anios=0, dias=99)]))
        assert fake.escala[None] == ESCALA_GLOBAL
        assert fake.borrados == [str(EMPRESA_A)]

    def test_guardar_parametros_crea_la_fila_propia(self) -> None:
        fake = _FakeRepo()
        svc = ConfiguracionService(fake)
        r = svc.set_parametros(EMPRESA_A, ParametrosUpdate(**{**GLOBAL, "base_dias_habiles": 20}))
        assert r.es_propia is True and r.base_dias_habiles == 20
        assert fake.parametros[None]["base_dias_habiles"] == 22, "no debe pisar la global"


class TestRangosDelSchema:
    """Los rangos duplican los CHECK de la base: Pydantic señala el campo, la base da un 500."""

    @pytest.mark.parametrize("campo,valor", [
        ("base_dias_habiles", 0), ("base_dias_habiles", 32),
        ("corte_antiguedad_mes", 13), ("periodo_vacacional_desde_mes", 0),
        ("vencimiento_anios", 0), ("primer_anio_dias", -1),
    ])
    def test_valor_fuera_de_rango_no_valida(self, campo: str, valor: int) -> None:
        with pytest.raises(Exception):
            ParametrosUpdate(**{**GLOBAL, campo: valor})

    def test_un_tramo_de_cero_dias_no_valida(self) -> None:
        with pytest.raises(Exception):
            TramoEscala(antiguedad_anios=0, dias=0)


# ── El WHERE lo pone la query ─────────────────────────────────────────────────────────────

class TestElWhereDelRepoLlevaLaEmpresa:
    """El fake de repo fija el contrato pero no toca la query real.

    Acá se faltea un escalón más abajo —el cliente de Supabase— para verificar que el filtro
    de empresa viaje EN LA QUERY. Filtrar en Python la lista completa expondría las filas de
    otras empresas a cualquiera que mire la respuesta cruda.

    Y en particular: la fila GLOBAL se pide con `.is_("empresa_id", "null")`, NO con
    `.eq("empresa_id", None)` — ese último manda `empresa_id=eq.None`, compara contra el
    string "None" y no matchea nada, en silencio.
    """

    def _repo_con_espia(self, monkeypatch):
        import repositories.configuracion_repo as mod

        llamadas: list = []

        class _Q:
            def select(self, *a, **k): return self
            def order(self, *a, **k): return self
            def eq(self, col, val):
                llamadas.append(("eq", col, val)); return self
            def is_(self, col, val):
                llamadas.append(("is", col, val)); return self
            def maybe_single(self): return self
            def execute(self): return SimpleNamespace(data=[], count=0)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.ConfiguracionRepo(), llamadas

    def test_la_fila_de_la_empresa_se_pide_con_eq(self, monkeypatch) -> None:
        repo, llamadas = self._repo_con_espia(monkeypatch)
        repo.find_parametros(str(EMPRESA_A))
        assert ("eq", "empresa_id", str(EMPRESA_A)) in llamadas

    def test_la_fila_global_se_pide_con_is_null(self, monkeypatch) -> None:
        repo, llamadas = self._repo_con_espia(monkeypatch)
        repo.find_parametros(None)
        assert ("is", "empresa_id", "null") in llamadas
        assert not [c for c in llamadas if c[0] == "eq"], (
            "la global NO se pide con .eq(empresa_id, None): eso compara contra el string 'None'"
        )

    def test_el_delete_de_la_escala_filtra_por_empresa(self, monkeypatch) -> None:
        """🔴 EL TEST DEL SERVICE NO ALCANZA PARA ESTO, y el mutation check lo mostró.

        `test_guardar_la_escala_de_A_no_toca_la_global` mira el dict del fake, que registra a
        quién se le pidió borrar — o sea, fija el CONTRATO. Pero el fake no ejecuta la query
        real: sacarle el `.eq("empresa_id", ...)` al DELETE del repo dejaba todo en verde.

        Y es la mutación más cara de todas: un DELETE sin filtro se lleva la fila GLOBAL, y
        con ella las reglas de TODAS las empresas que la estaban heredando. Sin error, sin
        aviso, y con el guardado respondiendo 200.
        """
        import repositories.configuracion_repo as mod

        filtros: list = []

        class _Del:
            def eq(self, col, val):
                filtros.append((col, val)); return self
            def execute(self): return SimpleNamespace(data=[])

        class _Q:
            def delete(self): return _Del()
            def insert(self, filas):
                self._filas = filas; return self
            def execute(self): return SimpleNamespace(data=getattr(self, "_filas", []))

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        mod.ConfiguracionRepo().replace_escala(str(EMPRESA_A), [{"antiguedad_anios": 0, "dias": 14}])
        assert filtros == [("empresa_id", str(EMPRESA_A))], (
            "el DELETE de la escala tiene que filtrar por empresa: sin el .eq se lleva la global"
        )

    def test_las_filas_nuevas_llevan_la_empresa(self, monkeypatch) -> None:
        # Sin empresa_id el INSERT crearía tramos GLOBALES, que es el otro lado del mismo daño.
        import repositories.configuracion_repo as mod

        insertadas: list = []

        class _Del:
            def eq(self, *a): return self
            def execute(self): return SimpleNamespace(data=[])

        class _Q:
            def delete(self): return _Del()
            def insert(self, filas):
                insertadas.extend(filas); return self
            def execute(self): return SimpleNamespace(data=insertadas)

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        mod.ConfiguracionRepo().replace_escala(str(EMPRESA_A), [{"antiguedad_anios": 0, "dias": 14}])
        assert insertadas == [{"antiguedad_anios": 0, "dias": 14, "empresa_id": str(EMPRESA_A)}]

    def test_la_escala_ordena_en_la_query(self, monkeypatch) -> None:
        import repositories.configuracion_repo as mod

        ordenes: list = []

        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def is_(self, *a, **k): return self
            def order(self, col, **k):
                ordenes.append(col); return self
            def execute(self): return SimpleNamespace(data=[])

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        mod.ConfiguracionRepo().find_escala(str(EMPRESA_A))
        assert ordenes == ["antiguedad_anios"]


# ── El índice parcial ─────────────────────────────────────────────────────────────────────

class TestElIndiceParcialProtegeLaFilaGlobal:
    """⚠️ ALCANCE REAL, para no venderlo de más: la suite no tiene Postgres, así que esto
    verifica que el DDL esté DECLARADO en la migración y en schema.sql — no que el motor lo
    rechace (eso lo hace Postgres si el DDL es válido, y se confirma al correr la 085).

    Igual cubre el modo de falla que importa, que es humano: `UNIQUE (empresa_id)` a secas se
    lee como suficiente y NO LO ES, porque en SQL NULL <> NULL — dejaría entrar dos, tres o
    cien filas globales y la lectura elegiría una al azar, cambiando las reglas de todas las
    empresas según el plan de la query. Si alguien "simplifica" el índice parcial a un UNIQUE
    común, esto rojea.
    """

    def _texto(self, ruta: str) -> str:
        from pathlib import Path
        return (Path(__file__).resolve().parents[1] / ruta).read_text(encoding="utf-8")

    @pytest.fixture
    def migracion(self) -> str:
        return self._texto("migrations/085_configuracion_reglas.sql")

    @pytest.fixture
    def schema(self) -> str:
        return self._texto("db/schema.sql")

    def test_la_migracion_declara_una_sola_fila_global_de_parametros(self, migracion: str) -> None:
        # Indexa la CONSTANTE (empresa_id IS NULL): dos filas globales colisionan.
        assert "ux_parametros_empresa_global" in migracion
        assert "((empresa_id IS NULL)) WHERE empresa_id IS NULL" in migracion

    def test_y_una_fila_por_empresa(self, migracion: str) -> None:
        assert "ux_parametros_empresa_por_empresa" in migracion
        assert "(empresa_id) WHERE empresa_id IS NOT NULL" in migracion

    def test_la_escala_global_no_repite_antiguedad(self, migracion: str) -> None:
        # Acá el parcial NO va sobre la constante: la escala global son VARIAS filas y lo que
        # no puede repetirse es el punto de corte.
        assert "ux_escala_global" in migracion
        assert "(antiguedad_anios) WHERE empresa_id IS NULL" in migracion

    def test_ningun_unique_comun_sobre_empresa_id(self, migracion: str) -> None:
        # Solo el SQL real: el encabezado MENCIONA `UNIQUE (empresa_id)` para explicar por qué
        # NO se usa, y buscarlo sobre el archivo entero matchearía esa explicación.
        sql = [ln for ln in migracion.splitlines() if not ln.lstrip().startswith("--")]
        assert not [ln for ln in sql if "UNIQUE (empresa_id)" in ln], (
            "un UNIQUE común sobre empresa_id no restringe las filas globales: NULL <> NULL"
        )

    @pytest.mark.parametrize("indice", [
        "ux_parametros_empresa_global", "ux_parametros_empresa_por_empresa",
        "ux_escala_global", "ux_escala_por_empresa",
        "ux_tipos_ausencia_nombre_global", "ux_tipos_ausencia_nombre_por_empresa",
    ])
    def test_schema_sql_refleja_los_seis_indices(self, schema: str, indice: str) -> None:
        # schema.sql es la fuente de RECONSTRUCCIÓN: si un índice vive solo en la migración,
        # una base rebuildeada desde cero nace sin él.
        assert indice in schema

    def test_la_unique_global_de_nombre_ya_no_esta_en_schema_sql(self, schema: str) -> None:
        # La 085 la dropea: con empresa_id nullable prohibía que dos empresas tuvieran cada
        # una su "Licencia especial".
        assert "ADD CONSTRAINT tipos_ausencia_nombre_key" not in schema

    def test_las_dos_tablas_nuevas_estan_en_schema_sql(self, schema: str) -> None:
        assert "CREATE TABLE public.parametros_empresa" in schema
        assert "CREATE TABLE public.reglas_vacaciones_escala" in schema


# ── Permisos ──────────────────────────────────────────────────────────────────────────────

class TestQuienPuedeTocarLasReglas:
    """CONFIGURACION es una sección PROPIA, y ese es el punto.

    mandos_medios tiene WRITE en VACACIONES y AUSENCIAS. Si las reglas colgaran de cualquiera
    de esas dos secciones, podría cambiar la escala de vacaciones de toda la empresa desde la
    pantalla en la que carga una licencia.
    """

    def test_admin_rrhh_lee_y_escribe(self) -> None:
        assert puede("admin_rrhh", Seccion.CONFIGURACION, Accion.READ)
        assert puede("admin_rrhh", Seccion.CONFIGURACION, Accion.WRITE)

    def test_gerencia_lectura_lee_pero_no_escribe(self) -> None:
        assert puede("gerencia_lectura", Seccion.CONFIGURACION, Accion.READ)
        assert not puede("gerencia_lectura", Seccion.CONFIGURACION, Accion.WRITE)

    @pytest.mark.parametrize("accion", [Accion.READ, Accion.WRITE])
    def test_mandos_medios_no_accede_ni_para_leer(self, accion: Accion) -> None:
        assert not puede("mandos_medios", Seccion.CONFIGURACION, accion)

    @pytest.mark.parametrize("rol", [None, "rol_inventado"])
    def test_fail_closed(self, rol) -> None:
        assert not puede(rol, Seccion.CONFIGURACION, Accion.READ)

    def test_no_se_reuso_vacaciones_ni_ausencias(self) -> None:
        # Guarda explícita: el día que alguien "simplifique" la sección, esto rojea.
        fugas = [s for s in (Seccion.VACACIONES, Seccion.AUSENCIAS)
                 if puede("mandos_medios", s, Accion.WRITE)
                 and not puede("mandos_medios", Seccion.CONFIGURACION, Accion.WRITE)]
        assert len(fugas) == 2, "mandos_medios debe escribir vac/aus pero NO configuración"


class TestLosEndpointsEstanGateados:
    """Ejercita la dependency real de cada ruta, no solo que exista.

    `assert ruta.dependencies` pasaría con el gate puesto en la sección equivocada. Acá se
    invoca el callable con un rol concreto: si alguien cambiara CONFIGURACION por AUSENCIAS,
    mandos_medios dejaría de romper y el test rojea.
    """

    def _rutas(self):
        from fastapi.routing import APIRoute

        from main import app
        return [r for r in app.routes
                if isinstance(r, APIRoute) and r.path.startswith("/api/configuracion")]

    async def _correr(self, ruta, rol: Optional[str]) -> None:
        """Invoca las dependencies de la ruta con un request mínimo: solo .state.user, que es
        lo único que require_permission lee."""
        req = SimpleNamespace(state=SimpleNamespace(user={"rol": rol} if rol else None))
        for dep in ruta.dependencies:
            await dep.dependency(req)

    def test_estan_las_tres_rutas(self) -> None:
        # Guarda de mínimo: sin ella, si el router dejara de montarse el barrido de abajo
        # recorrería una lista vacía y pasaría sin haber verificado nada.
        assert len(self._rutas()) >= 3

    def test_ninguna_ruta_quedo_sin_gate(self) -> None:
        sin_gate = [r.path for r in self._rutas() if not r.dependencies]
        assert sin_gate == []

    @pytest.mark.parametrize("rol", ["mandos_medios", None, "rol_inventado"])
    async def test_un_rol_sin_configuracion_rebota_en_todas(self, rol) -> None:
        for ruta in self._rutas():
            with pytest.raises(AppError) as e:
                await self._correr(ruta, rol)
            assert e.value.status_code == 403

    async def test_gerencia_lectura_lee_pero_no_escribe(self) -> None:
        for ruta in self._rutas():
            if "GET" in ruta.methods:
                await self._correr(ruta, "gerencia_lectura")  # no levanta
            else:
                with pytest.raises(AppError):
                    await self._correr(ruta, "gerencia_lectura")
