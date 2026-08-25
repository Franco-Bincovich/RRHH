"use client"

import { useEffect, useState } from "react"
import { Building2, ChevronsUpDown } from "lucide-react"

import { Select } from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { useCatalogoPermitido } from "@/hooks/useCatalogoPermitido"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId, setEmpresaActivaId } from "@/services/empresaStore"
import type { Empresa } from "@/types/empresa"

/**
 * Selector de empresa activa. Persiste en localStorage vía empresaStore.
 * Al cambiar, recarga la página para que todos los listados usen la nueva empresa.
 *
 * 🔴 NO PIDE `/api/empresas` SI EL ROL NO PUEDE LEERLAS. Este componente vive en TODAS las
 * pantallas, y `mandos_medios` no tiene `Seccion.EMPRESA + READ`: hasta el 25/8/2026 eso era un
 * **403 por cada navegación**, tragado por el `.catch` y visible sólo en la consola. Ver
 * `hooks/useCatalogoPermitido`, donde está por qué la salida no es ampliarle el permiso.
 */
export function EmpresaSelector() {
  const puedeLeerEmpresas = useCatalogoPermitido("empresa")
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [current, setCurrent] = useState<string>("todas")

  useEffect(() => {
    setCurrent(getEmpresaActivaId() ?? "todas")
    if (!puedeLeerEmpresas) return
    fetchEmpresas()
      .then((res) => setEmpresas(res.items.filter((e) => e.activa)))
      .catch(() => {})
  }, [puedeLeerEmpresas])

  if (empresas.length === 0) return null

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    setEmpresaActivaId(val === "todas" ? null : val)
    window.location.reload()
  }

  return (
    <div className="px-3 pb-2">
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-2.5 flex items-center">
          <Building2 className="size-3.5 text-sidebar-foreground/60" />
        </div>
        <Select
          size="sm"
          value={current}
          onChange={handleChange}
          aria-label="Empresa activa"
          /*
           * El ÚNICO select del producto que no usa la paleta de formulario: vive dentro del
           * sidebar, que tiene su propia superficie (`--sidebar-accent`) y su propio texto
           * (`--sidebar-foreground`) en los dos temas. Lo que queda acá es exactamente eso —
           * el resto (alto, radio, foco, estado deshabilitado) lo pone el componente.
           *
           * 🔴 `dark:bg-sidebar-accent` no es redundante con el `bg-sidebar-accent` de al lado.
           * La base del componente trae `dark:bg-input/30` para igualar a `<Input>`, y en modo
           * oscuro esa variante le gana a un `bg-*` sin prefijo: sin esta línea el selector de
           * empresa se pintaría con el fondo de los inputs y se despegaría del sidebar.
           *
           * `appearance-none` + `pl-7 pr-7` sostienen los dos íconos absolutos que lo rodean
           * (el edificio a la izquierda, el chevron a la derecha): sin esconder la flecha nativa
           * habría dos flechas.
           */
          className={cn(
            "appearance-none border-sidebar-border pl-7 pr-7 text-xs font-medium",
            "bg-sidebar-accent text-sidebar-foreground dark:bg-sidebar-accent",
            "cursor-pointer transition-colors hover:bg-sidebar-accent/80",
          )}
        >
          <option value="todas">Todas las empresas</option>
          {empresas.map((e) => (
            <option key={e.id} value={e.id}>{e.nombre}</option>
          ))}
        </Select>
        <div className="pointer-events-none absolute inset-y-0 right-2 flex items-center">
          <ChevronsUpDown className="size-3 text-sidebar-foreground/60" />
        </div>
      </div>
      {current !== "todas" && (
        <p className="text-xs text-muted-foreground mt-1 truncate px-1">
          {empresas.find((e) => e.id === current)?.nombre}
        </p>
      )}
    </div>
  )
}
