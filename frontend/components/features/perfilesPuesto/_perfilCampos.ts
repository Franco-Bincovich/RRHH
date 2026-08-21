import type {
  CampoPerfil, CamposPerfilResponse, OpcionPerfil, PerfilPuesto, PerfilPuestoUpdate,
} from "@/types/perfilPuesto"

/**
 * Las cuatro decisiones puras que hacen falta para construir el formulario CONTRA el endpoint
 * `/campos` en vez de contra una lista escrita en el front: qué vocabulario le toca a un select,
 * dónde arranca el bloque de requisitos, con qué valores nace el formulario y cómo se arma el
 * body que se manda.
 *
 * 🔴 VIVEN ACÁ Y NO EN EL COMPONENTE porque son las cuatro cosas que hay que poder DESMENTIR, y
 * el formulario se monta adentro de un `Dialog` (portal): con vitest sin jsdom,
 * `renderToStaticMarkup` de un modal devuelve `""`. Un test del modal pasaría con el formulario
 * entero borrado. Mismo motivo por el que `guardarCliente` está afuera de `ClienteModal`.
 */

/**
 * El vocabulario cerrado que le corresponde a un campo de tipo `select`.
 *
 * ⚠️ ESTE MAPA ES LA ÚNICA PIEZA DEL FORMULARIO QUE SABE NOMBRES DE CAMPOS, y no se puede evitar
 * desde este lado: el endpoint dice que `modalidad` es un `select`, pero NO dice cuál de los tres
 * vocabularios que devuelve le toca. Los nombres de las claves de la respuesta y los de los
 * campos no coinciden (`modalidad` → `modalidades`, `tipo_contrato` → `tipos_contrato`,
 * `nivel` → `niveles`), así que tampoco alcanza con pluralizar.
 *
 * 🔴 QUÉ PASA CON UN SELECT NUEVO QUE EL BACKEND AGREGUE Y QUE NO ESTÉ ACÁ: devuelve `[]`, y el
 * formulario lo dibuja como campo de TEXTO (ver `PerfilFormCampos`). Es la degradación correcta:
 * el campo sigue siendo visible y editable, y si el valor no pertenece al `Literal` el backend
 * responde 422 nombrando el campo. La alternativa —un `<select>` sin opciones— sería un control
 * imposible de usar que además no dice qué le falta.
 */
export function vocabularioDe(campo: string, catalogos: CamposPerfilResponse): OpcionPerfil[] {
  const porCampo: Record<string, OpcionPerfil[]> = {
    modalidad: catalogos.modalidades,
    tipo_contrato: catalogos.tipos_contrato,
    nivel: catalogos.niveles,
  }
  return porCampo[campo] ?? []
}

/** La etiqueta legible de un valor de vocabulario. Un valor sin etiqueta se muestra crudo antes
 *  que en blanco: el catálogo puede no haber llegado todavía. */
export function etiquetaDe(opciones: OpcionPerfil[], valor: string | null): string {
  if (!valor) return ""
  return opciones.find((o) => o.value === valor)?.label ?? valor
}

/**
 * Los cuatro campos que el aviso real mete bajo un solo título "Requisitos".
 *
 * ⚠️ La lista está acá y no en la respuesta del endpoint porque el backend hoy no declara a qué
 * bloque pertenece cada campo. Es el único acoplamiento por nombre además del mapa de arriba, y
 * lo que compra es concreto: saber ANTES de cuál de los campos va la nota.
 */
const CAMPOS_REQUISITOS = ["experiencia", "formacion", "conocimientos_tecnicos", "requisitos"]

/**
 * Índice del campo ARRIBA del cual va `nota_requisitos`.
 *
 * 🔴 LA NOTA VA ARRIBA DEL BLOQUE, NO EN UN TOOLTIP, y no es una preferencia de estilo: el
 * backend lo declara así en `schemas/_perfil_puesto_campos.py` con el porqué. Un tooltip se lee
 * DESPUÉS de haber escrito; para entonces Capital Humano ya pegó el bloque "Requisitos" entero
 * del aviso dentro de un solo campo y dejó los otros tres vacíos — que es el modo de falla que
 * este módulo tiene documentado, y la razón por la que las columnas están separadas.
 *
 * 🔴 SI NINGUNO DE LOS CUATRO CAMPOS ESTÁ, DEVUELVE 0 Y LA NOTA VA AL PRINCIPIO. Nunca devuelve
 * `-1` ni "no la muestres": una nota que desaparece en silencio porque alguien renombró un campo
 * es peor que una nota puesta un poco más arriba de lo ideal.
 */
export function indiceNotaRequisitos(campos: CampoPerfil[]): number {
  const i = campos.findIndex((c) => CAMPOS_REQUISITOS.includes(c.campo))
  return i === -1 ? 0 : i
}

/** Estado inicial del formulario: una entrada por campo del endpoint. Vacío en el alta; los
 *  valores del perfil en la edición. `null` del backend → `""`, que es lo que un control espera. */
export function valoresIniciales(
  campos: CampoPerfil[], perfil?: PerfilPuesto,
): Record<string, string> {
  const out: Record<string, string> = {}
  for (const c of campos) {
    const valor = perfil ? (perfil as unknown as Record<string, unknown>)[c.campo] : ""
    out[c.campo] = typeof valor === "string" ? valor : ""
  }
  return out
}

/**
 * El body que se manda, armado RECORRIENDO los campos del endpoint. Un campo nuevo en el backend
 * viaja solo, sin tocar esta función.
 *
 * 🔴 LOS SELECTS VACÍOS SE OMITEN Y LOS TEXTOS VACÍOS NO, y la asimetría es obligatoria:
 *   · un `select` sin elegir vale `""`, que **no pertenece a ningún `Literal`** — mandarlo sale
 *     como 422 con el nombre del campo, o sea que un perfil sin modalidad no se podría guardar;
 *   · un campo de texto vacío SÍ se manda, porque `""` es la única forma de VACIAR un campo ya
 *     cargado: el service del backend arma el patch con `exclude_none`, así que `null` significa
 *     "no lo toques". Omitir el texto vacío dejaría el contenido viejo y la pantalla mostraría
 *     algo distinto de lo que se guardó.
 */
export function armarPayload(
  valores: Record<string, string>, campos: CampoPerfil[],
): PerfilPuestoUpdate {
  const body: Record<string, string> = {}
  for (const c of campos) {
    const valor = (valores[c.campo] ?? "").trim()
    if (c.tipo === "select" && !valor) continue
    body[c.campo] = valor
  }
  return body as PerfilPuestoUpdate
}
