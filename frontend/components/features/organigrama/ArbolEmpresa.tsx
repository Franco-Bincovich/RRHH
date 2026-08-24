"use client"

import { useCallback, useEffect, useState } from "react"
import { Users } from "lucide-react"

import { Card } from "@/components/ui/card"
import { colorByEmpresa, initials, ORG_TREE_CSS, type EmpresaColor } from "@/utils/colorEmpresa"
import { fetchOrgEmpresa } from "@/services/organigrama"
import type { AreaNodoAPI, EmpleadoNodoAPI, EmpresaNodoAPI } from "@/types/organigrama"

function EmpleadoNodo({ emp, color }: { emp: EmpleadoNodoAPI; color: EmpresaColor }) {
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
        {emp.cargo && (
          <span className="text-[10px] leading-tight text-muted-foreground">{emp.cargo}</span>
        )}
      </span>
    </Card>
  )
}

function AreaNodo({ area, color }: { area: AreaNodoAPI; color: EmpresaColor }) {
  return (
    <>
      <Card padding="none" interactive className="inline-flex flex-col items-center gap-0.5 px-4 py-2 shadow-sm whitespace-nowrap">
        <span className="text-[12.5px] font-semibold text-foreground">{area.nombre}</span>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          Área · {area.total_empleados}
        </span>
      </Card>
      {area.empleados.length > 0 && (
        <ul>
          {area.empleados.map((emp) => (
            <li key={emp.id}>
              <EmpleadoNodo emp={emp} color={color} />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

export function ArbolEmpresa() {
  const [empresas, setEmpresas] = useState<EmpresaNodoAPI[]>([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setEmpresas(await fetchOrgEmpresa()) }
    catch { setError("No se pudo cargar el organigrama.") }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const empresasOrden = empresas.map((e) => e.id)

  if (loading) return (
    <div className="flex flex-col items-center gap-4 pt-6 animate-pulse">
      <div className="h-12 w-40 rounded-xl bg-muted" />
      <div className="flex gap-6">
        {[1, 2, 3].map((i) => <div key={i} className="h-24 w-32 rounded-xl bg-muted" />)}
      </div>
    </div>
  )
  if (error) return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  if (empresas.length === 0) return (
    <div className="flex flex-col items-center gap-2 py-16">
      <Users className="size-8 text-muted-foreground" />
      <p className="text-sm text-muted-foreground">No hay áreas ni colaboradores cargados.</p>
    </div>
  )

  return (
    <>
      <style>{ORG_TREE_CSS}</style>
      <div className="overflow-x-auto pb-8">
        <div className="org-tree inline-block min-w-full text-center">
          <ul>
            {empresas.map((empresa) => {
              const color = colorByEmpresa(empresa.id, empresasOrden)
              return (
                <li key={empresa.id}>
                  <div className="inline-flex flex-col items-center gap-0.5 rounded-xl border-t-[3px] bg-card px-5 py-2.5 shadow-sm whitespace-nowrap"
                    style={{ borderTopColor: color.dot }}>
                    <span className="text-[12.5px] font-semibold text-foreground">{empresa.nombre}</span>
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      {empresa.total_empleados} colaboradores
                    </span>
                  </div>
                  {empresa.areas.length > 0 && (
                    <ul>
                      {empresa.areas.map((area) => (
                        <li key={area.id}>
                          <AreaNodo area={area} color={color} />
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
    </>
  )
}
