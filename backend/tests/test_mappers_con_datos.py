"""
Los tres mappers cuyo cuerpo nunca se ejecutó **y cuyas tablas TIENEN DATOS HOY** en producción.
Molde: `test_ausencia_row.py`.

| Mapper | Tabla | Filas (catálogo vivo, 9/8/2026) |
|---|---|---|
| `evaluacion_repo.find_resultados_por_evaluados` | `evaluacion_resultados` | **307** |
| `audit_repo._build`                             | `auditoria`              | **143** |
| `proyecto_asignaciones_repo._build`             | `proyecto_asignaciones`  | **31**  |
| `vacante_repo.find_by_ids`                      | `vacantes`               | 0 → **con datos desde el 9/8** |

⚠️ `find_by_ids` estaba declarado como "0 filas, se mueve a urgente en cuanto exista la primera
vacante con candidatos". **Esa sesión llegó**: la ingesta de CVs por mail crea candidatos, y
`candidato_service.listar_todos_candidatos` usa este mapper para resolver el nombre del grupo de
cada uno. El disparador que la declaración anticipaba se cumplió, así que la declaración se borra
y el test se escribe.

Estos tres corren en producción cada vez que alguien abre `/auditoria`, la ficha de un proyecto o
un lote de evaluaciones — y su cuerpo no se había ejecutado NUNCA en un test.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS NO PUEDAN FALLAR?

**Que las listas estuvieran vacías.** Los tres abren con `if not <x>: return []`, así que con `[]`
no se ejecuta un solo lookup ni un solo `model_validate`. Es el escondite donde vivieron los dos
bugs de esta familia: el `_TA` sin definir de `_ausencia_row` y la clave leída distinta de la que
el `select` pide en `_ev_instancias_row`. Cada bloque tiene su
`test_la_lista_vacia_no_prueba_nada` y el anclaje del early-return por AST.

## 🔴 CORRECCIÓN a la declaración anterior

`evaluacion_repo` estaba declarado en `test_mappers_ejercitados` como *"módulo ev_* congelado"*.
**Es falso, y era el peor error de esa tabla**: `evaluacion_repo` es el módulo NUEVO de resultados
importados (`evaluacion_lotes` / `_evaluados` / `_resultados`), COMPLETO Y EN PRODUCCIÓN. El
congelado es `ev_*` (`ev_ciclos`, `ev_plantillas`, `ev_instancias`), que son otras tablas y están
en 0. Confundirlos dejó al mapper con MÁS datos de todo el sistema declarado como intocable.
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

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories.audit_repo as audit_mod  # noqa: E402
import repositories.evaluacion_repo as eval_mod  # noqa: E402
import repositories.proyecto_asignaciones_repo as pasig_mod  # noqa: E402
import repositories.vacante_repo as vac_mod  # noqa: E402
from tests._fake_supabase import FakeSupabase  # noqa: E402
from tests._mappers_early_return import guarda_de  # noqa: E402

E1, E2 = str(uuid4()), str(uuid4())
U1, U2 = str(uuid4()), str(uuid4())
P1, P2 = str(uuid4()), str(uuid4())
V1, V2, A1, A2 = str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4())

_PERSONAS = {
    "empresas": [{"id": E1, "nombre": "Karstec"}, {"id": E2, "nombre": "Dosuba"}],
    "users": [{"id": U1, "nombre": "Ana", "apellido": "Pérez"},
              {"id": U2, "nombre": "Luis", "apellido": "Gómez"}],
    "empleados": [{"id": P1, "nombre": "Ana", "apellido": "Pérez"},
                  {"id": P2, "nombre": "Luis", "apellido": "Gómez"}],
}


# ── 1. audit_repo._build — 143 filas en producción ────────────────────────────

class TestAuditBuild:
    """El de mayor volumen de los que quedaban sin ejercitar tras evaluaciones."""

    @pytest.fixture
    def base(self, monkeypatch) -> FakeSupabase:
        fake = FakeSupabase(dict(_PERSONAS))
        monkeypatch.setattr(audit_mod, "supabase_admin", fake)
        return fake

    def _fila(self, **kw) -> dict:
        base = {"id": str(uuid4()), "tabla": "empleados", "entidad": "empleado",
                "evento": "alta_empleado", "accion": "INSERT", "registro_id": str(uuid4()),
                "usuario_id": U1, "empresa_id": E1, "datos_anteriores": None,
                "datos_nuevos": None, "ip": None, "user_agent": None,
                "created_at": "2026-01-01T00:00:00+00:00"}
        return {**base, **kw}

    def _filas(self) -> list:
        return [
            self._fila(),
            self._fila(usuario_id=U2, empresa_id=E2, entidad="vacante", evento="baja_vacante"),
            # 🔴 Fila LEGACY del trigger viejo: `entidad` y `evento` en NULL, y sin usuario ni
            # empresa. Es el campo opcional en null que el módulo documenta, y existe de verdad
            # en producción — la tabla tiene filas de antes de la migración 058.
            self._fila(entidad=None, evento=None, usuario_id=None, empresa_id=None,
                       tabla="costos_nomina", accion="UPDATE"),
        ]

    def test_resuelve_usuario_y_empresa_de_CADA_fila(self, base) -> None:
        """Dos usuarios y dos empresas distintas: un mapper que copiara el primero rojea acá."""
        a, b, _ = audit_mod._build(self._filas())
        assert (a.usuario_nombre, a.empresa_nombre) == ("Ana Pérez", "Karstec")
        assert (b.usuario_nombre, b.empresa_nombre) == ("Luis Gómez", "Dosuba")

    def test_la_fila_legacy_cae_a_tabla_y_accion(self, base) -> None:
        """🔴 El fallback que el módulo documenta: `entidad` ← `tabla`, `evento` ← `accion`.
        Sin filas legacy en el fake, esta rama no se ejecuta y el fallback queda sin probar."""
        _, _, legacy = audit_mod._build(self._filas())
        assert (legacy.entidad, legacy.evento) == ("costos_nomina", "UPDATE")

    def test_sin_usuario_ni_empresa_los_nombres_son_None(self, base) -> None:
        """No hereda los de la fila anterior, que es el modo de falla de un mapper con estado."""
        _, _, legacy = audit_mod._build(self._filas())
        assert (legacy.usuario_nombre, legacy.empresa_nombre) == (None, None)

    def test_los_lookups_son_batch_y_solo_con_ids_reales(self, base) -> None:
        """Una consulta por dimensión, y los NULL no viajan en el `IN`."""
        audit_mod._build(self._filas())
        assert sorted(t for t, _, _ in base.consultas) == ["empresas", "users"]
        pedidos = {t: ids for t, _, ids in base.consultas}
        assert sorted(pedidos["users"]) == sorted([U1, U2])
        assert None not in pedidos["empresas"]

    def test_sin_usuarios_ni_empresas_no_consulta_nada(self, base) -> None:
        """Las dos ramas `if user_ids:` / `if emp_ids:`: un page de filas legacy no emite queries."""
        audit_mod._build([self._fila(usuario_id=None, empresa_id=None)])
        assert base.consultas == []

    def test_la_lista_vacia_no_prueba_nada(self, base) -> None:
        assert audit_mod._build([]) == []
        assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"

    def test_el_corto_circuito_sigue_en_la_primera_linea(self) -> None:
        assert guarda_de(audit_mod._build) == "rows"


# ── 2. evaluacion_repo.find_resultados_por_evaluados — 307 filas ──────────────

class TestResultadosPorEvaluados:
    """El mapper con MÁS datos del sistema. Ver la corrección del encabezado."""

    EV1, EV2 = str(uuid4()), str(uuid4())

    @pytest.fixture
    def base(self, monkeypatch) -> FakeSupabase:
        fake = FakeSupabase({"evaluacion_resultados": [
            {"id": str(uuid4()), "evaluado_id": self.EV2, "tipo_evaluador": "PAR",
             "competencia": "Comunicación", "orden": 2, "nota": 3.0,
             "created_at": "2026-07-01T00:00:00+00:00"},
            {"id": str(uuid4()), "evaluado_id": self.EV1, "tipo_evaluador": "AUTOEVALUACION",
             "competencia": "Liderazgo", "orden": 1, "nota": 4.5,
             "created_at": "2026-07-01T00:00:00+00:00"},
        ]})
        monkeypatch.setattr(eval_mod, "supabase_admin", fake)
        return fake

    def test_trae_los_resultados_de_los_evaluados_pedidos(self, base) -> None:
        salida = eval_mod.EvaluacionRepo().find_resultados_por_evaluados([self.EV1, self.EV2])
        assert {str(r.evaluado_id) for r in salida} == {self.EV1, self.EV2}
        assert {r.competencia for r in salida} == {"Comunicación", "Liderazgo"}
        assert {r.tipo_evaluador for r in salida} == {"PAR", "AUTOEVALUACION"}

    def test_filtra_por_evaluado_id_no_por_id(self, base) -> None:
        """La columna del `IN` es `evaluado_id`. Con `id` el resultado sería vacío y el mapper
        parecería correcto por el motivo equivocado."""
        eval_mod.EvaluacionRepo().find_resultados_por_evaluados([self.EV1])
        tabla, columna, ids = base.consultas[0]
        assert (tabla, columna, ids) == ("evaluacion_resultados", "evaluado_id", [self.EV1])

    def test_el_orden_lo_pone_la_QUERY_no_python(self, base) -> None:
        """🔴 El fake registra `.order()` y NO ordena, a propósito. Si ordenara, sacarle el
        `.order("orden")` al repo dejaría este test en verde — es el caso #3 de la regla."""
        eval_mod.EvaluacionRepo().find_resultados_por_evaluados([self.EV1, self.EV2])
        assert base.ordenes == [("evaluacion_resultados", "orden", False)]

    def test_sin_ids_no_consulta(self, base) -> None:
        assert eval_mod.EvaluacionRepo().find_resultados_por_evaluados([]) == []
        assert base.consultas == [] and base.ordenes == []

    def test_el_corto_circuito_sigue_en_la_primera_linea(self) -> None:
        assert guarda_de(eval_mod.EvaluacionRepo.find_resultados_por_evaluados) == "ids"


