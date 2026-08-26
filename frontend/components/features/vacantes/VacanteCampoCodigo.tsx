"use client"

import { FieldError } from "@/components/ui/FieldError"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

import { normalizarCodigo } from "./codigoVacante"

/**
 * El campo del CÓDIGO de la búsqueda, con la conversión a la vista.
 *
 * Vive aparte de `VacanteCamposBase` y no adentro porque lo usan DOS pantallas —el alta y la
 * corrección del código desde la ficha— y son el mismo campo con la misma ayuda. Escribirlo dos
 * veces daría dos textos que se separan, que es el modo de falla que este repo ya pagó con los
 * 81 `<select>` y sus 29 constantes de estilo copiadas.
 *
 * 🔴 "SE VA A USAR: …" ES LA PIEZA QUE HACE ACEPTABLE LA CONVERSIÓN. Capital Humano escribe
 * `Lider de equipo` y el sistema guarda `LIDER-DE-EQUIPO`: sin mostrarlo, el sistema estaría
 * guardando algo distinto de lo que la persona escribió y sin avisar — peor que rechazarla,
 * porque el rechazo por lo menos se ve. Se muestra SIEMPRE que la conversión dé algo, incluso si
 * coincide con lo tipeado: es el contrato "esto es lo que se guarda", no una advertencia.
 *
 * ⚠️ NO lleva `maxLength`. Sería el mismo pecado en chico: el input recibe TEXTO NATURAL, que es
 * más largo que el código, y cortarlo al tipear frenaría la tecla sin decir por qué. El largo lo
 * valida `validarCodigo` con un mensaje que dice cuántos caracteres sobran.
 *
 * ⚠️ `autoCapitalize`/`autoCorrect` apagados y `spellCheck={false}`: el autocorrector de un
 * teclado táctil "arregla" nombres propios y siglas. El valor se convierte igual al guardar, pero
 * lo que se ve mientras se escribe tiene que ser lo que se escribió.
 */
export function VacanteCampoCodigo({ value, error, onChange, ayuda = true }: {
  value: string
  error?: string
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void
  /** La ficha ya explica el contexto arriba; ahí la línea de ayuda sería una repetición.
   *  La vista previa de la conversión se muestra igual: no es ayuda, es el valor que se guarda. */
  ayuda?: boolean
}) {
  const canonico = normalizarCodigo(value)
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
        placeholder="Líder de equipo"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        aria-invalid={Boolean(error)}
        aria-describedby={ayuda ? "codigo-ayuda" : undefined}
        aria-required
      />
      {canonico && (
        // `aria-live="polite"`: quien usa lector de pantalla tiene que enterarse de la conversión
        // igual que quien la ve, y "polite" no interrumpe cada tecla.
        <p className="text-xs text-muted-foreground" aria-live="polite">
          Se va a usar:{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-foreground">{canonico}</code>
        </p>
      )}
      {ayuda && (
        <p id="codigo-ayuda" className="text-[11px] text-muted-foreground">
          Escribilo como te salga —&laquo;Líder de equipo&raquo;— y el sistema lo convierte. Es lo
          que el candidato escribe en el asunto del mail, y no se puede repetir en otra búsqueda.
        </p>
      )}
      {error && <FieldError>{error}</FieldError>}
    </div>
  )
}
