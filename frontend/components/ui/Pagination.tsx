import { ChevronLeft, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ELIPSIS, paginasVisibles, rangoVisible } from "@/components/ui/paginasVisibles"
import { Select } from "@/components/ui/select"

const NUM = new Intl.NumberFormat("es-AR")

/** Opciones del selector de filas por página. Sólo se usan si el consumidor pasa `onPageSizeChange`. */
const OPCIONES_TAMANO = [10, 20, 50, 100]

interface PaginationProps {
  page: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
  /**
   * Filas por página. Sigue siendo OPCIONAL —hay listados que no paginan de verdad— pero desde
   * el 25/8/2026 lo pasan los 14 que sí, y hasta entonces lo tenían **4 de 12**: faltaba justo en
   * /auditoria, que con 25 páginas es donde más se necesita.
   *
   * 🔴 EL RESETEO A `page = 1` LO HACE ESTE COMPONENTE, no el consumidor. Antes acá decía "quien
   * lo pase se hace cargo de volver a page = 1", y con 4 consumidores eso era una regla que cada
   * uno cumplía copiando `{ setPageSize(n); setPage(1) }`; con 14 es una regla que alguno va a
   * olvidar, y el síntoma es feo y silencioso: pasar de 100 a 20 filas estando en la página 9
   * deja pidiendo una página que ya no existe, o sea una tabla vacía sobre un filtro con datos.
   * Es la misma invariante que el bloque B fijó para los filtros ("`page` se resetea a 1 al
   * cambiar cualquier filtro"), resuelta en el mismo lugar donde vive el control.
   */
  onPageSizeChange?: (pageSize: number) => void
}

/**
 * Paginación numérica con elipsis: `‹ 1 … 5 [6] 7 … 87 ›`, más el pie "Mostrando 1–12 de 1.042"
 * y, si el consumidor lo habilita, el selector de filas por página.
 *
 * La aritmética —qué números entran, dónde va la elipsis, qué rango se está viendo— vive en
 * `paginasVisibles.ts`, que es puro y se testea sin renderizar. Acá queda sólo el render.
 *
 * ⚠️ `total` es EL TOTAL DE FILAS DEL FILTRO, no el largo de la página. Es la misma regla que el
 * resto del molde de paginación: un agregado sobre un listado paginado sale del backend. Pasarle
 * `items.length` haría que la barra diga siempre "1 de 1" sin ningún error visible.
 */
export function Pagination({ page, total, pageSize, onPageChange, onPageSizeChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const actual = Math.min(Math.max(page, 1), totalPages)
  const isFirst = actual <= 1
  const isLast = actual >= totalPages
  const [desde, hasta] = rangoVisible(actual, pageSize, total)

  return (
    <nav className="mt-4 flex flex-wrap items-center justify-between gap-3" aria-label="Paginación">
      <div className="flex items-center gap-3">
        {/* `tabular-nums`: el sistema de diseño pide cifras tabulares en TODOS los números, y el
            pie es el que más se nota — sin ellas el "1.033–1.042" cambia de ancho al pasar de
            página y el bloque entero se corre. */}
        <p className="text-sm text-muted-foreground tabular-nums" aria-live="polite">
          {total === 0
            ? "Sin resultados"
            : `Mostrando ${NUM.format(desde)}–${NUM.format(hasta)} de ${NUM.format(total)}`}
        </p>
        {onPageSizeChange && (
          <label className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <span className="sr-only sm:not-sr-only">Filas por página</span>
            <Select
              size="sm" className="w-auto"
              value={pageSize}
              aria-label="Filas por página"
              onChange={(e) => {
                onPageSizeChange(Number(e.target.value))
                // Ver el porqué en el docstring de la prop: la página 9 de 20 filas no existe
                // cuando el tamaño pasa a 100.
                onPageChange(1)
              }}
            >
              {OPCIONES_TAMANO.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </Select>
          </label>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          className="min-h-11 min-w-11"
          disabled={isFirst}
          onClick={() => onPageChange(actual - 1)}
          aria-label="Página anterior"
        >
          <ChevronLeft className="size-4" />
          <span className="sr-only sm:not-sr-only">Anterior</span>
        </Button>

        {paginasVisibles(actual, totalPages).map((item, i) =>
          item === ELIPSIS ? (
            // La elipsis NO es un botón: no hay nada que clickear y anunciarla al lector de
            // pantalla en cada barra es ruido. `key` por índice porque puede haber dos.
            <span key={`e${i}`} aria-hidden="true" className="px-1 text-sm text-muted-foreground">
              {ELIPSIS}
            </span>
          ) : (
            <Button
              key={item}
              variant={item === actual ? "default" : "outline"}
              className="min-h-11 min-w-11 tabular-nums"
              // La página actual queda clickeable pero marcada: deshabilitarla la saca del orden
              // de tabulación y el foco salta a otro lado al navegar con teclado.
              aria-current={item === actual ? "page" : undefined}
              aria-label={`Página ${item}`}
              onClick={() => onPageChange(item)}
            >
              {item}
            </Button>
          ),
        )}

        <Button
          variant="outline"
          className="min-h-11 min-w-11"
          disabled={isLast}
          onClick={() => onPageChange(actual + 1)}
          aria-label="Página siguiente"
        >
          <span className="sr-only sm:not-sr-only">Siguiente</span>
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </nav>
  )
}
