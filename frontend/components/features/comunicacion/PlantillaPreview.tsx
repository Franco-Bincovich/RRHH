"use client"

import type { PreviewResponse } from "@/types/plantillas"

/**
 * El preview de una plantilla, tal como lo devuelve el backend.
 *
 * Se renderiza con el MISMO renderer que el envío (una sola implementación, en el servidor): lo
 * que se ve acá es literalmente lo que va a recibir el destinatario. Dos renderers —uno de
 * preview y otro de envío— divergirían, que es la lección de los filtros duplicados front/back.
 */
export function PlantillaPreview({ preview }: { preview: PreviewResponse }) {
  return (
    <div className="rounded-lg border p-3">
      <p className="mb-1 text-sm font-medium">{preview.asunto}</p>
      {/* 🔴 EL ÚNICO dangerouslySetInnerHTML DEL REPO, y hay que entender por qué es seguro
          acá antes de copiarlo a otro lado. Este HTML NO viene del usuario: lo genera
          `services/mailer/_markdown.a_html` EN EL SERVIDOR, que escapa el texto entero primero
          y recién después aplica un conjunto cerrado de marcas (negrita, itálica, links
          http/https, listas). El usuario escribe Markdown, nunca HTML — justamente para que
          este renderizado sea el mismo que recibe el destinatario, sin una segunda
          implementación que pueda divergir.
          ⚠️ Si algún día el cuerpo pasara a ser HTML editable, esto DEJA de ser seguro. */}
      <div className="text-sm" dangerouslySetInnerHTML={{ __html: preview.cuerpo_html }} />
      {preview.faltantes.length > 0 && (
        <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
          Sin datos: {preview.faltantes.join(", ")} — el mail va a salir con ese hueco.
        </p>
      )}
      {!preview.con_datos_reales && (
        <p className="mt-1 text-xs text-muted-foreground">
          Vista con datos de ejemplo. Elegí un colaborador para ver los huecos reales.
        </p>
      )}
    </div>
  )
}
