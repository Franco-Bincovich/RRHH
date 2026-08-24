"use client"

import { forwardRef, useImperativeHandle, useState } from "react"
import { GitBranch } from "lucide-react"
import { colorByEmpresa, initials, MULTI_PROY, ORG_TREE_CSS, type EmpresaColor } from "@/utils/colorEmpresa"
import type { EmpleadoProyectoNodoAPI, OrgProyectosResponse, ProyectoOrgNodoAPI } from "@/types/organigrama"
import { Card } from "@/components/ui/card"

export interface ArbolProyectoRef {
  expandAll: () => void
  restore: () => void
}

interface Props { data: OrgProyectosResponse }

function EmpleadoNodo({ emp, color, esExterno }: {
  emp: EmpleadoProyectoNodoAPI; color: EmpresaColor; esExterno: boolean
}) {
  return (
    <Card padding="none" interactive className="inline-flex items-center gap-2 px-3 py-1.5 shadow-sm whitespace-nowrap">
      <span className="flex size-6 shrink-0 items-center justify-center rounded-full text-[9px] font-semibold"
        style={{ background: color.bg, color: color.text }}>
        {initials(emp.nombre, emp.apellido)}
      </span>
      <span className="flex flex-col text-left">
        <span className="text-[12px] font-medium leading-tight text-foreground">
          {emp.nombre} {emp.apellido}
        </span>
        <span className="text-[10px] leading-tight text-muted-foreground">{emp.rol}</span>
      </span>
      {esExterno && emp.empleado_empresa_nombre && (
        <span className="ml-1 rounded-full px-2 py-px text-[9px] font-semibold whitespace-nowrap"
          style={{ background: color.bg, color: color.text }}>
          {emp.empleado_empresa_nombre}
        </span>
      )}
      {emp.total_proyectos > 1 && (
        <span className="ml-1 rounded-full px-2 py-px text-[9px] font-semibold"
          style={{ background: MULTI_PROY.bg, color: MULTI_PROY.text }}>
          {emp.total_proyectos} proy.
        </span>
      )}
    </Card>
  )
}

function ProyectoNodo({ proyecto, expanded, onToggle, empresasOrden }: {
  proyecto: ProyectoOrgNodoAPI; expanded: boolean; onToggle: () => void; empresasOrden: string[]
}) {
  const proyColor = colorByEmpresa(proyecto.empresa_id, empresasOrden)
  return (
    <>
      <button
        onClick={onToggle}
        className="inline-flex cursor-pointer items-center gap-2 rounded-xl border-t-[3px] bg-card px-4 py-2 shadow-sm whitespace-nowrap transition-colors hover:bg-muted/50"
        style={{ borderTopColor: proyColor.dot }}>
        <span className="text-[10px] text-muted-foreground">{expanded ? "▾" : "▸"}</span>
        <span className="flex flex-col items-start">
          <span className="text-[12.5px] font-semibold text-foreground">{proyecto.nombre}</span>
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {proyecto.total_asignados} persona{proyecto.total_asignados !== 1 ? "s" : ""}
          </span>
        </span>
      </button>
      {expanded && proyecto.empleados.length > 0 && (
        <ul>
          {proyecto.empleados.map((emp) => {
            const color = colorByEmpresa(emp.empleado_empresa_id, empresasOrden)
            const esExterno = emp.empleado_empresa_id !== proyecto.empresa_id
            return (
              <li key={emp.id}>
                <EmpleadoNodo emp={emp} color={color} esExterno={esExterno} />
              </li>
            )
          })}
        </ul>
      )}
    </>
  )
}

export const ArbolProyecto = forwardRef<ArbolProyectoRef, Props>(({ data }, ref) => {
  const [expanded, setExpanded]   = useState<Record<string, boolean>>({})
  const [savedExp, setSavedExp]   = useState<Record<string, boolean>>({})
  const empresasOrden = data.empresas_orden.map((e) => e.id)

  useImperativeHandle(ref, () => ({
    expandAll: () => {
      setSavedExp({ ...expanded })
      const all: Record<string, boolean> = {}
      data.proyectos.forEach((p) => { all[p.id] = true })
      setExpanded(all)
    },
    restore: () => setExpanded(savedExp),
  }))

  function toggle(id: string) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const empresasConProyectos = data.empresas_orden.map((empresa) => ({
    ...empresa,
    proyectos: data.proyectos.filter((p) => p.empresa_id === empresa.id),
  }))

  if (data.proyectos.length === 0) return (
    <div className="flex flex-col items-center gap-2 py-16">
      <GitBranch className="size-8 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">No hay proyectos con asignaciones todavía.</p>
    </div>
  )

  return (
    <>
      <style>{ORG_TREE_CSS}</style>
      <p className="mb-4 text-xs text-muted-foreground">
        Tocá un proyecto para desplegar las personas asignadas. El color indica la empresa de pertenencia.
      </p>
      <div className="overflow-x-auto pb-8">
        <div className="org-tree inline-block min-w-full text-center">
          <ul>
            {empresasConProyectos.map((empresa) => {
              const color = colorByEmpresa(empresa.id, empresasOrden)
              return (
                <li key={empresa.id}>
                  <div className="inline-flex flex-col items-center gap-0.5 rounded-xl border-t-[3px] bg-card px-5 py-2.5 shadow-sm whitespace-nowrap"
                    style={{ borderTopColor: color.dot }}>
                    <span className="text-[12.5px] font-semibold text-foreground">{empresa.nombre}</span>
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      {empresa.proyectos.length > 0
                        ? `${empresa.proyectos.length} proyecto${empresa.proyectos.length > 1 ? "s" : ""}`
                        : "Sin proyectos propios"}
                    </span>
                  </div>
                  {empresa.proyectos.length > 0 && (
                    <ul>
                      {empresa.proyectos.map((proy) => (
                        <li key={proy.id}>
                          <ProyectoNodo proyecto={proy} expanded={!!expanded[proy.id]}
                            onToggle={() => toggle(proy.id)} empresasOrden={empresasOrden} />
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      </div>
      {/* Leyenda de colores */}
      <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground print:hidden">
        {data.empresas_orden.map((empresa) => {
          const color = colorByEmpresa(empresa.id, empresasOrden)
          return (
            <span key={empresa.id} className="flex items-center gap-1.5">
              <span className="size-2.5 rounded-full" style={{ background: color.dot }} />
              {empresa.nombre}
            </span>
          )
        })}
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ background: MULTI_PROY.bg }} />
          <span style={{ color: MULTI_PROY.text }}>En más de un proyecto</span>
        </span>
      </div>
    </>
  )
})

ArbolProyecto.displayName = "ArbolProyecto"
