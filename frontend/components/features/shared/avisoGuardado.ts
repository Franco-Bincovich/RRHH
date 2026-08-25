import { toast } from "sonner"

/**
 * La confirmación de que un alta o una edición salió bien.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ CIERRA: **NINGÚN ALTA DEL SISTEMA CONFIRMABA NADA.**
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Medido el 25/8/2026: de los **30 modales de formulario del producto, 29 tenían CERO
 * `toast.success`**. El único era `CesionModal`. El circuito era siempre el mismo —el modal se
 * cierra, la fila aparece en la tabla— y eso alcanza cuando la fila entra en pantalla; no alcanza
 * cuando el listado está paginado, filtrado o en otra pestaña, que es la mitad de los casos. El
 * usuario se quedaba mirando la misma pantalla sin saber si su click hizo algo.
 *
 * Lo llamativo es que los ERRORES sí se mostraban, y `sonner` ya estaba montado: no faltaba
 * infraestructura, faltaba la mitad buena del par. Un producto que sólo habla cuando algo sale
 * mal enseña a desconfiar de él.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * POR QUÉ UN HELPER Y NO 29 `toast.success` A MANO
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Escritos a mano, los 29 mensajes divergen en el primer mes: unos dicen "Guardado", otros
 * "Área creada correctamente", otros el nombre de la fila. Es exactamente lo que pasó con los 44
 * mensajes de error por campo (tres tamaños distintos, ver `FieldError`) y con los 81 `<select>`
 * (29 constantes de estilo copiadas). Con un helper, el vocabulario del producto es uno solo y
 * cambiarlo es un archivo.
 *
 * 🔑 EL GÉNERO ES UN DATO EXPLÍCITO, NO SE ADIVINA. "Área creada" y "Cliente creado" no se
 * pueden derivar de la palabra sin heurísticas que fallan justo con las excepciones del castellano
 * (`el área`, `el ítem`). Pedirlo como parámetro cuesta un carácter por call site y no puede
 * equivocarse.
 *
 * ⚠️ QUÉ **NO** VA ACÁ, y no es un olvido:
 *   · **Los cuatro imports por Excel** (formación, objetivos, nómina de empleados, nómina de
 *     costos). Terminan en un panel de resultado que dice cuántas filas entraron, cuántas se
 *     actualizaron y cuáles fallaron. Un toast encima sería una segunda confirmación más pobre
 *     que la que ya está en pantalla.
 *   · **El alta de usuario.** Su confirmación es `PasswordRevealModal`: la contraseña temporal se
 *     muestra UNA sola vez y hay que copiarla. Un toast compitiendo por la atención ahí es un
 *     riesgo, no una ayuda.
 *   · **Las altas en lote** (asignar empleados a un proyecto, asignar un área entera). Ya avisan
 *     con su clasificación en tres grupos —asignados / ya asignados / errores—, que es más de lo
 *     que este helper puede decir.
 *   · **Los borrados.** Tienen su propio circuito con `ConfirmDialog` y su propio aviso.
 */
export type Genero = "m" | "f"

/**
 * Avisa que la entidad se creó o se actualizó.
 *
 * @param sustantivo Cómo se llama la cosa en el producto, capitalizado: "Área", "Cliente",
 *   "Recordatorio". Es el vocabulario VISIBLE, no el nombre de la tabla — misma regla que
 *   `vocabulario.test.ts` (nunca "Empleado": es "Colaborador").
 * @param genero Gramatical, para concordar el participio. Ver arriba por qué no se deriva.
 * @param esEdicion `true` si la fila ya existía. El texto tiene que distinguirlos: "creada" y
 *   "actualizada" contestan preguntas distintas, y en un modal que hace las dos cosas el usuario
 *   necesita saber cuál pasó (sobre todo cuando abrió el de editar creyendo que era el de crear).
 */
export function avisarGuardado(sustantivo: string, genero: Genero, esEdicion: boolean): void {
  const participio = esEdicion ? "actualizad" : "cread"
  toast.success(`${sustantivo} ${participio}${genero === "f" ? "a" : "o"}`)
}

/** Un acto que no es un alta ni una edición y que igual merece confirmación explícita. */
export function avisarHecho(mensaje: string): void {
  toast.success(mensaje)
}
