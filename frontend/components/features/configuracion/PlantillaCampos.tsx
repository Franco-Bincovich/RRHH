"use client"

import { PlantillaVariables } from "@/components/features/configuracion/PlantillaVariables"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"

export type CampoPlantilla = "clave" | "contexto" | "asunto" | "cuerpo"

interface Props {
  valores: Record<CampoPlantilla, string>
  onCambio: (campo: CampoPlantilla, valor: string) => void
  /** contexto → variables que ese contexto declara. Lo trae el backend con el listado. */
  contextos: Record<string, string[]>
  /**
   * true al EDITAR una plantilla existente: `clave` y `contexto` quedan fijos.
   * No es un capricho de UI — la clave es con lo que el código pide la plantilla al enviarla, y
   * el contexto decide qué variables son válidas. Cambiar cualquiera de los dos no es editar
   * esta plantilla: es crear otra distinta con el texto de ésta.
   */
  bloqueada: boolean
}

/**
 * Los campos del editor de plantillas. Extraído de `PlantillaModal`, que estaba en 142/150 y no
 * tenía margen para el aviso de modo consolidado.
 *
 * El corte es por responsabilidad y no por tamaño: acá está el FORMULARIO (qué campos hay, cuáles
 * se bloquean al editar, y cómo se insertan las variables) y en el modal quedó el DIÁLOGO (abrir,
 * guardar, previsualizar, los errores). Molde: `_campos.tsx`, que ya hace lo mismo con los campos
 * de las reglas de negocio.
 *
 * Presentacional puro: no fetchea, no guarda y no sabe de permisos ni de empresas.
 */
export function PlantillaCampos({ valores, onCambio, contextos, bloqueada }: Props) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="pl-clave">Nombre interno</Label>
          <Input id="pl-clave" value={valores.clave} onChange={(e) => onCambio("clave", e.target.value)}
                 placeholder="bienvenida_empleado" disabled={bloqueada} />
        </div>
        <div>
          <Label htmlFor="pl-ctx">Tipo de mail</Label>
          <select id="pl-ctx" value={valores.contexto} onChange={(e) => onCambio("contexto", e.target.value)}
                  disabled={bloqueada}
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm">
            {Object.keys(contextos).map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      <div>
        <Label htmlFor="pl-asunto">Asunto</Label>
        <Input id="pl-asunto" value={valores.asunto} onChange={(e) => onCambio("asunto", e.target.value)} />
      </div>

      <div>
        <Label htmlFor="pl-cuerpo">Mensaje</Label>
        <Textarea id="pl-cuerpo" rows={10} value={valores.cuerpo}
                  onChange={(e) => onCambio("cuerpo", e.target.value)}
                  placeholder="Hola {{nombre_empleado}}, ..." />
        <p className="mt-1 text-xs text-muted-foreground">
          Podés usar <strong>**negrita**</strong>, *itálica*, listas con “- ” y links
          [texto](https://…).
        </p>
      </div>

      <div>
        <Label>Variables disponibles</Label>
        {/* Insertar concatena al final en vez de en el cursor: el textarea no expone la posición
            sin un ref, y RRHH escribe el mail primero y mete las variables después. */}
        <PlantillaVariables
          variables={contextos[valores.contexto] ?? []}
          onInsertar={(v) => onCambio("cuerpo", `${valores.cuerpo}{{${v}}}`)}
        />
      </div>
    </>
  )
}
