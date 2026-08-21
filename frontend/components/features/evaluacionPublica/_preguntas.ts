export interface PreguntaLikert { id: number; texto: string }
export interface Opcion { id: number; texto: string }
export interface PreguntaMultiple { id: number; texto: string; opciones: Opcion[] }

/**
 * El cuestionario de la evaluación pública, y los tres pasos en los que se recorre.
 *
 * Vivía adentro de `app/evaluacion/[token]/page.tsx`, que estaba en 258 líneas contra un límite de
 * 150 —el segundo archivo más grande del front después de la ficha de vacantes—. Se sacó al cortar
 * esa página.
 *
 * 🔴 LAS PREGUNTAS ESTÁN EN EL FRONT Y NO EN LA BASE, y eso es una decisión heredada que conviene
 * conocer antes de tocarlas: el backend recibe `{tipo, pregunta_id, respuesta}` y no valida contra
 * ningún catálogo, así que **el `id` de cada pregunta es el contrato**. Reordenar el array no
 * rompe nada; cambiarle el `id` a una pregunta sí: las respuestas ya guardadas quedan apuntando a
 * un texto que ya no es el que se contestó. Agregar preguntas al final es seguro.
 *
 * ⚠️ El módulo de assessment está APAGADO (`ASSESSMENT_ENABLED=false`): el router del backend no se
 * monta y estas dos rutas públicas salen de `PUBLIC_ROUTES`, así que hoy el link devuelve el 404
 * de plataforma. El código está entero y esto se mantiene igual.
 */
export const PREGUNTAS_SELF: PreguntaLikert[] = [
  { id: 1, texto: "Me adapto fácilmente a situaciones nuevas e impredecibles." },
  { id: 2, texto: "Suelo terminar lo que comienzo, incluso cuando resulta difícil." },
  { id: 3, texto: "Me mantengo calmado/a bajo presión o en situaciones de tensión." },
  { id: 4, texto: "Disfruto trabajar en equipo priorizando las necesidades del grupo." },
  { id: 5, texto: "Tomo la iniciativa cuando hay un problema que nadie está resolviendo." },
]

export const PREGUNTAS_COGNITIVAS: PreguntaMultiple[] = [
  { id: 1, texto: "¿Cuál es el siguiente número en la serie? 2, 6, 12, 20, 30, …",
    opciones: [{ id: 1, texto: "40" }, { id: 2, texto: "42" }, { id: 3, texto: "44" }, { id: 4, texto: "46" }] },
  { id: 2, texto: "Si todos los A son B, y algunos B son C, ¿qué podemos concluir?",
    opciones: [{ id: 1, texto: "Todos los A son C" }, { id: 2, texto: "Algunos A pueden ser C" }, { id: 3, texto: "Ningún A es C" }, { id: 4, texto: "Todos los C son A" }] },
  { id: 3, texto: "Un cuadrado se divide en 4 triángulos iguales y cada triángulo en 2. ¿Cuántos triángulos hay en total?",
    opciones: [{ id: 1, texto: "4" }, { id: 2, texto: "6" }, { id: 3, texto: "8" }, { id: 4, texto: "12" }] },
]

export const PREGUNTAS_TECNICAS: PreguntaMultiple[] = [
  { id: 1, texto: "¿Qué es el 'product backlog' en metodología Scrum?",
    opciones: [{ id: 1, texto: "El historial de versiones del producto" }, { id: 2, texto: "Lista priorizada de funcionalidades pendientes" }, { id: 3, texto: "Los errores encontrados en producción" }, { id: 4, texto: "El equipo de desarrollo del producto" }] },
  { id: 2, texto: "¿Cuál es la diferencia principal entre REST API y GraphQL?",
    opciones: [{ id: 1, texto: "REST usa HTTP, GraphQL usa WebSockets" }, { id: 2, texto: "GraphQL permite solicitar exactamente los datos necesarios" }, { id: 3, texto: "REST es siempre más rápido que GraphQL" }, { id: 4, texto: "GraphQL solo funciona con JavaScript" }] },
]

export const PASOS = [
  { label: "Self Assessment", ayuda: "Evaluá cada afirmación según tu nivel de acuerdo del 1 (muy en desacuerdo) al 5 (muy de acuerdo).", total: PREGUNTAS_SELF.length },
  { label: "Evaluación Cognitiva", ayuda: "Seleccioná la respuesta correcta para cada pregunta.", total: PREGUNTAS_COGNITIVAS.length },
  { label: "Evaluación Técnica", ayuda: "Respondé las siguientes preguntas sobre metodología y tecnología.", total: PREGUNTAS_TECNICAS.length },
]

export const ETIQUETAS_LIKERT = ["Muy en desacuerdo", "En desacuerdo", "Neutral", "De acuerdo", "Muy de acuerdo"]

/**
 * Cuántas preguntas del paso quedan sin contestar.
 *
 * 🔴 EXISTE PARA QUE EL BOTÓN DESHABILITADO DEJE DE SER MUDO. "Siguiente" se apaga hasta que el
 * paso esté completo, que es la forma correcta de evitar el error —prevenir en vez de corregir—,
 * pero un botón apagado sin motivo es el mismo problema que un formulario que no responde al
 * enviarse: la lectura razonable es que la pantalla está rota. Con cinco preguntas y un teléfono,
 * la que falta puede estar arriba del scroll.
 *
 * Es una CUENTA derivada de las respuestas, no un mensaje de validación: esta pantalla no tiene
 * mensajes por campo —no hay campo que pueda estar mal, sólo sin contestar— así que tampoco lleva
 * el banner `FormErrores`, que diría "Revisá 0 campos".
 */
export function faltanEnPaso(ids: number[], respuestas: Record<number, number>): number {
  return ids.filter((id) => respuestas[id] === undefined).length
}
