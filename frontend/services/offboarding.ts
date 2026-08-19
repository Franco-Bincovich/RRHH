import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { OffboardingCreate, OffboardingInstancia } from "@/types/offboarding"

export async function fetchOffboardings(): Promise<OffboardingInstancia[]> {
  return apiFetch<OffboardingInstancia[]>("/api/offboarding")
}

/**
 * Exporta los offboardings ACTIVOS — los mismos que muestra la pantalla.
 *
 * Ninguna de las dos puntas manda query params y las dos mandan `X-Empresa-Id` por
 * `authHeaders()`, así que traen el mismo conjunto. 🔴 El día que el listado gane un filtro
 * (motivo, estado), los dos tienen que armar sus params con UNA función de traducción
 * compartida — molde: `queryVacantes` en services/vacantes.ts.
 */
export function exportarOffboardings(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/offboarding/exportar", formato, "offboardings")
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

/**
 * Efectiviza la baja: escribe `fecha_egreso` en el empleado y cierra la instancia.
 *
 * 🔴 ES EL ÚNICO CAMINO QUE DA DE BAJA A ALGUIEN, y es irreversible desde la UI. Abrir el
 * trámite (`iniciarOffboarding`) ya NO cambia el estado del empleado: hasta que esto corre, la
 * persona sigue contando en headcount, organigrama, ausentismo y saldo de vacaciones.
 *
 * `fecha_egreso` es el HECHO —el día que la persona dejó de trabajar— y no se sincroniza con la
 * previsión que se cargó al abrir el trámite (`fecha_ultimo_dia`). Que difieran no es un error:
 * es lo que después permite comparar lo previsto con lo ocurrido.
 *
 * 🔴 LOS CUATRO ERRORES SE MUESTRAN CON SU MENSAJE, sin traducir. Los dos de fecha
 * —FECHA_EGRESO_FUTURA y FECHA_EGRESO_INVALIDA (anterior al ingreso)— son los que alguien
 * encuentra operando normal, y cada uno dice qué corregir. Los otros dos son
 * OFFBOARDING_YA_CERRADO y EMPLEADO_YA_DE_BAJA (409), que aparecen con dos pestañas abiertas.
 */
export async function efectivizarBaja(instanciaId: string, fechaEgreso: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`/api/offboarding/${instanciaId}/efectivizar`, {
    method: "POST",
    body: JSON.stringify({ fecha_egreso: fechaEgreso }),
  })
}
