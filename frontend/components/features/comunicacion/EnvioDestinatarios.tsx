"use client"

import type { Destinatario } from "@/components/features/comunicacion/envioAcciones"
import { ErrorCarga } from "@/components/ui/ErrorCarga"

const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

export const ERROR_DESTINATARIOS = "No se pudieron cargar los colaboradores."

interface Props {
  /** Los que se ven con el filtro de búsqueda aplicado. */
  visibles: Destinatario[]
  /**
   * Cuántos activos hay EN TOTAL. Cuando supera a los que se trajeron, la pantalla lo dice.
   *
   * Opcional porque el aviso es aditivo: una pantalla que no conoce su total simplemente no
   * afirma nada. Lo que no puede volver a pasar es afirmar de más — mostrar 100 de 400 sin una
   * palabra se lee como el padrón entero, y acá eso termina en un comunicado que no llega.
   */
  total?: number
  /** Los que se trajeron, antes del filtro de búsqueda. Es contra esto que se compara `total`. */
  traidos?: number
  sel: Set<string>
  search: string
  cargando: boolean
  /** La carga FALLÓ. Distinto de una lista vacía: ver el bloque de abajo. */
  error: boolean
  onSearch: (v: string) => void
  onToggle: (id: string) => void
  onReintentar: () => void
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
 *
 * 🔴 TRES ESTADOS, NO DOS: cargando · error · lista (que puede estar vacía DE VERDAD). "Falló la
 * consulta" y "no hay nadie activo" son hechos distintos y llevan al usuario a lugares distintos;
 * mostrarlos igual fue lo que hizo invisible el `page_size=200` durante meses.
 */
export function EnvioDestinatarios({
  visibles, total = 0, traidos = 0, sel, search, cargando, error, onSearch, onToggle, onReintentar,
}: Props) {
  // El buscador no se renderiza en el estado de error: filtrar una lista que no se pudo traer
  // sugiere que el problema es el filtro. Lo único accionable acá es reintentar.
  if (error) return <ErrorCarga mensaje={ERROR_DESTINATARIOS} onReintentar={onReintentar} />

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
              {search ? "Nadie coincide con la búsqueda." : "No hay colaboradores activos para enviar."}
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

      {/*
        🔴 El aviso compara contra los TRAÍDOS, no contra los visibles: si comparara con
        `visibles.length`, cada búsqueda que filtra dispararía el cartel y diría "faltan" cuando
        lo que hubo fue un filtro. Acá "faltan" significa una sola cosa: hay activos que esta
        pantalla NO trajo y a los que no se les puede mandar nada desde acá.
      */}
      {total > traidos && (
        <p className="text-xs text-amber-600 dark:text-amber-500">
          Esta lista trae {traidos} de {total} empleados activos. A los {total - traidos} restantes
          no se les puede enviar desde acá todavía.
        </p>
      )}
    </div>
  )
}
