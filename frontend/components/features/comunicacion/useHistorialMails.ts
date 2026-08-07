"use client"

import { useCallback, useEffect, useState } from "react"

import { cargarHistorialMails } from "@/components/features/comunicacion/cargarHistorialMails"
import { setFiltro } from "@/components/features/shared/filtros"
import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { MailEnviado, MailsFiltros } from "@/types/plantillas"

export const ESTADOS_MAIL = [
  { value: "enviado", label: "Enviados" },
  { value: "fallido", label: "No entregados" },
]

/**
 * Estado del historial de mails: filtros + carga. Molde `useFiltros<Modulo>` de `shared/filtros`.
 *
 * Los filtros van SERVER-SIDE, no filtrando el array en memoria: el backend devuelve los últimos
 * N (techo duro), así que filtrar acá daría "los fallidos ENTRE los últimos 100", que no es lo
 * que la pantalla dice. Es la misma razón por la que el repo aplica los filtros en la query.
 *
 * No hay reset de `page` porque no hay paginado (el historial no se pagina, por diseño), así que
 * este hook tampoco recibe `onFiltroChange`.
 */
export function useHistorialMails() {
  const [filtros, setFiltros] = useState<MailsFiltros>({})
  const [items, setItems] = useState<MailEnviado[]>([])
  const [limite, setLimite] = useState(0)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)
  const [intento, setIntento] = useState(0)

  useEffect(() => {
    void cargarHistorialMails(filtros, { setItems, setLimite, setCargando, setError })
  }, [filtros, intento])

  const set = setFiltro(filtros, setFiltros)

  const campos: FiltroCampo[] = [
    { tipo: "select", label: "Estado", value: filtros.estado ?? "", opciones: ESTADOS_MAIL,
      onChange: (v) => set("estado", v) },
    { tipo: "daterange", label: "Fecha",
      value: { desde: filtros.fecha_desde ?? "", hasta: filtros.fecha_hasta ?? "" },
      onChange: (v) => setFiltros({
        ...filtros,
        fecha_desde: v.desde || undefined,
        fecha_hasta: v.hasta || undefined,
      }) },
  ]

  const recargar = useCallback(() => setIntento((n) => n + 1), [])

  return { campos, items, limite, cargando, error, recargar }
}
