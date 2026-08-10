"use client"

import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { ClienteConHoras } from "@/types/horasCliente"

const MODALIDAD: Record<string, string> = { home_office: "Home Office", on_site: "On site" }

interface Props {
  clientes: ClienteConHoras[]
  onVerDetalle: (empleadoId: string, empleadoNombre: string) => void
}

/**
 * Los clientes colapsables con su detalle por empleado.
 *
 * ⚠️ El toggle es `useState` LOCAL y no un `<details>` nativo: hace falta saber qué grupo está
 * abierto para el aria-expanded y para que el estado sobreviva a un re-render del padre cuando
 * cambia el mes. No hay portal ni efecto, así que el markup se puede afirmar a string.
 *
 * ⚠️ "Ver detalle" se OMITE cuando la línea no tiene `empleado_id` — no se deshabilita. Un
 * `disabled` sobre el Button de shadcn no se puede afirmar en un test (el markup trae la clase
 * `disabled:` siempre) y además un botón muerto invita a clickearlo.
 *
 * El BORRAR no vive acá sino en el modal de detalle: se borra una carga de un día concreto, y
 * una línea de esta tabla es la SUMA de varias. Un botón de borrar sobre un agregado tendría que
 * elegir cuál de las cargas se lleva, que es una pregunta que el usuario no hizo.
 */
export function ClientesColapsables({ clientes, onVerDetalle }: Props) {
  const [abiertos, setAbiertos] = useState<Record<string, boolean>>({})
  const clave = (c: ClienteConHoras) => c.cliente_id ?? "sin-cliente"

  return (
    <div className="space-y-2">
      {clientes.map((c) => {
        const k = clave(c)
        const abierto = Boolean(abiertos[k])
        return (
          <div key={k} className="overflow-hidden rounded-lg border bg-card">
            <button
              type="button"
              aria-expanded={abierto}
              className="flex w-full items-center justify-between gap-3 p-4 text-left"
              onClick={() => setAbiertos((p) => ({ ...p, [k]: !p[k] }))}
            >
              <span className="flex items-center gap-2 font-medium text-foreground">
                {abierto ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
                {c.cliente_nombre}
              </span>
              <span className="text-sm tabular-nums text-muted-foreground">
                {c.horas} h · {c.registros} registro{c.registros !== 1 ? "s" : ""}
              </span>
            </button>
            {abierto && (
              <div className="border-t">
                {c.lineas.map((ln, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                    <div className="min-w-0">
                      <span className="font-medium text-foreground">
                        {ln.empleado_nombre ?? "Sin empleado"}
                      </span>
                      <span className="ml-2 text-xs text-muted-foreground">
                        {[ln.proyecto_texto, ln.tarea_texto,
                          ln.modalidad ? MODALIDAD[ln.modalidad] : null]
                          .filter(Boolean).join(" · ") || "Sin detalle"}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="tabular-nums text-foreground">{ln.horas} h</span>
                      {ln.empleado_id && (
                        <Button variant="ghost" size="sm"
                                aria-label={`Ver detalle de ${ln.empleado_nombre ?? ""}`}
                                onClick={() => onVerDetalle(ln.empleado_id as string,
                                                            ln.empleado_nombre ?? "")}>
                          Ver detalle
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
