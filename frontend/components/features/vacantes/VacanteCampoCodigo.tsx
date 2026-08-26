"use client"

import { FieldError } from "@/components/ui/FieldError"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

import { CODIGO_MAX } from "./codigoVacante"

/**
 * El campo del CÓDIGO de la búsqueda. Presentacional: sin estado, sin fetch, sin submit.
 *
 * Vive aparte de `VacanteCamposBase` y no adentro por una razón concreta: lo usan DOS pantallas
 * —el alta y la corrección del código desde la ficha— y son el mismo campo con la misma ayuda.
 * Escribirlo dos veces daría dos textos que se separan, que es el modo de falla que este repo ya
 * pagó con los 81 `<select>` y sus 29 constantes de estilo copiadas.
 *
 * 🔑 LA AYUDA DEBAJO DEL CAMPO NO ES DECORATIVA. El código es lo que el candidato tiene que
 * escribir en el asunto del mail para que su CV se asigne solo, y eso NO se deduce mirando un
 * input vacío rotulado "Código". Sin la línea, alguien pone "1" y se entera un mes después de
 * que las postulaciones caen todas en revisión manual.
 *
 * ⚠️ `autoCapitalize`/`autoCorrect` apagados y `spellCheck={false}`: en un teclado táctil, el
 * autocorrector convierte `ECO-2026` en cualquier cosa. El valor se normaliza igual al guardar,
 * pero lo que se ve mientras se escribe tiene que ser lo que se escribió.
 */
export function VacanteCampoCodigo({ value, error, onChange, ayuda = true }: {
  value: string
  error?: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  /** La ficha ya explica el contexto arriba; ahí la línea de ayuda sería una repetición. */
  ayuda?: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor="codigo">
        Código de la búsqueda
        <span className="ml-0.5 text-destructive" aria-hidden>*</span>
      </Label>
      <Input
        id="codigo"
        value={value}
        onChange={onChange}
        maxLength={CODIGO_MAX}
        placeholder="ECO-2026"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        aria-invalid={Boolean(error)}
        aria-describedby={ayuda ? "codigo-ayuda" : undefined}
        aria-required
      />
      {ayuda && (
        <p id="codigo-ayuda" className="text-[11px] text-muted-foreground">
          Es lo que el candidato escribe entre corchetes en el asunto del mail. Tiene que ser
          único en todo el sistema y no se puede repetir en otra búsqueda.
        </p>
      )}
      {error && <FieldError>{error}</FieldError>}
    </div>
  )
}
