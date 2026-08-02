"use client"

import type { ReactNode } from "react"
import { Accordion } from "@base-ui/react/accordion"
import { ChevronDown } from "lucide-react"

import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

export interface ConfigSectionProps {
  /** Id de la sección dentro del <Accordion.Root> de la página. */
  value: string
  /** Glifo del círculo de la izquierda; el círculo lo pone esta shell. */
  icon: ReactNode
  /** Clases del círculo — cada sección trae su color. */
  iconClassName?: string
  title: string
  /**
   * Texto plano, NO ReactNode: se renderiza dentro del <button> del trigger, y un link o
   * un botón anidado ahí es HTML inválido — además de que el click plegaría la sección en
   * vez de seguir el link. Lo interactivo va en `children`, que sí está fuera del trigger.
   */
  description?: string
  /** Chip de estado a la derecha del título (p. ej. "Conectado"). */
  badge?: ReactNode
  children: ReactNode
}

/**
 * Una sección plegable de /configuracion.
 *
 * Presentacional puro: no sabe qué contiene, de dónde salen sus datos ni quién puede
 * escribirlos. El gate de permisos lo decide quien la renderiza — una sección que aparece
 * y falla al guardar es peor que una que no aparece.
 */
export function ConfigSection({
  value,
  icon,
  iconClassName,
  title,
  description,
  badge,
  children,
}: ConfigSectionProps) {
  return (
    <Accordion.Item value={value} className="rounded-xl border bg-card">
      <Accordion.Header>
        <Accordion.Trigger className="group flex w-full cursor-pointer items-start gap-3 p-5 text-left">
          <div
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-full ring-1 ring-border",
              iconClassName ?? "bg-primary/10",
            )}
          >
            {icon}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold">{title}</h2>
              {badge}
            </div>
            {description && (
              <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          <ChevronDown className="mt-1 size-4 shrink-0 text-muted-foreground transition-transform group-data-panel-open:rotate-180" />
        </Accordion.Trigger>
      </Accordion.Header>

      <Accordion.Panel className="overflow-hidden px-5 pb-5">
        <Separator className="mb-4" />
        {children}
      </Accordion.Panel>
    </Accordion.Item>
  )
}
