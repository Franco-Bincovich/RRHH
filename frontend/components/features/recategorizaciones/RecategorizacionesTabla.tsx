import { Pencil } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { formatFecha } from "@/components/features/shared/fechas"
import type { Recategorizacion } from "@/types/recategorizacion"

import { CeldaCambios } from "./CeldaCambios"
import { montoLegible, paresCambiados } from "./_cambios"
import { columnas as construirColumnas } from "./_columnas"

/**
 * La planilla de recategorizaciones, presentacional. Dueña de los estados de carga/error/vacío.
 *
 * 🔴 LA ÚNICA ACCIÓN DE FILA ES EDITAR. No hay borrar en ninguna superficie de este módulo, y no
 * es que falte cablearlo: **el backend no publica un DELETE** (`recategorizaciones_escrituras.py`).
 * Borrar rompe la cadena de `*_anterior` que cuelga de cada fila —la siguiente quedaría afirmando
 * un valor previo que ya no existe— y la auditoría ya registra quién editó qué. Un ícono de
 * tacho acá prometería una operación que el servidor rechaza con 405.
 *
 * 🔴 SIN COLUMNA DE ESTADO NI DE APROBACIÓN (§7): esto es registro puro. El sistema de diseño
 * advierte que un prototipo anterior prometió un flujo de aprobación que no existe, y una columna
 * "Estado: Registrada" insinuaría que hay otros estados posibles.
 */
export function RecategorizacionesTabla({
  items, loading, error, mostrarImpacto, canWrite, chips, onRetry, onLimpiarTodo, onEditar,
  accionVacio, sujetoVacio,
}: {
  items: Recategorizacion[]
  loading: boolean
  error: boolean
  /** `false` saca la columna de impacto ENTERA. Ver `_columnas`. */
  mostrarImpacto: boolean
  canWrite: boolean
  chips: ChipFiltro[]
  onRetry: () => void
  onLimpiarTodo: () => void
  onEditar: (r: Recategorizacion) => void
  accionVacio?: ReactNode
  /**
   * Qué chip es el SUJETO de la frase del vacío. `"Colaborador"` cuando hay uno filtrado
   * ("Juan Pérez no tiene recategorizaciones…"); `undefined` deja la frase impersonal, que es lo
   * correcto sin filtro de persona — el sujeto no puede ser la empresa, que acá no es un filtro.
   */
  sujetoVacio?: string
}) {
  const cols = construirColumnas(mostrarImpacto).filter(
    (c) => c.clave !== "acciones" || canWrite,
  )

  if (error) return <ErrorState action={onRetry} />

  return (
    // Una sola <Table> para los tres estados: el encabezado se renderiza SIEMPRE, así la pantalla
    // no cambia de forma entre la carga, el vacío y los datos.
    <Table patron="datos">
      <Encabezado columnas={cols} />
      {loading ? (
        <FilasEsqueleto columnas={cols} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={cols.length}
          chips={chips}
          sustantivo="recategorizaciones"
          genero="femenino"
          claveSujeto={sujetoVacio}
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((r) => (
            <TableRow key={r.id}>
              <TableCell className="tabular-nums">{formatFecha(r.fecha_efectiva)}</TableCell>
              <TableCell className="font-medium">{r.empleado_nombre ?? "—"}</TableCell>
              <TableCell className="whitespace-normal">
                <CeldaCambios pares={paresCambiados(r)} />
              </TableCell>
              {/* El motivo envuelve en vez de truncarse: es una línea de explicación y es la
                  mitad de por qué alguien abre esta planilla. */}
              <TableCell className="whitespace-normal text-muted-foreground">{r.motivo}</TableCell>
              {mostrarImpacto && (
                <TableCell className="tabular-nums">{montoLegible(r.impacto_salarial)}</TableCell>
              )}
              <TableCell className="text-muted-foreground">
                {r.registrado_por_nombre ?? "—"}
              </TableCell>
              {canWrite && (
                <TableCell>
                  <button
                    type="button"
                    aria-label={`Editar la recategorización de ${r.empleado_nombre ?? "el colaborador"}`}
                    onClick={() => onEditar(r)}
                    className="flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                  >
                    <Pencil className="size-4" aria-hidden="true" />
                  </button>
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
