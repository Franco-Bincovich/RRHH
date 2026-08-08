"""
Tests de limpieza de columnas del export en inventario, evaluaciones y objetivos.

Verifican que construir_filas_export de cada módulo NO emite keys de UUID crudo
(id, empresa_id, empleado_id, etc.) y SÍ emite los nombres resueltos + fechas
dd/mm/aaaa. Puro sobre los helpers — no toca motor, router ni ownership.
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

from datetime import date, datetime
from uuid import uuid4

from schemas.evaluaciones import InstanciaResponse
from schemas.inventario import AsignacionResponse
from schemas.objetivo import ObjetivoResponse
from schemas.area import AreaResponse
from schemas.capacitacion import CapacitacionResponse
# ⚠️ ALIAS OBLIGATORIO: `InstanciaResponse` existe en schemas.evaluaciones Y en
# schemas.onboarding. Sin el alias, el segundo import tapa al primero y el test de evaluaciones
# construye el modelo equivocado (falla con "5 validation errors", que no dice eso).
from schemas.onboarding import InstanciaResponse as OnboardingInstanciaResponse
from schemas.periodo import PeriodoResponse
from schemas.proyectos import CosteoResumen, ProyectoResponse
from schemas.vacante import CandidatoGrupoResponse
from services._evaluaciones_export import construir_filas_export as filas_evaluaciones
from services._inventario_export import construir_filas_export as filas_inventario
from services._objetivos_export import construir_filas_export as filas_objetivos
from services._areas_export import construir_filas_export as filas_areas
from services._candidatos_export import construir_filas_export as filas_candidatos
from services._capacitaciones_catalogo_export import construir_filas_export as filas_catalogo
from services._onboarding_export import construir_filas_export as filas_onboarding
from services._periodos_export import construir_filas_export as filas_periodos
from services._proyectos_export import construir_filas_export as filas_proyectos

# Ninguna fila del export debe contener estas keys (nombres de campo crudos con UUID).
_UUID_KEYS = {"id", "empresa_id", "empleado_id", "item_id", "ciclo_id", "evaluador_id", "responsable_id"}


# ── Inventario asignaciones ───────────────────────────────────────────────────

def test_inventario_export_sin_uuids_con_nombres():
    row = AsignacionResponse(
        id="a-1", empresa_id="e-1", empresa_nombre="Karstec", item_id="it-1",
        item_nombre="Notebook Dell", item_tipo="Notebook", item_numero_serie="SN-9",
        empleado_id="emp-1", empleado_nombre="Ana Lopez", fecha_asignacion=date(2026, 3, 1),
        fecha_devolucion=None, estado_devolucion=None, notas=None,
        created_at=datetime(2026, 3, 1, 10, 30, 0),
    )
    fila = filas_inventario([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Empresa"] == "Karstec" and fila["Empleado"] == "Ana Lopez"
    assert fila["Equipo"] == "Notebook Dell" and fila["N° serie"] == "SN-9"
    assert fila["Fecha asignación"] == "01/03/2026" and fila["Creada"] == "01/03/2026"
    assert fila["Fecha devolución"] == ""  # None → ''


# ── Evaluaciones instancias ───────────────────────────────────────────────────

def test_evaluaciones_export_sin_uuids_con_nombres():
    row = InstanciaResponse(
        id=uuid4(), empresa_id=uuid4(), empresa_nombre="Karstec", ciclo_id=uuid4(),
        ciclo_nombre="Q1 2026", empleado_id=uuid4(), empleado_nombre="Ana Lopez",
        empleado_area="Tecnología", evaluador_id=uuid4(), evaluador_nombre="Juan Pérez",
        estado="finalizada", puntaje_global=4.5, fecha_evaluacion=date(2026, 4, 10),
    )
    fila = filas_evaluaciones([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Empresa"] == "Karstec" and fila["Empleado"] == "Ana Lopez"
    assert fila["Ciclo"] == "Q1 2026" and fila["Evaluador"] == "Juan Pérez"
    assert fila["Área"] == "Tecnología" and fila["Estado"] == "finalizada"
    assert fila["Puntaje"] == 4.5 and fila["Fecha evaluación"] == "10/04/2026"


# ── Objetivos ─────────────────────────────────────────────────────────────────

def test_objetivos_export_sin_uuids_con_nombres():
    row = ObjetivoResponse(
        id="o-1", empresa_id="e-1", empresa_nombre="Karstec", responsable_id="u-1",
        responsable_nombre="Sofía RRHH", titulo="Migrar nómina", descripcion="Q2",
        prioridad="alta", estado="haciendo", fecha_entrega=date(2026, 6, 30),
        created_at=datetime(2026, 1, 5, 9, 0, 0), updated_at=datetime(2026, 2, 1, 12, 0, 0),
    )
    fila = filas_objetivos([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Empresa"] == "Karstec" and fila["Responsable"] == "Sofía RRHH"
    assert fila["Título"] == "Migrar nómina" and fila["Prioridad"] == "alta"
    assert fila["Fecha entrega"] == "30/06/2026"
    assert fila["Creada"] == "05/01/2026" and fila["Actualizada"] == "01/02/2026"  # sin hora


# ── Proyectos ─────────────────────────────────────────────────────────────────

def _proyecto(**kw) -> ProyectoResponse:
    base = dict(
        id=uuid4(), empresa_id=uuid4(), empresa_nombre="Karstec", nombre="Migración AWS",
        descripcion="Portar de Supabase a RDS", estado="activo",
        fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 9, 30), presupuesto=500000.0,
        costeo=CosteoResumen(costo_acumulado=125000.0, presupuesto_restante=375000.0,
                             pct_consumido=25.0),
        created_at=datetime(2026, 1, 15, 8, 45, 0),
    )
    return ProyectoResponse(**{**base, **kw})


def test_proyectos_export_sin_uuids_con_nombres():
    fila = filas_proyectos([_proyecto()])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Empresa"] == "Karstec" and fila["Proyecto"] == "Migración AWS"
    assert fila["Estado"] == "activo" and fila["Presupuesto"] == 500000.0
    assert fila["Fecha inicio"] == "01/02/2026" and fila["Fecha fin"] == "30/09/2026"
    assert fila["Creado"] == "15/01/2026"  # sin hora


def test_proyectos_export_aplana_el_costeo():
    """🔴 `costeo` es un objeto anidado (`CosteoResumen`). El motor renderiza escalares: sin
    aplanar, la celda saldría con el `repr` de Python — y son justo las dos columnas que alguien
    abre el Excel para mirar."""
    fila = filas_proyectos([_proyecto()])[0]
    assert fila["Costo acumulado"] == 125000.0
    assert fila["Presupuesto restante"] == 375000.0
    assert fila["% consumido"] == "25.0%"
    assert "costeo" not in fila and "CosteoResumen" not in str(fila)


def test_proyectos_export_sin_presupuesto_no_inventa_un_cero_por_ciento():
    """`pct_consumido` es None cuando el presupuesto es 0: no hay contra qué medir. "0%" diría
    que no se consumió nada, que es una afirmación distinta y falsa."""
    sin = _proyecto(presupuesto=0.0, costeo=CosteoResumen(
        costo_acumulado=0.0, presupuesto_restante=0.0, pct_consumido=None))
    assert filas_proyectos([sin])[0]["% consumido"] == ""


def test_proyectos_export_con_fechas_vacias_no_rompe():
    """`fecha_fin` es opcional — un proyecto abierto no tiene cierre."""
    fila = filas_proyectos([_proyecto(fecha_inicio=None, fecha_fin=None)])[0]
    assert fila["Fecha inicio"] == "" and fila["Fecha fin"] == ""


# ── Áreas ─────────────────────────────────────────────────────────────────────

def _area(**kw) -> AreaResponse:
    base = dict(
        id=str(uuid4()), empresa_id=str(uuid4()), nombre="GESTION DE DEUDA",
        descripcion="Cobranzas y mora", responsable_id=str(uuid4()),
        responsable_nombre="Ana Gómez", cantidad_empleados=4,
        created_at=datetime(2026, 1, 15, 8, 45, 0),
    )
    return AreaResponse(**{**base, **kw})


def test_areas_export_sin_uuids_con_nombres():
    fila = filas_areas([_area()])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Área"] == "GESTION DE DEUDA" and fila["Responsable"] == "Ana Gómez"
    assert fila["Descripción"] == "Cobranzas y mora" and fila["Empleados"] == 4
    assert fila["Creada"] == "15/01/2026"  # sin hora


def test_areas_export_sin_responsable_no_rompe():
    """`responsable_id` está sin cargar en varias áreas de producción."""
    fila = filas_areas([_area(responsable_id=None, responsable_nombre=None)])[0]
    assert fila["Responsable"] is None and fila["Área"] == "GESTION DE DEUDA"


def test_areas_export_NO_colapsa_nombres_repetidos():
    """🔴 El nombre de un área no es único: producción tiene "GESTION DE DEUDA" y
    "GD - GESTION DE DEUDA", y nada impide dos exactamente iguales. Agrupar por nombre
    escondería un área entera y su dotación."""
    filas = filas_areas([_area(cantidad_empleados=4), _area(cantidad_empleados=9)])
    assert len(filas) == 2
    assert [f["Empleados"] for f in filas] == [4, 9]


# ── Candidatos · Períodos · Catálogo de capacitaciones · Onboarding ───────────
#
# Los cuatro tienen 0 o 1 fila en producción, así que estos tests son la única verificación que
# van a tener por un buen rato: nadie va a abrir el archivo y notar que una columna dice
# cualquier cosa. Se afirma lo mismo que en los de arriba —sin UUIDs, sin objetos anidados
# volcados como repr, fechas vacías como "" y no "None"— por el camino real de cada proyección.

_UUID_KEYS_LOTE_B = _UUID_KEYS | {"vacante_id", "template_id", "cerrado_por", "reabierto_por"}


def test_candidatos_export_sin_uuids_con_nombres():
    row = CandidatoGrupoResponse(
        id=str(uuid4()), vacante_id=str(uuid4()), empresa_id=str(uuid4()), nombre="Ana",
        apellido="Gómez", email="ana@x.com", telefono="1155667788", cargo_anterior="Analista",
        empresa_anterior="Otra SA", etapa_pipeline="entrevista", score_ia=7.5,
        cv_storage_path="cvs/privado/ana.pdf", created_at=datetime(2026, 3, 4, 10, 0, 0),
        grupo_nombre="Dev Backend", busqueda_activa=True,
    )
    fila = filas_candidatos([row])[0]
    assert _UUID_KEYS_LOTE_B.isdisjoint(fila.keys())
    assert fila["Nombre"] == "Ana" and fila["Búsqueda"] == "Dev Backend"
    assert fila["Búsqueda activa"] == "Sí" and fila["Etapa"] == "entrevista"
    assert fila["Cargado"] == "04/03/2026"  # sin hora
    # 🔴 La ruta del bucket privado no puede viajar en un Excel.
    assert "cvs/privado" not in str(fila)


def test_candidatos_export_sin_telefono_ni_cargo_no_rompe():
    row = CandidatoGrupoResponse(
        id=str(uuid4()), nombre="Beto", apellido="Pérez", email="b@x.com",
        etapa_pipeline="nuevo", created_at=datetime(2026, 3, 4, 10, 0, 0),
    )
    fila = filas_candidatos([row])[0]
    assert fila["Teléfono"] is None and fila["Búsqueda activa"] == "No"


def test_periodos_export_sin_uuids_de_usuario():
    row = PeriodoResponse(
        id=str(uuid4()), empresa_id=str(uuid4()), modulo=None, desde=date(2026, 1, 1),
        hasta=date(2026, 1, 31), estado="cerrado", cerrado_por=str(uuid4()),
        cerrado_at=datetime(2026, 2, 1, 9, 0, 0), reabierto_por=None, reabierto_at=None,
    )
    fila = filas_periodos([row])[0]
    assert _UUID_KEYS_LOTE_B.isdisjoint(fila.keys())
    assert row.cerrado_por not in str(fila)
    assert fila["Módulo"] == "Todos"                  # NULL = todos los módulos, no un blanco
    assert fila["Desde"] == "01/01/2026" and fila["Cerrado el"] == "01/02/2026"
    assert fila["Reabierto el"] == ""                 # None → '', nunca "None"


def test_catalogo_capacitaciones_export_sin_uuids_con_booleanos_legibles():
    row = CapacitacionResponse(
        id=str(uuid4()), empresa_id=str(uuid4()), empresa_nombre="Karstec",
        nombre="Ley Micaela", descripcion="Obligatoria por ley", categoria="Normativa",
        duracion_horas=4.0, obligatoria=True, activo=False,
        created_at=datetime(2026, 1, 5, 9, 0, 0),
    )
    fila = filas_catalogo([row])[0]
    assert _UUID_KEYS_LOTE_B.isdisjoint(fila.keys())
    assert fila["Empresa"] == "Karstec" and fila["Nombre"] == "Ley Micaela"
    assert fila["Obligatoria"] == "Sí" and fila["Estado"] == "Inactiva"
    assert "True" not in str(fila) and "False" not in str(fila)
    assert fila["Creada"] == "05/01/2026"


def test_onboarding_export_sin_uuids_y_con_la_fecha_formateada():
    row = OnboardingInstanciaResponse(
        id=uuid4(), empleado_id=uuid4(), empresa_id=uuid4(), empresa_nombre="Karstec",
        empleado_nombre="Ana Gómez", empleado_cargo="Analista", empleado_area="Sistemas",
        template_id=uuid4(), estado="en_curso", fecha_inicio="2026-02-10", progreso=30,
        tareas_completadas=3, tareas_total=10,
    )
    fila = filas_onboarding([row])[0]
    assert _UUID_KEYS_LOTE_B.isdisjoint(fila.keys())
    assert fila["Empleado"] == "Ana Gómez" and fila["Área"] == "Sistemas"
    # 🔴 `fecha_inicio` llega como str: el `_fecha` de los otros exports reventaría acá.
    assert fila["Inicio"] == "10/02/2026"
    assert fila["Progreso"] == "30%" and fila["Tareas totales"] == 10


def test_onboarding_export_con_fecha_vacia_da_string_vacio_no_None():
    row = OnboardingInstanciaResponse(
        id=uuid4(), empleado_id=uuid4(), empleado_nombre="Beto", template_id=uuid4(),
        estado="en_curso", fecha_inicio="", progreso=0, tareas_completadas=0, tareas_total=0,
    )
    fila = filas_onboarding([row])[0]
    assert fila["Inicio"] == "" and "None" not in str(fila["Inicio"])
