"""
KPI "Antigüedad promedio" (`docs/SISTEMA-DE-DISENO.md` §6), del bloque "Indicadores del período".

Es el ÚNICO de los KPIs nuevos de esta tanda que arranca con dato real: `empleados.fecha_ingreso`
es NOT NULL y está cargada en los 31 empleados de producción. Los otros tres miden tablas vacías.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 DEVUELVE PROMEDIO **Y** MEDIANA, y no es indecisión: con 2 empresas de tamaños distintos el
promedio solo miente, y acá ya miente
═══════════════════════════════════════════════════════════════════════════════════════════
Medido contra el catálogo vivo el 21/8/2026, con los 31 activos:

    KARSTEC - IT NET | DATOS      12 personas   promedio 1,97 años   mediana 1,22 años
    SERVICIOS Y CONSULTORIA ...   19 personas   promedio 1,61 años   mediana 1,78 años

En la primera el promedio es **61% más alto que la mediana**, y la diferencia es UNA persona que
entró en 2018 contra once que entraron en los últimos dos años. Un tablero que muestre solo
"1,97" le dice a Capital Humano que la dotación tiene casi dos años de casa; la mediana dice que
la mitad no llega a quince meses. La segunda es la contraria (mediana > promedio: hay ingresos
muy recientes que tiran el promedio para abajo), así que ni siquiera se puede aprender la
dirección del sesgo y corregir a ojo.

Calcular las dos cuesta una `statistics.median` sobre una lista que ya está en memoria: el costo
es cero y la alternativa es elegir cuál de las dos verdades a medias mostrar. §6 pide "antigüedad
promedio" y ese es el número que va en la card; **la mediana viaja al lado para que la sesión de
front pueda mostrarla como contraste** (leyenda de la card, tooltip, lo que decida el diseño).

═══════════════════════════════════════════════════════════════════════════════════════════
POR QUÉ `fecha_ingreso` Y NO `fecha_ingreso_reconocida`
═══════════════════════════════════════════════════════════════════════════════════════════
`fecha_ingreso_reconocida` es la antigüedad reconocida a efectos de convenio, que conceptualmente
es MEJOR respuesta para este KPI. Está cargada en **10 de 31** (catálogo vivo, 21/8/2026), así
que un cálculo que la prefiriera mezclaría dos criterios distintos en el mismo promedio según
quién tenga el campo cargado — y el número cambiaría solo a medida que RRHH complete el padrón,
sin que nadie edite una fecha de ingreso. `fecha_ingreso` es NOT NULL y está al 100%: un solo
criterio para todos. Si algún día la reconocida se carga entera, el cambio es de una línea y con
su commit propio.
"""
import statistics
from datetime import date
from typing import Optional, Tuple
from uuid import UUID

from integrations.supabase_client import supabase_admin

# Años medios del calendario gregoriano. Con 365 pelado, una antigüedad de 20 años se corre
# ~5 días; no cambia el KPI pero tampoco cuesta nada tenerlo bien.
DIAS_POR_ANIO = 365.25


def antiguedad(hoy: date, empresa_id: Optional[UUID]) -> Tuple[float, float]:
    """(promedio, mediana) de antigüedad en AÑOS de los empleados activos, a 1 decimal.

    Sin activos devuelve (0.0, 0.0): es el empty state del KPI, no un error.

    Solo `estado = 'activo'`: la antigüedad de la dotación es de quien está. Un preingreso
    todavía no empezó a acumularla (y su `fecha_ingreso` es futura, así que además restaría), y
    una baja dejó de acumularla el día que se fue.
    """
    q = supabase_admin.table("empleados").select("fecha_ingreso").eq("estado", "activo")
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    dias = [(hoy - date.fromisoformat(str(f))).days
            for r in (q.execute().data or []) if (f := r.get("fecha_ingreso"))]
    if not dias:
        return 0.0, 0.0
    return (round(sum(dias) / len(dias) / DIAS_POR_ANIO, 1),
            round(statistics.median(dias) / DIAS_POR_ANIO, 1))
