"use client"

import { ErrorCarga } from "@/components/ui/ErrorCarga"
import type { Empleado } from "@/types/empleado"

/**
 * La lista de resultados del selector de empleados. PRESENTACIONAL: sin estado, sin fetch, sin
 * efectos — recibe los cuatro desenlaces ya resueltos y solo decide qué se ve.
 *
 * Vive aparte de `EmpleadoCombobox` para que se pueda TESTEAR: vitest corre sin jsdom, así que un
 * componente con `useEffect` renderiza siempre su estado inicial y un test suyo mostraría el mismo
 * markup con el bug y sin él. Acá los estados entran por props. Molde: `AsignacionesCapTable`.
 */

interface Props {
  empleados: Empleado[]
  /** Cuántos hay del otro lado. Es lo que permite decir "estás viendo una parte". */
  total: number
  cargando: boolean
  error: boolean
  /** Lo que el usuario escribió. Decide CUÁL de los dos mensajes de vacío corresponde. */
  termino: string
  onElegir: (e: Empleado) => void
  onReintentar: () => void
}

/**
 * 🔴 LOS DOS VACÍOS NO SON EL MISMO VACÍO, y ésta es la función que los separa.
 *
 * "No hay empleados" es una afirmación sobre la BASE. Decirla cuando lo que pasó es que nadie
 * coincide con lo tipeado manda al usuario a cargar gente que ya existe — y es literalmente la
 * frase que ya mintió una vez acá, cuando un 422 se mostraba como lista vacía.
 *
 * Es función pura y exportada a propósito: así los dos mensajes se pueden afirmar UNO CONTRA EL
 * OTRO en un test, sin renderizar. Un test que solo mirara "dice algo" no distingue el caso.
 */
export function mensajeVacio(termino: string): string {
  return termino.trim()
    ? `Sin resultados para "${termino.trim()}". Probá con otro nombre o apellido.`
    : "No hay empleados activos para elegir."
}

export function ResultadosEmpleados({
  empleados, total, cargando, error, termino, onElegir, onReintentar,
}: Props) {
  if (error) {
    return (
      <ErrorCarga mensaje="No se pudieron cargar los empleados." onReintentar={onReintentar} />
    )
  }
  if (cargando) {
    return <p className="px-1 py-2 text-sm text-muted-foreground">Buscando...</p>
  }
  if (empleados.length === 0) {
    return <p className="px-1 py-2 text-sm text-muted-foreground">{mensajeVacio(termino)}</p>
  }

  return (
    <div className="flex flex-col">
      <ul className="max-h-56 overflow-y-auto rounded-lg border border-input">
        {empleados.map((e) => (
          <li key={e.id}>
            <button
              type="button"
              className="w-full px-2.5 py-2 text-left text-sm hover:bg-muted focus-visible:bg-muted focus-visible:outline-none"
              onClick={() => onElegir(e)}
            >
              {e.nombre} {e.apellido}
              {(e.roles?.[0] ?? e.cargo) && (
                <span className="text-muted-foreground"> — {e.roles?.[0] ?? e.cargo}</span>
              )}
            </button>
          </li>
        ))}
      </ul>
      {/*
        🔴 ESTE CARTEL ES EL ARREGLO, tanto como la búsqueda del servidor. El defecto no era que
        se mostraran 20 de 400: era que se mostraban 100 de 400 **en silencio**, y una lista que
        no dice que está recortada se lee como la lista completa.
      */}
      {total > empleados.length && (
        <p className="px-1 pt-1.5 text-xs text-muted-foreground">
          Mostrando {empleados.length} de {total}. Escribí para encontrar a alguien más.
        </p>
      )}
    </div>
  )
}
