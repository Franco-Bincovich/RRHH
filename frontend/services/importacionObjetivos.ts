import { apiFetch, postMultipart } from "@/services/api"
import type {
  FilaObjetivoPreview,
  ImportacionObjetivosPreview,
  ImportacionObjetivosResultado,
} from "@/types/importacionObjetivos"

const BASE = "/api/importacion/objetivos"

/**
 * Paso 1: sube el Excel y devuelve qué filas se van a cargar y cuáles tienen problemas.
 * NO persiste nada.
 *
 * Usa `postMultipart` (el helper de `services/api`) y no un `fetch` a mano como
 * `services/importacion.ts`: así hereda el refresh de token y el `ApiError` con `message`, que
 * es lo que el modal muestra tal cual. Los mensajes del backend están redactados para el
 * usuario —"Faltan columnas obligatorias: Responsable"— y reemplazarlos por un genérico tira
 * justo lo que hace falta para arreglar el archivo.
 */
export function previewImportObjetivos(file: File): Promise<ImportacionObjetivosPreview> {
  const form = new FormData()
  form.append("file", file)
  return postMultipart<ImportacionObjetivosPreview>(`${BASE}/preview`, form)
}

/**
 * Paso 2: crea los objetivos revisados.
 *
 * 🔴 `empresa_id` va en el BODY, no en el header: importar es una ACCIÓN y la empresa es un dato
 * del formulario, no el selector del sidebar (Vista vs Acción). Por eso la pantalla exige tener
 * una empresa concreta elegida antes de dejar abrir el modal.
 */
export function confirmarImportObjetivos(
  empresaId: string, filas: FilaObjetivoPreview[],
): Promise<ImportacionObjetivosResultado> {
  return apiFetch<ImportacionObjetivosResultado>(`${BASE}/confirmar`, {
    method: "POST",
    body: JSON.stringify({ empresa_id: empresaId, filas }),
  })
}
