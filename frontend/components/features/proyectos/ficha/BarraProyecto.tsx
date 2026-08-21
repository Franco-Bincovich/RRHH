import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { FichaIdentidad, iniciales } from "@/components/ui/FichaIdentidad"
import type { Proyecto } from "@/types/proyecto"

import { ESTADO_ESTILO } from "../ProyectoCard"
import { datosClaveProyecto } from "./_datosClaveProyecto"

/**
 * La barra de identidad de la ficha de un PROYECTO. Reemplaza al `<PageHeader>` + la flecha de
 * volver que la pantalla tenía sueltos en una fila de flex.
 *
 * 🔴 EL CHIP REUSA `ESTADO_ESTILO` DE `ProyectoCard`, que ya existe y ya está testeado. La barra
 * anterior usaba un `ESTADO_VARIANT` propio, declarado en la página, donde `activo` era
 * `variant="default"` —o sea `bg-primary`—: un relleno azul pegado al botón "Editar", que es el
 * otro relleno azul de la barra. Los dos mapas describían el mismo dato con distinto criterio; el
 * de la página se borró.
 *
 * 🔴 EL SUBTÍTULO ES LA DESCRIPCIÓN Y NO LA EMPRESA, y el cambio es a propósito: la empresa pasó
 * a ser uno de los cuatro datos clave, y repetirla en el subtítulo gastaría el renglón que hoy
 * muestra la descripción — que hasta esta tanda no se veía en ninguna parte de la ficha.
 */
export function BarraProyecto({ proyecto, acciones }: { proyecto: Proyecto; acciones?: ReactNode }) {
  return (
    <FichaIdentidad
      volverA="/proyectos"
      volverLabel="Proyectos"
      actual={proyecto.nombre}
      monograma={iniciales(proyecto.nombre)}
      titulo={proyecto.nombre}
      subtitulo={proyecto.descripcion || "Sin descripción"}
      chip={
        <Badge variant="outline" className={`capitalize ${ESTADO_ESTILO[proyecto.estado]}`}>
          {proyecto.estado}
        </Badge>
      }
      datos={datosClaveProyecto(proyecto)}
      acciones={acciones}
    />
  )
}
