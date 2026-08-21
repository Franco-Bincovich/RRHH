"use client"

import { ClipboardList } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Resultado } from "@/types/assessment"

import { COLUMNAS_RESULTADOS, TIPO_LABEL, fmtDate } from "./_grillaAssessment"

/**
 * Los resultados de las evaluaciones completadas. Como campañas: sin filtros y sin paginado, así
 * que (a) (b) y (d) del patrón no aplican — `GET /api/assessment/resultados` no acepta un Query.
 *
 * 🔴 EL VACÍO NO USA `TablaVacia` Y ESA ES LA DECISIÓN DEL ARCHIVO. Su frase sin filtros es
 * "cuando se cargue el primero va a aparecer acá", y acá **nadie carga un resultado**: aparece
 * solo cuando alguien termina de responder el link que le mandaron. Ofrecerle al usuario de RRHH
 * que cargue el primero lo mandaría a buscar un botón que no existe y que no debería existir.
 * El encabezado sí se mantiene, que es lo que el patrón pide: el vacío es una fila de la tabla.
 *
 * ⚠️ LA NAVEGACIÓN ENTRA POR PROP (`onAbrir`) Y NO POR `useRouter()` ADENTRO. No es preferencia:
 * `useRouter` sólo funciona con el router de la app montado, así que un componente que lo llama
 * no se puede renderizar en un test —vitest corre sin jsdom y sin router— y la tabla entera
 * quedaría sin cobertura. Con la prop, la página sigue siendo la que decide adónde se va. Mismo
 * criterio que `EvaluadosResultadosTable`, que recibe `onFicha`.
 */
export function ResultadosTabla({
  resultados, loading, error, onReintentar, mostrarEmpresa, onAbrir,
}: {
  resultados: Resultado[]
  loading: boolean
  error: boolean
  onReintentar: () => void
  mostrarEmpresa: boolean
  /** Abrir el detalle de un resultado. Ver el ⚠️ del encabezado. */
  onAbrir: (id: string) => void
}) {
  const columnas = COLUMNAS_RESULTADOS.filter((c) => c.clave !== "empresa" || mostrarEmpresa)

  if (error) {
    return (
      <ErrorState
        title="No se pudieron cargar los resultados"
        description="La lista no llegó. Puede ser un corte momentáneo de conexión."
        action={onReintentar}
      />
    )
  }

  return (
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : resultados.length === 0 ? (
        <TableBody>
          <TableRow data-vacio="" className="hover:bg-transparent">
            <TableCell colSpan={columnas.length} className="h-auto whitespace-normal p-0">
              <EmptyState
                icon={<ClipboardList />}
                title="Todavía no completó nadie"
                description="Un resultado aparece acá cuando la persona termina de responder el link de su campaña: no se carga a mano."
              />
            </TableCell>
          </TableRow>
        </TableBody>
      ) : (
        <TableBody>
          {resultados.map((r) => (
            <TableRow
              key={r.id}
              className="cursor-pointer"
              onClick={() => onAbrir(r.id)}
            >
              <TableCell className="font-medium">{r.evaluado_nombre}</TableCell>
              {mostrarEmpresa && (
                <TableCell className="text-muted-foreground">{r.empresa_nombre ?? "—"}</TableCell>
              )}
              <TableCell className="text-muted-foreground">{TIPO_LABEL[r.tipo] ?? r.tipo}</TableCell>
              <TableCell className="text-muted-foreground tabular-nums">
                {r.fecha_completado ? fmtDate(r.fecha_completado) : "—"}
              </TableCell>
              <TableCell>
                {r.perfil_dominante ? <Badge variant="outline">{r.perfil_dominante}</Badge> : "—"}
              </TableCell>
              {/* Cifras tabulares: alinean los dígitos entre filas y hacen comparable la columna. */}
              <TableCell className="text-right font-semibold tabular-nums">
                {r.score_general ?? "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
