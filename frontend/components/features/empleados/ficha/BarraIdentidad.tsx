import Link from "next/link"
import { ChevronRight } from "lucide-react"
import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import type { Empleado } from "@/types/empleado"

import { ESTADO_ESTILO, etiquetaEstado } from "../_estadoEmpleado"
import { datosClave } from "./_datosClave"

/**
 * La BARRA DE IDENTIDAD del patrón "Ficha de detalle" (`docs/SISTEMA-DE-DISENO.md` §3): migas de
 * pan, monograma de 46px, nombre, chip de estado, cuatro datos clave en una línea y las acciones
 * a la derecha con la primaria al final.
 *
 * Reemplaza al `<PageHeader>` + botón "Volver" que la ficha tenía. La diferencia no es estética:
 * el encabezado anterior mostraba el nombre y el rol y nada más, así que para saber de qué empresa
 * era la persona, quién es su superior o desde cuándo trabaja había que bajar a leer el panel
 * laboral — que son los cuatro datos con los que se decide qué hacer con la ficha.
 *
 * 🔴 EL ORDEN DE LAS ACCIONES LO PONE EL LLAMADOR, y la primaria va ÚLTIMA (§3). No se ordena acá
 * porque este componente no sabe cuál es la primaria de cada ficha; lo que sí hace es ponerlas
 * todas juntas a la derecha, alineadas al final.
 */
export function BarraIdentidad({ empleado, acciones }: { empleado: Empleado; acciones?: ReactNode }) {
  const nombre = `${empleado.nombre} ${empleado.apellido}`
  const rol = (empleado.roles ?? []).join(", ") || empleado.cargo || "Sin rol asignado"

  return (
    <div className="mb-4">
      <nav aria-label="Migas de pan" className="mb-3 flex items-center gap-1 text-xs text-muted-foreground">
        <Link href="/empleados" className="rounded-sm underline-offset-2 hover:text-foreground hover:underline">
          Colaboradores
        </Link>
        <ChevronRight className="size-3" aria-hidden="true" />
        {/* La miga actual NO es un link: llevaría a la página en la que ya estás. */}
        <span className="text-foreground" aria-current="page">{nombre}</span>
      </nav>

      <Card as="section" aria-label="Identidad" className="flex flex-wrap items-start gap-4">
        {/* Monograma de 46px. Neutro a propósito: el único relleno fuerte de la barra es el botón
            primario, y un círculo azul de 46px al lado le gana por tamaño. */}
        <div
          aria-hidden="true"
          className="flex size-[46px] shrink-0 items-center justify-center rounded-full bg-secondary text-base font-semibold text-secondary-foreground"
        >
          {(empleado.nombre[0] ?? "").toUpperCase()}{(empleado.apellido[0] ?? "").toUpperCase()}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-semibold text-foreground">{nombre}</h1>
            <Badge variant="outline" className={ESTADO_ESTILO[empleado.estado] ?? ""}>
              {etiquetaEstado(empleado.estado)}
            </Badge>
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">{rol}</p>

          {/* Los cuatro datos clave, en UNA línea. El porqué de cuáles son, en `_datosClave.ts`. */}
          <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
            {datosClave(empleado).map((d) => (
              <div key={d.label} className="min-w-0">
                <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {d.label}
                </dt>
                <dd className="truncate text-sm text-foreground">{d.valor}</dd>
              </div>
            ))}
          </dl>
        </div>

        {acciones && <div className="flex flex-wrap items-center gap-2 sm:ml-auto">{acciones}</div>}
      </Card>
    </div>
  )
}
