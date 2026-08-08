import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { OnboardingDetalle, OnboardingInstancia, OnboardingTemplate, TemplateTarea } from "@/types/onboarding"

export async function fetchOnboardings(): Promise<OnboardingInstancia[]> {
  return apiFetch<OnboardingInstancia[]>("/api/onboarding")
}

/**
 * Exporta los onboardings activos. El listado no tiene filtros propios (la empresa viaja por el
 * header, igual que en `fetchOnboardings`), así que las dos puntas traen el mismo conjunto por
 * construcción: no hay query params que puedan divergir.
 */
export function exportarOnboardings(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/onboarding/exportar", formato, "onboarding")
}

export async function fetchOnboardingEmpleado(empleadoId: string): Promise<OnboardingDetalle> {
  return apiFetch<OnboardingDetalle>(`/api/onboarding/${empleadoId}`)
}

export async function iniciarOnboarding(empleadoId: string, templateId?: string): Promise<OnboardingInstancia> {
  return apiFetch<OnboardingInstancia>(`/api/onboarding/${empleadoId}/iniciar`, {
    method: "POST",
    ...(templateId ? { body: JSON.stringify({ template_id: templateId }) } : {}),
  })
}

export async function completarTarea(instanciaId: string, tareaId: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(
    `/api/onboarding/${instanciaId}/tareas/${tareaId}/completar`,
    { method: "PUT" },
  )
}

// ── Templates ──────────────────────────────────────────────────────────────────

export async function fetchTemplates(): Promise<OnboardingTemplate[]> {
  return apiFetch<OnboardingTemplate[]>("/api/onboarding/templates")
}

/**
 * Exporta las plantillas — las MISMAS que muestra la pantalla.
 *
 * Ninguna de las dos puntas manda query params y las dos mandan `X-Empresa-Id` por
 * `authHeaders()`, así que traen el mismo conjunto. 🔴 Y el recorte que de verdad importa acá
 * no es la empresa sino la VISIBILIDAD: el backend resuelve qué plantillas ve este usuario a
 * partir de su token (públicas de su empresa + privadas propias). Por eso el archivo no puede
 * traer las privadas de otro aunque el pedido salga de la misma pantalla.
 */
export function exportarTemplates(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/onboarding/templates/exportar", formato, "plantillas_onboarding")
}

export async function fetchTemplate(id: string): Promise<OnboardingTemplate> {
  return apiFetch<OnboardingTemplate>(`/api/onboarding/templates/${id}`)
}

export async function createTemplate(data: { nombre: string; empresa_id: string; descripcion?: string }): Promise<OnboardingTemplate> {
  return apiFetch<OnboardingTemplate>("/api/onboarding/templates", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateTemplate(
  id: string,
  data: { nombre?: string; descripcion?: string; es_publica?: boolean },
): Promise<OnboardingTemplate> {
  return apiFetch<OnboardingTemplate>(`/api/onboarding/templates/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function deleteTemplate(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`/api/onboarding/templates/${id}`, { method: "DELETE" })
}

export async function addTarea(
  templateId: string,
  data: { titulo: string; descripcion?: string; semana: 1 | 2 | 3 | 4; orden: number },
): Promise<TemplateTarea> {
  return apiFetch<TemplateTarea>(`/api/onboarding/templates/${templateId}/tareas`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateTarea(
  templateId: string,
  tareaId: string,
  data: { titulo?: string; descripcion?: string; semana?: number; orden?: number },
): Promise<TemplateTarea> {
  return apiFetch<TemplateTarea>(`/api/onboarding/templates/${templateId}/tareas/${tareaId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function deleteTarea(templateId: string, tareaId: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(
    `/api/onboarding/templates/${templateId}/tareas/${tareaId}`,
    { method: "DELETE" },
  )
}
