"use client"

import { useEffect, useState } from "react"
import { ScanSearch } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { LeyendaDescarte } from "@/components/features/candidatos/ClasificacionBadge"
import { useCriterioScreening } from "@/components/features/configuracion/useCriterioScreening"
import { AccionBloqueada } from "@/components/ui/AccionBloqueada"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { ScreeningCriterio } from "@/types/screening"

const CAMPOS: { key: keyof ScreeningCriterio; label: string; ayuda: string }[] = [
  { key: "def_relevante", label: "Relevante", ayuda: "Cuándo un CV pasa el filtro sin dudas." },
  { key: "def_dudoso", label: "Dudoso", ayuda: "Todo lo que no es claramente lo uno ni lo otro. Es el default: ante la duda, siempre acá." },
  { key: "def_no_relevante", label: "No relevante", ayuda: "Conviene dejarlo angosto: solo cuando el perfil es de un campo claramente distinto." },
  { key: "instrucciones", label: "Notas adicionales (opcional)", ayuda: "Cualquier aclaración para el criterio de tu empresa." },
]

/**
 * Editor del criterio del clasificador de CVs (migración 100).
 *
 * 🔴 LO QUE ESTA PANTALLA **NO** DEJA CAMBIAR, Y ESO ES DELIBERADO: las tres categorías, el
 * formato de salida, la separación system/user, el sanitizado del CV y el sesgo "ante la duda,
 * dudoso". Los textos de acá se INSERTAN COMO DATO dentro de una estructura fija — no la
 * reemplazan ni la extienden, así que un texto que diga "ignorá lo anterior" es tan inocuo como
 * el mismo texto adentro de un CV. Hay tests que lo demuestran.
 */
export function ScreeningSection({ editable, motivoBloqueo }: {
  editable: boolean
  /** Por qué HOY no se puede guardar (vista consolidada), o `null`. Lo decide la página. */
  motivoBloqueo: string | null
}) {
  const { criterio, loading, guardando, guardar, restaurar } = useCriterioScreening()
  const [form, setForm] = useState<ScreeningCriterio>(criterio)

  useEffect(() => { setForm(criterio) }, [criterio])

  return (
    <ConfigSection
      value="screening"
      icon={<ScanSearch className="size-5 text-primary" />}
      title="Criterio de preselección de CVs"
      description="Con qué criterio el sistema separa los CVs que a primera vista no corresponden a la búsqueda."
    >
      {loading ? <Skeleton className="h-40 w-full" /> : (
        <div className="space-y-4">
          <LeyendaDescarte />

          {!criterio.es_propia && (
            <p className="text-xs text-muted-foreground">
              Estás usando el criterio general. Si lo editás y guardás, tu empresa pasa a tener el
              suyo propio y deja de seguir los cambios del general.
            </p>
          )}

          {CAMPOS.map(({ key, label, ayuda }) => (
            <div key={key} className="space-y-1">
              <label htmlFor={`scr-${key}`} className="text-sm font-medium text-foreground">{label}</label>
              <p className="text-xs text-muted-foreground">{ayuda}</p>
              <textarea
                id={`scr-${key}`}
                rows={2}
                maxLength={2000}
                disabled={!editable}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                className="w-full rounded-md border border-input bg-background p-2 text-sm disabled:opacity-60"
              />
            </div>
          ))}

          {editable && (
            <AccionBloqueada motivo={motivoBloqueo}>
              {(bloqueada) => (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" disabled={bloqueada || guardando} onClick={() => guardar(form)}>
                    {guardando ? "Guardando..." : "Guardar criterio"}
                  </Button>
                  {/* El `!es_propia` ya bloqueaba este botón antes: restaurar el criterio general
                      cuando ya se está usando el general no hace nada. Es la misma clase de
                      precondición, y por eso conviven en el mismo `disabled`. */}
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={bloqueada || guardando || !criterio.es_propia}
                    onClick={() => restaurar()}
                  >
                    Restaurar el criterio general
                  </Button>
                </div>
              )}
            </AccionBloqueada>
          )}
        </div>
      )}
    </ConfigSection>
  )
}
