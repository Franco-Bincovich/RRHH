import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { FichaIdentidad, iniciales } from "@/components/ui/FichaIdentidad"
import type { ResultadoDetalle } from "@/types/assessment"

import { datosClaveAssessment } from "./_datosClaveAssessment"

/**
 * La barra de identidad de la ficha del RESULTADO de un assessment.
 *
 * 🔴 SON DOS CHIPS Y NO UNO, que es una desviación del patrón y está decidida. Un resultado de
 * assessment **no tiene estado** —no hay borrador, activo ni cerrado: existe o no existe—, así
 * que el lugar del chip de estado queda libre. Lo ocupan las dos cosas que sí clasifican al
 * resultado: el **perfil dominante** (la etiqueta cualitativa) y el **score general** (el número).
 * El score está acá y no abajo por una razón concreta: la grilla de "Scores por dimensión"
 * excluye la clave `general` a propósito —no es una dimensión—, así que si el chip no lo mostrara,
 * **el score general no aparecería en ninguna parte de la pantalla**.
 *
 * 🔴 NINGUNO DE LOS DOS ES `variant="default"`. El score venía con ese variant, o sea `bg-primary`:
 * el relleno de marca a la altura del título. Los dos usan ahora pares semánticos neutros — y son
 * neutros a propósito: **pintar un score de verde o de rojo sería decidir qué puntaje está bien**,
 * y eso no lo define ni el modelo ni este repo. El color de las dimensiones de abajo es otra cosa
 * (son series, no juicios); ver `_areasAssessment.ts`.
 *
 * Los dos chips desaparecen si su dato es nulo: un chip que dice "—" ocupa el lugar sin informar.
 */
export function BarraAssessment({ resultado, acciones }: {
  resultado: ResultadoDetalle
  acciones?: ReactNode
}) {
  const nombre = resultado.evaluado_nombre || "Evaluado"
  const CHIP = "bg-secondary text-secondary-foreground border-border"

  return (
    <FichaIdentidad
      volverA="/assessment"
      volverLabel="Assessment"
      actual={nombre}
      monograma={iniciales(nombre)}
      titulo={nombre}
      subtitulo={`Assessment ${resultado.tipo}`}
      chip={
        <>
          {resultado.perfil_dominante && (
            <Badge variant="outline" className={CHIP}>{resultado.perfil_dominante}</Badge>
          )}
          {resultado.score_general != null && (
            <Badge variant="outline" className={CHIP}>Score general {resultado.score_general}</Badge>
          )}
        </>
      }
      datos={datosClaveAssessment(resultado)}
      acciones={acciones}
    />
  )
}
