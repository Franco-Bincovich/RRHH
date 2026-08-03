"""
Núcleo puro — CUÁNTO QUEDA: cupos + consumos → saldo POR PERÍODO, con vencimiento FIFO.

🔴 POR QUÉ EL RESULTADO ES POR PERÍODO Y NO UN ESCALAR.
Un `(cupos, consumos) -> int` no alcanza: el vencimiento es "a fin de P+4, lo más viejo
primero", así que para saber cuánto queda hay que saber a QUÉ PERÍODO pertenece cada día. Un
total colapsa esa información y el FIFO deja de ser expresable — el saldo daría el mismo
número para alguien con 14 días por vencer el mes que viene y para alguien con 14 días
recién devengados.

Mismo contrato que `_vacaciones_cupos.py`: nada de repos ni ids, solo datos. Los dos
consumidores (el service con un empleado, R11 con N en batch) llaman a la MISMA función.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from config.reglas_vacaciones import REGLAS, ReglasVacaciones


@dataclass(frozen=True)
class Consumo:
    """Días que salen del cupo. Lo arma el ADAPTADOR de cada consumidor, no este módulo — así
    el núcleo no sabe nada de tablas.

    🔴 `dias_liquidados` se traduce distinto según de dónde venga la fila, y no es una
    inconsistencia sino la diferencia entre las dos tablas:
      · `solicitudes_vacaciones` → consume `dias` SIEMPRE. La licencia se tomó; que además se
        haya pagado o no es administrativo y no devuelve días.
      · `vacaciones_pendientes`  → consume `dias_liquidados`. Ahí los días NO se tomaron, así
        que lo único que los consume es que se paguen.
    """
    dias: int
    periodo: Optional[int]  # None = la fila no lo declara (todas las previas a la mig. 083)
    tomado: bool            # True = gozado; False = planificado (pedido a futuro)


@dataclass(frozen=True)
class SaldoPeriodo:
    periodo: int
    cupo: int
    gozados: int
    pedidos: int
    disponibles: int
    vence: date
    vencido: bool


@dataclass(frozen=True)
class SaldoCalculado:
    por_periodo: tuple[SaldoPeriodo, ...]
    asignados: int     # suma de cupos NO vencidos
    gozados: int
    pedidos: int
    disponibles: int   # lo que queda utilizable hoy
    vencidos: int      # días que se perdieron por no gozarse a tiempo


def vence_el(periodo: int, reglas: ReglasVacaciones = REGLAS) -> date:
    """Último día en que se puede gozar el período: 31/12 de P + años de acumulación."""
    return date(periodo + reglas.anios_acumulacion, 12, 31)


def esta_vencido(periodo: int, hoy: date, reglas: ReglasVacaciones = REGLAS) -> bool:
    """El 31/12 de P+4 TODAVÍA CUENTA; el 1/1 siguiente ya no. Por eso es `>` y no `>=`."""
    return hoy > vence_el(periodo, reglas)


def imputar_consumo_sin_periodo(disponible: dict[int, int], hoy: date,
                                reglas: ReglasVacaciones = REGLAS) -> Optional[int]:
    """🚩 POLÍTICA ABIERTA CON RRHH, AISLADA ACÁ A PROPÓSITO — devuelve a qué período imputar
    un consumo que no declara el suyo, o None si no hay ninguno.

    QUÉ HACE HOY: lo imputa al período MÁS VIEJO no vencido que todavía tenga saldo. Si
    ninguno tiene saldo, al más viejo no vencido igual (queda en negativo, visible). Si no
    hay ninguno sin vencer, devuelve None y el consumo se descarta del cálculo por período.

    POR QUÉ ESTA Y NO OTRA — las tres opciones que se evaluaron:
      · Imputar al año de `fecha_desde`. DESCARTADA por evidencia que ya está en el repo: el
        encabezado de la migración 083 dice explícitamente que el año de `fecha_desde` NO es
        el período, y que ese desfasaje es justamente lo que la columna vino a representar
        (hay licencias tomadas en 2026 que son del período 2025). Sería inventar el dato.
      · Un cubo aparte que reste del total pero no de ningún período. DESCARTADA porque un día
        que no pertenece a ningún período tampoco vence nunca, así que arrastraría el total
        para siempre y el saldo nunca cerraría contra la suma de los períodos.
      · FIFO desde el más viejo (ELEGIDA). No introduce NINGÚN concepto nuevo: es la misma
        regla que RRHH ya confirmó para el vencimiento ("de atrás para adelante"). Y es la
        conservadora: gasta primero lo que está por vencer, así que nunca sobreestima lo que
        le queda a la persona.

    ⚠️ HOY NO ACTÚA SOBRE NINGUNA FILA: `solicitudes_vacaciones` tiene 0 filas en producción
    (verificado el 30/7/2026), o sea que no hay un solo consumo sin período. La política
    importa para el import histórico que RRHH todavía no entregó. Si la respuesta es otra,
    se cambia esta función y nada más.
    """
    vigentes = sorted(p for p in disponible if not esta_vencido(p, hoy, reglas))
    if not vigentes:
        return None
    return next((p for p in vigentes if disponible[p] > 0), vigentes[0])


def saldo(cupos: dict[int, int], consumos: list[Consumo], hoy: date,
          reglas: ReglasVacaciones = REGLAS) -> SaldoCalculado:
    """Saldo por período. `cupos` sale de `_vacaciones_cupos.cupos_por_periodo`.

    Un consumo CON período descuenta de ESE período aunque no tenga cupo (el período aparece
    con cupo 0 y disponible negativo): un descuadre se muestra, no se esconde — mismo criterio
    que el `excedido` del reporte de saldos, que tampoco oculta los negativos.
    """
    gozados: dict[int, int] = {p: 0 for p in cupos}
    pedidos: dict[int, int] = {p: 0 for p in cupos}
    todos = dict(cupos)

    def aplicar(periodo: int, c: Consumo) -> None:
        todos.setdefault(periodo, 0)
        gozados.setdefault(periodo, 0)
        pedidos.setdefault(periodo, 0)
        (gozados if c.tomado else pedidos)[periodo] += c.dias

    for c in (x for x in consumos if x.periodo is not None):
        aplicar(c.periodo, c)  # type: ignore[arg-type]
    # Los sin período van DESPUÉS, para que el FIFO vea el saldo ya afectado por los declarados.
    for c in (x for x in consumos if x.periodo is None):
        libre = {p: todos[p] - gozados[p] - pedidos[p] for p in todos}
        destino = imputar_consumo_sin_periodo(libre, hoy, reglas)
        if destino is not None:
            aplicar(destino, c)

    filas = tuple(
        SaldoPeriodo(
            periodo=p, cupo=todos[p], gozados=gozados[p], pedidos=pedidos[p],
            disponibles=todos[p] - gozados[p] - pedidos[p],
            vence=vence_el(p, reglas), vencido=esta_vencido(p, reglas=reglas, hoy=hoy),
        )
        for p in sorted(todos)
    )
    vivas = [f for f in filas if not f.vencido]
    return SaldoCalculado(
        por_periodo=filas,
        asignados=sum(f.cupo for f in vivas),
        gozados=sum(f.gozados for f in filas),
        pedidos=sum(f.pedidos for f in filas),
        disponibles=sum(f.disponibles for f in vivas),
        # Solo lo que sobró cuenta como perdido: un período vencido y agotado no perdió nada,
        # y uno excedido no "perdió" un número negativo de días.
        vencidos=sum(max(f.disponibles, 0) for f in filas if f.vencido),
    )
