import { apiFetch } from "@/services/api"
import type { OffboardingCreate, OffboardingInstancia } from "@/types/offboarding"

export async function fetchOffboardings(): Promise<OffboardingInstancia[]> {
  return apiFetch<OffboardingInstancia[]>("/api/offboarding")
}

export async function iniciarOffboarding(data: OffboardingCreate): Promise<OffboardingInstancia> {
  return apiFetch<OffboardingInstancia>("/api/offboarding", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function marcarActivoDevuelto(
  instanciaId: string,
  activoId: string,
  devuelto: boolean,
): Promise<void> {
  await apiFetch<{ ok: boolean }>(
    `/api/offboarding/${instanciaId}/activos/${activoId}`,
    { method: "PUT", body: JSON.stringify({ devuelto }) },
  )
}

/**
 * Registra la entrevista de salida de un offboarding.
 * empresa_id NO va como parámetro: apiFetch inyecta X-Empresa-Id y el backend acota la
 * instancia a esa empresa, igual que el resto de las escrituras del módulo.
 */
export async function registrarEntrevista(
  instanciaId: string,
  entrevistaSalida: boolean,
  notas: string | null,
): Promise<void> {
  await apiFetch<{ ok: boolean }>(`/api/offboarding/${instanciaId}/entrevista`, {
    method: "PUT",
    body: JSON.stringify({ entrevista_salida: entrevistaSalida, notas_entrevista: notas }),
  })
}
