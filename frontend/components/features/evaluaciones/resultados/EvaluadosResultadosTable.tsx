"use client"

import { ChevronRight } from "lucide-react"

import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import type { EvaluadoListadoItem } from "@/types/evaluacionReportes"

import { COLUMNAS_EVALUADOS } from "./_grillaEvaluados"

interface Props {
  items: EvaluadoListadoItem[]
  loading: boolean
  onFicha: (id: string) => void
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
}

/**
 * El listado de evaluados de un lote. Dueña de la carga y del vacío; el ERROR se queda en el
 * panel, que es quien tiene el reintento.
 *
 * 🔴 EL SUSTANTIVO ES "EVALUADOS" Y NO SE HABLA DE CICLOS. El sistema **no corre evaluaciones:
 * importa resultados** calculados afuera (`docs/SISTEMA-DE-DISENO.md` §7). Nada acá puede
 * insinuar un proceso con instancias, vencimientos ni pendientes — no existen.
 *
 * ⚠️ Sin `claveSujeto`: el sujeto de la frase del vacío sería la EMPRESA, y acá el recorte por
 * empresa lo hace el LOTE (cada lote es de una sociedad) y no un chip del panel. La frase arranca
 * impersonal: "No hay evaluados con sector Ventas".
 */
export function EvaluadosResultadosTable({ items, loading, onFicha, chips, onLimpiarTodo }: Props) {
  return (
    <Table patron="datos">
      <Encabezado columnas={COLUMNAS_EVALUADOS} />
      {loading ? (
        <FilasEsqueleto columnas={COLUMNAS_EVALUADOS} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={COLUMNAS_EVALUADOS.length}
          chips={chips}
          sustantivo="evaluados"
          onLimpiarTodo={onLimpiarTodo}
        />
      ) : (
        <TableBody>
          {items.map((e) => (
            <TableRow key={e.id} className="group">
              <TableCell className="font-medium">
                {e.apellido} {e.nombre}
                {/* La fila que el matcheo no pudo resolver contra un legajo. Va al lado del
                    nombre crudo del CSV, nunca dentro. */}
                {!e.asignado && <Badge variant="outline" className="ml-2">Sin asignar</Badge>}
              </TableCell>
              <TableCell className="text-muted-foreground">{e.sector ?? "—"}</TableCell>
              <TableCell className="text-muted-foreground">{e.superior ?? "—"}</TableCell>
              <TableCell className="text-xs text-muted-foreground">{e.tipos.join(", ") || "—"}</TableCell>
              <TableCell className="text-right tabular-nums">
                {e.nota_final != null ? e.nota_final : <span className="text-muted-foreground">Sin nota</span>}
              </TableCell>
              <TableCell className="text-right">
                {/* 🔴 SIEMPRE VISIBLE, sólo cambia de color al apuntar (§3). Revelar la ficha en
                    hover obliga a barrer la tabla con el mouse para descubrir que existe — y la
                    ficha es lo único que explica de dónde sale la nota. */}
                <button
                  type="button"
                  onClick={() => onFicha(e.id)}
                  aria-label={`Ver la ficha de ${e.apellido} ${e.nombre}`}
                  className="ml-auto flex h-8 items-center gap-1 rounded-md px-2 text-xs text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                >
                  Ver ficha <ChevronRight className="size-3.5" aria-hidden="true" />
                </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
