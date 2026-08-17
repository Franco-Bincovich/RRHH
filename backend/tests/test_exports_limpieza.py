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

from schemas.inventario import AsignacionResponse
from schemas.objetivo import ObjetivoResponse
from schemas.offboarding import AccesoResponse, ActivoResponse, OffboardingResponse
from schemas.area import AreaResponse
from schemas.capacitacion import CapacitacionResponse
from schemas.empresa import EmpresaResponse
# El alias YA NO ES OBLIGATORIO desde el 2026-08-11: la colisión era con
# `schemas.evaluaciones.InstanciaResponse`, y ese archivo se borró con el módulo `ev_*` (J5a).
# Se conserva igual, por explícito: `InstanciaResponse` es un nombre que tres módulos podrían
# querer, y el alias dice de cuál es sin ir a leer los imports.
from schemas.onboarding import InstanciaResponse as OnboardingInstanciaResponse
from schemas.onboarding import TemplateResponse
from schemas.periodo import PeriodoResponse
from schemas.proyectos import CosteoResumen, ProyectoResponse
from schemas.vacaciones_pendientes import VacacionPendienteResponse
from schemas.candidato import CandidatoGrupoResponse
from schemas.vacante import VacanteResponse
from services._inventario_export import construir_filas_export as filas_inventario
from services._objetivos_export import construir_filas_export as filas_objetivos
from services._areas_export import construir_filas_export as filas_areas
from services._candidatos_export import construir_filas_export as filas_candidatos
from services._capacitaciones_catalogo_export import construir_filas_export as filas_catalogo
from services._onboarding_export import construir_filas_export as filas_onboarding
from services._periodos_export import construir_filas_export as filas_periodos
from services._proyectos_export import construir_filas_export as filas_proyectos
from services._empresas_export import construir_filas_export as filas_empresas
from services._onboarding_templates_export import construir_filas_export as filas_templates
from services._usuarios_export import construir_filas_export as filas_usuarios
from services._vacaciones_pendientes_export import construir_filas_export as filas_pendientes
from services._offboarding_export import construir_filas_export as filas_offboarding_activo
from services._vacantes_export import construir_filas_export as filas_vacantes

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


# ── Evaluaciones instancias: BORRADO el 2026-08-11 (bloque J5a) ───────────────
# `test_evaluaciones_export_sin_uuids_con_nombres` cubría `services/_evaluaciones_export.py`,
# que se fue con el módulo `ev_*`. No es una baja de cobertura del motor de export: los otros
# 10 bloques de este archivo verifican la misma invariante —que ninguna fila exportada filtre
# UUIDs crudos— sobre exports que sí tienen pantalla.


# ── Objetivos ─────────────────────────────────────────────────────────────────

