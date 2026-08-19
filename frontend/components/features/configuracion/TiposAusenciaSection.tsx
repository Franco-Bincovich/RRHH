"use client"

import { useState } from "react"
import { ListChecks, Plus } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { TipoAusenciaFila } from "@/components/features/configuracion/TipoAusenciaFila"
import { candidatosAPadre, ordenarPorJerarquia } from "@/components/features/configuracion/tiposJerarquia"
import { useTiposAusencia } from "@/components/features/configuracion/useTiposAusencia"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Select } from "@/components/ui/select"

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
  const [padre, setPadre] = useState("")

  const agregar = async () => {
    if (!nuevo.trim()) return
    // `padre` vacío = tipo de primer nivel. Con valor, crea un SUBTIPO de ese padre (mig 088).
    if (await crear(nuevo.trim(), padre || undefined)) { setNuevo(""); setPadre("") }
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
            {ordenarPorJerarquia(tipos).map(({ tipo: t, hijo }) => (
              <TipoAusenciaFila
                key={t.id}
                tipo={t}
                editable={editable}
                ocupado={Boolean(ocupado[t.id])}
                onEditar={(cambios) => editar(t.id, cambios)}
                indentado={hijo}
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
              {/* El selector ofrece SOLO tipos de primer nivel (`candidatosAPadre`): así la
                  profundidad 2 se respeta por construcción y el 422 del backend no se ve nunca. */}
              <Select
                size="sm" className="w-auto"
                aria-label="Colgar de un tipo (opcional)"
                value={padre}
                onChange={(e) => setPadre(e.target.value)}
              >
                <option value="">Tipo general</option>
                {candidatosAPadre(tipos).map((t) => (
                  <option key={t.id} value={t.id}>Subtipo de {t.nombre}</option>
                ))}
              </Select>
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
