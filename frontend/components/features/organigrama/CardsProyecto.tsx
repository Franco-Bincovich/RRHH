"use client"

import { GrillaTarjetas } from "@/components/ui/GrillaTarjetas"
import { GitBranch } from "lucide-react"
import { periodoTexto, valorHoraTexto } from "@/components/features/organigrama/contratoAsignacion"
import { colorByEmpresa, initials, MULTI_PROY, type EmpresaColor } from "@/utils/colorEmpresa"
import type { EmpleadoProyectoNodoAPI, OrgProyectosResponse, ProyectoOrgNodoAPI } from "@/types/organigrama"

function GrupoEmpresa({ empresaNombre, empleados, color, proyectoEmpresaId }: {
  empresaNombre: string; empleados: EmpleadoProyectoNodoAPI[];
  color: EmpresaColor; proyectoEmpresaId: string
}) {
  const [primero, ...resto] = empleados
  return (
    <div>
      <div className="flex items-center gap-2 py-2 text-xs font-semibold text-foreground">
        <span className="size-2 rounded-full" style={{ background: color.dot }} />
        {empresaNombre}
        <span className="ml-auto text-[11px] font-normal text-muted-foreground">{empleados.length}</span>
      </div>
      {primero && (
        <div className="flex items-center gap-2 py-1 pl-1 text-[12.5px]">
          <span className="flex size-5 shrink-0 items-center justify-center rounded-full text-[9px] font-semibold"
            style={{ background: color.bg, color: color.text }}>
            {initials(primero.nombre, primero.apellido)}
          </span>
          <span className="min-w-0 truncate text-foreground">
            {primero.nombre} {primero.apellido}
          </span>
          <span className="shrink-0 text-[11px] text-muted-foreground">· {primero.rol}</span>
          {primero.total_proyectos > 1 && (
            <span className="ml-auto shrink-0 rounded-full px-2 py-px text-[9.5px] font-semibold"
              style={{ background: MULTI_PROY.bg, color: MULTI_PROY.text }}>
              {primero.total_proyectos} proy.
            </span>
          )}
        </div>
      )}
      {primero && (
        // Alineado con el nombre (pl-7 = avatar + gap), no con el borde: se lee como detalle de
        // esa persona y no como un dato del grupo.
        <p className="pl-7 pb-1 text-[11px] text-muted-foreground">
          {valorHoraTexto(primero.valor_hora)} · {periodoTexto(primero.fecha_desde, primero.fecha_hasta)}
        </p>
      )}
      {resto.length > 0 && (
        <p className="py-0.5 pl-7 text-[12px] text-muted-foreground">
          +{resto.length} de {empresaNombre}
        </p>
      )}
    </div>
  )
}

function ProyectoCard({ proyecto, empresasOrden }: {
  proyecto: ProyectoOrgNodoAPI; empresasOrden: string[]
}) {
  const dueñaColor = colorByEmpresa(proyecto.empresa_id, empresasOrden)

  // Agrupar empleados por empresa
  const grupos = new Map<string, { nombre: string; color: EmpresaColor; empleados: EmpleadoProyectoNodoAPI[] }>()
  proyecto.empleados.forEach((emp) => {
    if (!grupos.has(emp.empleado_empresa_id)) {
      grupos.set(emp.empleado_empresa_id, {
        nombre: emp.empleado_empresa_nombre ?? emp.empleado_empresa_id,
        color: colorByEmpresa(emp.empleado_empresa_id, empresasOrden),
        empleados: [],
      })
    }
    grupos.get(emp.empleado_empresa_id)!.empleados.push(emp)
  })

  // Colaboradoras = empresas distintas a la dueña
  const colaboradoras = [...grupos.keys()]
    .filter((id) => id !== proyecto.empresa_id)
    .map((id) => grupos.get(id)!.nombre)

  return (
    <div className="overflow-hidden rounded-[14px] border bg-card shadow-sm">
      <div className="flex items-center gap-2 px-4 pt-3 pb-1">
        <span className="size-2.5 rounded-full" style={{ background: dueñaColor.dot }} />
        <span className="text-[14px] font-semibold text-foreground truncate">{proyecto.nombre}</span>
        <span className="ml-auto shrink-0 rounded-full bg-muted px-2.5 py-px text-[11px] font-semibold text-muted-foreground">
          {proyecto.total_asignados}
        </span>
      </div>
      <p className="border-b px-4 pb-2.5 text-[11.5px] text-muted-foreground">
        Dueña: <strong className="font-medium text-foreground">{proyecto.empresa_nombre}</strong>
        {colaboradoras.length > 0
          ? <> · Colabora: <strong className="font-medium text-foreground">{colaboradoras.join(", ")}</strong></>
          : " · Sin colaboradoras"}
      </p>
      <div className="space-y-0.5 px-4 py-1 pb-3">
        {grupos.size === 0
          ? <p className="py-4 text-center text-xs text-muted-foreground">Sin personas asignadas.</p>
          : [...grupos.values()].map((grupo) => (
              <GrupoEmpresa key={grupo.nombre} empresaNombre={grupo.nombre}
                empleados={grupo.empleados} color={grupo.color} proyectoEmpresaId={proyecto.empresa_id} />
            ))
        }
      </div>
    </div>
  )
}

interface Props { data: OrgProyectosResponse }

export function CardsProyecto({ data }: Props) {
  const empresasOrden = data.empresas_orden.map((e) => e.id)

  if (data.proyectos.length === 0) return (
    <div className="flex flex-col items-center gap-2 py-16">
      <GitBranch className="size-8 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">No hay proyectos con asignaciones todavía.</p>
    </div>
  )

  return (
    <div>
      <GrillaTarjetas>
        {data.proyectos.map((p) => (
          <ProyectoCard key={p.id} proyecto={p} empresasOrden={empresasOrden} />
        ))}
      </GrillaTarjetas>
      <p className="mt-4 text-xs text-muted-foreground print:hidden">
        Cada proyecto tiene una empresa dueña y puede sumar colaboradoras. La gente se agrupa
        por su empresa de pertenencia. El tag "N proy." marca a quien está en más de un proyecto.
      </p>
    </div>
  )
}
