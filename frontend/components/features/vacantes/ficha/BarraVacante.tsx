import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { FichaIdentidad, iniciales } from "@/components/ui/FichaIdentidad"
import type { Vacante } from "@/types/vacantes"

import { ESTADO_ESTILO, ESTADO_LABEL } from "../_grillaVacantes"
import { datosClaveVacante } from "./_datosClaveVacante"

/**
 * La barra de identidad de la ficha de una VACANTE.
 *
 * 🔴 EL CHIP REUSA `ESTADO_ESTILO` DEL LISTADO, que ya existe y ya está testeado. La ficha tenía
 * su propio `ESTADO_VARIANTS` escrito en la página, donde `en_proceso` era `variant="default"` —el
 * relleno de marca— y `cerrada` era `destructive` sólido: la misma vacante se veía de un color en
 * el listado y de otro en su ficha. Ese mapa se borró.
 *
 * 🔴 EL SUBTÍTULO ES LA DESCRIPCIÓN Y ANTES ERA EL ÁREA. El área subió a los cuatro datos clave, y
 * el renglón quedó para la descripción, que vivía en una tarjeta suelta debajo del encabezado
 * junto con el estado y la fecha de apertura — los tres datos que ahora están acá arriba. Esa
 * tarjeta se borró: no le quedaba nada adentro.
 */
export function BarraVacante({ vacante, candidatos, acciones }: {
  vacante: Vacante
  /** Cuántos candidatos tiene el pipeline. Por qué el largo del array alcanza: `_datosClaveVacante`. */
  candidatos: number
  acciones?: ReactNode
}) {
  return (
    <FichaIdentidad
      volverA="/vacantes"
      volverLabel="Vacantes"
      actual={vacante.titulo}
      monograma={iniciales(vacante.titulo)}
      titulo={vacante.titulo}
      subtitulo={vacante.descripcion || "Sin descripción"}
      chip={
        <Badge variant="outline" className={ESTADO_ESTILO[vacante.estado]}>
          {ESTADO_LABEL[vacante.estado]}
        </Badge>
      }
      datos={datosClaveVacante(vacante, candidatos)}
      acciones={acciones}
    />
  )
}
