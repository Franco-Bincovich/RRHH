"use client"

import { useState } from "react"
import { Mail, Plus } from "lucide-react"

import { EnviarPlantillaModal } from "@/components/features/comunicacion/EnviarPlantillaModal"
import { PlantillaCard } from "@/components/features/comunicacion/PlantillaCard"
import { PlantillaModal } from "@/components/features/comunicacion/PlantillaModal"
import { usePlantillas } from "@/components/features/comunicacion/usePlantillas"
import { EmptyState } from "@/components/ui/EmptyState"
import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { AccionBloqueada } from "@/components/ui/AccionBloqueada"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { useEmpresaConcreta } from "@/hooks/useEmpresaConcreta"
import type { Plantilla } from "@/types/plantillas"

/**
 * Plantillas de mail — pestaña "Plantillas" de /comunicacion.
 *
 * 🔴 ESTE COMPONENTE VIVÍA EN /configuracion Y SE MUDÓ EL 7/8/2026. El argumento de entonces
 * está en el historial de git y era razonable con lo que había: "es el ABM de un texto que se
 * toca dos veces al año, no justifica una pantalla ni una entrada en el sidebar". Lo que lo
 * invalidó no fue una discusión de diseño: fue que desde acá ahora se MANDAN MAILS a la gente
 * (botón "Enviar" por tarjeta). Eso es una acción operativa recurrente, con historial propio y con
 * consecuencias hacia afuera de la empresa — deja de ser configuración.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 AHORA SON TARJETAS, Y SE FUE EL ACORDEÓN.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `docs/SISTEMA-DE-DISENO.md` §5 nombra a comunicación junto a perfiles de puesto y reportes:
 * "cada plantilla de mail guardada, una tarjeta". Hasta el 21/8/2026 esto era una lista de filas
 * envuelta en `ConfigSection` —la shell plegable de /configuracion—, y **este mismo archivo ya
 * anotaba que el acordeón sobraba**: "un acordeón de un solo ítem adentro de una pestaña es
 * redundante y quedó pendiente a propósito; mezclar la mudanza con un rediseño hace que el diff
 * no se pueda revisar". Ése era el diff que faltaba, y es éste.
 *
 * ⚠️ NO HAY FILTROS NI PIE, y no faltan: `GET /api/plantillas` no acepta un solo Query y devuelve
 * la lista entera. Sin filtros no hay chips que mostrar y sin `page` no hay pie que armar —
 * ponerle chips a una pantalla que no filtra sería inventar filtros que el backend no puede
 * honrar.
 *
 * `editable=false` (gerencia_lectura) muestra las plantillas en SOLO LECTURA, con el mismo
 * criterio que las reglas: el texto con el que la empresa se comunica es información, y quien
 * puede leer todos los reportes debería poder verlo. Lo que se oculta son las dos acciones.
 */
export function PlantillasSection({ editable }: { editable: boolean }) {
  const { items, contextos, loading, recargar } = usePlantillas()
  // 🔴 GUARDAR UNA PLANTILLA ES SOBRE UNA EMPRESA (`require_empresa_id` en `routers/plantillas`),
  // así que en la vista consolidada el modal se abriría para fallar con 400 al guardar. Se
  // bloquea el ENTRY POINT y no el botón de guardar del modal: abrir un formulario que no se
  // puede enviar es peor que no poder abrirlo, porque el usuario ya escribió el texto.
  const { motivo: motivoSinEmpresa } = useEmpresaConcreta()
  const [abierta, setAbierta] = useState<Plantilla | null>(null)
  const [nueva, setNueva] = useState(false)
  const [enviando, setEnviando] = useState<Plantilla | null>(null)

  const open = nueva || abierta !== null
  const nuevaBtn = (
    <AccionBloqueada motivo={motivoSinEmpresa}>
      {(bloqueada) => (
        <Button
          variant="outline"
          className="min-h-11 gap-1.5"
          disabled={bloqueada}
          onClick={() => setNueva(true)}
        >
          <Plus className="size-4" />
          Nueva plantilla
        </Button>
      )}
    </AccionBloqueada>
  )

  return (
    <>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <p className="max-w-xl text-sm text-muted-foreground">
          El texto de los mails que el sistema envía. Podés usar variables como el nombre del
          colaborador.
        </p>
        {editable && nuevaBtn}
      </div>

      {loading ? (
        /* El esqueleto son TARJETAS del mismo alto que las reales, con el shimmer de 1,2s que
           pide §3: así la pantalla no cambia de forma cuando llegan los datos. */
        <GrillaTarjetas>
          {[1, 2, 3].map((i) => <Skeleton key={i} shimmer className="h-28 rounded-xl" />)}
        </GrillaTarjetas>
      ) : items.length === 0 ? (
        /*
         * 🔴 COPY PROPIO, no `textoVacio`. Esta pantalla no tiene filtros, así que el helper sólo
         * podría dar su rama genérica —"Cuando se cargue la primera va a aparecer acá"—, y acá esa
         * frase se queda corta en lo único que importa: sin plantillas **el sistema no manda
         * ningún mail**. Eso no es "todavía no hay datos", es una capacidad apagada, y decirlo es
         * lo que hace que alguien cargue la primera. Para `gerencia_lectura`, que no puede
         * crearlas, la frase sigue siendo cierta y no le pide nada.
         */
        <Card padding="sm">
          <EmptyState
            icon={<Mail />}
            title="Todavía no hay plantillas cargadas"
            description="Mientras no haya ninguna, el sistema no tiene con qué escribirle a la gente: los envíos de esta pantalla salen de una plantilla."
            action={editable ? nuevaBtn : undefined}
          />
        </Card>
      ) : (
        <GrillaTarjetas>
          {items.map((p) => (
            <PlantillaCard
              key={p.id}
              plantilla={p}
              editable={editable}
              onEditar={setAbierta}
              bloqueo={motivoSinEmpresa}
              onEnviar={setEnviando}
            />
          ))}
        </GrillaTarjetas>
      )}

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