# ── 3. proyecto_asignaciones_repo._build — 31 filas ───────────────────────────

class TestProyectoAsignacionesBuild:

    @pytest.fixture
    def base(self, monkeypatch) -> FakeSupabase:
        fake = FakeSupabase(dict(_PERSONAS))
        monkeypatch.setattr(pasig_mod, "supabase_admin", fake)
        return fake

    def _filas(self) -> list:
        base = {"proyecto_id": str(uuid4()), "fecha_desde": None, "fecha_hasta": None,
                "created_at": "2026-01-01T00:00:00+00:00"}
        return [
            {**base, "id": str(uuid4()), "empleado_id": P1, "empleado_empresa_id": E1,
             "rol": "Desarrollo", "valor_hora": 100.0, "activo": True},
            # 🔴 Empleado de OTRA empresa: el modelo lo soporta a propósito (un proyecto de A
            # puede tener gente de B) y es justo lo que este mapper resuelve.
            {**base, "id": str(uuid4()), "empleado_id": P2, "empleado_empresa_id": E2,
             "rol": "QA", "valor_hora": 0.0, "activo": False},
        ]

    def test_resuelve_empleado_y_su_empresa_de_CADA_fila(self, base) -> None:
        a, b = pasig_mod._build(self._filas())
        assert (a.empleado_nombre, a.empleado_empresa_nombre) == ("Ana Pérez", "Karstec")
        assert (b.empleado_nombre, b.empleado_empresa_nombre) == ("Luis Gómez", "Dosuba")

    def test_la_empresa_sale_del_EMPLEADO_no_del_proyecto(self, base) -> None:
        """Las dos asignaciones son del MISMO proyecto y dan empresas distintas: es la evidencia
        de que el nombre sale de `empleado_empresa_id` y no de una constante del proyecto."""
        filas = self._filas()
        assert filas[0]["proyecto_id"] == filas[1]["proyecto_id"]
        a, b = pasig_mod._build(filas)
        assert a.empleado_empresa_nombre != b.empleado_empresa_nombre

    def test_un_empleado_desconocido_deja_el_nombre_en_None(self, base) -> None:
        """No revienta con un id que el lookup no encuentra (empleado borrado)."""
        fila = {**self._filas()[0], "empleado_id": str(uuid4())}
        assert pasig_mod._build([fila])[0].empleado_nombre is None

    def test_los_lookups_son_batch(self, base) -> None:
        pasig_mod._build(self._filas())
        assert sorted(t for t, _, _ in base.consultas) == ["empleados", "empresas"]

    def test_la_lista_vacia_no_prueba_nada(self, base) -> None:
        assert pasig_mod._build([]) == []
        assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"

    def test_el_corto_circuito_sigue_en_la_primera_linea(self) -> None:
        assert guarda_de(pasig_mod._build) == "rows"


