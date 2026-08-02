import { toast } from "sonner"

import { guardarEscala, guardarParametros } from "@/services/configuracion"
import type { Parametros, TramoEscala } from "@/types/configuracion"

/*
 * Las escrituras de configuración, sin React. Mismo criterio que accionesIntegracion: no
 * tocan estado, así que fuera del hook se leen y se testean sin montar nada.
 *
 * El mensaje de error sale del backend cuando lo trae (`ESCALA_TRAMOS_DUPLICADOS` explica
 * cuál es el tramo repetido); el texto genérico es el último recurso, no el primero.
 */

function avisar(e: unknown, generico: string): void {
  const msg = e instanceof Error && e.message ? e.message : generico
  toast.error(msg)
}

export async function guardarParametrosConAviso(
  datos: Parametros,
  recargar: () => Promise<void>,
): Promise<boolean> {
  try {
    await guardarParametros(datos)
    await recargar()
    toast.success("Reglas guardadas.")
    return true
  } catch (e) {
    avisar(e, "No se pudieron guardar las reglas. Intentá de nuevo.")
    return false
  }
}

export async function guardarEscalaConAviso(
  tramos: TramoEscala[],
  recargar: () => Promise<void>,
): Promise<boolean> {
  try {
    await guardarEscala(tramos)
    await recargar()
    toast.success(
      tramos.length === 0
        ? "Escala propia quitada: vuelve a regir la escala general."
        : "Escala guardada.",
    )
    return true
  } catch (e) {
    avisar(e, "No se pudo guardar la escala. Intentá de nuevo.")
    return false
  }
}
