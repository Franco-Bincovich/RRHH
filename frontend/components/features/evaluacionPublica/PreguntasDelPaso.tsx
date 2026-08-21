import {
  PASOS, PREGUNTAS_COGNITIVAS, PREGUNTAS_SELF, PREGUNTAS_TECNICAS,
} from "./_preguntas"
import { FilaLikert, FilaMultiple } from "./Preguntas"

/**
 * El cuerpo del paso: su título, su instrucción y sus preguntas.
 *
 * Salió de `app/evaluacion/[token]/page.tsx`, que quedaba en 157 líneas contra el límite de 150.
 * El corte deja en la página lo que decide (qué estado mostrar, qué pasa al avanzar, qué hacer si
 * el envío falla) y acá lo que dibuja.
 *
 * ⚠️ EL PASO 0 ES LIKERT Y LOS OTROS DOS SON OPCIÓN MÚLTIPLE, y por eso las respuestas llegan en
 * tres diccionarios separados y no en uno: los `id` de pregunta se repiten entre los tres
 * cuestionarios —hay una pregunta 1 en cada uno— así que un diccionario único las pisaría entre
 * sí. Es la misma razón por la que el backend recibe `{tipo, pregunta_id, respuesta}` y no sólo
 * el id.
 */
export function PreguntasDelPaso({ paso, self, cognitivas, tecnicas, onSelf, onCognitiva, onTecnica }: {
  paso: number
  self: Record<number, number>
  cognitivas: Record<number, number>
  tecnicas: Record<number, number>
  onSelf: (id: number, v: number) => void
  onCognitiva: (id: number, v: number) => void
  onTecnica: (id: number, v: number) => void
}) {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foreground">{PASOS[paso].label}</h1>
      <p className="text-sm text-muted-foreground">{PASOS[paso].ayuda}</p>

      {paso === 0 && PREGUNTAS_SELF.map((q) => (
        <FilaLikert key={q.id} pregunta={q} elegido={self[q.id]} onElegir={(v) => onSelf(q.id, v)} />
      ))}
      {paso === 1 && PREGUNTAS_COGNITIVAS.map((q) => (
        <FilaMultiple key={q.id} pregunta={q} elegido={cognitivas[q.id]} onElegir={(v) => onCognitiva(q.id, v)} />
      ))}
      {paso === 2 && PREGUNTAS_TECNICAS.map((q) => (
        <FilaMultiple key={q.id} pregunta={q} elegido={tecnicas[q.id]} onElegir={(v) => onTecnica(q.id, v)} />
      ))}
    </div>
  )
}
