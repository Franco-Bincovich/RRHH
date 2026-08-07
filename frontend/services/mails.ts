import { filtrosActivos } from "@/components/features/shared/filtros"
import { apiFetch } from "@/services/api"
import type { MailHistorialResponse, MailsFiltros } from "@/types/plantillas"

const BASE = "/api/mails"

/**
 * Historial de mails enviados, del más reciente al más viejo.
 *
 * 🔴 NO HAY `exportarHistorial()`, y no se agrega "por comodidad". `mail_enviado` guarda datos
 * personales por definición —nombre, dirección y el cuerpo entero del mail—, así que un Excel
 * con eso es justamente el archivo que no se quiere que circule. La decisión vive en
 * `backend/repositories/mail_enviado_repo.py` y esto la respeta. Consecuencia: este listado no
 * entra en `test_paridad_list_export.py`, que solo empareja listados que TIENEN export.
 *
 * Tampoco pagina: el backend devuelve los últimos N (techo duro de 200) y `limite` vuelve en la
 * respuesta para que la pantalla pueda decir que está viendo un recorte.
 *
 * Los filtros pasan por `filtrosActivos` para que un `""` del control no viaje como filtro real
 * y devuelva cero filas — el bug incómodo de rastrear porque la pantalla se ve "bien, pero
 * vacía". Es la misma normalización que usan los demás módulos.
 */
export async function fetchHistorialMails(
  filtros: MailsFiltros = {},
  limite?: number,
): Promise<MailHistorialResponse> {
  const params = new URLSearchParams(filtrosActivos(filtros) as Record<string, string>)
  if (limite) params.set("limite", String(limite))
  const qs = params.toString()
  return apiFetch<MailHistorialResponse>(qs ? `${BASE}?${qs}` : BASE)
}
