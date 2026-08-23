"use client"

import type { ReactNode } from "react"
import { BellRing } from "lucide-react"

import { CampoNumero } from "@/components/features/configuracion/_campos"
import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { Button } from "@/components/ui/button"
import type { Parametros } from "@/types/configuracion"

export interface AvisosReglasProps {
  /** null mientras carga o si falló: el encabezado igual se renderiza, y `fallback` ocupa el
   *  cuerpo. Devolver null entero haría aparecer y desaparecer bloques del acordeón. */
  params: Parametros | null
  fallback: ReactNode
  onCampo: (campo: keyof Parametros, valor: number) => void
  editable: boolean
  guardando: boolean
  onGuardar: () => void
}

/**
 * Los dos parámetros de la migración 114: período de prueba y aviso por defecto de los eventos.
 *
 * 🔑 SECCIÓN PROPIA Y NO DENTRO DE "VACACIONES", aunque los nueve valores sean UNA fila de
 * `parametros_empresa` y viajen en el mismo PUT. Lo que agrupa un bloque del acordeón es de qué
 * habla, no en qué tabla vive: meter "avisar 7 días antes de un evento" entre la escala por
 * antigüedad y el vencimiento de días haría que nadie lo encuentre. El borrador SÍ es
 * compartido, y por eso este componente no tiene estado: lo recibe de `ReglasSections`.
 *
 * ⚠️ LOS DOS SON DE FAMILIAS DISTINTAS y están juntos igual, porque los dos son "cuándo el
 * sistema tiene que avisar de algo". El período de prueba todavía no lo consume nadie —se guarda
 * y se muestra—, y el aviso de eventos sí: es el default que toma un evento nuevo sin
 * `dias_aviso` propio. La ayuda de cada campo lo dice, para que nadie configure el primero
 * esperando una notificación que no existe.
 */
export function AvisosReglas(p: AvisosReglasProps) {
  return (
    <ConfigSection
      value="avisos"
      icon={<BellRing className="size-5 text-primary" />}
      title="Avisos y período de prueba"
      description="Con cuánta anticipación avisan los recordatorios de la agenda y cuánto dura el período de prueba."
    >
      {!p.params ? p.fallback : (
        <div className="space-y-4">
          <CampoNumero
            id="dias-aviso-evento"
            etiqueta="Avisar recordatorios con"
            ayuda="Días de anticipación con los que un recordatorio de la agenda aparece en el dashboard. Es el valor por defecto: cada recordatorio puede pisarlo con el suyo, y cambiar esto afecta a los NUEVOS, no a los ya cargados."
            editable={p.editable}
            valor={p.params.dias_aviso_evento}
            onChange={(v) => p.onCampo("dias_aviso_evento", v)}
            min={0}
            max={365}
            sufijo="días"
          />
          <CampoNumero
            id="periodo-prueba"
            etiqueta="Período de prueba"
            ayuda="Días desde el ingreso. La LCT fija 90."
            editable={p.editable}
            valor={p.params.periodo_prueba_dias}
            onChange={(v) => p.onCampo("periodo_prueba_dias", v)}
            min={1}
            max={730}
            sufijo="días"
          />

          {/* Mismo criterio que el aviso de la ventana vacacional: decirlo es peor que callarlo
              solo si uno prefiere que alguien lo configure, asuma que el sistema lo aplica, y
              se entere el día que no pasó nada. */}
          <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
            El período de prueba por ahora es <strong>informativo</strong>: se guarda, pero
            todavía no hay ningún aviso ni cálculo que lo use.
          </p>

          {p.editable && (
            <Button onClick={p.onGuardar} disabled={p.guardando}>
              {p.guardando ? "Guardando…" : "Guardar"}
            </Button>
          )}
        </div>
      )}
    </ConfigSection>
  )
}
