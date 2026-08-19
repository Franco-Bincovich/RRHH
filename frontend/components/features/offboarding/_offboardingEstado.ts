import type { ActivoResponse, OffboardingInstancia } from "@/types/offboarding"

/**
 * Las transformaciones PURAS de la lista de offboardings: dada una lista y un cambio, la lista
 * nueva. Sin React, sin fetch, sin toasts.
 *
 * Separado de `useOffboardings.ts` porque el hook llegaba a 97 y su límite es 80. El corte no es
 * arbitrario: acá está lo que se puede razonar y testear sin montar nada, y allá lo que necesita
 * el ciclo de vida del componente. Es también lo que hace testeable el update optimista, que es
 * la parte con más chances de romperse en silencio.
 */

/** Porcentaje de activos devueltos. Es el MISMO criterio que muestra la barra de progreso. */
export function calcProgress(activos: ActivoResponse[]): number {
  if (activos.length === 0) return 0
  return Math.round((activos.filter((a) => a.devuelto).length / activos.length) * 100)
}

/**
 * Reemplaza un activo dentro de su instancia y recalcula el progreso de esa instancia.
 *
 * 🔴 EL PROGRESO SE RECALCULA ACÁ Y NO SE PIDE AL BACKEND. `inst.progreso` viene del servidor en
 * la carga inicial, pero después de un toggle optimista la barra tiene que moverse en el mismo
 * render que la casilla: dejarla con el valor viejo hasta el próximo fetch mostraría "3 de 5
 * devueltos — 40%", que es peor que no mostrar nada porque se lee como un bug del cálculo.
 */
export function conActivoParcheado(
  lista: OffboardingInstancia[],
  instanciaId: string,
  activoId: string,
  nuevo: (a: ActivoResponse) => ActivoResponse,
): OffboardingInstancia[] {
  return lista.map((o) => {
    if (o.id !== instanciaId) return o
    const activos = o.activos.map((a) => (a.id === activoId ? nuevo(a) : a))
    return { ...o, activos, progreso: calcProgress(activos) }
  })
}

/** Refleja la entrevista de salida que `EntrevistaSalida` ya persistió por su cuenta. */
export function conEntrevista(
  lista: OffboardingInstancia[],
  id: string,
  realizada: boolean,
  notas: string | null,
): OffboardingInstancia[] {
  return lista.map((o) =>
    o.id === id ? { ...o, entrevista_salida: realizada, notas_entrevista: notas } : o,
  )
}
