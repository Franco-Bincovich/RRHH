import { AlertCircle } from "lucide-react"

/**
 * El PRIMER nivel de la validación en dos niveles del patrón de modal de formulario
 * (`docs/SISTEMA-DE-DISENO.md` §3): el banner de resumen, arriba, **con la cuenta**.
 *
 * 🔴 POR QUÉ LA CUENTA Y NO LA LISTA DE CAMPOS. El banner contesta "¿cuánto me falta?" de un
 * vistazo; el "¿qué corrijo?" lo contesta el segundo nivel, en cada campo, que es donde el
 * usuario ya tiene el ojo puesto cuando arregla. Un banner que repite los siete mensajes obliga
 * a leer dos veces lo mismo y, en un modal que scrollea, empuja el primer campo fuera de la
 * pantalla — justo el que hay que arreglar.
 *
 * 🔴 POR QUÉ HACE FALTA IGUAL. Sin él, en un formulario de 30 campos con dos secciones, el único
 * indicio de que algo falló es un borde rojo que puede estar abajo del scroll: se aprieta
 * "Guardar", no pasa nada visible, y la lectura razonable es que el sistema está roto.
 *
 * `role="alert"` para que el lector de pantalla lo anuncie al aparecer, que es el mismo momento
 * en que el usuario vidente ve el borde rojo.
 */
export function FormErrores({ cantidad }: { cantidad: number }) {
  if (cantidad === 0) return null

  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-md border border-danger-line bg-danger-wash px-3 py-2 text-xs text-destructive"
    >
      <AlertCircle className="mt-px size-4 shrink-0" aria-hidden="true" />
      <span>
        <strong className="font-semibold tabular-nums">
          Revisá {cantidad} {cantidad === 1 ? "campo" : "campos"}
        </strong>{" "}
        antes de guardar.
      </span>
    </div>
  )
}
