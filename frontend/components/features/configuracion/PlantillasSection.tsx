"use client"

import { useState } from "react"
import { Mail, Pencil, Plus } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { PlantillaModal } from "@/components/features/configuracion/PlantillaModal"
import { usePlantillas } from "@/components/features/configuracion/usePlantillas"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Plantilla } from "@/types/plantillas"

/**
 * Plantillas de mail, dentro del panel de configuración.
 *
 * Va acá y no en una pantalla propia por cuatro razones: la conexión de Gmail —la cuenta DESDE
 * la que salen estos mails— ya vive en esta misma pantalla; es el mismo dueño y la misma sección
 * de permisos que las reglas de negocio; el gate por bloque ya está resuelto en la página; y una
 * pantalla propia arrastraría una entrada en el sidebar y su test estructural para algo que se
 * toca dos veces al año.
 *
 * `editable=false` (gerencia_lectura) muestra las plantillas en SOLO LECTURA, con el mismo
 * criterio que las reglas: el texto con el que la empresa se comunica es información, y quien
 * puede leer todos los reportes debería poder verlo. Lo que se oculta es el botón de editar.
 */
export function PlantillasSection({ editable }: { editable: boolean }) {
  const { items, contextos, loading, recargar } = usePlantillas()
  const [abierta, setAbierta] = useState<Plantilla | null>(null)
  const [nueva, setNueva] = useState(false)

  const open = nueva || abierta !== null

  return (
    <>
      <ConfigSection
        value="plantillas"
        icon={<Mail className="size-4" />}
        title="Plantillas de mail"
        description="El texto de los mails que el sistema envía. Podés usar variables como el nombre del empleado."
        badge={items.length > 0 && <Badge variant="secondary" className="ml-auto">{items.length}</Badge>}
      >
        {loading ? (
          <div className="h-9 animate-pulse rounded-md bg-muted" />
        ) : (
          <div className="space-y-2">
            {items.length === 0 && (
              <p className="text-sm text-muted-foreground">Todavía no hay plantillas cargadas.</p>
            )}
            {items.map((p) => (
              <div key={p.id} className="flex items-center justify-between gap-3 rounded-lg border p-2.5">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{p.clave}</p>
                  <p className="truncate text-xs text-muted-foreground">{p.asunto}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {p.es_global && <Badge variant="outline">General</Badge>}
                  {editable && (
                    <Button variant="ghost" size="sm" onClick={() => setAbierta(p)}>
                      <Pencil className="size-4" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
            {editable && (
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setNueva(true)}>
                <Plus className="size-4" />
                Nueva plantilla
              </Button>
            )}
          </div>
        )}
      </ConfigSection>

      <PlantillaModal
        open={open}
        plantilla={abierta}
        contextos={contextos}
        onClose={() => { setAbierta(null); setNueva(false) }}
        onSuccess={() => { setAbierta(null); setNueva(false); void recargar() }}
      />
    </>
  )
}
