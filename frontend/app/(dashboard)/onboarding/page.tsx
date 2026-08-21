"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus, UserCheck } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/ui/EmptyState"
import { IniciarOnboardingModal } from "@/components/features/onboarding/IniciarOnboardingModal"
import { Button } from "@/components/ui/button"
import { OnboardingAcciones } from "@/components/features/onboarding/OnboardingAcciones"
import { useOnboardingDetalle } from "@/components/features/onboarding/useOnboardingDetalle"
import { OnboardingList } from "@/components/features/onboarding/OnboardingList"
import { OnboardingChecklist } from "@/components/features/onboarding/OnboardingChecklist"
import { fetchOnboardings } from "@/services/onboarding"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { OnboardingInstancia } from "@/types/onboarding"

export default function OnboardingPage() {
  const canWrite = useCanWrite()
  const [onboardings, setOnboardings] = useState<OnboardingInstancia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const { detalle, setDetalle, loadingDetalle, handleSelect, handleTareaToggled } =
    useOnboardingDetalle(setOnboardings)

  // El reintento del `ErrorState` necesita poder volver a disparar la carga, así que la función
  // sale del efecto y vive acá.
  const cargarOnboardings = useCallback(() => {
    setLoading(true); setError(null)
    fetchOnboardings()
      .then(setOnboardings)
      .catch(() => setError("No se pudieron cargar los onboardings"))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { cargarOnboardings() }, [cargarOnboardings])

  function handleOnboardingIniciado(instancia: OnboardingInstancia) {
    setOnboardings((prev) => [instancia, ...prev])
    setModalOpen(false)
  }

  // mostrar columna empresa solo cuando el topbar está en "Todas"
  const mostrarEmpresa = !empresaActivaId
  const iniciarBtn = (
    <Button className="min-h-11 gap-1.5" onClick={() => setModalOpen(true)}>
      <Plus className="size-4" />
      <span className="hidden sm:inline">Iniciar onboarding</span>
    </Button>
  )

  // ─── Main render ─────────────────────────────────────────────────────────────

  return (
    <div>
      {/* 🔴 EL ENCABEZADO Y SUS ACCIONES SE RENDERIZAN SIEMPRE. Acá vivían dos `return` tempranos
          —uno de carga y otro de error— que se llevaban la pantalla entera: durante la carga
          desaparecían el título, el export y el acceso a los templates, y la pantalla cambiaba de
          forma dos veces seguidas. Ahora sólo cambia el CONTENIDO.
          `onboardings.length` como conteo es correcto ACÁ Y SÓLO ACÁ: `GET /api/onboarding` no
          pagina y devuelve todo, así que el largo del array ES el total. */}
      <div className="relative">
        <PageHeader
          title="Onboarding"
          description={loading ? "Cargando..." : `${onboardings.length} colaboradores en proceso`}
        />
        <OnboardingAcciones canWrite={canWrite} iniciarBtn={iniciarBtn} />
      </div>

      {loading ? (
        <ul className="space-y-3" role="list">
          {[1, 2, 3].map((i) => (
            <li key={i}><Skeleton shimmer className="h-24 w-full rounded-xl" /></li>
          ))}
        </ul>
      ) : error ? (
        <ErrorState description={error} action={cargarOnboardings} />
      ) : onboardings.length === 0 ? (
        /*
         * 🔴 COPY PROPIO, y el motivo es el mismo que en offboarding: **vacío no es una carencia**.
         * Un cero acá significa que nadie está entrando esta semana, no que falte cargar un dato —
         * y el onboarding no se "carga": se INICIA eligiendo un template y una persona, con el
         * botón de arriba. La frase genérica de `textoVacio` ("cuando se cargue el primero va a
         * aparecer acá") mandaría a buscar un alta que no tiene ese nombre.
         */
        <EmptyState
          icon={<UserCheck />}
          title="No hay ningún ingreso en curso"
          description="Cuando inicies un onboarding, el proceso aparece acá con su checklist semana por semana."
          action={canWrite ? iniciarBtn : undefined}
        />
      ) : (
        <OnboardingList
          onboardings={onboardings}
          mostrarEmpresa={mostrarEmpresa}
          deshabilitado={loadingDetalle}
          onAbrir={handleSelect}
        />
      )}

      {/* Backdrop del checklist */}
      {detalle && (
        <div
          className="fixed inset-0 z-30 bg-black/20 dark:bg-black/40"
          aria-hidden="true"
          onClick={() => setDetalle(null)}
        />
      )}

      {/* Checklist panel */}
      {detalle && (
        <OnboardingChecklist
          detalle={detalle}
          canWrite={canWrite}
          onClose={() => setDetalle(null)}
          onTareaToggled={handleTareaToggled}
        />
      )}

      {/* Modal iniciar onboarding */}
      {modalOpen && (
        <IniciarOnboardingModal
          activos={onboardings}
          onClose={() => setModalOpen(false)}
          onSuccess={handleOnboardingIniciado}
        />
      )}
    </div>
  )
}
