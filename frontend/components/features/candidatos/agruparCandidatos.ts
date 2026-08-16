import type { CandidatoConGrupo, GrupoCandidatos } from "@/types/candidato"

/**
 * ⚠️ EL MISMO LITERAL QUE USA EL BACKEND en `_contar_grupos` para los huérfanos. Está duplicado
 * entre las dos puntas y no hay test que lo ate (uno es Python y el otro TS). Si cambia de un
 * lado, el `conteo` no matchea y ese grupo cae al fallback de abajo: muestra lo visible en vez
 * del total. Degrada a un número honesto, no a uno inventado — ver el fallback.
 */
const SIN_BUSQUEDA = "Sin búsqueda"

/**
 * Agrupa candidatos por grupo_nombre. Un grupo es "activo" si alguno de sus candidatos
 * pertenece a una búsqueda viva. Orden: grupos activos primero, cerrados después.
 *
 * 🔴 AGRUPA DENTRO DE LA PÁGINA, y el listado se pagina PLANO. Por eso el conteo del encabezado
 * NO sale de acá: llega en `conteo` desde el backend, calculado sobre el filtro entero. Sin eso,
 * una búsqueda de 40 candidatos que aparece con 4 filas en la página 3 diría "4".
 *
 * @param conteo nombre de grupo → total en TODO el filtro (`conteo_por_grupo` de la respuesta).
 */
export function agruparCandidatos(
  items: CandidatoConGrupo[], conteo: Record<string, number> = {},
): GrupoCandidatos[] {
  const mapa = new Map<string, GrupoCandidatos>()
  for (const c of items) {
    const nombre = c.grupo_nombre ?? SIN_BUSQUEDA
    let grupo = mapa.get(nombre)
    if (!grupo) {
      grupo = { nombre, activa: false, candidatos: [], totalGrupo: 0 }
      mapa.set(nombre, grupo)
    }
    grupo.candidatos.push(c)
    if (c.busqueda_activa) grupo.activa = true
  }
  for (const grupo of mapa.values()) {
    // Fallback al largo visible cuando el backend no mandó la clave. Es lo peor que puede pasar
    // y sigue siendo cierto ("hay al menos estos"); poner 0, o dejar el campo en undefined y que
    // la pantalla imprima "NaN candidatos", serían las dos formas de mentir.
    grupo.totalGrupo = conteo[grupo.nombre] ?? grupo.candidatos.length
  }
  return [...mapa.values()].sort((a, b) => Number(b.activa) - Number(a.activa))
}
