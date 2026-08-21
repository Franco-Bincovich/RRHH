import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { FichaIdentidad, iniciales } from "@/components/ui/FichaIdentidad"
import type { OnboardingTemplate } from "@/types/onboarding"

import { InlineEdit } from "../InlineEdit"
import { datosClaveTemplate } from "./_datosClaveTemplate"

/**
 * La barra de identidad de la ficha de un TEMPLATE de onboarding.
 *
 * 🔴 EL TÍTULO Y EL SUBTÍTULO SIGUEN SIENDO EDITABLES EN EL LUGAR, y por eso `FichaIdentidad` los
 * recibe como nodos y no como strings. Es la única de las seis fichas que edita su propio nombre
 * sin abrir un modal, y forzar texto plano acá habría dejado a esta pantalla afuera del patrón —o
 * peor, le habría sacado una capacidad que ya tenía para que entrara.
 *
 * 🔴 EL CHIP DICE LA VISIBILIDAD AUNQUE EL CONTROL DE AL LADO DIGA LO MISMO, y la repetición es
 * deliberada. El `VisibilidadToggle` sólo se dibuja con permiso de escritura, así que hasta ahora
 * un rol de sólo lectura **no tenía forma de saber si una plantilla era privada** —que es
 * justamente lo que explica por qué no le aparece en la lista a un compañero—. El chip es el
 * ESTADO y está siempre; el toggle es el CONTROL y está para quien puede accionarlo. La
 * alternativa —esconder el chip cuando hay toggle— haría que la barra cambie de forma según el
 * rol, que es peor que decir dos veces una palabra.
 *
 * El chip usa los pares semánticos y NO `variant="default"`: privada es ATENCIÓN (es la que
 * explica una ausencia), compartida es NEUTRO (es el caso normal, no un logro).
 */
export function BarraTemplate({ template, onGuardarCampo, canWrite, acciones }: {
  template: OnboardingTemplate
  onGuardarCampo: (campo: "nombre" | "descripcion", valor: string) => Promise<void>
  canWrite: boolean
  acciones?: ReactNode
}) {
  return (
    <FichaIdentidad
      volverA="/onboarding/templates"
      volverLabel="Templates"
      actual={template.nombre}
      monograma={iniciales(template.nombre)}
      titulo={
        <InlineEdit
          value={template.nombre}
          onSave={(v) => onGuardarCampo("nombre", v)}
          className="text-lg font-semibold text-foreground"
          placeholder="Nombre del template"
          canEdit={canWrite}
        />
      }
      subtitulo={
        <InlineEdit
          value={template.descripcion ?? ""}
          onSave={(v) => onGuardarCampo("descripcion", v)}
          className="text-sm text-muted-foreground"
          multiline
          placeholder="Agregar descripción…"
          canEdit={canWrite}
        />
      }
      chip={
        <Badge
          variant="outline"
          className={
            template.es_publica
              ? "bg-secondary text-secondary-foreground border-border"
              : "bg-warning-wash text-warning border-warning-line"
          }
        >
          {template.es_publica ? "Compartida" : "Privada"}
        </Badge>
      }
      datos={datosClaveTemplate(template)}
      acciones={acciones}
    />
  )
}
