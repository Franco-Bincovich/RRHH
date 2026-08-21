"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { ErrorState } from "@/components/ui/ErrorState"
import { EmpleadoModal } from "@/components/features/empleados/EmpleadoModal"
import { AccionesFicha } from "@/components/features/empleados/ficha/AccionesFicha"
import { BarraIdentidad } from "@/components/features/empleados/ficha/BarraIdentidad"
import { LoadingSkeleton } from "@/components/features/empleados/ficha/_primitives"
import { OffboardingModal } from "@/components/features/empleados/ficha/OffboardingModal"
import { DatosEmpleadoSection } from "@/components/features/empleados/ficha/DatosEmpleadoSection"
import { AdjuntosSection } from "@/components/features/adjuntos/AdjuntosSection"
import { InventarioSection } from "@/components/features/empleados/ficha/InventarioSection"
import { HistorialCambiosSection } from "@/components/features/empleados/ficha/HistorialCambiosSection"
import { HistorialSalarialSection } from "@/components/features/empleados/ficha/HistorialSalarialSection"
import { RecategorizacionesSection } from "@/components/features/empleados/ficha/RecategorizacionesSection"
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
      <BarraIdentidad
        empleado={empleado}
        acciones={
          canWrite ? (
            <AccionesFicha
              empleado={empleado}
              onActivado={recargarEmpleado}
              onOffboarding={() => setOffboardingOpen(true)}
              onEditar={() => setEditOpen(true)}
            />
          ) : undefined
        }
      />

      {/*
       * 🔴 TRES COLUMNAS DE PANELES INDEPENDIENTES (§3), y el reparto no es alfabético: cada
       * columna contesta una pregunta distinta, así que se lee una sola y alcanza.
       *   1. quién es      → datos personales y laborales (los dos paneles de campos)
       *   2. qué tiene     → lo que la empresa le dio: documentos, inventario, cesiones
       *   3. qué le pasó   → su línea de tiempo: sueldo y vacaciones
       * `items-start` para que cada panel mida lo suyo: sin él, los tres de una fila se estiran
       * al alto del más largo y quedan con medio panel vacío.
       */}
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4">
          <DatosEmpleadoSection empleado={empleado} />
        </div>
        <div className="flex flex-col gap-4">
          <AdjuntosSection entidad="empleado" entidadId={id} />
          <InventarioSection empleadoId={id} />
          <CesionesSection empleadoId={id} />
        </div>
        <div className="flex flex-col gap-4">
          <HistorialSalarialSection empleadoId={id} />
          {/* Va en la TERCERA columna —"qué le pasó"— junto al sueldo y las vacaciones, y no en
              la primera con los datos del legajo: una recategorización es un hecho fechado de su
              línea de tiempo, no un atributo suyo. El rol vigente ya está arriba, en el panel
              laboral; acá está cómo llegó a serlo. */}
          <RecategorizacionesSection empleadoId={id} />
          <VacacionesSection empleadoId={id} />
        </div>
      </div>

      {/*
       * 🔴 EL HISTORIAL DE CAMBIOS QUEDA A LO ANCHO, FUERA DE LAS TRES COLUMNAS, y es una
       * excepción declarada: adentro trae la MISMA tabla de 5 columnas que usa /auditoria más su
       * paginación, y en un tercio de pantalla eso no entra sin scroll horizontal. No se lo
       * convirtió al patrón de historial ("de → a") porque `AuditTable` la comparten esta ficha y
       * la pantalla de auditoría: cambiarla acá sería migrar /auditoria de rebote, que es
       * exactamente lo que esta tanda no hace.
       */}
      <div className="mt-4">
        <HistorialCambiosSection empleadoId={id} />
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
