import type { DatoClave } from "@/components/ui/FichaIdentidad"
import { formatFecha } from "@/components/features/shared/fechas"
import type { ResultadoDetalle } from "@/types/assessment"

/**
 * Los CUATRO datos clave de la barra de identidad del RESULTADO de un assessment
 * (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 POR QUÉ ESTOS CUATRO. El título es la persona evaluada y todo lo que hay debajo son sus
 * puntajes. Lo que falta para poder leerlos —y lo que la barra contesta— es **de qué medición
 * son**: sin eso, un radar es un dibujo sin contexto.
 *
 *   · **Empresa** — de qué sociedad del grupo salió la campaña. Es multiempresa.
 *   · **Área** — para qué área se midió.
 *   · **Posición objetivo** — CONTRA QUÉ se midió. Es el dato que más cambia la lectura: los
 *     mismos puntajes se leen distinto si el objetivo era un rol de conducción o uno técnico.
 *   · **Completado** — cuándo. Un assessment de hace dos años no describe a la misma persona, y
 *     esa es la única forma de darse cuenta.
 *
 * Qué quedó afuera y por qué, para no rediscutirlo:
 *   · **Tipo** (completo / conductual / cognitivo) — es el subtítulo, debajo del nombre.
 *   · **Perfil dominante** y **score general** — son los dos chips, al lado del título. No son
 *     "de qué medición es": son el resultado, y el resultado tiene que leerse a la altura del
 *     nombre, no en la línea de metadatos.
 *   · **Cuántas preguntas respondió / cuánto tardó** — no llegan en el resultado.
 */
export function datosClaveAssessment(resultado: ResultadoDetalle): DatoClave[] {
  return [
    { label: "Empresa", valor: resultado.empresa_nombre ?? "—" },
    { label: "Área", valor: resultado.area_nombre ?? "—" },
    // "Sin definir" y no "—": una campaña puede correrse sin posición objetivo a propósito
    // (`posicion_objetivo` es opcional en el alta), así que el vacío acá es una decisión de quien
    // la creó y no un dato que falte cargar.
    { label: "Posición objetivo", valor: resultado.posicion_objetivo || "Sin definir" },
    // "Sin completar" es el estado REAL de un link que se envió y nadie respondió: `null` en
    // `fecha_completado` no es un dato faltante, es que todavía no pasó.
    {
      label: "Completado",
      valor: resultado.fecha_completado ? formatFecha(resultado.fecha_completado) : "Sin completar",
    },
  ]
}
