import { apiFetch, postMultipart } from "@/services/api"
import type {
  FilaFormacionPreview,
  ImportacionFormacionPreview,
  ImportacionFormacionResultado,
} from "@/types/importacionFormacion"

const BASE = "/api/importacion/formacion"

/**
 * Paso 1: sube el Excel, matchea a los colaboradores contra el padrón de la empresa y clasifica.
 * NO persiste nada.
 *
 * 🔴 `empresa_id` VA COMO CAMPO DEL FORM, no en el header, y ya desde el preview — a diferencia
 * del import de objetivos, donde la empresa recién viaja en el confirmar. El motivo es que acá
 * la empresa cambia EL RESULTADO del preview: contra qué padrón se matchean los colaboradores y
 * contra qué catálogo se decide si un curso hay que crearlo. Mandarla solo al confirmar daría un
 * preview calculado contra una empresa y escrito contra otra.
 *
 * Usa `postMultipart` (el helper de `services/api`) y no un `fetch` a mano: así hereda el
 * refresh de token y el `ApiError` con `message`, que es lo que el modal muestra tal cual.
 */
export function previewFormacion(
  file: File, empresaId: string,
): Promise<ImportacionFormacionPreview> {
  const form = new FormData()
  form.append("file", file)
  form.append("empresa_id", empresaId)
  return postMultipart<ImportacionFormacionPreview>(`${BASE}/preview`, form)
}

/**
 * Paso 2: crea las capacitaciones que falten en el catálogo y carga las asignaciones revisadas.
 *
 * 🔴 RECIBE LAS FILAS DEL PREVIEW TAL CUAL. No se re-parsea el Excel: lo que se escribe es lo
 * que el usuario vio y aprobó. El backend revalida igual (`estado` es un `Literal`, no `str`)
 * porque el body viaja por la red y el cliente lo puede alterar.
 *
 * 🔴 `empresa_id` va en el BODY: importar es una ACCIÓN y la empresa es un dato del formulario,
 * no el selector del sidebar (Vista vs Acción). Por eso la pantalla exige tener una empresa
 * concreta elegida antes de dejar abrir el modal.
 */
export function confirmarFormacion(
  filas: FilaFormacionPreview[], empresaId: string,
): Promise<ImportacionFormacionResultado> {
  return apiFetch<ImportacionFormacionResultado>(`${BASE}/confirmar`, {
    method: "POST",
    body: JSON.stringify({ empresa_id: empresaId, filas }),
  })
}
