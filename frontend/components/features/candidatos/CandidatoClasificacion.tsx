import { ClasificacionBadge, LeyendaDescarte } from "@/components/features/candidatos/ClasificacionBadge"
import { CorregirClasificacion } from "@/components/features/screening/CorregirClasificacion"
import type { CandidatoConGrupo } from "@/types/candidato"

/**
 * La preselección en la ficha del candidato: etiqueta, motivo y la leyenda del filtro.
 *
 * Componente aparte y no inline en `CandidatoDetailPanel` porque ese archivo estaba en 145/150.
 *
 * 🔴 EL MOTIVO VA SIEMPRE QUE EXISTA, al lado de la etiqueta y con el mismo peso. Una etiqueta
 * sola —"No relevante"— se lee como un veredicto; con el motivo al lado ("Perfil en gastronomía,
 * la búsqueda es contable") se lee como lo que es: una observación que un humano puede descartar
 * en dos segundos. Esa diferencia es el módulo entero.
 *
 * A diferencia de la fila del listado, acá la etiqueta se muestra SIEMPRE, incluso sin clasificar:
 * en la ficha la pregunta "¿esto ya pasó por el filtro?" es pertinente y su respuesta cambia qué
 * hace RRHH (correr el botón en la búsqueda, o leer el CV a mano).
 */
export function CandidatoClasificacion({ candidato, onCorregido }: {
  candidato: CandidatoConGrupo
  onCorregido?: () => void
}) {
  return (
    <div className="space-y-2">
      <ClasificacionBadge
        clasificacion={candidato.clasificacion_ia}
        sinTexto={Boolean(candidato.screening_warning)}
        // Llegó al modelo y falló: hay motivo y no hay clasificación. Reintentable.
        fallo={!candidato.clasificacion_ia && Boolean(candidato.clasificacion_motivo)}
      />
      {candidato.clasificacion_motivo && (
        <p className="text-sm text-foreground">{candidato.clasificacion_motivo}</p>
      )}
      {candidato.clasificacion_origen === "humano" && (
        <p className="text-xs font-medium text-foreground">Corregido a mano</p>
      )}
      {/* El mismo control que en la ficha de la vacante: los dos caminos de revisión tienen
          que poder corregir, o el que no puede se vuelve el camino equivocado. */}
      <CorregirClasificacion
        candidatoId={candidato.id}
        actual={candidato.clasificacion_ia}
        motivoActual={candidato.clasificacion_motivo}
        onCorregido={onCorregido}
      />
      {candidato.clasificacion_ia && <LeyendaDescarte />}
    </div>
  )
}
