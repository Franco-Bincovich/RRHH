import { UsersRound } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { EquipoMiembro } from "@/types/equipo"

import { COLUMNAS } from "./_grillaEquipo"

/**
 * Tabla de "mi equipo", presentacional. Dueña de los estados de carga/error/vacío.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO ES UNA FILA CON `colSpan` COMO EN EL PATRÓN, PERO **NO** ES `TablaVacia`.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `TablaVacia` arma su texto con `textoVacio(chips, sustantivo)`, y sin chips esa función dice
 * *"Todavía no hay X · Cuando se cargue el primero va a aparecer acá"*. Acá esa frase sería
 * **falsa**: quien mira esta pantalla no puede cargar a nadie. No tener gente a cargo no es un
 * dato faltante, es el estado real de alguien a quien no le asignaron reportes — y la acción no
 * es suya, es de Capital Humano cargando `manager_id`.
 *
 * Por eso el texto es propio y la estructura es la del patrón: la fila de `colSpan` con
 * `data-vacio` para que el hover de datos la excluya (`tablePatron.ts`), el encabezado intacto y
 * la misma `<Table patron="datos">` para los tres estados. Lo que NO se puede reusar es
 * `TablaVacia` entera, porque no admite reemplazar su copy — está anotado para la sesión que
 * decida si el patrón suma esa puerta.
 *
 * ⚠️ Y ESTA PANTALLA NO TIENE FILTROS NI PAGINACIÓN, tampoco por olvido: `GET /api/equipo` no
 * acepta un solo Query y devuelve la lista entera ("sin paginación: lista corta", dice su
 * router). Sin filtros no hay chips que mostrar, y sin `total` del backend no hay pie que armar.
 * Ponerle chips a una pantalla que no filtra sería exactamente lo que el bloque B prohíbe.
 */
export function EquipoTable({
  items, loading, error, onRetry,
}: {
  items: EquipoMiembro[]
  loading: boolean
  error: boolean
  onRetry: () => void
}) {
  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={COLUMNAS} />
      {loading ? (
        <FilasEsqueleto columnas={COLUMNAS} />
      ) : items.length === 0 ? (
        <TableBody>
          {/* `data-vacio`: el patrón de tabla excluye esta fila del hover de datos. `h-auto` gana
              al 46px de las filas: acá la fila no es una fila, es el panel entero. */}
          <TableRow data-vacio="" className="hover:bg-transparent">
            <TableCell colSpan={COLUMNAS.length} className="h-auto whitespace-normal p-0">
              <EmptyState
                icon={<UsersRound />}
                title="Todavía no tenés colaboradores a cargo"
                description="Cuando Capital Humano te asigne personas como responsable directo, van a aparecer acá."
              />
            </TableCell>
          </TableRow>
        </TableBody>
      ) : (
        <TableBody>
          {items.map((m) => (
            <TableRow key={m.id}>
              <TableCell className="font-medium">{m.apellido}</TableCell>
              <TableCell>{m.nombre}</TableCell>
              <TableCell className="text-muted-foreground">{m.empresa ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
