"""
Catálogo de secciones del sistema — el enum `Seccion` y nada más.

SALIÓ DE `utils/permisos.py`, que llegó a 217 líneas contra el límite de 200 al sumarse la
sección de la agenda de eventos. El corte es por RESPONSABILIDAD y no solo por líneas: `permisos`
es el MODELO —qué puede cada rol, y la dependency que lo aplica—, y esto es un INVENTARIO que
crece con cada módulo nuevo. Mezclarlos hacía que el archivo del modelo de seguridad, que casi
nunca debería cambiar, fuera también el que se toca en cada feature.

⚠️ `permisos.py` LO RE-EXPORTA, así que `from utils.permisos import Seccion` sigue funcionando y
ningún caller cambió. Los ~204 gates del repo y el espejo con `frontend/services/permisos.ts`
importan de allá.

🔴 CADA SECCIÓN NUEVA LLEVA ESCRITO POR QUÉ NO REUSÓ UNA EXISTENTE. No es prosa decorativa: la
pregunta "¿por qué esto no cuelga de la vecina obvia?" se hizo cuatro veces (clientes, perfiles
de puesto, recategorizaciones, eventos) y sin la respuesta al lado se vuelve a discutir. La
invariante que las gobierna a todas está en el docstring del enum.
"""
from enum import Enum


class Seccion(str, Enum):
    """
    Conjunto cerrado de secciones del sistema. Una por módulo con router real
    registrado en main.py (auth queda fuera: no es una sección de negocio gateada).
    """

    EMPLEADOS = "empleados"
    AREAS = "areas"
    AUSENCIAS = "ausencias"
    VACACIONES = "vacaciones"
    VACANTES = "vacantes"
    CANDIDATOS = "candidatos"
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"
    COSTOS = "costos"
    SUCESION = "sucesion"
    ASSESSMENT = "assessment"
    ORGANIGRAMA = "organigrama"
    DASHBOARD = "dashboard"
    EMPRESA = "empresa"
    REPORTES = "reportes"
    IMPORTACION = "importacion"
    INTEGRACIONES = "integraciones"
    CAPACITACIONES = "capacitaciones"
    EVALUACIONES = "evaluaciones"
    INVENTARIO = "inventario"
    OBJETIVOS = "objetivos"
    USUARIOS = "usuarios"
    PROCESOS = "procesos"
    PROYECTOS = "proyectos"
    AUDITORIA = "auditoria"
    PERIODOS = "periodos"
    # Reglas de negocio configurables (escala de vacaciones, base de días hábiles, tipos de
    # ausencia). Sección PROPIA a propósito: NO se reusa VACACIONES ni AUSENCIAS porque
    # mandos_medios tiene WRITE en las dos, y cargar una vacación no es lo mismo que cambiar
    # la regla con la que se calculan todas.
    CONFIGURACION = "configuracion"
    # Catálogo de clientes (migración 102). SECCIÓN PROPIA, y la decisión merece explicación
    # porque el repo tiene un precedente que dice lo contrario:
    #
    # `/comunicacion` NO creó sección y reusa `configuracion`, con el argumento —correcto— de
    # que `puede()` es genérica: para cualquier sección fuera de MANDOS_MEDIOS_SECCIONES el
    # resultado es idéntico (admin escribe, gerencia lee, mandos nada), así que una sección
    # nueva "daría el mismo resultado a cambio de tocar el espejo manual con permisos.py".
    #
    # Lo que distingue este caso: comunicación era una RUTA DE FRONT sobre endpoints que YA
    # existían y ya estaban gateados con `configuracion`. Clientes es un módulo nuevo con
    # routers propios montados en main.py, y la invariante declarada de este enum es
    # justamente "una por módulo con router real registrado en main.py". Reusar acá dejaría el
    # gate del módulo apuntando a una sección que nombra otra cosa, y el día que alguien quiera
    # que gerencia vea clientes pero no la configuración de reglas, habría que partirlo con
    # datos ya cargados.
    #
    # NO se reusó PROYECTOS —que es la vecina obvia— porque el diseño de la carga de horas dejó
    # a `proyectos` explícitamente FUERA de ese flujo: el proyecto ahí es texto libre. Atarlos
    # por el permiso sugeriría un parentesco que el modelo no tiene.
    #
    # El costo es una línea acá y una en `frontend/services/permisos.ts`, y ese espejo NO es a
    # ciegas: `tests/test_espejo_permisos.py` compara los dos enteros y falla si falta una.
    CLIENTES = "clientes"
    # Catálogo de perfiles de puesto (migraciones 113/116). SECCIÓN PROPIA, por el mismo
    # criterio que CLIENTES: es un módulo nuevo con routers propios montados en
    # registro_routers.py, y la invariante declarada de este enum es "una por módulo con router
    # real registrado".
    #
    # NO se reusó VACANTES —que es la vecina obvia, y con la que va a haber un puente— porque
    # son dos permisos que se van a querer separar: un perfil de puesto es material de consulta
    # estable del equipo, y una vacante es un proceso de selección en curso. Atarlos hoy
    # obligaría a partirlos después con datos cargados, que es exactamente el costo que la nota
    # de CLIENTES describe.
    PERFILES_PUESTO = "perfiles_puesto"
    # Recategorizaciones (migraciones 113/116/117). SECCIÓN PROPIA, mismo criterio que las dos
    # de arriba: módulo nuevo con routers propios registrados.
    #
    # NO se reusó EMPLEADOS —que es la vecina obvia, y de cuya ficha cuelga una de las dos
    # vistas— porque ataría el permiso de RECATEGORIZAR al de editar el legajo, y son dos cosas
    # distintas: cualquiera que administra empleados corrige un teléfono, no cualquiera decide
    # que alguien cambió de categoría.
    #
    # ⚠️ Y NO reemplaza al gate de COSTOS: `impacto_salarial` se omite de la respuesta según
    # `Seccion.COSTOS + READ`, aparte de esto. Son dos ejes: esta sección dice quién ve el
    # módulo, COSTOS dice quién ve el monto adentro.
    RECATEGORIZACIONES = "recategorizaciones"
    # Agenda de eventos del dashboard (migración 113). SECCIÓN PROPIA, mismo criterio que las
    # tres de arriba: módulo nuevo con routers propios registrados.
    #
    # NO se reusó DASHBOARD —que es donde los eventos se van a MOSTRAR— porque el dashboard no
    # es un módulo con datos propios: es el panel que lee de todos los demás, y su sección está
    # abierta a todo rol que entra al sistema. Colgar de ahí el ABM de la agenda le daría
    # escritura sobre eventos a cualquiera que pueda ver el panel.
    #
    # NO se reusó CONFIGURACION —la otra vecina— porque un evento no es una regla de negocio:
    # se carga y se resuelve todas las semanas, y `configuracion` es lo que se toca una vez y
    # gobierna cálculos. El DEFAULT de días de aviso sí vive allá (`parametros_empresa`), y esa
    # división es la correcta: la regla en configuración, los hechos acá.
    EVENTOS = "eventos"
