"use client"

import { useEffect, useState } from "react"

import { fetchProyectos } from "@/services/proyectos"
import type { Proyecto } from "@/types/proyecto"

import type { FiltroCampo } from "@/components/ui/FiltersBar"

/**
 * Filtros del listado de evaluados. LOS CUATRO SON SERVER-SIDE.
 *
 * 🔴 CAMBIÓ EL 15/8/2026 Y EL CAMBIO ES EL PUNTO DEL MÓDULO. Antes este hook recibía el array
 * completo (`todos: EvaluadoListadoItem[]`), derivaba de ahí las opciones de sector y devolvía
 * un `filtrados` calculado en memoria; sólo `proyecto_id` iba al backend. Con ~30 evaluados por
 * lote eso funcionaba. Al paginar, "filtrar por sector" pasaría a significar "buscar el sector
 * entre las 20 filas que estás viendo": alguien que está en la página 3 no aparece nunca.
 *
 * Ahora el hook no ve datos. Sólo produce `campos` (la UI) y `filtros` (lo que viaja), y el
 * panel se los pasa al backend en el listado Y en el export, por el mismo traductor.
 *
 * @param sectores opciones del desplegable, del LOTE ENTERO — vienen en la respuesta, no de la
 *   página. Derivarlas de lo visible dejaría fuera del desplegable a los sectores que no
 *   aparecen en la página 1, y esos serían justo los que hay que ir a buscar.
 * @param onFiltroChange se dispara con CUALQUIER cambio; la pantalla lo cablea a volver a la
 *   página 1 (invariante 4 del Bloque B). El hook no conoce `page`, a propósito.
 */
export function useFiltrosEvaluadosResultados(sectores: string[], onFiltroChange: () => void) {
  const [sector, setSector] = useState("")
  const [perfil, setPerfil] = useState("")
  const [conNota, setConNota] = useState("")
  const [proyecto, setProyecto] = useState("")
  const [proyectos, setProyectos] = useState<Proyecto[]>([])

  useEffect(() => {
    fetchProyectos().then((r) => setProyectos(r.items)).catch(() => setProyectos([]))
  }, [])

  /** Un solo lugar donde "setear un filtro" implica volver a la página 1. */
  function cambiar(set: (v: string) => void) {
    return (v: string) => {
      set(v)
      onFiltroChange()
    }
  }

  const campos: FiltroCampo[] = [
    {
      tipo: "select", label: "Sector", value: sector, onChange: cambiar(setSector),
      opciones: sectores.map((s) => ({ value: s, label: s })),
    },
    {
      tipo: "select", label: "Perfil", value: perfil, onChange: cambiar(setPerfil),
      opciones: [{ value: "lider", label: "Líder" }, { value: "general", label: "General" }],
    },
    {
      tipo: "select", label: "Nota final", value: conNota, onChange: cambiar(setConNota),
      opciones: [{ value: "si", label: "Con nota" }, { value: "no", label: "Sin nota" }],
    },
    ...(proyectos.length > 0 ? [{
      tipo: "select" as const, label: "Proyecto", value: proyecto, onChange: cambiar(setProyecto),
      opcionTodos: "Todos los proyectos",
      opciones: proyectos.map((p) => ({ value: p.id, label: p.nombre })),
    }] : []),
  ]

  return {
    campos,
    filtros: {
      sector: sector || undefined, perfil: perfil || undefined,
      con_nota: conNota || undefined, proyecto_id: proyecto || undefined,
    },
  }
}
