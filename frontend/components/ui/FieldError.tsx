import type { ReactNode } from "react"

/**
 * El SEGUNDO nivel de la validación en dos niveles del patrón de modal de formulario
 * (`docs/SISTEMA-DE-DISENO.md` §3): el mensaje POR CAMPO, que dice **qué corregir**.
 * El primero es `FormErrores`, el banner de resumen con la cuenta.
 *
 * 🔴 MIDE 11px, Y ESTABA ESCRITO A MANO EN 44 LUGARES CON TRES TAMAÑOS DISTINTOS. §3 dice
 * 11px; el repo tenía `text-sm` (14px) en 8 sitios, `text-xs` (12px) en 32 y el `text-[11px]`
 * correcto sólo en los 4 del modal de empleado — o sea que el mismo mensaje medía distinto
 * según el formulario, y el más grande competía visualmente con la etiqueta del campo. Es el
 * mismo modo de falla que ya había pasado con los `<select>`: una constante de estilo copiada
 * entre archivos diverge sola. Migrar sin dejar un barrido no cierra nada — el próximo campo
 * nuevo nace con `text-sm` en el próximo PR. Lo vigila `components/ui/fieldError.test.tsx`.
 *
 * 🔑 DEVUELVE null CON CONTENIDO VACÍO, y por eso el consumidor no necesita su propio
 * condicional: `<FieldError>{errors.nombre}</FieldError>` no pinta nada cuando no hay error.
 * Los `{errors.x && ...}` que ya existen siguen siendo correctos (redundantes, no dañinos).
 *
 * `role="alert"` para que el lector de pantalla lo anuncie al aparecer, que es el mismo momento
 * en que el usuario vidente ve el borde rojo. `id` para poder colgarlo de un `aria-describedby`
 * del campo, como hace `components/ui/select.tsx`.
 */
export function FieldError({ id, children }: { id?: string; children?: ReactNode }) {
  if (!children) return null

  return (
    <p id={id} role="alert" className="mt-1 text-[11px] text-destructive">
      {children}
    </p>
  )
}
