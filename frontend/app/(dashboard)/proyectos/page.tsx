"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { cargarProyectos } from "@/components/features/proyectos/cargarProyectos"
import { ProyectoModal } from "@/components/features/proyectos/ProyectoModal"
import { ProyectosGrid } from "@/components/features/proyectos/ProyectosGrid"
import { useFiltrosProyectos } from "@/components/features/proyectos/useFiltrosProyectos"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { createProyecto, exportarProyectos, updateProyecto } from "@/services/proyectos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Proyecto, ProyectoCreate, ProyectoUpdate } from "@/types/proyecto"

const PAGE_SIZE_INICIAL = 20

export default function ProyectosPage() {
  const canWrite = useCanWrite()
  const [proyectos, setProyectos] = useState<Proyecto[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing]     = useState<Proyecto | null>(null)
  const [page, setPage]           = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [total, setTotal]         = useState(0)
  // 🔴 Cambiar cualquier filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar parado
  // en la 7 pediría una página que el resultado nuevo no tiene y la grilla saldría vacía sobre
  // un filtro que sí tiene proyectos.
  const { filtros, campos } = useFiltrosProyectos(() => setPage(1))

  const chips = chipsDeCampos(campos)

  // La carga vive en cargarProyectos: apaga el loading en un finally y se testea sin renderizar
  // (vitest corre sin jsdom, así que acá adentro no habría forma de verificarlo).
  const load = useCallback(async () => {
    await cargarProyectos(filtros, { setProyectos, setLoading, setError, setTotal }, page, pageSize)
    // filtros es un objeto nuevo por render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page, pageSize])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function handleSave(body: ProyectoCreate | ProyectoUpdate) {
    try {
      if (editing) { await updateProyecto(editing.id, body as ProyectoUpdate); toast.success("Proyecto actualizado") }
      else { await createProyecto(body as ProyectoCreate); toast.success("Proyecto creado") }
      setModalOpen(false); setEditing(null); await load()
    } catch { toast.error("No se pudo guardar el proyecto.") }
  }

  return (
    <div className="space-y-6">
      {/* 🔴 LAS ACCIONES VAN POR LA PROP `action` DE `PageHeader`, como en las otras 76 pantallas.
          Estaban como un <div> HERMANO adentro de un flex propio, y por eso el arreglo del
          encabezado compartido —que envuelve la fila de acciones en mobile— no llegaba acá: a
          390px "Nuevo proyecto" se salía 5px de la pantalla. Un encabezado armado a mano al lado
          del compartido es exactamente lo que hace que un arreglo del primitivo no valga para
          todos. */}
      <PageHeader
        title="Proyectos"
        /* El conteo sale de `total` (el del filtro entero, del backend) y no de
           `proyectos.length`: con paginación el largo del array es 20 en cualquier padrón. */
        description={loading && total === 0
          ? "Gestión de proyectos y costeo por horas"
          : `${total} proyecto${total !== 1 ? "s" : ""} · gestión y costeo por horas`}
        action={
          <div className="flex items-center gap-2">
            {/* Los MISMOS `filtros` que alimentan el listado: el archivo no puede traer filas que
                la pantalla no esté mostrando. Exportar es LECTURA, no va detrás de canWrite. */}
            <ExportMenu onExport={(formato) => exportarProyectos(formato, filtros)} />
            {canWrite && (
              <Button size="sm" className="min-h-[2.75rem] shrink-0 gap-1.5"
                onClick={() => { setEditing(null); setModalOpen(true) }}>
                <Plus className="size-4" /> Nuevo proyecto
              </Button>
            )}
          </div>
        }
      />

      {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los chips
          de la fila inferior). Detrás de "Más filtros" queda sólo Área, que es el recorte a otra
          entidad — el porqué está en `_camposProyectos.ts`. `disabled` durante la carga: los
          controles quedan a la vista con sus chips pero no se pueden tocar (§3). */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <ProyectosGrid
        proyectos={proyectos} loading={loading} error={error} canWrite={canWrite}
        onEdit={(p) => { setEditing(p); setModalOpen(true) }}
        onRetry={load}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}>
            Crear el primero
          </Button>
        ) : undefined}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página (era
       * `total > pageSize`): es lo que dice cuántos resultados dio el filtro.
       * 🔴 Y VA DETRÁS DE `!loading && !error`, QUE ES EL BUG QUE ESTA PANTALLA TENÍA: sin esa
       * guarda la barra se dibujaba SOBRE el esqueleto, con el `total` del pedido ANTERIOR — o
       * sea, mientras cargaba el resultado de un filtro nuevo, el pie seguía afirmando el conteo
       * del filtro viejo. Es el mismo caso que apareció en /vacantes.
       * El total que muestra es el TOTAL FILTRADO del backend, no `proyectos.length`.
       */}
      {!loading && !error && proyectos.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}

      <ProyectoModal open={modalOpen} proyecto={editing}
        onClose={() => { setModalOpen(false); setEditing(null) }} onSave={handleSave} />
    </div>
  )
}
