"use client"

import { ErrorState } from "@/components/ui/ErrorState"
import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { Skeleton } from "@/components/ui/skeleton"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { ReactNode } from "react"
import { KanbanView } from "@/components/features/objetivos/KanbanView"
import { ListView } from "@/components/features/objetivos/ListView"
import type { EstadoObjetivo, Objetivo } from "@/types/objetivo"

/**
 * El área de contenido de /objetivos: el selector de vista y lo que cada vista renderiza, con
 * sus estados de carga y de error.
 *
 * Extraído de app/(dashboard)/objetivos/page.tsx, que estaba en 148/150 — dos líneas libres. El
 * movimiento fue PURO: las clases, el `cn()` de la pestaña activa, el orden de las guardas
 * (loading → error → vista) y el skeleton son idénticos a los que estaban en la página.
 *
 * 🔴 POR QUÉ SE EXTRAJO ESTE BLOQUE Y NO EL DE ACCIONES, que era la otra opción.
 * Acá es donde el módulo CRECE: vienen dos vistas más (una anual y otra de tiempo libre), y cada
 * una suma un valor al tipo `Vista`, una etiqueta en la pestaña y una rama de render. Con el
 * bloque en la página, esas tres cosas la empujaban sobre el límite otra vez. El bloque de
 * acciones, en cambio, es estable: son tres botones que no cambian con las vistas nuevas.
 *
 * ⚠️ La etiqueta de la pestaña sigue saliendo del ternario `v === "tablero" ? ... : ...`, tal
 * como estaba en la página: se movió VERBATIM y no se "mejoró" de paso. Con la tercera vista ese
 * ternario deja de servir y hay que cambiarlo por un mapa `Vista → label`; hacerlo ahora habría
 * mezclado un rediseño con una división, que es lo que este corte evita.
 *
 * 🔑 El selector, las guardas y el render viajaron JUNTOS a propósito, aunque en la página
 * estuvieran separados por el `loading`/`error`. Son una sola unidad: agregar una vista sin
 * agregar su pestaña —o al revés— es el bug que este archivo hace imposible de escribir por
 * accidente, porque las dos listas están a la vista una al lado de la otra.
 *
 * Presentacional y controlado: no tiene estado propio, no fetchea. `vista` y su setter, los
 * datos y los handlers los sigue teniendo la página.
 */

export type Vista = "tablero" | "lista"

/**
 * 🔴 EL ESQUELETO DEJÓ DE SER COMPARTIDO, y ése es el cambio del patrón acá. Era una pila de seis
 * barras que se dibujaba para las DOS vistas, así que la de Lista perdía su encabezado mientras
 * cargaba y la de Tablero mostraba renglones donde iban a aparecer columnas. Ahora cada vista
 * carga con su propia forma: `ListView` con `FilasEsqueleto` (mismas columnas, mismos anchos) y
 * el tablero con tarjetas. Lo único que sigue compartido es el ERROR, que sí es de la pantalla.
 */
function TableroSkeleton() {
  return (
    <GrillaTarjetas>
      {[1, 2, 3].map((i) => <Skeleton key={i} shimmer className="h-64 rounded-xl" />)}
    </GrillaTarjetas>
  )
}

interface Props {
  vista: Vista
  onVista: (v: Vista) => void
  loading: boolean
  error: boolean
  onReintentar: () => void
  objetivos: Objetivo[]
  /**
   * Cuántas RAÍCES hay en el filtro entero, según el backend. Viaja hasta las dos vistas y no se
   * deriva de `objetivos.length` en ningún lado: hoy coinciden porque este listado no pagina,
   * y el día que pagine `length` es el tamaño de la página. Ver el contrato al pie de
   * `schemas/objetivo.py::ObjetivoListResponse`.
   */
  total: number
  mostrarEmpresa: boolean
  canWrite: boolean
  onMover: (id: string, estado: EstadoObjetivo) => Promise<void>
  moviendo: string | null
  onEdit: (obj: Objetivo) => void
  onDelete: (objetivo: Objetivo) => void
  deletingId: string | null
  /** Los filtros activos, para explicar el vacío con sus valores reales y ofrecer quitarlos. */
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  /** Qué ofrecer cuando NO hay filtros y tampoco datos: el alta. `undefined` sin permiso. */
  accionVacio?: ReactNode
}

export function ObjetivosVistas({
  vista, onVista, loading, error, onReintentar, objetivos, total, mostrarEmpresa,
  canWrite, onMover, moviendo, onEdit, onDelete, deletingId, chips, onLimpiarTodo, accionVacio,
}: Props) {
  return (
    <>
      <Tabs value={vista} onValueChange={onVista}>
        <TabList className="mb-4">
          <Tab value="tablero">Tablero</Tab>
          <Tab value="lista">Lista</Tab>
        </TabList>

        {/* El ERROR sigue viviendo FUERA de los paneles: es estado de la pantalla, no de una
            solapa, y duplicarlo adentro de cada panel lo haría divergir. La CARGA, en cambio, se
            bajó a cada vista — ver el 🔴 del esqueleto. */}
        {error ? (
          <ErrorState description="No se pudieron cargar los objetivos." action={onReintentar} />
        ) : (
          <>
            <TabPanel value="tablero">
              {loading ? <TableroSkeleton /> : (
                <KanbanView objetivos={objetivos} total={total} onMover={onMover} moviendo={moviendo}
                  canWrite={canWrite} onEdit={onEdit} onDelete={onDelete} deletingId={deletingId} />
              )}
            </TabPanel>
            <TabPanel value="lista">
              <ListView objetivos={objetivos} loading={loading} total={total} showEmpresa={mostrarEmpresa}
                canWrite={canWrite} onEdit={onEdit} onDelete={onDelete} deletingId={deletingId}
                chips={chips} onLimpiarTodo={onLimpiarTodo} accionVacio={accionVacio} />
            </TabPanel>
          </>
        )}
      </Tabs>
    </>
  )
}