def test_objetivos_export_sin_uuids_con_nombres():
    row = ObjetivoResponse(
        id="o-1", empresa_id="e-1", empresa_nombre="Karstec", responsable_id="u-1",
        responsable_nombre="Sofía RRHH", titulo="Migrar nómina", descripcion="Q2",
        prioridad="alta", estado="haciendo", fecha_entrega=date(2026, 6, 30),
        created_at=datetime(2026, 1, 5, 9, 0, 0), updated_at=datetime(2026, 2, 1, 12, 0, 0),
        tipo="anual", periodicidad="", areas_involucradas=["Sistemas", "Legales"],
    )
    fila = filas_objetivos([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Empresa"] == "Karstec" and fila["Responsable"] == "Sofía RRHH"
    assert fila["Título"] == "Migrar nómina" and fila["Prioridad"] == "alta"
    assert fila["Fecha entrega"] == "30/06/2026"
    assert fila["Creada"] == "05/01/2026" and fila["Actualizada"] == "01/02/2026"  # sin hora
    # Las tres columnas de la migración 119 tampoco pueden filtrar uuids ni estructuras de
    # Python: el array de áreas sale como texto, no como su `repr`.
    assert fila["Tipo"] == "anual" and fila["Áreas involucradas"] == "Sistemas; Legales"


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


# ── Usuarios del sistema ──────────────────────────────────────────────────────
#
# 🔴 El único export del repo que lista PERSONAS CON ACCESO, así que acá "columna de más" no es
# ruido: es una pista para elegir a quién atacar. La fila de entrada llega DELIBERADAMENTE con
# campos que el repo hoy no proyecta (`password_hash`, `must_change_password`, `ultimo_acceso`)
# — sin ellos, borrar la proyección entera dejaría este test en verde por falta de qué filtrar.
# La cobertura completa del módulo está en tests/test_usuarios_export.py.


def test_usuarios_export_sin_ids_ni_credenciales():
    row = {
        "id": str(uuid4()), "nombre": "Ana", "apellido": "Gómez", "email": "ana@karstec.com",
        "username": "agomez", "rol": "admin_rrhh", "activo": True,
        "password_hash": "$2b$12$secreto", "must_change_password": True,
        "ultimo_acceso": "2026-08-01T10:00:00+00:00",
    }
    fila = filas_usuarios([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Nombre"] == "Ana" and fila["Email"] == "ana@karstec.com"
    assert fila["Rol"] == "Administrador RRHH"   # traducido, no el enum crudo
    assert fila["Activo"] == "Sí"
    # Ni la key ni el valor: un hash renombrado seguiría siendo un hash.
    assert "$2b$12$secreto" not in str(fila) and "ultimo_acceso" not in str(fila)
    assert row["id"] not in str(fila)


# ── Empresas ──────────────────────────────────────────────────────────────────
#
# El único export que hoy se puede verificar mirando el archivo: producción tiene 2 empresas.
# La cobertura completa está en tests/test_empresas_export.py.


def _empresa_row(**kw) -> EmpresaResponse:
    base = dict(
        id=str(uuid4()), nombre="Karstec SA", razon_social="Karstec Sociedad Anónima",
        cuit="30-71234567-9", direccion="Av. Siempreviva 742", telefono="1144556677",
        email="admin@karstec.com", logo_url="https://cdn/avatars/logos/karstec.png",
        activa=True, created_at=datetime(2026, 1, 15, 8, 45, 0), updated_at=None,
    )
    return EmpresaResponse(**{**base, **kw})


def test_empresas_export_sin_uuid_ni_url_de_logo():
    row = _empresa_row()
    fila = filas_empresas([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert row.id not in str(fila) and "cdn/avatars" not in str(fila)
    assert fila["Empresa"] == "Karstec SA" and fila["CUIT"] == "30-71234567-9"
    assert fila["Estado"] == "Activa" and fila["Alta"] == "15/01/2026"  # sin hora


def test_empresas_export_marca_la_inactiva_y_no_usa_booleanos():
    """🔴 La columna por la que se abre este archivo. Con todas activas, el ternario se podría
    reemplazar por el literal "Activa" y nada rojearía."""
    filas = filas_empresas([_empresa_row(), _empresa_row(nombre="DOSUBA", activa=False)])
    assert [f["Estado"] for f in filas] == ["Activa", "Inactiva"]
    assert "True" not in str(filas) and "False" not in str(filas)


def test_empresas_export_sin_cuit_ni_razon_social_no_rompe():
    """Son opcionales en el schema y hay empresas de producción con estos campos vacíos."""
    fila = filas_empresas([_empresa_row(cuit=None, razon_social=None, telefono=None)])[0]
    assert fila["CUIT"] is None and fila["Razón social"] is None
    assert fila["Empresa"] == "Karstec SA"


# ── Plantillas de onboarding ──────────────────────────────────────────────────
#
# La cobertura de la VISIBILIDAD —lo que de verdad puede filtrar datos acá— está en
# tests/test_templates_export.py. Esto cubre solo la limpieza de columnas.


def _template_row(**kw) -> TemplateResponse:
    base = dict(
        id=uuid4(), nombre="Ingreso general", empresa_id=uuid4(), empresa_nombre="Karstec",
        descripcion="Alta de un ingresante", created_by=uuid4(),
        created_by_nombre="Sofía RRHH", es_publica=True, tareas=[], tareas_total=8,
    )
    return TemplateResponse(**{**base, **kw})


def test_templates_export_sin_uuids_con_nombres():
    row = _template_row()
    fila = filas_templates([row])[0]
    assert _UUID_KEYS_LOTE_B.isdisjoint(fila.keys())
    assert str(row.id) not in str(fila) and str(row.created_by) not in str(fila)
    assert fila["Plantilla"] == "Ingreso general" and fila["Autor"] == "Sofía RRHH"
    assert fila["Empresa"] == "Karstec" and fila["Tareas"] == 8


def test_templates_export_distingue_publica_de_privada_sin_booleanos():
    filas = filas_templates([_template_row(), _template_row(nombre="Borrador", es_publica=False)])
    assert [f["Visibilidad"] for f in filas] == ["Pública", "Privada"]
    assert "True" not in str(filas) and "False" not in str(filas)


def test_templates_export_no_vuelca_la_lista_de_tareas():
    """🔴 `tareas` es una lista de objetos anidados: el motor renderiza escalares, así que
    volcarla dejaría el `repr` de Python dentro de una celda. Va el conteo."""
    fila = filas_templates([_template_row(tareas_total=3)])[0]
    assert fila["Tareas"] == 3
    assert "tareas" not in fila and "TareaResponse" not in str(fila)


def test_templates_export_sin_autor_no_rompe():
    """`created_by` es NULL en las plantillas anteriores al cableado del autor."""
    fila = filas_templates([_template_row(created_by=None, created_by_nombre=None)])[0]
    assert fila["Autor"] is None and fila["Plantilla"] == "Ingreso general"


# ── Días de vacaciones pendientes ─────────────────────────────────────────────
#
# La cobertura del OWNERSHIP —lo que de verdad puede filtrar datos acá— está en
# tests/test_vacaciones_pendientes_export.py. Esto cubre solo la limpieza de columnas.


def _pendiente_row(**kw) -> VacacionPendienteResponse:
    base = dict(
        id=str(uuid4()), empresa_id=str(uuid4()), empresa_nombre="Karstec",
        empleado_id=str(uuid4()), empleado_nombre="Ana Gómez", area_id=str(uuid4()),
        area_nombre="Sistemas", periodo=2024, dias=10, dias_liquidados=4,
        comentario="Saldo 2024", created_at=datetime(2026, 2, 10, 9, 0, 0),
    )
    return VacacionPendienteResponse(**{**base, **kw})


def test_pendientes_export_sin_uuids_con_nombres():
    row = _pendiente_row()
    fila = filas_pendientes([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert row.id not in str(fila) and row.empleado_id not in str(fila)
    assert fila["Empleado"] == "Ana Gómez" and fila["Área"] == "Sistemas"
    assert fila["Período"] == 2024 and fila["Cargado"] == "10/02/2026"  # sin hora


def test_pendientes_export_calcula_lo_que_falta_liquidar():
    """🔴 La columna por la que se abre este archivo: lo que la empresa todavía debe. Los
    números están elegidos para que la resta no coincida con ninguna de las dos de origen."""
    fila = filas_pendientes([_pendiente_row(dias=10, dias_liquidados=4)])[0]
    assert fila["Días"] == 10 and fila["Liquidados"] == 4 and fila["Sin liquidar"] == 6


def test_pendientes_export_distingue_todo_liquidado_de_nada_pendiente():
    """"10 y 10 liquidados" y "0 pendientes" dan los dos 0 sin liquidar y significan cosas
    distintas: por eso las tres columnas van juntas y ninguna reemplaza a las otras."""
    filas = filas_pendientes([
        _pendiente_row(dias=10, dias_liquidados=10), _pendiente_row(dias=0, dias_liquidados=0)])
    assert [f["Sin liquidar"] for f in filas] == [0, 0]
    assert [f["Días"] for f in filas] == [10, 0]


def test_pendientes_export_sin_comentario_ni_area_no_rompe():
    fila = filas_pendientes([_pendiente_row(comentario=None, area_nombre=None)])[0]
    assert fila["Comentario"] is None and fila["Área"] is None


# ── Vacantes ──────────────────────────────────────────────────────────────────
#
# La cobertura del filtro de estado está en tests/test_vacantes_export.py. Acá, la limpieza:
# 🔴 la fila de entrada trae los bloques de TEXTO LARGO cargados a propósito — sin ellos,
# "no vuelca los párrafos" pasaría con la proyección borrada, por falta de qué dejar afuera.

_VACANTE_TEXTO_LARGO = "Se busca perfil con experiencia. " * 12


def _vacante_row(**kw) -> VacanteResponse:
    base = dict(
        id=str(uuid4()), codigo="VAC-0001", empresa_id=str(uuid4()), empresa_nombre="Karstec",
        titulo="Dev Backend", area_id=str(uuid4()), area_nombre="Sistemas", estado="con_candidatos",
        tipo_contrato="Tiempo indeterminado", modalidad="Híbrido", jornada="Full time",
        ubicacion="CABA", email_contacto="rrhh@karstec.com",
        fecha_apertura=date(2026, 3, 1), created_at=datetime(2026, 2, 20, 9, 0, 0),
        descripcion=_VACANTE_TEXTO_LARGO, requisitos=_VACANTE_TEXTO_LARGO,
        funciones=_VACANTE_TEXTO_LARGO, copy_publicacion=_VACANTE_TEXTO_LARGO,
        hashtags="#dev #python", linkedin_post_id="urn:li:share:7100000000",
    )
    return VacanteResponse(**{**base, **kw})


def test_vacantes_export_sin_uuids_ni_textos_largos():
    row = _vacante_row()
    fila = filas_vacantes([row])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert row.id not in str(fila) and row.area_id not in str(fila)
    assert _VACANTE_TEXTO_LARGO not in str(fila)          # los párrafos no entran en una celda
    assert "urn:li:share" not in str(fila)                # id interno de otra plataforma
    assert fila["Título"] == "Dev Backend" and fila["Ubicación"] == "CABA"


def test_vacantes_export_traduce_el_estado_como_la_pantalla():
    """`con_candidatos` es un valor de base, no algo que se le muestre a nadie. Mismos labels
    que ESTADO_LABELS de VacantesTable.tsx."""
    fila = filas_vacantes([_vacante_row()])[0]
    assert fila["Estado"] == "Con candidatos"
    assert "con_candidatos" not in str(fila)


def test_vacantes_export_con_opcionales_vacios_no_rompe():
    """Una vacante recién creada no tiene modalidad, jornada ni fecha de apertura."""
    fila = filas_vacantes([_vacante_row(
        modalidad=None, jornada=None, ubicacion=None, tipo_contrato=None,
        email_contacto=None, fecha_apertura=None)])[0]
    assert fila["Fecha de apertura"] == "" and "None" not in str(fila["Fecha de apertura"])
    assert fila["Modalidad"] is None and fila["Creada"] == "20/02/2026"


# ── Offboarding (procesos activos) ────────────────────────────────────────────
#
# 🔴 La fila de entrada trae listas de activos/accesos POBLADAS y notas de entrevista cargadas
# a propósito: sin ellas, "van contados y no volcados" y "las notas no salen" pasarían con la
# proyección borrada, por falta de qué dejar afuera. Cobertura completa en
# tests/test_offboarding_export.py.

_OFF_NOTAS = "Dijo que se va por el clima del equipo."


def _offboarding_row(**kw) -> OffboardingResponse:
    base = dict(
        id=uuid4(), empleado_id=uuid4(), empresa_id=uuid4(), empresa_nombre="Karstec",
        empleado_nombre="Ana Gómez", motivo="despido", estado="en_curso",
        fecha_inicio="2026-03-01", progreso=60, entrevista_salida=True,
        notas_entrevista=_OFF_NOTAS,
        activos=[ActivoResponse(id=uuid4(), tipo_activo="Notebook", descripcion=None,
                                estado="pendiente", devuelto=i < 3) for i in range(5)],
        accesos=[AccesoResponse(id=uuid4(), tipo="VPN", descripcion=None, revocado=i < 1)
                 for i in range(2)],
    )
    return OffboardingResponse(**{**base, **kw})


def test_offboarding_export_cuenta_las_listas_en_vez_de_volcarlas():
    fila = filas_offboarding_activo([_offboarding_row()])[0]
    assert _UUID_KEYS.isdisjoint(fila.keys())
    assert fila["Activos devueltos"] == 3 and fila["Activos totales"] == 5
    assert fila["Accesos revocados"] == 1 and fila["Accesos totales"] == 2
    assert "ActivoResponse" not in str(fila) and "AccesoResponse" not in str(fila)


def test_offboarding_export_NO_emite_las_notas_de_la_entrevista():
    """Texto libre sobre por qué se fue una persona: no viaja en un Excel. El flag sí."""
    fila = filas_offboarding_activo([_offboarding_row()])[0]
    assert _OFF_NOTAS not in str(fila) and "notas_entrevista" not in fila
    assert fila["Entrevista de salida"] == "Sí"


def test_offboarding_export_traduce_el_motivo_y_formatea_la_fecha_string():
    """`fecha_inicio` llega como str ISO, no como date: un `_fecha` con `.strftime()` reventaría."""
    fila = filas_offboarding_activo([_offboarding_row()])[0]
    assert fila["Motivo"] == "Desvinculación" and "despido" not in str(fila)
    assert fila["Inicio"] == "01/03/2026" and fila["Progreso"] == "60%"
