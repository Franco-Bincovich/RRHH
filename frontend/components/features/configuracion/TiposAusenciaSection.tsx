"use client"

import { useState } from "react"
import { ListChecks, Plus } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { TipoAusenciaFila } from "@/components/features/configuracion/TipoAusenciaFila"
import { useTiposAusencia } from "@/components/features/configuracion/useTiposAusencia"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * Catálogo de tipos de ausencia: alta, renombre, baja lógica y la política de ausentismo.
 *
 * ⚠️ `cuenta_ausentismo` (de acá) y `justificada` (del formulario de cada ausencia) son
 * ORTOGONALES, no dos nombres de lo mismo. Este flag dice si el TIPO computa en la tasa;
 * `justificada` dice si ESA vez hubo certificado. Una licencia por maternidad puede estar
 * justificada y aun así no computar como ausentismo.
 */
export function TiposAusenciaSection({ editable }: { editable: boolean }) {
  const { tipos, loading, ocupado, editar, crear } = useTiposAusencia()
  const [nuevo, setNuevo] = useState("")

  const agregar = async () => {
    if (!nuevo.trim()) return
    if (await crear(nuevo.trim())) setNuevo("")
  }

  return (
    <ConfigSection
      value="tipos-ausencia"
      icon={<ListChecks className="size-5 text-primary" />}
      title="Tipos de ausencia"
      description="Qué tipos se pueden elegir al cargar una ausencia y cuáles computan en la tasa de ausentismo."
    >
      {loading ? (
        <Skeleton className="h-20 w-full" />
      ) : (
        <div className="space-y-4">
          <ul className="divide-y text-sm" role="list">
            {tipos.map((t) => (
              <TipoAusenciaFila
                key={t.id}
                tipo={t}
                editable={editable}
                ocupado={Boolean(ocupado[t.id])}
                onEditar={(cambios) => editar(t.id, cambios)}
              />
            ))}
          </ul>

          {editable && (
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Input
                  aria-label="Nombre del tipo nuevo"
                  placeholder="Nombre del tipo nuevo"
                  value={nuevo}
                  onChange={(e) => setNuevo(e.target.value)}
                />
              </div>
              <Button onClick={agregar} disabled={Boolean(ocupado.nuevo) || !nuevo.trim()}>
                <Plus className="mr-2 size-4" />
                {ocupado.nuevo ? "Agregando…" : "Agregar"}
              </Button>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Dar de baja un tipo lo saca de los formularios pero{" "}
            <strong>no borra nada</strong>: las ausencias ya cargadas lo siguen mostrando.
          </p>
        </div>
      )}
    </ConfigSection>
  )
}
