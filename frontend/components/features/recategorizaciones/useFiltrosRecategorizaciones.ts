import { useMemo, useState } from "react"

import type { FiltroCampo } from "@/components/ui/FiltersBar"
import { chipsDeCampos, type ChipFiltro } from "@/components/ui/filtrosChips"
import type { RecategorizacionesFiltros } from "@/services/recategorizaciones"
import type { Empleado } from "@/types/empleado"

/**
 * Los TRES filtros de la planilla: colaborador, y el rango de fechas efectivas.
 *
 * 🔴 NO SE INVENTAN FILTROS QUE EL BACKEND NO TIENE. No hay filtro por área ni por empresa: la
 * empresa viaja por el header (es una VISTA, la manda el sidebar) y por área el backend
 * directamente no filtra. Uno client-side dejaría el export —que va server-side— trayendo filas
 * que la pantalla no muestra.
 *
 * 🔴 EL COLABORADOR NO ES UN `<select>` SINO EL COMBOBOX COMPARTIDO, y por eso vive en la página
 * y no adentro de `FiltersBar`: un select plano pide la lista entera y con 400 colaboradores
 * deja a 300 fuera del alcance sin decirlo. Lo que este hook aporta es su CHIP, para que el
 * estado vacío pueda decir "Juan Pérez no tiene recategorizaciones…".
 *
 * ⚠️ El chip del colaborador se arma a mano y va PRIMERO: `textoVacio` usa el chip cuya `clave`
 * coincide con `claveSujeto` como SUJETO de la frase, y el resto como condiciones.
 */
export function useFiltrosRecategorizaciones(onFiltroChange: () => void) {
  // Se guarda el empleado ENTERO y no solo el id: el chip necesita el nombre, y pedirlo de vuelta
  // por red para escribir una etiqueta que el combobox ya tenía sería una consulta de más.
  const [empleado, setEmpleado] = useState<Empleado | null>(null)
  const [rango, setRango] = useState({ desde: "", hasta: "" })

  const filtros = useMemo<RecategorizacionesFiltros>(() => ({
    empleadoId: empleado?.id,
    fechaDesde: rango.desde || undefined,
    fechaHasta: rango.hasta || undefined,
  }), [empleado, rango])

  const campos: FiltroCampo[] = [
    {
      tipo: "daterange", label: "Período", value: rango,
      onChange: (v) => { setRango(v); onFiltroChange() },
    },
  ]

  function elegirEmpleado(e: Empleado | null) {
    setEmpleado(e)
    onFiltroChange()
  }

  const chips: ChipFiltro[] = [
    ...(empleado ? [{
      clave: "Colaborador",
      etiqueta: "Colaborador",
      valor: `${empleado.nombre} ${empleado.apellido}`,
      quitar: () => elegirEmpleado(null),
    }] : []),
    ...chipsDeCampos(campos),
  ]

  return { filtros, campos, chips, empleado, elegirEmpleado }
}
