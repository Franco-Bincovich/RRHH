"""
La masa salarial del mes del dashboard: el valor del período, el del mes anterior y la variación.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 ESTE MÓDULO ES LA ÚNICA MASA SALARIAL DEL DASHBOARD — antes había DOS
═══════════════════════════════════════════════════════════════════════════════════════════
Hasta el 21/8/2026 la misma pantalla mostraba dos cards con dos fórmulas distintas sobre la
misma tabla:
  · "Costo total nómina" = Σ `costos_nomina.salario_bruto`  (`dashboard_service._calcular_kpis`)
  · "Masa salarial"      = Σ `costos_nomina.total`          (esto, vía `generate_costos`)
Con `costos_nomina` en 0 filas las dos decían $0 y la contradicción era invisible. El día que
RRHH cargue el primer período, la pantalla iba a mostrar dos números distintos uno al lado del
otro. `docs/SISTEMA-DE-DISENO.md` §6 pide UNA "Masa salarial del mes".

SOBREVIVE `total`, Y EL MOTIVO NO ES DE CÓDIGO SINO DE QUÉ MIDE CADA COLUMNA:
  · `salario_bruto` es lo que GANA la persona.
  · `total` es una columna GENERADA en la base (`bruto + cargas + bonos + otros`) = lo que la
    persona le CUESTA a la empresa. Hoy `bonos` y `otros_costos` son siempre 0 —ningún camino de
    escritura los toca, ni la carga manual ni el import— así que `total` es hoy `bruto + cargas`.
"Masa salarial" en RRHH es el costo laboral total, no la suma de los sueldos, y es lo que ya
mide el reporte R5 (`reportes/_reporte_costos.generate_costos`, cuyo encabezado dice literalmente
"masa salarial (nómina total)"). Dejar el otro habría dejado el KPI contando distinto que el
reporte que RRHH exporta al lado.

⚠️ QUEDA UNA TERCERA SUPERFICIE CON EL OTRO SENTIDO, Y NO SE TOCÓ ACÁ:
`costo_service.get_dashboard_costos` (pantalla /costos, `DashboardCostosResponse.total_nomina`)
suma `monto_bruto`, o sea `salario_bruto`. Ahí la pregunta es otra —el total de la PLANILLA que
se está mirando, que lista bruto y neto por persona— así que no es el mismo bug. Pero es una
divergencia DECLARADA, no resuelta: si alguien compara el dashboard con /costos para el mismo
mes, los números no van a coincidir. Está anotado en `docs/DEUDA-TECNICA.md`.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 `variacion` ES `Optional` Y `None` NO ES `0.0`
═══════════════════════════════════════════════════════════════════════════════════════════
Antes el cálculo era `... if anterior else 0.0` y el front lo renderiza con signo
(`formatVariacion`), así que con el mes anterior sin cargar la pantalla AFIRMABA
**"+0% vs mes anterior"** — una afirmación sobre un dato que no existe, y la más creíble de
todas: "no cambió" es exactamente lo que uno espera leer. Con `costos_nomina` en 0 filas eso es
lo que la pantalla dice HOY sobre las dos empresas.

`None` = **no hay base de comparación**. Un número = la variación real, incluido el `0.0`
legítimo de dos meses iguales. El backend tiene que poder decir las dos cosas; cómo se muestra
la diferencia es del front.

⚠️ Lo que este módulo NO puede distinguir, y es correcto que no lo haga: un mes anterior CARGADO
que suma 0 de un mes anterior SIN CARGAR. Las dos son la misma suma, y de las dos la variación
porcentual es indefinida (dividir por cero). `None` es la respuesta de las dos.

Precedente en el repo: `DashboardCostosResponse.variacion_porcentual` ya era `Optional[float]`
por este mismo motivo (`costo_service.py:60`). Esto lo alinea; no lo inventa.
"""
from typing import Optional, Tuple
from uuid import UUID

from services.reportes._reporte_costos import generate_costos


def _mes_anterior(anio: int, mes: int) -> Tuple[int, int]:
    return (anio - 1, 12) if mes == 1 else (anio, mes - 1)


def masa_salarial(anio: int, mes: int,
                  empresa_id: Optional[UUID]) -> Tuple[float, float, Optional[float]]:
    """Masa salarial del mes, la del anterior y la variación % (o `None` si no hay base).

    Reusa `generate_costos` (R5) en vez de sumar la columna acá: un segundo sumador sobre
    `costos_nomina` es exactamente el problema que este módulo vino a cerrar.
    """
    pa, pm = _mes_anterior(anio, mes)
    actual = float(generate_costos(mes, anio, empresa_id)["total_nomina"])
    anterior = float(generate_costos(pm, pa, empresa_id)["total_nomina"])
    variacion = round((actual - anterior) / anterior * 100, 2) if anterior else None
    return round(actual, 2), round(anterior, 2), variacion
