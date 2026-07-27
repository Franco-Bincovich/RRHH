"use client"

import { useEffect, useState } from "react"

import { Label } from "@/components/ui/label"
import { fetchEmpleados } from "@/services/empleados"
import { fetchEmpresas } from "@/services/empresas"
import { fetchEquipo } from "@/services/equipo"
import type { Empleado } from "@/types/empleado"
import type { Empresa } from "@/types/empresa"
import type { EquipoMiembro } from "@/types/equipo"

interface SeleccionEmpleadoProps {
  isMando: boolean
  empresaId: string
  empleadoId: string
  onEmpresaChange: (empresaId: string) => void
  onEmpleadoChange: (empleadoId: string) => void
  errorEmpresa?: string
  errorEmpleado?: string
}

const SELECT_CLASS =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50"

/**
 * Bloque Empresa + Empleado del alta de vacaciones/ausencias, con la lógica de rol
 * encapsulada:
 *  - mandos_medios: SIN campo Empresa; Empleado se puebla desde el roster de ownership
 *    (GET /api/equipo, cross-empresa) y arranca habilitado. Cada opción = "Apellido,
 *    Nombre — Empresa" para desambiguar entre empresas.
 *  - admin/gerencia: comportamiento clásico — Empresa visible + Empleado por empresa.
 * El estado del form vive en el modal padre; este componente solo fetchea y notifica.
 */
export function SeleccionEmpleado({
  isMando, empresaId, empleadoId, onEmpresaChange, onEmpleadoChange, errorEmpresa, errorEmpleado,
}: SeleccionEmpleadoProps) {
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [equipo, setEquipo] = useState<EquipoMiembro[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isMando) return
    setLoading(true)
    fetchEquipo().then(setEquipo).catch(() => setEquipo([])).finally(() => setLoading(false))
  }, [isMando])

  useEffect(() => {
    if (isMando) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => setEmpresas([]))
  }, [isMando])

  useEffect(() => {
    if (isMando || !empresaId) { setEmpleados([]); return }
    setLoading(true)
    fetchEmpleados({ page: 1, pageSize: 100, estado: "activo", empresaId })
      .then((r) => setEmpleados(r.items)).catch(() => setEmpleados([])).finally(() => setLoading(false))
  }, [isMando, empresaId])

  if (isMando) {
    return (
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empleado_id">Empleado <span className="text-destructive" aria-hidden>*</span></Label>
        <select id="empleado_id" className={SELECT_CLASS} value={empleadoId} onChange={(e) => onEmpleadoChange(e.target.value)} disabled={loading} aria-required aria-invalid={Boolean(errorEmpleado)}>
          <option value="">{loading ? "Cargando..." : "Seleccionar empleado"}</option>
          {equipo.map((m) => (
            <option key={m.id} value={m.id}>{m.apellido}, {m.nombre}{m.empresa ? ` — ${m.empresa}` : ""}</option>
          ))}
        </select>
        {errorEmpleado && <p className="text-xs text-destructive" role="alert">{errorEmpleado}</p>}
      </div>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empresa_id">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
        <select id="empresa_id" className={SELECT_CLASS} value={empresaId} onChange={(e) => onEmpresaChange(e.target.value)} aria-required aria-invalid={Boolean(errorEmpresa)}>
          <option value="">Seleccionar empresa</option>
          {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
        </select>
        {errorEmpresa && <p className="text-xs text-destructive" role="alert">{errorEmpresa}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empleado_id">Empleado <span className="text-destructive" aria-hidden>*</span></Label>
        <select id="empleado_id" className={SELECT_CLASS} value={empleadoId} onChange={(e) => onEmpleadoChange(e.target.value)} disabled={!empresaId || loading} aria-required aria-invalid={Boolean(errorEmpleado)}>
          <option value="">
            {!empresaId ? "Seleccioná primero una empresa" : loading ? "Cargando..." : "Seleccionar empleado"}
          </option>
          {empleados.map((e) => <option key={e.id} value={e.id}>{e.nombre} {e.apellido}</option>)}
        </select>
        {errorEmpleado && <p className="text-xs text-destructive" role="alert">{errorEmpleado}</p>}
      </div>
    </>
  )
}
