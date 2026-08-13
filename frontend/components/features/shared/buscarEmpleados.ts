import { cargarEmpleados, type EstadoEmpleados } from "@/components/features/shared/cargarEmpleados"

/**
 * La POLÍTICA de búsqueda del selector de empleados: qué se le pide al backend cuando alguien
 * escribe en el combobox.
 *
 * 🔴 EL FILTRO VA AL SERVIDOR, y ese es el arreglo entero. Antes cada modal pedía una página de
 * 100 y buscaba —o ni siquiera— sobre esa lista: con 400 colaboradores en una empresa, 300 no se
 * podían elegir y la pantalla no lo decía. El usuario no lo reporta como bug, concluye que el
 * dato no está cargado y se lo pide a desarrollo. Con `search` el universo es la tabla entera y
 * el tope de 100 del endpoint deja de ser el techo de lo alcanzable: pasa a ser el tamaño de la
 * tanda que se muestra.
 *
 * Vive en un módulo aparte —y no adentro del componente— por la misma razón que
 * `cargarEmpleados`: vitest corre SIN jsdom, así que un `useEffect` no se ejecuta y un test de
 * componente no podría ver qué se pidió. Acá se testea la función.
 *
 * 🔑 `/api/empleados` YA aceptaba `search` (`empleado_repo.py:56-58`, `ilike` sobre nombre Y
 * apellido, compuesto con el resto de los filtros y con la barrera de empresa). No hubo que
 * agregar nada del lado del backend.
 *
 * ⚠️ LÍMITE REAL DE ESA BÚSQUEDA, para no venderla de más: el `or` del repo compara el término
 * contra `nombre` y contra `apellido` **por separado**, así que "Gómez Ana" no matchea a nadie
 * aunque exista Ana Gómez. Por eso el campo dice "Buscar por nombre o apellido" y no "Buscar
 * empleado": el rótulo declara lo que la consulta hace. Cambiarlo es tocar un filtro que también
 * usan el listado y el export de empleados, y eso es otra sesión.
 */
/**
 * Cuántos resultados se muestran por búsqueda.
 *
 * 20 y no `MAX_PAGE_SIZE`: con búsqueda del lado del servidor, una lista larga no agrega alcance
 * —lo que no entra se alcanza escribiendo dos letras más— y sí agrega scroll. El número que
 * importaba nunca fue este, era que el filtro viajara.
 */
export const RESULTADOS_VISIBLES = 20

export interface OpcionesBusqueda {
  /** Lo que el usuario escribió. Vacío = primera tanda, sin filtrar. */
  termino: string
  /** Acota a una empresa. `undefined` = consolidado (lo que el header ya resuelve). */
  empresaId?: string
}

/**
 * Pide al backend los empleados que coinciden con lo escrito y deja el estado en uno de los tres
 * desenlaces (cargando · error · lista, que puede estar vacía de verdad). Nunca lanza.
 *
 * Delega en `cargarEmpleados` en vez de hacer su propio `fetch` + `catch`: ahí vive la invariante
 * que distingue un error de una lista vacía, que es la que rescató el bug del `page_size=200`.
 * Reimplementarla acá sería tener dos copias de la única regla que no se puede perder.
 *
 * `estado: "activo"` es fijo: ninguno de los seis lugares que usan este selector puede asignarle
 * algo a alguien dado de baja.
 */
export async function buscarEmpleados(
  { termino, empresaId }: OpcionesBusqueda,
  estado: EstadoEmpleados,
): Promise<void> {
  await cargarEmpleados(
    {
      page: 1,
      pageSize: RESULTADOS_VISIBLES,
      estado: "activo",
      empresaId,
      // `|| undefined` y no el string vacío: `fetchEmpleados` omite el param si es falsy, y un
      // `search=` vacío en la URL es ruido que el backend igual ignoraría.
      search: termino.trim() || undefined,
    },
    estado,
  )
}
