"""
Registro de los routers en la app. Salió de `main.py`, que quedó en 199/200.

El corte es por RESPONSABILIDAD, no solo por líneas: `main.py` es la configuración de la app
—middlewares en un orden que es load-bearing, handlers de error, el health check exento— y esto
es un inventario de 50+ módulos que crece con cada feature. Mezclarlos hacía que el archivo que
NADIE debe tocar a la ligera fuera también el que se toca en cada tanda.

🔴 `registrar()` ES UNA FUNCIÓN, y los flags se leen ADENTRO. Si los `if settings.*_enabled`
estuvieran a nivel de módulo, se evaluarían UNA vez al importar y `importlib.reload(main)` —que
es como los tests prueban el gateo por flag— no volvería a mirarlos. El apagado de assessment y
del link público de horas depende de que esto se re-ejecute.
"""
from fastapi import FastAPI

from config.settings import settings
from routers.areas import router as areas_router
from routers.areas_escrituras import router as areas_escrituras_router
from routers.auth import router as auth_router
from routers.cesiones import router as cesiones_router
from routers.clientes import router as clientes_router
from routers.clientes_escrituras import router as clientes_escrituras_router
from routers.recategorizaciones import router as recategorizaciones_router
from routers.recategorizaciones_empleado import router as recategorizaciones_empleado_router
from routers.recategorizaciones_escrituras import router as recategorizaciones_escrituras_router
from routers.perfiles_puesto import router as perfiles_puesto_router
from routers.perfiles_puesto_catalogos import router as perfiles_puesto_catalogos_router
from routers.perfiles_puesto_escrituras import router as perfiles_puesto_escrituras_router
from routers.eventos_agenda import router as eventos_agenda_router
from routers.eventos_agenda_escrituras import router as eventos_agenda_escrituras_router
from routers.costos import router as costos_router
from routers.costos_escrituras import router as costos_escrituras_router
from routers.empleados import router as empleados_router
from routers.empleados_catalogos import router as empleados_catalogos_router
from routers.empresa import router as empresa_router
from routers.offboarding import router as offboarding_router
from routers.offboarding_escrituras import router as offboarding_escrituras_router
from routers.offboarding_tramite import router as offboarding_tramite_router
from routers.onboarding import router as onboarding_router
from routers.onboarding_templates import router as onboarding_templates_router
from routers.onboarding_templates_escrituras import router as onboarding_templates_escrituras_router
from routers.assessment import router as assessment_router
from routers.horas_publico import router as horas_publico_router
from routers.horas_publico_carga import router as horas_publico_carga_router
from routers.dashboard import router as dashboard_router
from routers.organigrama import router as organigrama_router
from routers.importacion_nomina_empleados import router as importacion_nomina_empleados_router
from routers.mail_historial import router as mail_historial_router
from routers.plantillas import router as plantillas_router
from routers.importacion_nomina import router as importacion_nomina_router
from routers.importacion_objetivos import router as importacion_objetivos_router
from routers.importacion_formacion import router as importacion_formacion_router
from routers.integraciones import router as integraciones_router
from routers.reportes import router as reportes_router
from routers.sucesion import router as sucesion_router
from routers.candidatos import router as candidatos_router
from routers.candidatos_escrituras import router as candidatos_escrituras_router
from routers.ausencias import router as ausencias_router
from routers.ausencias_tipos import router as ausencias_tipos_router
from routers.configuracion import router as configuracion_router
from routers.screening import router as screening_router
from routers.screening_criterio import router as screening_criterio_router
from routers.vacaciones import router as vacaciones_router
from routers.vacaciones_empleado import router as vacaciones_empleado_router
from routers.vacaciones_pendientes import router as vacaciones_pendientes_router
from routers.equipo import router as equipo_router
from routers.dashboard_equipo import router as dashboard_equipo_router
from routers.vacantes import router as vacantes_router
from routers.vacantes_escrituras import router as vacantes_escrituras_router
from routers.vacantes_integraciones import router as vacantes_integraciones_router
from routers.capacitaciones import router as capacitaciones_router
from routers.asignaciones_capacitacion import router as asignaciones_cap_router
from routers.asignaciones_capacitacion_escrituras import router as asignaciones_cap_escrituras_router
from routers.evaluaciones_import import router as evaluaciones_import_router
from routers.evaluaciones_resultados import router as evaluaciones_resultados_router
from routers.evaluaciones_resultados_export import router as evaluaciones_resultados_export_router
from routers.inventario_items import router as inventario_items_router
from routers.inventario_items_escrituras import router as inventario_items_escrituras_router
from routers.inventario_asignaciones import router as inventario_asignaciones_router
from routers.objetivos import router as objetivos_router
from routers.objetivos_catalogos import router as objetivos_catalogos_router
from routers.objetivos_escrituras import router as objetivos_escrituras_router
from routers.usuarios import router as usuarios_router
from routers.usuarios_escrituras import router as usuarios_escrituras_router
from routers.procesos import router as procesos_router
from routers.proyectos import router as proyectos_router
from routers.proyecto_asignaciones import router as proyecto_asignaciones_router
from routers.horas_cliente import router as horas_cliente_router
from routers.horas_cliente_escrituras import router as horas_cliente_escrituras_router
from routers.proyecto_horas import router as proyecto_horas_router
from routers.auditoria import router as auditoria_router
from routers.adjuntos import router as adjuntos_router
from routers.periodos import router as periodos_router


