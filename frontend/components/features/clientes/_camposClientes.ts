import type { FiltroCampo } from "@/components/ui/FiltersBar"

/**
 * Armado del array de <FiltersBar> para /clientes. Aparte de la página por lo mismo que en el
 * resto del bloque: **es lo único que un test puede ejercitar sin DOM**, así que los chips se
 * prueban contra el cableado real y no contra campos inventados.
 *
 * 🔴 "VER BAJAS" DEJÓ DE SER UN BOTÓN QUE ALTERNA Y PASÓ A SER UN SELECT, y no es cosmética: los
 * chips se derivan de los `FiltroCampo`, y el patrón tiene cinco tipos de control (select,
 * search, date, daterange, multiselect) — **ninguno es un botón de dos estados**. Con el botón,
 * el filtro quedaba activo sin chip y sin contador: la única señal de que la pantalla estaba
 * mostrando más filas de lo normal era que el botón decía "Ocultar bajas". Es el mismo cambio
 * que el checkbox de /candidatos.
 *
 * 🔴 EL FILTRO ES BINARIO, no tri-estado: el backend recibe `incluir_inactivos: bool`, y `false`
 * significa "sólo los activos". No hay forma de pedir "sólo las bajas", así que ofrecer esa
 * tercera opción sería un filtro que el backend no puede honrar.
 *
 * ⚠️ EL DEFAULT DE ESTA PANTALLA OCULTA FILAS Y NO PRODUCE CHIP, y conviene saberlo: sin nada
 * elegido se ven sólo los activos, que es el default del backend. Es la única forma de que el
 * chip signifique lo mismo que en el resto del sistema ("esto está recortando lo que ves"): si
 * la opción vacía trajera todo, el estado por defecto de la pantalla cambiaría de golpe y las
 * bajas aparecerían mezcladas con los activos al entrar.
 *
 * 🔴 NO HAY FILTRO DE EMPRESA, y no es un olvido: el catálogo es GLOBAL (migraciones 108/109). El
 * router no lee `X-Empresa-Id` ni acepta un `empresa_id`. La pantalla lo DICE en el subtítulo.
 *
 * Sin estado ni efectos: recibe el valor y su setter. El reset de página lo dispararía
 * `onFiltroChange`, que acá no hace falta porque el listado no pagina (el backend no acepta
 * `page`) — se recibe igual para no divergir del molde y para el día que pagine.
 */
export const BAJAS_OPCIONES = [
  { value: "todos", label: "Activos y dados de baja" },
]

export interface ArgsCamposClientes {
  bajasFiltro: string
  setBajasFiltro: (v: string) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposClientes): FiltroCampo[] {
  return [
    { tipo: "select" as const, label: "Estado", value: a.bajasFiltro, opcionTodos: "Sólo activos",
      onChange: (v: string) => { a.setBajasFiltro(v); a.onFiltroChange() }, opciones: BAJAS_OPCIONES },
  ]
}
