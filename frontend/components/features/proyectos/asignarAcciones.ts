import { toast } from "sonner"

import { asignarArea, asignarBulk } from "@/services/proyectos"

/** Los datos que TODOS los asignados comparten. El caso particular se ajusta después con el PUT. */
export interface DatosComunes {
  rol: string
  valorHora: string
  fechaDesde: string
  fechaHasta: string
}

function cuerpo(d: DatosComunes) {
  return {
    rol: d.rol.trim(), valor_hora: parseFloat(d.valorHora) || 0,
    fecha_desde: d.fechaDesde || undefined, fecha_hasta: d.fechaHasta || undefined,
  }
}

/**
 * Alta por selección manual. Devuelve true si hay que recargar.
 *
 * 🔴 El mensaje distingue las tres cosas porque el BACKEND las distingue. Antes decía "N no se
 * pudieron (ya asignados o inactivos)" — el texto tenía que adivinar lo que el tipo no separaba.
 */
export async function enviarSeleccion(proyectoId: string, ids: string[], d: DatosComunes): Promise<boolean> {
  try {
    const res = await asignarBulk(proyectoId, { empleado_ids: ids, ...cuerpo(d) })
    const ok = `${res.asignados.length} colaborador${res.asignados.length !== 1 ? "es" : ""} asignado${res.asignados.length !== 1 ? "s" : ""}`
    const yaEstaban = res.ya_asignados.length ? `${res.ya_asignados.length} ya estaban en el proyecto.` : ""
    if (res.errores.length) toast.warning(`${ok}. ${yaEstaban} ${res.errores.length} no se pudieron.`.trim())
    else if (yaEstaban) toast.success(`${ok}. ${yaEstaban}`)
    else toast.success(ok)
    return true
  } catch { toast.error("No se pudo asignar. Intentá de nuevo."); return false }
}

/**
 * Alta del ÁREA ENTERA (foto: se resuelve ahora y no queda vínculo). Devuelve true si recargar.
 *
 * El 422 de área vacía llega con su mensaje propio ("revisá que tengan el área cargada en su
 * ficha"), que es accionable: se muestra tal cual en vez de un texto genérico.
 */
export async function enviarArea(proyectoId: string, areaId: string, d: DatosComunes): Promise<boolean> {
  try {
    const res = await asignarArea(proyectoId, { area_id: areaId, ...cuerpo(d) })
    toast.success(`${res.asignados.length} asignado${res.asignados.length !== 1 ? "s" : ""} del área.`)
    return true
  } catch (e) {
    toast.error(e instanceof Error && e.message ? e.message : "No se pudo asignar el área.")
    return false
  }
}
