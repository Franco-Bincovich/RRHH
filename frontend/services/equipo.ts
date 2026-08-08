import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { EquipoMiembro } from "@/types/equipo"

/**
 * Roster de empleados visibles por ownership (cross-empresa). Para admin_rrhh/gerencia
 * son todos; para mandos_medios, su gente. Sin paginación (lista corta).
 */
export async function fetchEquipo(): Promise<EquipoMiembro[]> {
  return apiFetch<EquipoMiembro[]>("/api/equipo")
}

/**
 * Exporta el roster.
 *
 * 🔴 NO LLEVA NINGÚN PARÁMETRO, y eso ES la invariante list↔export acá: el universo no sale de
 * un filtro que el cliente pueda mandar, sale del OWNERSHIP del usuario del token. Las dos
 * puntas traen lo mismo porque las dos preguntan lo mismo — el día que este export aceptara un
 * `empleado_id` o una empresa, sería la vía para pedir gente que la pantalla no muestra.
 */
export function exportarEquipo(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/equipo/exportar", formato, "equipo")
}
