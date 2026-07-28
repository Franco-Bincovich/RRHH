"use client"

import { useEffect, useMemo, useState } from "react"

import { fetchProyectos } from "@/services/proyectos"
import type { Proyecto } from "@/types/proyecto"

import type { FiltroCampo } from "@/components/ui/FiltersBar"
import type { EvaluadoListadoItem } from "@/types/evaluacionReportes"

// Filtros del listado de evaluados. Datos chicos (~30 filas) → filtra en cliente para el
// display; el export reusa `filtros` como Query server-side (misma lógica que _pasa del backend).
export function useFiltrosEvaluadosResultados(todos: EvaluadoListadoItem[]) {
  const [sector, setSector] = useState("")
  const [perfil, setPerfil] = useState("")
  const [conNota, setConNota] = useState("")
  const [proyecto, setProyecto] = useState("")
  const [proyectos, setProyectos] = useState<Proyecto[]>([])

  const sectores = useMemo(
    () => Array.from(new Set(todos.map((e) => e.sector).filter((s): s is string => !!s))),
    [todos],
  )

  useEffect(() => {
    fetchProyectos().then((r) => setProyectos(r.items)).catch(() => setProyectos([]))
  }, [])

  const campos: FiltroCampo[] = [
    {
      tipo: "select", label: "Sector", value: sector, onChange: setSector,
      opciones: sectores.map((s) => ({ value: s, label: s })),
    },
    {
      tipo: "select", label: "Perfil", value: perfil, onChange: setPerfil,
      opciones: [{ value: "lider", label: "Líder" }, { value: "general", label: "General" }],
    },
    {
      tipo: "select", label: "Nota final", value: conNota, onChange: setConNota,
      opciones: [{ value: "si", label: "Con nota" }, { value: "no", label: "Sin nota" }],
    },
    // ⚠️ Proyecto es el ÚNICO filtro server-side de este panel: resolver "quién trabaja en el
    // proyecto X" necesita la base. Los otros tres se aplican sobre el array ya traído. Por eso
    // `proyecto` viaja en `filtros` (que va al backend) y NO participa de `filtrados`.
    ...(proyectos.length > 0 ? [{
      tipo: "select" as const, label: "Proyecto", value: proyecto, onChange: setProyecto,
      opcionTodos: "Todos los proyectos",
      opciones: proyectos.map((p) => ({ value: p.id, label: p.nombre })),
    }] : []),
  ]

  const filtrados = useMemo(
    () => todos.filter((e) =>
      (!sector || e.sector === sector) &&
      (!perfil || e.perfil === perfil) &&
      (!conNota || (conNota === "si") === (e.nota_final != null))),
    [todos, sector, perfil, conNota],
  )

  return { campos, filtrados, filtros: { sector, perfil, con_nota: conNota, proyecto_id: proyecto || undefined } }
}
