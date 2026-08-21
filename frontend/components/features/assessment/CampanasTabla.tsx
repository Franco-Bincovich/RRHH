"use client"

import type { ReactNode } from "react"

import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import { ErrorState } from "@/components/ui/ErrorState"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { Campana } from "@/types/assessment"

import { COLUMNAS_CAMPANAS, ESTADO_ESTILO, TIPO_LABEL, fmtDate } from "./_grillaAssessment"

/**
 * Las campañas de assessment. Dueña de sus tres estados: carga, error y vacío.
 *
 * ⚠️ (a) (b) y (d) DEL PATRÓN NO APLICAN, y no es un olvido: `GET /api/assessment/campanas` no
 * acepta un solo Query y devuelve la lista entera. Sin filtros no hay chips, y sin paginado no
 * hay pie. Los chips que `TablaVacia` recibe van vacíos a propósito — su frase sin filtros
 * ("todavía no hay ninguna") es exactamente la correcta acá.
 */
export function CampanasTabla({
  campanas, loading, error, onReintentar, mostrarEmpresa, accionVacio,
}: {
  campanas: Campana[]
  loading: boolean
  error: boolean
  onReintentar: () => void
  mostrarEmpresa: boolean
  /** El alta, para ofrecerla desde el vacío. `undefined` sin permiso de escritura. */
  accionVacio?: ReactNode
}) {
  const columnas = COLUMNAS_CAMPANAS.filter((c) => c.clave !== "empresa" || mostrarEmpresa)

  if (error) {
    return (
      <ErrorState
        title="No se pudieron cargar las campañas"
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
      ) : campanas.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={[]}
          sustantivo="campañas"
          genero="femenino"
          onLimpiarTodo={() => {}}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {campanas.map((c) => {
            // "Completados" se compara contra los links ENVIADOS, no contra un total teórico: una
            // campaña sin links todavía no le pidió nada a nadie, y ahí 0/0 no es un logro.
            const completa = c.links_enviados > 0 && c.completados === c.links_enviados
            return (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.nombre}</TableCell>
                {mostrarEmpresa && (
                  <TableCell className="text-muted-foreground">{c.empresa_nombre ?? "—"}</TableCell>
                )}
                <TableCell className="text-muted-foreground">{TIPO_LABEL[c.tipo] ?? c.tipo}</TableCell>
                <TableCell className="text-muted-foreground tabular-nums">{fmtDate(c.created_at)}</TableCell>
                <TableCell className="text-right text-muted-foreground tabular-nums">{c.links_enviados}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {/* `text-success` en vez del `text-emerald-600 dark:text-emerald-400` que estaba
                      escrito a mano: el token ya trae su valor de modo oscuro y sí lo mide el
                      barrido de contraste. */}
                  <span className={completa ? "font-medium text-success" : ""}>{c.completados}</span>
                  <span className="text-muted-foreground">/{c.links_enviados}</span>
                </TableCell>
                <TableCell>
                  {/* El estilo sale de `_grillaAssessment`: ninguno de los cuatro estados se pinta
                      ya con el color de la marca — ver el 🔴 de ese archivo. */}
                  <Badge variant="outline" className={`capitalize ${ESTADO_ESTILO[c.estado] ?? ""}`}>
                    {c.estado}
                  </Badge>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      )}
    </Table>
  )
}
