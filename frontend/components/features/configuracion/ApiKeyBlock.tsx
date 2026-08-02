"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export interface ApiKeyBlockProps {
  /** Id del input, para el <Label htmlFor>. */
  id: string
  /** Rótulo del campo cuando todavía no hay key cargada. */
  etiqueta: string
  placeholder: string
  conectada: boolean
  guardando: boolean
  /** Guarda la key; si resuelve `true` el campo se limpia. */
  onGuardar: (key: string) => Promise<boolean>
}

/**
 * Formulario de una API key.
 *
 * Anthropic y Zernio son el MISMO formulario con otro rótulo. Copiado en dos bloques, el día
 * que cambie el flujo cambiaría en uno solo; acá cambia en los dos o en ninguno.
 *
 * El valor tipeado es estado LOCAL a propósito: es un secreto en tránsito, no pertenece al
 * estado compartido de integraciones y se descarta apenas se guarda.
 */
export function ApiKeyBlock({
  id,
  etiqueta,
  placeholder,
  conectada,
  guardando,
  onGuardar,
}: ApiKeyBlockProps) {
  const [key, setKey] = useState("")

  const guardar = async () => {
    if (!key.trim()) return
    if (await onGuardar(key.trim())) setKey("")
  }

  return (
    <div className="space-y-3">
      {conectada && (
        <p className="text-sm text-muted-foreground">
          Key actual: <span className="font-mono tracking-widest">••••••••</span>
        </p>
      )}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <Label htmlFor={id} className="mb-1.5 block text-sm">
            {conectada ? "Nueva key (reemplaza la actual)" : etiqueta}
          </Label>
          <Input
            id={id}
            type="password"
            placeholder={placeholder}
            value={key}
            onChange={(e) => setKey(e.target.value)}
          />
        </div>
        <Button onClick={guardar} disabled={guardando || !key.trim()}>
          {guardando ? "Guardando…" : conectada ? "Actualizar" : "Guardar"}
        </Button>
      </div>
    </div>
  )
}
