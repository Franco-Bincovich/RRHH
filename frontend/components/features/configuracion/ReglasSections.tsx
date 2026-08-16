"use client"

import { useEffect, useState } from "react"
import { Percent } from "lucide-react"

import { AvisosReglas } from "@/components/features/configuracion/AvisosReglas"
import { CampoNumero } from "@/components/features/configuracion/_campos"
import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { useConfiguracion } from "@/components/features/configuracion/useConfiguracion"
import { VacacionesReglas } from "@/components/features/configuracion/VacacionesReglas"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import type { Parametros, TramoEscala } from "@/types/configuracion"

/**
 * Las reglas de negocio configurables: Vacaciones, Ausentismo y Avisos.
 *
 * 🔑 LAS TRES SECCIONES COMPARTEN UN SOLO BORRADOR, y por eso viven bajo un mismo componente
 * aunque en pantalla sean tres bloques del acordeón: los NUEVE valores son UNA fila de
 * parametros_empresa y se guardan con un PUT del juego completo. Con un borrador por sección,
 * guardar en una pisaría con valores viejos lo que la otra acababa de cambiar — y con la tercera
 * (migración 114) eso dejó de ser hipotético: guardar la base de días hábiles mandaría el
 * período de prueba viejo, y el usuario vería revertirse algo que acababa de escribir.
 *
 * ⚠️ Los encabezados se renderizan SIEMPRE, aun cargando o con error, y el estado ocupa el
 * cuerpo. Devolver un Skeleton suelto en vez de las secciones metía un hijo que no es
 * Accordion.Item dentro del Accordion.Root, y además hacía aparecer y desaparecer bloques
 * del acordeón mientras carga.
 *
 * `editable` viene de afuera: quién puede escribir lo decide la página, no este componente.
 */
export function ReglasSections({ editable }: { editable: boolean }) {
  const { config, loading, error, ocupado, guardarParametros, guardarEscala } = useConfiguracion()
  const [params, setParams] = useState<Parametros | null>(null)
  const [tramos, setTramos] = useState<TramoEscala[]>([])

  // El borrador se resincroniza con cada recarga —incluida la de después de guardar— para que
  // lo que se ve sea lo que quedó persistido y no lo que se tipeó.
  useEffect(() => {
    if (!config) return
    const { es_propia: _ignorado, ...valores } = config.parametros
    setParams(valores)
    setTramos(config.escala.tramos)
  }, [config])

  const fallback = loading ? (
    <Skeleton className="h-20 w-full" />
  ) : (
    <p className="text-sm text-muted-foreground">
      No se pudo cargar la configuración.
      {error && " Si es la primera vez, puede que falte correr la migración 085."}
    </p>
  )

  const onCampo = (campo: keyof Parametros, valor: number) =>
    setParams((p) => (p ? { ...p, [campo]: valor } : p))

  return (
    <>
      <VacacionesReglas
        params={params}
        fallback={fallback}
        onCampo={onCampo}
        tramos={tramos}
        onTramos={setTramos}
        escalaPropia={config?.escala.es_propia ?? false}
        editable={editable}
        guardandoParams={Boolean(ocupado.parametros)}
        guardandoEscala={Boolean(ocupado.escala)}
        onGuardarParams={() => params && guardarParametros(params)}
        onGuardarEscala={() => guardarEscala(tramos)}
      />

      <ConfigSection
        value="ausentismo"
        icon={<Percent className="size-5 text-primary" />}
        title="Ausentismo"
        description="Base de días hábiles con la que se calculan las tasas de ausentismo."
      >
        {!params ? fallback : (
          <div className="space-y-4">
            <CampoNumero
              id="base-dias-habiles"
              etiqueta="Días hábiles por mes"
              ayuda="Denominador de las tasas: días de ausencia ÷ (este número × dotación). Aparece escrito en el reporte de ausentismo y en el KPI del dashboard."
              editable={editable}
              valor={params.base_dias_habiles}
              onChange={(v) => onCampo("base_dias_habiles", v)}
              min={1}
              max={31}
              sufijo="días"
            />
            {editable && (
              <Button
                onClick={() => guardarParametros(params)}
                disabled={Boolean(ocupado.parametros)}
              >
                {ocupado.parametros ? "Guardando…" : "Guardar"}
              </Button>
            )}
          </div>
        )}
      </ConfigSection>

      <AvisosReglas
        params={params}
        fallback={fallback}
        onCampo={onCampo}
        editable={editable}
        guardando={Boolean(ocupado.parametros)}
        onGuardar={() => params && guardarParametros(params)}
      />
    </>
  )
}
