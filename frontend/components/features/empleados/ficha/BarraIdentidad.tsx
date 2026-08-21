import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { FichaIdentidad } from "@/components/ui/FichaIdentidad"
import type { Empleado } from "@/types/empleado"

import { ESTADO_ESTILO, etiquetaEstado } from "../_estadoEmpleado"
import { datosClave } from "./_datosClave"

/**
 * La barra de identidad de la ficha de un LEGAJO: el patrón genérico
 * (`components/ui/FichaIdentidad.tsx`) con lo que es propio de un empleado —el monograma de sus
 * iniciales, el rol como subtítulo, el chip de estado y los cuatro datos de `_datosClave`.
 *
 * Reemplazó al `<PageHeader>` + botón "Volver" que la ficha tenía. La diferencia no es estética:
 * el encabezado anterior mostraba el nombre y el rol y nada más, así que para saber de qué empresa
 * era la persona, quién es su superior o desde cuándo trabaja había que bajar a leer el panel
 * laboral — que son los cuatro datos con los que se decide qué hacer con la ficha.
 *
 * 🔴 LA FORMA SE FUE AL PRIMITIVO CUANDO APARECIÓ LA SEGUNDA FICHA, y este archivo se quedó sólo
 * con lo que ninguna otra entidad comparte. Copiar la barra habría dejado seis que se ven iguales
 * hasta que una cambia.
 */
export function BarraIdentidad({ empleado, acciones }: { empleado: Empleado; acciones?: ReactNode }) {
  const nombre = `${empleado.nombre} ${empleado.apellido}`

  return (
    <FichaIdentidad
      volverA="/empleados"
      volverLabel="Colaboradores"
      actual={nombre}
      monograma={`${(empleado.nombre[0] ?? "").toUpperCase()}${(empleado.apellido[0] ?? "").toUpperCase()}`}
      titulo={nombre}
      subtitulo={(empleado.roles ?? []).join(", ") || empleado.cargo || "Sin rol asignado"}
      chip={
        <Badge variant="outline" className={ESTADO_ESTILO[empleado.estado] ?? ""}>
          {etiquetaEstado(empleado.estado)}
        </Badge>
      }
      datos={datosClave(empleado)}
      acciones={acciones}
    />
  )
}
