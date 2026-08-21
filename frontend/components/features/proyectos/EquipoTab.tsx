"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus, Trash2, Pencil } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AsignacionModal } from "./AsignacionModal"
import { AsignarEmpleadosModal } from "./AsignarEmpleadosModal"
import { fetchAsignaciones, updateAsignacion, deleteAsignacion } from "@/services/proyectos"
import type { Asignacion, AsignacionUpdate } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })

interface Props {
  proyectoId: string
  proyectoEmpresaId: string   // para detectar empleados de otra empresa
  canWrite: boolean
}

export function EquipoTab({ proyectoId, proyectoEmpresaId, canWrite }: Props) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading]           = useState(true)
  const [assignOpen, setAssignOpen]     = useState(false)
  const [editing, setEditing]           = useState<Asignacion | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setAsignaciones((await fetchAsignaciones(proyectoId)).items) }
    catch { toast.error("No se pudo cargar el equipo.") }
    finally { setLoading(false) }
  }, [proyectoId])

  useEffect(() => { load() }, [load])

  async function handleEditSave(body: AsignacionUpdate) {
    if (!editing) return
    await updateAsignacion(proyectoId, editing.id, body)
    toast.success("Asignación actualizada")
    setEditing(null); await load()
  }

  async function handleDelete(asig: Asignacion) {
    if (!confirm(`¿Quitar a ${asig.empleado_nombre ?? "este colaborador"} del proyecto?`)) return
    try { await deleteAsignacion(proyectoId, asig.id); toast.success("Asignación eliminada"); await load() }
    catch { toast.error("No se puede quitar: tiene horas registradas.") }
  }

  if (loading) return (
    <div className="space-y-2 animate-pulse">
      {[1, 2, 3].map((i) => <div key={i} className="h-14 rounded-lg bg-muted" />)}
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{asignaciones.length} colaborador{asignaciones.length !== 1 ? "es" : ""} asignado{asignaciones.length !== 1 ? "s" : ""}</p>
        {canWrite && (
          <Button size="sm" className="min-h-[2.75rem] gap-1.5"
            onClick={() => setAssignOpen(true)}>
            <Plus className="size-4" /> Asignar colaboradores
          </Button>
        )}
      </div>

      {asignaciones.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Sin colaboradores asignados.</p>
      ) : (
        <div className="divide-y divide-border rounded-xl border bg-card">
          {asignaciones.map((a) => {
            const esOtraEmpresa = a.empleado_empresa_id !== proyectoEmpresaId
            return (
              <div key={a.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{a.empleado_nombre}</span>
                    {a.empleado_empresa_nombre && (
                      <Badge variant={esOtraEmpresa ? "outline" : "secondary"} className="text-xs">
                        {a.empleado_empresa_nombre}
                      </Badge>
                    )}
                    {!a.activo && <Badge variant="destructive" className="text-xs">Inactivo</Badge>}
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {a.rol} · {ARS.format(a.valor_hora)}/h
                  </p>
                </div>
                {canWrite && (
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" size="icon" className="size-8"
                      onClick={() => setEditing(a)}>
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" className="size-8 text-destructive hover:text-destructive"
                      onClick={() => handleDelete(a)}>
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <AsignarEmpleadosModal open={assignOpen} proyectoId={proyectoId}
        yaAsignadosIds={asignaciones.map((a) => a.empleado_id)}
        onClose={() => setAssignOpen(false)}
        onSuccess={() => { setAssignOpen(false); load() }} />

      <AsignacionModal open={editing !== null} asignacion={editing}
        onClose={() => setEditing(null)} onSave={handleEditSave} />
    </div>
  )
}
