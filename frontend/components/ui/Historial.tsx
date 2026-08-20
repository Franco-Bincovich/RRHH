import { ArrowRight } from "lucide-react"

/**
 * Un HISTORIAL del patrón "Ficha de detalle" (`docs/SISTEMA-DE-DISENO.md` §3):
 * **lista, no tabla** — fecha a la izquierda, "de → a" con la flecha en acento, y chip "Vigente"
 * en el registro actual.
 *
 * 🔴 POR QUÉ NO ES UNA TABLA, que es la forma en la que estos datos suelen terminar. Una tabla
 * pide columnas fijas y las llena con lo que haya: para un cambio, el 90% de las celdas repiten
 * el mismo texto y la única información —qué cambió y desde qué valor— queda partida en dos
 * columnas que hay que leer juntas. La lista pone el cambio en una sola línea legible
 * ("de $100.000 → $120.000") y deja la fecha como ancla a la izquierda, que es por donde se
 * recorre un historial.
 *
 * 🔴 EL CHIP "VIGENTE" VA EN UNO SOLO, y por eso lo decide ESTE componente (el primero de la
 * lista) y no el llamador: es el error obvio —marcar todos los registros, o ninguno— y dejarlo
 * en manos de cada pantalla lo garantiza en la tercera. La lista se recibe ORDENADA de más
 * reciente a más antigua, que es como la devuelven los repos del backend.
 */
export interface EntradaHistorial {
  /** Clave estable de React. */
  clave: string
  /** El ancla temporal, ya legible: "Marzo 2026", "12/03/2026". */
  fecha: string
  /** Valor anterior. `null` en el registro más viejo: ahí no hay "de". */
  desde?: string | null
  /** Valor nuevo. */
  hasta: string
  /** Texto opcional a la derecha del valor ("neto $…", "por Ana Pérez"). */
  detalle?: string
}

export function Historial({ entradas, vacio }: { entradas: EntradaHistorial[]; vacio: string }) {
  if (entradas.length === 0) return <p className="text-sm text-muted-foreground">{vacio}</p>

  return (
    <ul role="list" className="flex flex-col gap-2">
      {entradas.map((e, i) => (
        <li key={e.clave} className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
          <span className="w-28 shrink-0 text-xs tabular-nums text-muted-foreground">{e.fecha}</span>
          {e.desde != null && (
            <>
              <span className="tabular-nums text-muted-foreground line-through">{e.desde}</span>
              {/* La flecha en acento: es lo único que se ve en color de la línea, y marca la
                  dirección del cambio sin agregar una palabra. */}
              <ArrowRight className="size-3.5 shrink-0 text-accent-foreground" aria-label="cambia a" />
            </>
          )}
          <span className="font-medium tabular-nums text-foreground">{e.hasta}</span>
          {e.detalle && <span className="text-xs tabular-nums text-muted-foreground">{e.detalle}</span>}
          {i === 0 && (
            <span className="rounded-md border border-primary bg-accent px-1.5 py-0.5 text-[10px] font-semibold text-accent-foreground">
              Vigente
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}
