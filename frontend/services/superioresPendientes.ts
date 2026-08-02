import { apiFetch } from "@/services/api"
import type {
  ResolucionPendientesResult,
  SuperioresPendientesListResponse,
} from "@/types/importacion"

const BASE = "/api/importacion/superiores-pendientes"

/**
 * Superiores que el import de nómina leyó del CSV y no pudo resolver a un manager_id.
 *
 * Respeta el selector de empresa del sidebar (`apiFetch` inyecta X-Empresa-Id): es una VISTA,
 * filtra lo que se mira. En estado sano devuelve 0.
 */
export async function fetchSuperioresPendientes(): Promise<SuperioresPendientesListResponse> {
  return apiFetch<SuperioresPendientesListResponse>(BASE)
}

/**
 * Reintenta los pendientes contra el estado ACTUAL de empleados y limpia los que resuelve.
 *
 * ⚠️ La empresa activa acota QUÉ pendientes se reintentan, NO dónde se busca al superior: un
 * superior puede ser de otra empresa del grupo. Esa decisión vive en el backend
 * (`services/_alcance_mandos.py` y `_superiores_matcher`), no acá.
 */
export async function resolverSuperioresPendientes(): Promise<ResolucionPendientesResult> {
  return apiFetch<ResolucionPendientesResult>(`${BASE}/resolver`, { method: "POST" })
}