# ── 4. vacante_repo.find_by_ids — con datos desde esta sesión ─────────────────

class TestVacanteFindByIds:
    """Resuelve el título del grupo de cada candidato en el listado (anti-N+1).

    Con la ingesta por mail creando candidatos, este mapper pasó a correr en producción cada vez
    que alguien abre `/candidatos`.
    """

    @pytest.fixture
    def base(self, monkeypatch) -> FakeSupabase:
        fake = FakeSupabase({"vacantes": [
            {"id": V1, "codigo": "VAC-0001", "titulo": "Analista", "area_id": A1,
             "empresa_id": E1, "estado": "nueva", "created_at": "2026-01-01T00:00:00+00:00",
             "areas": {"nombre": "Sistemas"}, "empresas": {"nombre": "Karstec"}},
            {"id": V2, "codigo": "VAC-0002", "titulo": "Dev", "area_id": A2,
             "empresa_id": E2, "estado": "cerrada", "created_at": "2026-02-01T00:00:00+00:00",
             # Sin área ni empresa embebidas: los dos derivados opcionales en null.
             "areas": None, "empresas": None},
        ]})
        monkeypatch.setattr(vac_mod, "supabase_admin", fake)
        return fake

    def test_trae_las_vacantes_pedidas_con_sus_derivados(self, base) -> None:
        """Dos vacantes distintas: un mapper que copiara la primera para todas rojea acá."""
        a, b = vac_mod.VacanteRepo().find_by_ids([V1, V2])
        assert (a.codigo, a.titulo, a.area_nombre, a.empresa_nombre) == \
               ("VAC-0001", "Analista", "Sistemas", "Karstec")
        assert (b.codigo, b.titulo, b.area_nombre, b.empresa_nombre) == \
               ("VAC-0002", "Dev", None, None)

    def test_filtra_por_id_y_en_UNA_sola_query(self, base) -> None:
        """El anti-N+1 que el docstring declara: un `IN`, no una consulta por candidato."""
        vac_mod.VacanteRepo().find_by_ids([V1, V2])
        assert len(base.consultas) == 1
        tabla, columna, ids = base.consultas[0]
        assert (tabla, columna) == ("vacantes", "id") and sorted(ids) == sorted([V1, V2])

    def test_sin_ids_no_consulta(self, base) -> None:
        assert vac_mod.VacanteRepo().find_by_ids([]) == []
        assert base.consultas == [], "con lista vacía no consulta nada: no prueba nada"

    def test_el_corto_circuito_sigue_en_la_primera_linea(self) -> None:
        assert guarda_de(vac_mod.VacanteRepo.find_by_ids) == "ids"
