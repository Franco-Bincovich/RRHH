"use client"

import type { ReactNode } from "react"
import { Accordion } from "@base-ui/react/accordion"
import { ChevronDown } from "lucide-react"

import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

export interface ConfigSectionProps {
  /** Id de la sección dentro del <Accordion.Root> de la página. */
  value: string
  /**
   * Glifo del círculo de la izquierda; el círculo lo pone esta shell.
   * OPCIONAL: las cards del dashboard no lo pasan. Ahí el círculo de 40px descuadraría la
   * grilla contra las cards vecinas que no son plegables y no tienen dónde ponerlo.
   */
  icon?: ReactNode
  /** Clases del círculo — cada sección trae su color. */
  iconClassName?: string
  title: string
  /**
   * Texto plano, NO ReactNode: se renderiza dentro del <button> del trigger, y un link o
   * un botón anidado ahí es HTML inválido — además de que el click plegaría la sección en
   * vez de seguir el link. Lo interactivo va en `children`, que sí está fuera del trigger.
   */
  description?: string
  /** Chip a la derecha del título: estado ("Conectado") o contador de lo que hay adentro. */
  badge?: ReactNode
  children: ReactNode
}

/**
 * La ÚNICA sección plegable del sistema: /configuracion y las cards del dashboard usan esta
 * shell, no dos. Vive en `features/configuracion/` porque nació ahí; es agnóstica del módulo.
 *
 * Presentacional puro: no sabe qué contiene, de dónde salen sus datos ni quién puede
 * escribirlos. El gate de permisos lo decide quien la renderiza — una sección que aparece
 * y falla al guardar es peor que una que no aparece.
 *
 * El estado abierto/cerrado lo tiene el <Accordion.Root> del que cuelga y NO se persiste: es
 * una preferencia de sesión, no un dato del usuario.
 *
 * ⚠️ PLEGADA NO MUESTRA NADA DEL CONTENIDO — ni un asomo, ni las primeras filas. Hubo un prop
 * `preview` para eso y se sacó: en las cards del dashboard dejaba 6 filas a la vista y la card
 * plegada terminaba ocupando casi lo mismo que abierta, o sea que se pagaba la complejidad del
 * acordeón sin recuperar la pantalla. Lo que resume el contenido va en `badge` (un contador),
 * que ocupa una línea compartida con el título. Si algún día hace falta un asomo de verdad,
 * es otro componente: la gracia de éste es que plegado mide siempre lo mismo.
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
          {icon && (
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-full ring-1 ring-border",
                iconClassName ?? "bg-primary/10",
              )}
            >
              {icon}
            </div>
          )}
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
