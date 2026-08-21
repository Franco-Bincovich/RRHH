"use client"

import { useRef, useState } from "react"
import { Building2, Upload } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Campo } from "@/components/ui/fichaPanel"
import { formatFecha } from "@/components/features/shared/fechas"
import { uploadLogo } from "@/services/empresas"
import type { Empresa } from "@/types/empresa"

/**
 * El panel de marca de la ficha de una empresa: el logo, el control para cambiarlo y desde cuándo
 * la sociedad existe en el sistema.
 *
 * 🔴 QUÉ QUEDÓ ACÁ Y QUÉ SUBIÓ A LA BARRA. El CUIT, el email, el teléfono y la dirección eran los
 * cuatro campos de esta grilla y ahora son los cuatro datos clave del encabezado (§3): son lo que
 * identifica a la sociedad, y para verlos había que entrar a una solapa. Lo que se quedó es lo
 * que no entra en una línea de texto —una imagen— más el dato que **no estaba en ninguna parte de
 * la pantalla**: desde cuándo está cargada. Sin él, una ficha vacía se lee igual si la crearon
 * ayer que si hace un año que nadie la completa.
 *
 * ⚠️ EL ERROR DE SUBIDA SIGUE SIENDO SILENCIOSO, tal como estaba: el `catch` no muestra nada y el
 * usuario reintenta. No se cambió acá porque avisar bien pide decidir qué se le dice (tamaño,
 * formato, permiso) y eso es una decisión de producto, no un ajuste de layout. Queda anotado.
 */
export function LogoPanel({ empresa, canWrite, onCambiado }: {
  empresa: Empresa
  canWrite: boolean
  onCambiado: (empresa: Empresa) => void
}) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [subiendo, setSubiendo] = useState(false)

  async function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setSubiendo(true)
    try {
      onCambiado(await uploadLogo(empresa.id, file))
    } catch {
      // error silencioso — usuario puede reintentar
    } finally {
      setSubiendo(false)
      if (fileInputRef.current) fileInputRef.current.value = ""
    }
  }

  return (
    <Card as="section" aria-label="Marca" className="h-fit">
      <h2 className="mb-3 text-base font-semibold text-foreground">Marca</h2>
      <div className="flex items-center gap-4">
        <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-xl border bg-muted">
          {empresa.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={empresa.logo_url} alt={`Logo de ${empresa.nombre}`} className="size-full object-contain" />
          ) : (
            <Building2 className="size-8 text-muted-foreground" aria-hidden="true" />
          )}
        </div>
        <div>
          <p className="mb-1 text-sm font-medium">Logo</p>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleLogoChange} />
          {canWrite && (
            <Button
              variant="outline"
              size="sm"
              className="min-h-9"
              onClick={() => fileInputRef.current?.click()}
              disabled={subiendo}
            >
              <Upload className="mr-1.5 size-3.5" />
              {subiendo ? "Subiendo..." : empresa.logo_url ? "Cambiar logo" : "Subir logo"}
            </Button>
          )}
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-1">
        <Campo label="Alta en el sistema" value={formatFecha(empresa.created_at)} />
      </dl>
    </Card>
  )
}
