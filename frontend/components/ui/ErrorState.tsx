import { AlertTriangle, SearchX } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ApiError } from "@/services/api"

interface ErrorStateProps {
  title?: string
  description?: string
  /** Reintentar. Ante un 404 NO se ofrece: reintentar lo mismo devuelve lo mismo. */
  action?: () => void
  /**
   * La salida: a dónde volver cuando no hay nada que reintentar. Es lo que se ofrece ante un
   * 404. Si la pantalla no declara ninguna, ante un 404 NO SE PINTA BOTÓN — mejor ninguno que
   * uno etiquetado "Volver" que en realidad recarga.
   */
  onVolver?: () => void
  /**
   * El error tal cual lo devolvió la API. Si es un 404, la pantalla cambia entera: otro
   * título, otro mensaje y otro botón. Pasarlo es lo único que cada pantalla tiene que hacer;
   * la decisión vive acá.
   */
  error?: unknown
}

/**
 * 🔴 UN 404 NO ES "ALGO SALIÓ MAL", Y OFRECERLE "REINTENTAR" ES MENTIRLE AL USUARIO: reintentar
 * lo mismo va a devolver lo mismo. Aplanar los dos casos al mismo cartel dejaba a alguien de
 * RRHH apretando un botón que no podía funcionar, sin saber que lo que tenía que hacer era
 * volver.
 *
 * 🔴 Y IMPORTA MÁS DE LO QUE PARECE: el 404 es TAMBIÉN la respuesta cuando el recurso es de
 * OTRA EMPRESA. Es un caso legítimo y frecuente —alguien abre un link viejo con el selector de
 * empresa en otra sociedad— y el contrato de la barrera de empresa dice que "no existe" y "es
 * de otra empresa" se ven IDÉNTICOS, a propósito, para no confirmar la existencia de recursos
 * ajenos. Por eso el mensaje de acá nombra las dos posibilidades sin distinguirlas ("no existe
 * o no está disponible en la empresa seleccionada"): es accionable —decile a alguien que revise
 * el selector— y no delata nada. Un texto que dijera "pertenece a otra empresa" rompería el
 * contrato desde el front.
 */
const NO_ENCONTRADO = {
  title: "No se encontró",
  description:
    "El recurso que buscás no existe o no está disponible en la empresa seleccionada. " +
    "Revisá el selector de empresa o volvé al listado.",
}

const FALLO = {
  title: "Algo salió mal",
  description: "Ocurrió un error inesperado. Intentá de nuevo en unos instantes.",
}

/** ¿La API dijo 404? Solo un ApiError lo puede decir: un string no distingue nada. */
export function esNoEncontrado(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

export function ErrorState({ title, description, action, onVolver, error }: ErrorStateProps) {
  const noEncontrado = esNoEncontrado(error)
  const base = noEncontrado ? NO_ENCONTRADO : FALLO
  const Icono = noEncontrado ? SearchX : AlertTriangle
  // Ante un 404 la única salida honesta es volver. Fuera de un 404 se prefiere reintentar, y
  // volver queda como alternativa para las pantallas que no tienen forma de recargar.
  const salida = noEncontrado
    ? onVolver && { texto: "Volver", al: onVolver }
    : (action && { texto: "Reintentar", al: action }) || (onVolver && { texto: "Volver", al: onVolver })

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center px-4">
      <div
        className={
          noEncontrado
            ? "mb-4 flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground"
            : "mb-4 flex size-14 items-center justify-center rounded-full bg-destructive/10 text-destructive"
        }
      >
        <Icono className="size-7" />
      </div>
      <h3 className="text-base font-semibold text-foreground">{title ?? base.title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">
        {description ?? base.description}
      </p>
      {salida && (
        <Button variant="outline" className="mt-5 min-h-11" onClick={salida.al}>
          {salida.texto}
        </Button>
      )}
    </div>
  )
}
