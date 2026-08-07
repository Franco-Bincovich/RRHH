"use client"

import type { Destinatario } from "@/components/features/configuracion/envioAcciones"

const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

interface Props {
  /** Los que se ven con el filtro de búsqueda aplicado. */
  visibles: Destinatario[]
  sel: Set<string>
  search: string
  cargando: boolean
  onSearch: (v: string) => void
  onToggle: (id: string) => void
}

/**
 * A quién se le manda: buscador + lista con casillas. Presentacional puro, sin fetch ni estado.
 *
 * Separado del modal para poder testearlo: `Dialog` de base-ui monta por PORTAL y vitest corre
 * sin jsdom, así que renderizar el modal entero devuelve string vacío (ver `dialog.test.tsx`).
 * Acá se puede afirmar sobre el markup real.
 *
 * 🔴 SE MARCA QUIÉN NO TIENE EMAIL, y no se lo esconde ni se lo bloquea. El backend cuenta a esa
 * persona como FALLIDA con ese motivo, así que igual iba a aparecer en el resumen; verlo antes
 * de apretar es la diferencia entre elegir a conciencia y enterarse después. Ocultarlo dejaría
 * a alguien fuera de un comunicado sin que nadie se entere de que faltó.
 */
export function EnvioDestinatarios({ visibles, sel, search, cargando, onSearch, onToggle }: Props) {
  return (
    <div className="space-y-3">
      <input
        className={INPUT_CLS} type="search" value={search} placeholder="Buscar por nombre…"
        aria-label="Buscar destinatario" onChange={(e) => onSearch(e.target.value)}
      />

      <div className="rounded-md border">
        <div className="max-h-56 divide-y overflow-y-auto">
          {cargando ? (
            <div className="h-9 animate-pulse bg-muted" />
          ) : visibles.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">
              {search ? "Nadie coincide con la búsqueda." : "No hay empleados activos para enviar."}
            </p>
          ) : visibles.map((e) => (
            <label key={e.id} className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm">
              <input type="checkbox" checked={sel.has(e.id)} onChange={() => onToggle(e.id)} />
              <span className="flex-1 text-foreground">{e.nombre} {e.apellido}</span>
              {e.email_corporativo ? (
                <span className="truncate text-xs text-muted-foreground">{e.email_corporativo}</span>
              ) : (
                <span className="text-xs text-amber-600 dark:text-amber-500">sin email cargado</span>
              )}
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
