import type { ReactNode } from "react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Button } from "@/components/ui/button"
import { TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { textoVacio } from "@/components/ui/textoVacio"

/**
 * El estado VACÍO **adentro de la tabla** (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 LA TABLA MANTIENE SU ENCABEZADO, y ese es el cambio de comportamiento de este patrón. Antes
 * /empleados reemplazaba la tabla ENTERA por un `<EmptyState>`: desaparecían los nombres de las
 * columnas, la pantalla cambiaba de forma y el usuario perdía la referencia de qué estaba
 * mirando justo en el momento en que necesita entender por qué no ve nada. Acá el vacío es una
 * fila más —una sola celda con `colSpan`—, así que el encabezado, los anchos y el marco quedan
 * exactamente donde estaban y lo único que cambia es el contenido.
 *
 * Las dos salidas son las del patrón y no se ejecutan solas: **quitar el último filtro** (el
 * chip más a la derecha, que es el que el usuario acaba de poner) o **limpiar todo**. Si no hay
 * filtros, no hay nada que quitar y lo que va es la acción de crear el primero.
 */
export function TablaVacia({ colSpan, chips, sustantivo, claveSujeto, onLimpiarTodo, accion }: {
  colSpan: number
  chips: ChipFiltro[]
  /** Qué se lista, en plural: "colaboradores". */
  sustantivo: string
  /** Qué chip es el sujeto de la frase. Ver `textoVacio`. */
  claveSujeto?: string
  onLimpiarTodo: () => void
  /** La acción de "todavía no hay nada": solo se muestra SIN filtros puestos. */
  accion?: ReactNode
}) {
  const { titulo, descripcion } = textoVacio(chips, sustantivo, claveSujeto)
  const ultimo = chips[chips.length - 1]

  return (
    <TableBody>
      {/* `data-vacio`: el patrón de tabla excluye esta fila del hover de datos — ver `tablePatron.ts`. */}
      <TableRow data-vacio="" className="hover:bg-transparent">
        {/* `h-auto` gana al 46px que el patrón de tabla le pone a las filas: acá la fila no es
            una fila de datos, es el panel entero. */}
        <TableCell colSpan={colSpan} className="h-auto whitespace-normal p-0">
          <EmptyState
            icon={<Filtro />}
            title={titulo}
            description={descripcion}
            action={
              ultimo ? (
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <Button variant="outline" className="min-h-11" onClick={ultimo.quitar}>
                    Quitar {ultimo.etiqueta.toLowerCase()}: {ultimo.valor}
                  </Button>
                  <Button variant="ghost" className="min-h-11" onClick={onLimpiarTodo}>
                    Limpiar todo
                  </Button>
                </div>
              ) : (
                accion
              )
            }
          />
        </TableCell>
      </TableRow>
    </TableBody>
  )
}

/** El embudo, dibujado inline: es el único ícono del archivo y lucide no trae uno con este trazo. */
function Filtro() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 4h18l-7 8v7l-4 2v-9L3 4z" />
    </svg>
  )
}
