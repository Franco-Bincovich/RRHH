"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Briefcase } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { CandidatoModal } from "@/components/features/vacantes/CandidatoModal"
import { CodigoPostulacion } from "@/components/features/vacantes/CodigoPostulacion"
import { LinkedinModal } from "@/components/features/vacantes/LinkedinModal"
import { PipelineSeleccion } from "@/components/features/vacantes/PipelineSeleccion"
import { ClasificarCvsButton } from "@/components/features/screening/ClasificarCvsButton"
import { InformacionPuestoSection } from "@/components/features/vacantes/InformacionPuestoSection"
import { PublicacionSection } from "@/components/features/vacantes/PublicacionSection"
import { VacanteImagenes } from "@/components/features/vacantes/VacanteImagenes"
import { AccionesVacante } from "@/components/features/vacantes/ficha/AccionesVacante"
import { BarraVacante } from "@/components/features/vacantes/ficha/BarraVacante"
import { VacanteSkeleton } from "@/components/features/vacantes/ficha/VacanteSkeleton"
import { getSession } from "@/services/api"
import { useCanWrite } from "@/hooks/useCanWrite"
import { fetchCandidatos, fetchVacante } from "@/services/vacantes"
import type { Candidato, Vacante } from "@/types/vacantes"

export default function VacanteDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [vacante, setVacante] = useState<Vacante | null>(null)
  const [candidatos, setCandidatos] = useState<Candidato[]>([])
  const [loading, setLoading] = useState(true)
  // Entero y no booleano: `ErrorState` necesita el ApiError para distinguir el 404.
  const [error, setError] = useState<unknown>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [linkedinModalOpen, setLinkedinModalOpen] = useState(false)
  const canWrite = useCanWrite()

  const userEmail = getSession()?.user.email ?? ""

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [v, cs] = await Promise.all([fetchVacante(id), fetchCandidatos(id)])
      setVacante(v)
      setCandidatos(cs)
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  if (loading) return <VacanteSkeleton />

  if (error) return <ErrorState error={error} action={load} onVolver={() => router.push("/vacantes")} />

  if (!vacante) {
    return (
      <EmptyState
        icon={<Briefcase />}
        title="Vacante no encontrada"
        description="La vacante que buscás no existe o fue eliminada."
        action={<Button onClick={() => router.push("/vacantes")}>Ver vacantes</Button>}
      />
    )
  }

  return (
    <div>
      <BarraVacante
        vacante={vacante}
        candidatos={candidatos.length}
        acciones={
          <AccionesVacante
            vacante={vacante}
            canWrite={canWrite}
            onPublicarLinkedin={() => setLinkedinModalOpen(true)}
            onAgregarCandidato={() => setModalOpen(true)}
          />
        }
      />

      {/* Va ARRIBA de la publicación: es lo que hay que copiar ANTES de escribir el aviso. */}
      <CodigoPostulacion vacanteId={id} />

      <InformacionPuestoSection vacante={vacante} canWrite={canWrite} onSaved={setVacante} />

      <PublicacionSection vacante={vacante} canWrite={canWrite} onSaved={setVacante} />

      <VacanteImagenes vacanteId={id} />

      {/* Va pegado al pipeline porque lo que cambia son los candidatos de abajo, y
          separado del botón de revisar la casilla porque son DOS corridas distintas: aquella
          trae CVs (Gmail + Storage), esta los clasifica (N llamadas al modelo). Juntarlas
          cortaría la primera por presupuesto. `onListo` refresca la lista. */}
      {canWrite && <ClasificarCvsButton vacanteId={id} onListo={load} />}

      {/* El total de candidatos NO se repite acá: está en la barra de identidad, arriba. */}
      <h2 className="mb-4 text-base font-semibold text-foreground">Pipeline de selección</h2>

      <PipelineSeleccion
        candidatos={candidatos}
        canWrite={canWrite}
        onMovido={(actualizado) =>
          setCandidatos((prev) => prev.map((c) => (c.id === actualizado.id ? actualizado : c)))
        }
        onRecargar={load}
      />

      <CandidatoModal
        open={modalOpen}
        vacanteId={id}
        onClose={() => setModalOpen(false)}
        onSuccess={() => {
          setModalOpen(false)
          load()
        }}
      />

      <LinkedinModal
        open={linkedinModalOpen}
        vacanteId={id}
        defaultEmail={vacante.email_contacto ?? userEmail}
        onClose={() => setLinkedinModalOpen(false)}
        onSuccess={load}
      />
    </div>
  )
}
