"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowLeft, Download } from "lucide-react"

import { Card } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { BarraAssessment } from "@/components/features/assessment/ficha/BarraAssessment"
import { ScoresSection } from "@/components/features/assessment/ficha/ScoresSection"
import { fetchResultado } from "@/services/assessment"
import type { ResultadoDetalle } from "@/types/assessment"

export default function AssessmentDetailPage() {
  const params  = useParams()
  const router  = useRouter()
  const id      = params.id as string

  const [resultado, setResultado] = useState<ResultadoDetalle | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(false)
  // Módulo desactivado a propósito (no es un bug): redirige a /dashboard y no renderiza.
  // Es useState y NO const a propósito: un const colapsa a literal `false` por control-flow,
  // TS re-marca el cuerpo inalcanzable, se pierde el narrowing de `resultado` y `next build` falla.
  const [moduloActivo] = useState(false)

  const cargar = useCallback(() => {
    setError(false)
    setLoading(true)
    fetchResultado(id)
      .then(setResultado)
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!moduloActivo) { router.replace("/dashboard"); return }
    cargar()
  }, [router, moduloActivo, cargar])

  if (!moduloActivo) return null

  function back() { router.push("/assessment") }

  if (loading) {
    // El esqueleto tiene la grilla exacta (§3): la barra de identidad, el radar y los scores.
    return (
      <div className="space-y-6">
        <Skeleton shimmer className="h-[118px] w-full rounded-xl" />
        <Skeleton shimmer className="h-64 w-full rounded-xl" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {[...Array(4)].map((_, i) => <Skeleton key={i} shimmer className="h-20 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (error || !resultado) {
    return (
      <div>
        <Button variant="ghost" size="sm" className="mb-4 min-h-11 gap-2" onClick={back}>
          <ArrowLeft className="size-4" /> Volver
        </Button>
        {error
          ? <ErrorState action={cargar} />
          : <EmptyState icon={<ArrowLeft />} title="Resultado no encontrado" description="El perfil solicitado no existe o fue eliminado." />
        }
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Esta ficha NO TIENE ACCIONES, y por eso la barra va sin el grupo de la derecha: los tres
          botones de descarga están deshabilitados desde que existen (la entrega de archivos es el
          D2 del plan) y viven en su propio panel, que es donde se explica que todavía no. Subir
          un botón inerte a la barra de identidad lo pondría en el lugar de la acción primaria. */}
      <BarraAssessment resultado={resultado} />

      <ScoresSection scores={resultado.scores ?? {}} />

      <Card as="section" aria-label="Descargar reportes">
        <h2 className="mb-4 text-base font-semibold text-foreground">Descargar reportes</h2>
        <div className="flex flex-wrap gap-3">
          {(["Ejecutivo", "Comercial", "Competencias"] as const).map((tipo) => (
            <Button key={tipo} variant="outline" className="min-h-11 gap-2" disabled>
              <Download className="size-4" />
              Reporte {tipo}
            </Button>
          ))}
        </div>
      </Card>
    </div>
  )
}
