import { Badge } from "@/components/ui/badge"
import type { EstadoCandidato } from "@/types/candidato"

/**
 * SI LA POSTULACIÓN SIGUE VIVA. El otro eje de la ficha de un candidato.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 POR QUÉ ESTE COMPONENTE EXISTE — LA TARJETA DECÍA "OFERTA" DESPUÉS DE CONTRATAR
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Reportado el 24/8/2026: se contrata a alguien, el panel deja de ofrecer "Contratar" —o sea que
 * el sistema SÍ sabe que ya no está disponible— y la tarjeta sigue diciendo **Oferta**.
 *
 * 🔑 **Y NO ERA UN PROBLEMA DE REFRESCO.** `onContratado` ya llamaba a `refetch()` y los datos
 * que llegaban eran correctos. Lo que pasaba es que la fila mostraba UN SOLO EJE de los dos:
 *   · `etapa_pipeline` — **DÓNDE llegó** en el proceso. `contratar` **no la toca a propósito**
 *     (`services/_candidato_contratar.py:13-15`): "oferta" es la última etapa del CHECK y ahí se
 *     queda, porque pisarla perdería en qué punto se cerró cada búsqueda, que es la métrica del
 *     embudo.
 *   · `estado` — **CÓMO terminó**. Es lo que `contratar` escribe (`contratado`).
 * La fila pintaba la etapa y **`estado` no se renderizaba en NINGÚN lugar del front**: su único
 * uso en todo el código era el booleano `contratable` de `CandidatoAcciones`. O sea que el dato
 * viajaba por HTTP, estaba tipado, y el usuario no podía verlo nunca.
 *
 * Por eso el arreglo es mostrar el eje que faltaba y no "refrescar mejor": el dato estaba fresco.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 SÓLO SE PINTA CUANDO EL ESTADO **NO** ES `activo`
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `activo` es el estado de casi todas las filas: un chip "Activo" en cada una sería ruido en
 * todas y no informaría en ninguna — mismo criterio con el que `ClasificacionBadge` no pinta
 * "Sin clasificar" en el listado. Lo que hay que poder ver de un vistazo es la EXCEPCIÓN: quién
 * ya se contrató, quién se descartó, a quién se dejó en espera.
 *
 * ⚠️ Y NO REEMPLAZA a la etiqueta de etapa: las dos son ciertas y dicen cosas distintas
 * ("llegó hasta la oferta" + "se contrató"). Reemplazarla borraría el dato del embudo de la
 * pantalla, que es justo lo que el backend se cuidó de no pisar.
 */

/** El vocabulario tal como lo lee alguien de Capital Humano, no el literal del CHECK. */
const LABELS: Record<EstadoCandidato, string> = {
  activo: "Activo",
  contratado: "Contratado",
  descartado: "Descartado",
  en_espera: "En espera",
}

/**
 * 🔑 `contratado` es el ÚNICO con color propio, y es el mismo verde que `ClasificacionBadge` usa
 * para "relevante": es el desenlace bueno y el que el usuario busca confirmar después de apretar
 * el botón. `descartado` y `en_espera` van en gris —no en rojo— por el mismo motivo que ese
 * archivo explica para `no_relevante`: un rojo se lee como error del sistema, y descartar a un
 * candidato es una decisión normal del proceso, no una falla.
 */
const ESTILOS: Partial<Record<EstadoCandidato, string>> = {
  contratado: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
}

export function EstadoCandidatoBadge({ estado }: { estado: EstadoCandidato }) {
  if (estado === "activo") return null

  return (
    <Badge variant="outline" className={ESTILOS[estado]}>
      {LABELS[estado] ?? estado}
    </Badge>
  )
}