def registrar(app: FastAPI) -> None:
    """Monta todos los routers. Los dos gateados por flag se resuelven en cada llamada."""
    # ── Routers ───────────────────────────────────────────────────────────────────
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(areas_router, prefix="/api/areas", tags=["areas"])
    app.include_router(areas_escrituras_router, prefix="/api/areas", tags=["areas"])  # mismo prefijo: las rutas no cambian
    app.include_router(empleados_catalogos_router, prefix="/api/empleados", tags=["empleados"])  # ANTES de empleados (rutas estáticas vs /{id})
    app.include_router(empleados_router, prefix="/api/empleados", tags=["empleados"])
    app.include_router(cesiones_router, prefix="/api", tags=["cesiones"])
    app.include_router(clientes_router, prefix="/api/clientes", tags=["clientes"])
    app.include_router(clientes_escrituras_router, prefix="/api/clientes", tags=["clientes"])  # mismo prefijo: las rutas no cambian
    # 🔴 catalogos ANTES del CRUD: `/campos` es una ruta estática y el CRUD tiene `/{id}`. Al
    # revés, FastAPI resuelve por orden de declaración y `/campos` entraría como el path param.
    app.include_router(perfiles_puesto_catalogos_router, prefix="/api/perfiles-puesto", tags=["perfiles-puesto"])
    app.include_router(perfiles_puesto_router, prefix="/api/perfiles-puesto", tags=["perfiles-puesto"])
    app.include_router(perfiles_puesto_escrituras_router, prefix="/api/perfiles-puesto", tags=["perfiles-puesto"])  # mismo prefijo: las rutas no cambian
    app.include_router(recategorizaciones_router, prefix="/api/recategorizaciones", tags=["recategorizaciones"])
    app.include_router(recategorizaciones_escrituras_router, prefix="/api/recategorizaciones", tags=["recategorizaciones"])  # mismo prefijo: las rutas no cambian
    # Ruta anidada bajo el empleado (el historial de la ficha), como cesiones: va en /api.
    app.include_router(recategorizaciones_empleado_router, prefix="/api", tags=["recategorizaciones"])
    # Agenda de eventos (migración 113). `/pendientes` es una ruta estática y el CRUD tiene
    # `/{id}`: el orden LITERAL-antes-que-parámetro se resuelve DENTRO de `eventos_agenda.py`,
    # que las declara en ese orden, así que acá los dos routers van en el orden natural.
    app.include_router(eventos_agenda_router, prefix="/api/eventos", tags=["eventos"])
    app.include_router(eventos_agenda_escrituras_router, prefix="/api/eventos", tags=["eventos"])  # mismo prefijo: las rutas no cambian
    app.include_router(ausencias_tipos_router, prefix="/api/ausencias", tags=["ausencias"])  # ANTES de ausencias (rutas estáticas /tipos vs /{id})
    app.include_router(ausencias_router, prefix="/api/ausencias", tags=["ausencias"])
    app.include_router(vacaciones_empleado_router, prefix="/api/vacaciones", tags=["vacaciones"])  # ANTES de vacaciones (rutas estáticas /saldo y /empleado vs /{id})
    app.include_router(vacaciones_router, prefix="/api/vacaciones", tags=["vacaciones"])
    app.include_router(vacaciones_pendientes_router, prefix="/api/vacaciones-pendientes", tags=["vacaciones"])  # prefijo propio: /api/vacaciones/{id} se comería una ruta anidada
    app.include_router(equipo_router, prefix="/api/equipo", tags=["equipo"])
    app.include_router(dashboard_equipo_router, prefix="/api/dashboard-equipo", tags=["dashboard"])
    app.include_router(vacantes_router, prefix="/api/vacantes", tags=["vacantes"])
    app.include_router(vacantes_escrituras_router, prefix="/api/vacantes", tags=["vacantes"])  # mismo prefijo: las rutas no cambian
    app.include_router(vacantes_integraciones_router, prefix="/api/vacantes", tags=["vacantes"])  # ídem: LinkedIn y Gmail
    app.include_router(candidatos_router, prefix="/api/candidatos", tags=["candidatos"])
    app.include_router(candidatos_escrituras_router, prefix="/api/candidatos", tags=["candidatos"])  # mismo prefijo: las rutas no cambian
    app.include_router(onboarding_templates_router, prefix="/api/onboarding/templates", tags=["onboarding"])
    app.include_router(onboarding_templates_escrituras_router, prefix="/api/onboarding/templates", tags=["onboarding"])
    app.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
    app.include_router(offboarding_router, prefix="/api/offboarding", tags=["offboarding"])
    app.include_router(offboarding_escrituras_router, prefix="/api/offboarding", tags=["offboarding"])  # mismo prefijo: las rutas no cambian
    app.include_router(offboarding_tramite_router, prefix="/api/offboarding", tags=["offboarding"])  # mismo prefijo: las rutas no cambian
    app.include_router(costos_router, prefix="/api/costos", tags=["costos"])
    app.include_router(costos_escrituras_router, prefix="/api/costos", tags=["costos"])
    app.include_router(sucesion_router, prefix="/api/sucesion", tags=["sucesion"])
    # 🔴 LOS DOS MÓDULOS GATEADOS POR FLAG, y los dos porque tienen rutas PÚBLICAS. Apagado, su
    # prefijo devuelve el 404 de plataforma, idéntico al de cualquier ruta inventada. La OTRA mitad
    # del gateo lee el MISMO flag en middleware/auth.py::_is_public — sin ella el 404 sería un 401 y
    # esa diferencia delataría al módulo. Encender: ASSESSMENT_ENABLED / HORAS_PUBLICO_ENABLED.
    if settings.assessment_enabled:
        app.include_router(assessment_router, prefix="/api/assessment", tags=["assessment"])
    if settings.horas_publico_enabled:
        app.include_router(horas_publico_router, prefix="/api/horas-publico", tags=["horas-publico"])
        app.include_router(horas_publico_carga_router, prefix="/api/horas-publico", tags=["horas-publico"])  # mismo prefijo
    app.include_router(organigrama_router, prefix="/api/organigrama", tags=["organigrama"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(empresa_router, prefix="/api/empresas", tags=["empresa"])
    app.include_router(reportes_router, prefix="/api/reportes", tags=["reportes"])
    app.include_router(importacion_nomina_empleados_router, prefix="/api/importacion", tags=["importacion"])
    app.include_router(plantillas_router, prefix="/api/plantillas", tags=["plantillas"])
    app.include_router(mail_historial_router, prefix="/api/mails", tags=["plantillas"])  # historial de envíos
    app.include_router(importacion_nomina_router, prefix="/api/importacion", tags=["importacion"])
    app.include_router(importacion_objetivos_router, prefix="/api/importacion", tags=["importacion"])
    app.include_router(importacion_formacion_router, prefix="/api/importacion", tags=["importacion"])
    app.include_router(integraciones_router, prefix="/api/integraciones", tags=["integraciones"])
    app.include_router(configuracion_router, prefix="/api/configuracion", tags=["configuracion"])
    app.include_router(screening_router, prefix="/api/screening", tags=["screening"])
    app.include_router(screening_criterio_router, prefix="/api/screening/criterio", tags=["screening"])
    # 🔴 EL ORDEN ENTRE ESTOS DOS NO ES COSMÉTICO — invertirlo APAGA el listado de asignaciones.
    # Starlette resuelve por ORDEN DE REGISTRO, no por especificidad: `/api/capacitaciones/{id}`
    # matchea `/api/capacitaciones/asignaciones` con `id="asignaciones"`, y como `id` es UUID el
    # pedido muere en un 422 `PEDIDO_INVALIDO` antes de llegar al handler correcto. Estuvo así
    # hasta el 13/8/2026; no se notó porque la tabla está en 0 filas y nadie abrió la pantalla.
    # La regla es la de FastAPI: la ruta LITERAL se monta antes que la que lleva parámetro.
    app.include_router(asignaciones_cap_router, prefix="/api/capacitaciones/asignaciones", tags=["capacitaciones"])
    app.include_router(asignaciones_cap_escrituras_router, prefix="/api/capacitaciones/asignaciones", tags=["capacitaciones"])  # mismo prefijo: las rutas no cambian
    app.include_router(capacitaciones_router, prefix="/api/capacitaciones", tags=["capacitaciones"])
    app.include_router(evaluaciones_import_router, prefix="/api/evaluaciones/importar", tags=["evaluaciones"])
    app.include_router(evaluaciones_resultados_export_router, prefix="/api/evaluaciones/resultados", tags=["evaluaciones"])
    app.include_router(evaluaciones_resultados_router, prefix="/api/evaluaciones/resultados", tags=["evaluaciones"])
    app.include_router(inventario_items_router, prefix="/api/inventario/items", tags=["inventario"])
    app.include_router(inventario_items_escrituras_router, prefix="/api/inventario/items", tags=["inventario"])  # mismo prefijo: las rutas no cambian
    app.include_router(inventario_asignaciones_router, prefix="/api/inventario/asignaciones", tags=["inventario"])
    # catalogos ANTES del resto, igual que en perfiles-puesto. Acá el orden todavía no es
    # load-bearing —el módulo no tiene ningún GET /{id} que se coma /campos— pero
    # `ObjetivoService.get_by_id` ya está escrito esperando uno. El porqué, en el docstring de
    # objetivos_catalogos.py.
    app.include_router(objetivos_catalogos_router, prefix="/api/objetivos", tags=["objetivos"])
    app.include_router(objetivos_router, prefix="/api/objetivos", tags=["objetivos"])
    app.include_router(objetivos_escrituras_router, prefix="/api/objetivos", tags=["objetivos"])  # mismo prefijo: las rutas no cambian
    app.include_router(usuarios_router, prefix="/api/usuarios", tags=["usuarios"])
    app.include_router(usuarios_escrituras_router, prefix="/api/usuarios", tags=["usuarios"])  # mismo prefijo: las rutas no cambian
    app.include_router(procesos_router, prefix="/api/procesos", tags=["procesos"])
    app.include_router(proyectos_router, prefix="/api/proyectos", tags=["proyectos"])
    app.include_router(proyecto_asignaciones_router, prefix="/api/proyectos", tags=["proyectos"])
    app.include_router(proyecto_horas_router, prefix="/api/proyectos", tags=["proyectos"])
    app.include_router(horas_cliente_router, prefix="/api/horas-cliente", tags=["horas"])
    app.include_router(horas_cliente_escrituras_router, prefix="/api/horas-cliente", tags=["horas"])  # mismo prefijo: las rutas no cambian
    app.include_router(auditoria_router, prefix="/api/auditoria", tags=["auditoria"])
    app.include_router(adjuntos_router, prefix="/api/adjuntos", tags=["adjuntos"])
    app.include_router(periodos_router, prefix="/api/periodos", tags=["periodos"])
