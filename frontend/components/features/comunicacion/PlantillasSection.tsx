"use client"

import { useState } from "react"
import { Mail, Pencil, Plus, Send } from "lucide-react"

// ConfigSection sigue viviendo en `features/configuracion/`: es la shell plegable COMPARTIDA
// (la usan también las cards del dashboard), no una pieza de este módulo.
import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { EnviarPlantillaModal } from "@/components/features/comunicacion/EnviarPlantillaModal"
import { PlantillaModal } from "@/components/features/comunicacion/PlantillaModal"
import { usePlantillas } from "@/components/features/comunicacion/usePlantillas"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Plantilla } from "@/types/plantillas"

/**
 * Plantillas de mail — pestaña "Plantillas" de /comunicacion.
 *
 * 🔴 ESTE COMPONENTE VIVÍA EN /configuracion Y SE MUDÓ EL 7/8/2026. El argumento de entonces
 * está en el historial de git y era razonable con lo que había: "es el ABM de un texto que se
 * toca dos veces al año, no justifica una pantalla ni una entrada en el sidebar". Lo que lo
 * invalidó no fue una discusión de diseño: fue que desde acá ahora se MANDAN MAILS a la gente
 * (botón "Enviar" por fila). Eso es una acción operativa recurrente, con historial propio y con
 * consecuencias hacia afuera de la empresa — deja de ser configuración.
 *
 * Se mudó TAL CUAL: sigue usando `ConfigSection` (la shell plegable compartida), que en la
 * pestaña se monta bajo un `Accordion.Root` propio. Que un acordeón de un solo ítem adentro de
 * una pestaña sea redundante es cierto y quedó pendiente a propósito: mezclar la mudanza con un
 * rediseño hace que el diff no se pueda revisar.
 *
 * `editable=false` (gerencia_lectura) muestra las plantillas en SOLO LECTURA, con el mismo
 * criterio que las reglas: el texto con el que la empresa se comunica es información, y quien
 * puede leer todos los reportes debería poder verlo. Lo que se oculta es el botón de editar.
 *
 * 🔴 ENVIAR VA DETRÁS DEL MISMO `editable` QUE EDITAR, y no de un gate propio: el backend gatea
 * `POST /api/plantillas/enviar` con WRITE sobre configuración —la misma dependencia que el PUT—,
 * o sea que solo `admin_rrhh` puede. Un botón visible para `gerencia_lectura` daría 403 al
 * apretarlo, que es peor que no estar.
 */
export function PlantillasSection({ editable }: { editable: boolean }) {
  const { items, contextos, loading, recargar } = usePlantillas()
  const [abierta, setAbierta] = useState<Plantilla | null>(null)
  const [nueva, setNueva] = useState(false)
  const [enviando, setEnviando] = useState<Plantilla | null>(null)

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
                    <>
                      <Button variant="ghost" size="sm" aria-label={`Enviar ${p.clave}`}
                              onClick={() => setEnviando(p)}>
                        <Send className="size-4" />
                      </Button>
                      <Button variant="ghost" size="sm" aria-label={`Editar ${p.clave}`}
                              onClick={() => setAbierta(p)}>
                        <Pencil className="size-4" />
                      </Button>
                    </>
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

      {/* No recarga al cerrar: enviar no cambia ninguna plantilla. */}
      <EnviarPlantillaModal
        open={enviando !== null}
        plantilla={enviando}
        onClose={() => setEnviando(null)}
      />
    </>
  )
}
