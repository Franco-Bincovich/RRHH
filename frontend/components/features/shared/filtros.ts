/**
 * Molde del patrón `useFiltros<Modulo>` + el helper generalizable de AuditFilters.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * REGLAS TRANSVERSALES DEL BLOQUE B — valen para TODO filtro nuevo
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * 1. **Si el filtro afecta al export, va server-side. Una sola implementación.**
 *    Filtrar en el cliente y también en el backend son dos copias de la misma regla que
 *    divergen sin avisar. Además el export no ve el array del cliente: si el filtro vive
 *    solo ahí, el archivo sale con más filas de las que se ven en pantalla.
 *
 * 2. **Todo filtro que acote EMPLEADOS entra por `_ownership_filter`, nunca por un `.eq()`
 *    nuevo en el repo.** En vacaciones y ausencias el ownership de `mandos_medios` viaja por
 *    ese mismo canal (una sola lista de `empleado_id` que llega como `.in_()`). Un filtro que
 *    lo esquive no da un error: devuelve datos de empleados que ese rol no debería ver.
 *
 * 3. **La composición con ownership es por INTERSECCIÓN, nunca por reemplazo.** Ownership ∩
 *    área ∩ empleado. Si la intersección queda vacía, el resultado es vacío — no "sin filtro".
 *
 * 4. **`page` se resetea a 1 al cambiar cualquier filtro.** Si no, se filtra estando en la
 *    página 4 y la pantalla queda vacía aunque haya resultados. El hook NO conoce `page`:
 *    recibe `onFiltroChange` y la página lo cablea a `() => setPage(1)`.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * EL MOLDE — qué se saca de AuditFilters (el precedente más rico: 5 controles → 7 filtros)
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * a. **Un objeto de filtros tipado, uno por módulo**, que viaja entero de la UI al service.
 *    Nunca parámetros posicionales: `services/vacaciones.ts` y `ausencias.ts` son la prueba
 *    de por qué — sus filtros están corridos una posición entre sí y `tsc` no lo ve.
 *
 * b. **El MISMO tipo lo consumen el listado y el export**, y los dos construyen sus query
 *    params con la MISMA función de traducción. Es lo que hace estructuralmente imposible
 *    que un filtro quede en uno solo de los dos (ver services/capacitaciones.ts).
 *
 * c. **`valor || undefined`** — normalizar el `""` del control a "sin filtro" en UN lugar,
 *    que es lo que hace `setFiltro` de acá abajo.
 *
 * d. **Los labels de los valores del backend viven en un catálogo aparte** (ENTIDAD_LABEL,
 *    EVENTO_LABEL), no hardcodeados en el JSX.
 *
 * e. **El repo aplica cada filtro con un `if` plano y sin ramas** (`audit_repo.py:79-91`):
 *    sumar un filtro es sumar una línea.
 *
 * Esqueleto:
 *
 *     export function useFiltrosModulo(onFiltroChange: () => void) {
 *       const [filtros, setFiltros] = useState<ModuloFiltros>({})
 *       const set = setFiltro(filtros, (f) => { setFiltros(f); onFiltroChange() })
 *       const campos: FiltroCampo[] = [
 *         { tipo: "select", label: "Estado", value: filtros.estado ?? "",
 *           onChange: (v) => set("estado", v), opciones: ESTADOS },
 *       ]
 *       return { campos, filtros }
 *     }
 *
 * Lo que NO hay que copiar de auditoría: la barra escrita a mano (usar `FiltersBar`) y la
 * ausencia de export.
 */

/**
 * Etiqueta de un área en el selector. En modo consolidado (sin empresa concreta) sufija con
 * el nombre de la empresa, porque las áreas son POR EMPRESA y dos empresas pueden tener una
 * "Sistemas" cada una: sin el sufijo el selector muestra dos opciones idénticas.
 *
 * Estaba duplicada en los hooks de vacaciones, ausencias y empleados; vive acá para que el
 * cuarto módulo que filtre por área no escriba una quinta copia.
 */
export function etiquetaArea(
  area: { nombre: string; empresa_id?: string | null },
  empresas: { id: string; nombre: string }[],
  empresaConcreta: boolean,
): string {
  if (empresaConcreta) return area.nombre
  const emp = empresas.find((e) => e.id === area.empresa_id)
  return emp ? `${area.nombre} — ${emp.nombre}` : area.nombre
}

/** Valores que un filtro puede tomar en el objeto de filtros de un módulo. */
export type ValorFiltro = string | string[] | undefined

/**
 * Devuelve un setter sobre un objeto de filtros que normaliza "vacío" a `undefined`.
 *
 * Es el `set` de AuditFilters, generalizado. El punto es que la normalización ocurra en un
 * solo lugar: un `""` que se cuele como valor viaja al backend como filtro real y devuelve
 * cero filas, que es un bug incómodo de rastrear porque la pantalla se ve "bien, pero vacía".
 * Un array vacío se trata igual (multiselect sin nada tildado = sin filtro).
 *
 * @example
 *   const set = setFiltro(filtros, aplicar)
 *   set("estado", "")        // → { ...filtros, estado: undefined }
 *   set("areas", [])         // → { ...filtros, areas: undefined }
 */
export function setFiltro<T extends Record<string, ValorFiltro>>(
  filtros: T,
  onChange: (filtros: T) => void,
) {
  return <K extends keyof T>(campo: K, valor: T[K]) => {
    const vacio = valor === undefined || valor === "" || (Array.isArray(valor) && valor.length === 0)
    onChange({ ...filtros, [campo]: vacio ? undefined : valor })
  }
}

/**
 * Saca del objeto de filtros las claves sin valor, para armar los query params.
 * Usar SIEMPRE antes de mandar al backend: deja fuera los `undefined` y los arrays vacíos.
 */
export function filtrosActivos<T extends Record<string, ValorFiltro>>(filtros: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(filtros).filter(([, v]) => v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0)),
  ) as Partial<T>
}
