"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Pencil, LogOut } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { EmpleadoModal } from "@/components/features/empleados/EmpleadoModal"
import { LoadingSkeleton } from "@/components/features/empleados/ficha/_primitives"
import { OffboardingModal } from "@/components/features/empleados/ficha/OffboardingModal"
import { DatosEmpleadoSection } from "@/components/features/empleados/ficha/DatosEmpleadoSection"
import { AdjuntosSection } from "@/components/features/adjuntos/AdjuntosSection"
import { InventarioSection } from "@/components/features/empleados/ficha/InventarioSection"
import { HistorialCambiosSection } from "@/components/features/empleados/ficha/HistorialCambiosSection"
import { HistorialSalarialSection } from "@/components/features/empleados/ficha/HistorialSalarialSection"
import { VacacionesSection } from "@/components/features/empleados/ficha/VacacionesSection"
import { CesionesSection } from "@/components/features/empleados/ficha/CesionesSection"
import { fetchEmpleado } from "@/services/empleados"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Empleado } from "@/types/empleado"

export default function EmpleadoDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [empleado, setEmpleado] = useState<Empleado | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [offboardingOpen, setOffboardingOpen] = useState(false)

  const canWrite = useCanWrite()

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    setError(false)
    fetchEmpleado(id)
      .then((data) => { if (!cancelled) setEmpleado(data) })
      .catch(() => { if (!cancelled) setError(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id])

  async function recargarEmpleado() {
    const updated = await fetchEmpleado(id)
    setEmpleado(updated)
  }

  if (loading) return <LoadingSkeleton />

  if (error || !empleado) {
    return <ErrorState action={() => router.push("/empleados")} />
  }

  return (
    <div>
      <div className="mb-4">
        <Button
          variant="ghost"
          size="sm"
          className="min-h-11 gap-2"
          onClick={() => router.push("/empleados")}
        >
          <ArrowLeft className="size-4" />
          Volver a Empleados
        </Button>
      </div>

      <PageHeader
        title={`${empleado.nombre} ${empleado.apellido}`}
        description={empleado.roles?.[0] ?? empleado.cargo}
        action={
          canWrite ? (
            <div className="flex gap-2">
              {empleado.estado === "activo" && (
                <Button
                  variant="outline"
                  className="min-h-11 gap-2 text-destructive hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => setOffboardingOpen(true)}
                >
                  <LogOut className="size-4" />
                  Iniciar offboarding
                </Button>
              )}
              <Button className="min-h-11" onClick={() => setEditOpen(true)}>
                <Pencil />
                Editar
              </Button>
            </div>
          ) : undefined
        }
      />

      <div className="space-y-4">
        <DatosEmpleadoSection empleado={empleado} />
        <AdjuntosSection entidad="empleado" entidadId={id} />
        <InventarioSection empleadoId={id} />
        <HistorialSalarialSection empleadoId={id} />
        <HistorialCambiosSection empleadoId={id} />
        <VacacionesSection empleadoId={id} />
        <CesionesSection empleadoId={id} />
      </div>

      {canWrite && (
        <>
          <EmpleadoModal
            open={editOpen}
            onClose={() => setEditOpen(false)}
            onSuccess={async () => {
              setEditOpen(false)
              await recargarEmpleado()
            }}
            empleado={empleado}
          />
          <OffboardingModal
            open={offboardingOpen}
            empleadoId={id}
            onClose={() => setOffboardingOpen(false)}
            onSuccess={async () => {
              setOffboardingOpen(false)
              await recargarEmpleado()
            }}
          />
        </>
      )}
    </div>
  )
}
