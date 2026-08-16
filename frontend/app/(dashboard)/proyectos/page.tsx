"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { cargarProyectos } from "@/components/features/proyectos/cargarProyectos"
import { ProyectoModal } from "@/components/features/proyectos/ProyectoModal"
import { ProyectosGrid } from "@/components/features/proyectos/ProyectosGrid"
import { useFiltrosProyectos } from "@/components/features/proyectos/useFiltrosProyectos"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { createProyecto, exportarProyectos, updateProyecto } from "@/services/proyectos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Proyecto, ProyectoCreate, ProyectoUpdate } from "@/types/proyecto"

const PAGE_SIZE = 20

export default function ProyectosPage() {
  const canWrite = useCanWrite()
  const [proyectos, setProyectos] = useState<Proyecto[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing]     = useState<Proyecto | null>(null)
  const [page, setPage]           = useState(1)
  const [total, setTotal]         = useState(0)
  // 🔴 Cambiar cualquier filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar parado
  // en la 7 pediría una página que el resultado nuevo no tiene y la grilla saldría vacía sobre
  // un filtro que sí tiene proyectos.
  const { filtros, campos } = useFiltrosProyectos(() => setPage(1))

  // La carga vive en cargarProyectos: apaga el loading en un finally y se testea sin renderizar
  // (vitest corre sin jsdom, así que acá adentro no habría forma de verificarlo).
  const load = useCallback(async () => {
    await cargarProyectos(filtros, { setProyectos, setLoading, setError, setTotal }, page, PAGE_SIZE)
    // filtros es un objeto nuevo por render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page])  // eslint-disable-line react-hooks/exhaustive-deps

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
      <div className="flex items-start justify-between gap-4">
        <PageHeader title="Proyectos" description="Gestión de proyectos y costeo por horas" />
        <div className="flex shrink-0 items-center gap-2">
          {/* Los MISMOS `filtros` que alimentan el listado: el archivo no puede traer filas que
              la pantalla no esté mostrando. Exportar es LECTURA, así que no va detrás de canWrite. */}
          <ExportMenu onExport={(formato) => exportarProyectos(formato, filtros)} />
          {canWrite && (
            <Button size="sm" className="min-h-[2.75rem] shrink-0 gap-1.5"
              onClick={() => { setEditing(null); setModalOpen(true) }}>
              <Plus className="size-4" /> Nuevo proyecto
            </Button>
          )}
        </div>
      </div>

      <FiltersBar campos={campos} />

      <ProyectosGrid
        proyectos={proyectos} loading={loading} error={error} canWrite={canWrite}
        onEdit={(p) => { setEditing(p); setModalOpen(true) }}
        onCrear={() => { setEditing(null); setModalOpen(true) }}
      />

      {total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <ProyectoModal open={modalOpen} proyecto={editing}
        onClose={() => { setModalOpen(false); setEditing(null) }} onSave={handleSave} />
    </div>
  )
}
