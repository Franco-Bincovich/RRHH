import type { FiltroCampo } from "@/components/ui/FiltersBar"

/**
 * Armado del array de <FiltersBar> para /eventos. Aparte de la página por lo mismo que en el
 * resto del bloque: **es lo único que un test puede ejercitar sin DOM**, así que los chips se
 * prueban contra el cableado real y no contra campos inventados.
 *
 * 🔴 "VER RESUELTOS" DEJÓ DE SER UN BOTÓN QUE ALTERNA Y PASÓ A SER UN SELECT, y no es cosmética:
 * los chips se derivan de los `FiltroCampo`, y el patrón tiene cinco tipos de control — ninguno
 * es un botón de dos estados. Con el botón, el filtro quedaba activo sin chip y sin contador: la
 * única señal de que la agenda estaba mostrando más filas de lo normal era el texto del propio
 * botón, que además vivía arriba a la derecha, lejos de la tabla. Es el mismo cambio que el
 * checkbox de /candidatos y el toggle de /clientes.
 *
 * 🔴 EL FILTRO ES BINARIO, no tri-estado: el backend recibe `incluir_resueltas: bool`, y `false`
 * significa "sólo los pendientes". No hay forma de pedir "sólo los resueltos", así que ofrecer esa
 * tercera opción sería un filtro que el backend no puede honrar.
 *
 * ⚠️ EL DEFAULT DE ESTA PANTALLA OCULTA FILAS Y NO PRODUCE CHIP: sin nada elegido se ven sólo los
 * pendientes, que es el default del backend y lo que una agenda tiene que mostrar. Es la única
 * forma de que el chip signifique lo mismo que en el resto del sistema ("esto está recortando lo
 * que ves").
 *
 * ⚠️ NO HAY MÁS FILTROS PORQUE EL BACKEND NO ACEPTA NINGUNO: `GET /api/eventos` recibe
 * `incluir_resueltas`, `page` y `page_size`, y nada más. El recorte por empresa lo hace el header
 * del sidebar, y el de visibilidad lo hace el propio backend con `sujeto(request)` — un evento
 * privado de otro usuario no aparece, y eso no es un filtro que el usuario pueda tocar.
 *
 * Sin estado ni efectos: recibe el valor y su setter. El reset de página lo dispara
 * `onFiltroChange` (invariante 4 del bloque B).
 */
export const RESUELTOS_OPCIONES = [
  { value: "todos", label: "Pendientes y resueltos" },
]

export interface ArgsCamposEventos {
  resueltosFiltro: string
  setResueltosFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposEventos): FiltroCampo[] {
  return [
    { tipo: "select" as const, label: "Estado", value: a.resueltosFiltro, opcionTodos: "Sólo pendientes",
      onChange: (v: string) => { a.setResueltosFiltro(v); a.onFiltroChange() }, opciones: RESUELTOS_OPCIONES },
  ]
}
