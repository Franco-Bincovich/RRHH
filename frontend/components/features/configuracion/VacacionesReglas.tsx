"use client"

import type { ReactNode } from "react"
import { CalendarDays } from "lucide-react"

import { CampoMes, CampoNumero } from "@/components/features/configuracion/_campos"
import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { EscalaAntiguedad } from "@/components/features/configuracion/EscalaAntiguedad"
import { Badge } from "@/components/ui/badge"
import { AccionBloqueada } from "@/components/ui/AccionBloqueada"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import type { Parametros, TramoEscala } from "@/types/configuracion"

export interface VacacionesReglasProps {
  /** null mientras carga o si falló: el encabezado igual se renderiza, y `fallback` ocupa el
   *  cuerpo. Devolver null entero haría aparecer y desaparecer bloques del acordeón. */
  params: Parametros | null
  fallback: ReactNode
  onCampo: (campo: keyof Parametros, valor: number) => void
  tramos: TramoEscala[]
  onTramos: (t: TramoEscala[]) => void
  escalaPropia: boolean
  editable: boolean
  /** Por qué HOY no se puede guardar (vista consolidada), o `null`. Lo decide la página. */
  motivoBloqueo: string | null
  guardandoParams: boolean
  guardandoEscala: boolean
  onGuardarParams: () => void
  onGuardarEscala: () => void
}

/** Las 5 reglas de vacaciones: escala, corte de antigüedad, ventana para tomarlas,
 *  primer año y vencimiento. */
export function VacacionesReglas(p: VacacionesReglasProps) {
  return (
    <ConfigSection
      value="vacaciones"
      icon={<CalendarDays className="size-5 text-primary" />}
      title="Vacaciones"
      description="Escala por antigüedad, cuándo se pueden tomar, primer año y vencimiento."
      badge={!p.escalaPropia && (
        <Badge variant="outline" className="ml-auto">Escala general</Badge>
      )}
    >
      {!p.params ? p.fallback : (
      <div className="space-y-5">
        <div>
          <h3 className="mb-2 text-sm font-medium">Días por antigüedad</h3>
          <EscalaAntiguedad tramos={p.tramos} onChange={p.onTramos} editable={p.editable} />
          {p.editable && (
            <AccionBloqueada motivo={p.motivoBloqueo} className="mt-3">
              {(bloqueada) => (
                <Button size="sm" onClick={p.onGuardarEscala} disabled={bloqueada || p.guardandoEscala}>
                  {p.guardandoEscala ? "Guardando…" : "Guardar escala"}
                </Button>
              )}
            </AccionBloqueada>
          )}
        </div>

        <Separator />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <CampoMes
            id="corte-antiguedad"
            etiqueta="Mes de corte de antigüedad"
            ayuda="Mes contra el que se mide la antigüedad para ubicar a cada persona en la escala."
            editable={p.editable}
            valor={p.params.corte_antiguedad_mes}
            onChange={(v) => p.onCampo("corte_antiguedad_mes", v)}
          />
          <CampoNumero
            id="vencimiento"
            etiqueta="Vencimiento"
            ayuda="Años que sobreviven los días no tomados antes de vencer."
            editable={p.editable}
            valor={p.params.vencimiento_anios}
            onChange={(v) => p.onCampo("vencimiento_anios", v)}
            min={1}
            max={20}
            sufijo="años"
          />
          <CampoMes
            id="vac-desde"
            etiqueta="Se pueden tomar desde"
            editable={p.editable}
            valor={p.params.periodo_vacacional_desde_mes}
            onChange={(v) => p.onCampo("periodo_vacacional_desde_mes", v)}
          />
          <CampoMes
            id="vac-hasta"
            etiqueta="Hasta"
            editable={p.editable}
            valor={p.params.periodo_vacacional_hasta_mes}
            onChange={(v) => p.onCampo("periodo_vacacional_hasta_mes", v)}
          />
        </div>

        {/* El aviso es literal porque la alternativa es peor: alguien configura la ventana,
            asume que el sistema la hace cumplir, y las licencias fuera de rango entran igual
            sin que nadie se entere. Sale cuando se defina si bloquea o solo avisa. */}
        <p className="rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
          Por ahora esta ventana es <strong>informativa</strong>: el sistema la guarda pero
          todavía no impide cargar licencias fuera de ella.
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <CampoMes
            id="primer-anio-mes"
            etiqueta="Primer año: ingresos desde"
            ayuda="Quien ingresa a partir de este mes recibe los días de al lado en su primer año."
            editable={p.editable}
            valor={p.params.primer_anio_mes_corte}
            onChange={(v) => p.onCampo("primer_anio_mes_corte", v)}
          />
          <CampoNumero
            id="primer-anio-dias"
            etiqueta="Primer año: días"
            editable={p.editable}
            valor={p.params.primer_anio_dias}
            onChange={(v) => p.onCampo("primer_anio_dias", v)}
            min={0}
            max={365}
            sufijo="días"
          />
        </div>

        {p.editable && (
          <AccionBloqueada motivo={p.motivoBloqueo}>
            {(bloqueada) => (
              <Button onClick={p.onGuardarParams} disabled={bloqueada || p.guardandoParams}>
                {p.guardandoParams ? "Guardando…" : "Guardar reglas"}
              </Button>
            )}
          </AccionBloqueada>
        )}
      </div>
      )}
    </ConfigSection>
  )
}
