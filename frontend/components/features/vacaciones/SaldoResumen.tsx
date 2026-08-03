"use client"

import type { SaldoPeriodo, SaldoVacaciones } from "@/types/vacaciones"

interface Props {
  saldo: SaldoVacaciones
  diasSolicitados?: number
  tipo: string
}

const ITEMS = [
  { key: "asignados" as const, label: "Asignados"   },
  { key: "gozados"   as const, label: "Gozados"     },
  { key: "pedidos"   as const, label: "Pedidos"     },
  { key: "disponibles" as const, label: "Disponibles" },
]

/**
 * "2026-12-31" → "31/12/2026", partiendo el string.
 *
 * 🔴 NO se usa `new Date(iso)`: un ISO de solo fecha se parsea en UTC, y en Argentina (UTC−3)
 * `toLocaleDateString` devuelve el día ANTERIOR. Acá eso no es cosmético: la fecha es un
 * VENCIMIENTO, así que el 31/12 —el último día en que los días todavía se pueden gozar— se
 * mostraría como 30/12 y le sacaría un día a la persona justo en el borde que importa.
 */
function fecha(iso: string): string {
  const [a, m, d] = iso.slice(0, 10).split("-")
  return d ? `${d}/${m}/${a}` : iso
}

/**
 * Los períodos que todavía sirven para pedir días: ni vencidos ni agotados.
 *
 * Un período vencido no se muestra porque no se puede usar —el total de días perdidos ya lo
 * dice el aviso de `vencidos`, y repetirlo fila por fila convierte el desglose en un historial
 * de lo que se perdió en vez de un mapa de lo que queda—. Uno agotado tampoco: una fila en 0 se
 * lee como saldo hasta que se mira el número.
 */
function utilizables(saldo: SaldoVacaciones): SaldoPeriodo[] {
  return (saldo.por_periodo ?? []).filter((p) => !p.vencido && p.disponibles > 0)
}

export function SaldoResumen({ saldo, diasSolicitados, tipo }: Props) {
  const excede =
    tipo === "vacaciones" &&
    diasSolicitados != null &&
    diasSolicitados > 0 &&
    diasSolicitados > saldo.disponibles
  // Ya vienen ordenados del backend (`sorted(todos)` en _vacaciones_fifo.saldo), así que el
  // primero es el más viejo y el `[0]` de abajo es el que vence antes. No se re-ordena acá: dos
  // criterios de orden sobre lo mismo es como empiezan a divergir el reporte y la pantalla.
  const periodos = utilizables(saldo)

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs text-muted-foreground">Saldo de vacaciones</p>
      <div className="flex gap-2">
        {ITEMS.map(({ key, label }) => (
          <div
            key={key}
            className={`flex flex-1 flex-col items-center rounded-lg border px-2 py-1.5 text-center ${
              key === "disponibles" && saldo[key] < 0
                ? "border-destructive/40 bg-destructive/10"
                : "border-border bg-muted/30"
            }`}
          >
            <span className="text-[10px] text-muted-foreground">{label}</span>
            <span className={`text-base font-semibold tabular-nums ${key === "disponibles" && saldo[key] < 0 ? "text-destructive" : ""}`}>
              {saldo[key]}
            </span>
          </div>
        ))}
      </div>
      {periodos.length > 0 && (
        <div className="mt-1 flex flex-col gap-1">
          <p className="text-[10px] font-medium text-muted-foreground">Por período</p>
          <ul className="flex flex-col gap-0.5" role="list">
            {periodos.map((p) => (
              <li key={p.periodo} className="flex items-baseline justify-between gap-2 text-xs">
                <span className="text-muted-foreground">
                  {p.periodo} · vence {fecha(p.vence)}
                </span>
                <span className="shrink-0 font-medium tabular-nums">{p.disponibles}</span>
              </li>
            ))}
          </ul>
          {/* El desglose solo dice cuántos días hay en cada año; sin esta línea el usuario ve
              dos números y no sabe cuál se le cae primero, que es la única decisión que el
              desglose existe para informar. Los días se gastan del más viejo al más nuevo. */}
          <p className="text-[10px] text-muted-foreground">
            Se usa primero el período {periodos[0].periodo}, que vence el {fecha(periodos[0].vence)}.
          </p>
        </div>
      )}
      {saldo.vencidos > 0 && (
        // No es un error ni una alerta accionable: ya pasó y no hay nada que hacer. Va en el
        // tono de aviso y aclara que NO están en "Disponibles", porque el reflejo al ver dos
        // números es sumarlos.
        <p className="text-xs text-muted-foreground">
          Se vencieron {saldo.vencidos} días sin gozar. No se cuentan en el saldo disponible.
        </p>
      )}
      {excede && (
        <p className="text-xs text-amber-600 dark:text-amber-400" role="alert">
          Los días solicitados ({diasSolicitados}) superan el saldo disponible ({saldo.disponibles}).
          RRHH puede igualmente registrar la solicitud.
        </p>
      )}
    </div>
  )
}
