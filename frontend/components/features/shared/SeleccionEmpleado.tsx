"use client"

import { useEffect, useState } from "react"

import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { fetchEmpresas } from "@/services/empresas"
import { fetchEquipo } from "@/services/equipo"
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

  // Los empleados de la rama admin/gerencia ya no se precargan: los busca `EmpleadoCombobox`
  // contra el backend. La rama `isMando` SIGUE con `fetchEquipo` — ver el comentario de abajo.

  // 🔴 ESTA RAMA NO USA `EmpleadoCombobox`, Y NO ES UN OLVIDO. `mandos_medios` no tiene permiso
  // sobre `Seccion.EMPLEADOS`, así que buscar contra `/api/empleados` le daría 403 donde hoy
  // funciona. Su universo es `/api/equipo` (roster por ownership, cross-empresa, sin paginar) y
  // es CORTO por definición: son sus subordinados, no el padrón. No hay truncamiento que sacar.
  if (isMando) {
    return (
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empleado_id">Colaborador <span className="text-destructive" aria-hidden>*</span></Label>
        <Select id="empleado_id" value={empleadoId} onChange={(e) => onEmpleadoChange(e.target.value)} disabled={loading} aria-required aria-invalid={Boolean(errorEmpleado)}>
          <option value="">{loading ? "Cargando..." : "Seleccionar colaborador"}</option>
          {equipo.map((m) => (
            <option key={m.id} value={m.id}>{m.apellido}, {m.nombre}{m.empresa ? ` — ${m.empresa}` : ""}</option>
          ))}
        </Select>
        {errorEmpleado && <p className="text-xs text-destructive" role="alert">{errorEmpleado}</p>}
      </div>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empresa_id">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
        <Select id="empresa_id" value={empresaId} onChange={(e) => onEmpresaChange(e.target.value)} aria-required aria-invalid={Boolean(errorEmpresa)}>
          <option value="">Seleccionar empresa</option>
          {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
        </Select>
        {errorEmpresa && <p className="text-xs text-destructive" role="alert">{errorEmpresa}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="empleado_id">Colaborador <span className="text-destructive" aria-hidden>*</span></Label>
        <EmpleadoCombobox
          id="empleado_id" value={empleadoId} empresaId={empresaId || undefined}
          disabled={!empresaId} mensajeDeshabilitado="Seleccioná primero una empresa"
          invalid={Boolean(errorEmpleado)}
          onChange={(e) => onEmpleadoChange(e?.id ?? "")}
        />
        {errorEmpleado && <p className="text-xs text-destructive" role="alert">{errorEmpleado}</p>}
      </div>
    </>
  )
}
