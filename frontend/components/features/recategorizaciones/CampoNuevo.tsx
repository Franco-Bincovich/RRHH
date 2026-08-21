import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

/**
 * Uno de los tres campos que SÍ se cargan (rol, seniority, categoría), con su valor anterior al
 * lado cuando lo hay.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VALOR ANTERIOR SE MUESTRA, NO SE EDITA. Es texto, nunca un control.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Los `*_anterior` los completa el BACKEND leyendo la última recategorización previa a la fecha
 * efectiva (o, si no hay ninguna, al empleado). No entran en ningún schema de entrada. Dejarlos
 * escribir —aunque fuera "para corregirlos"— permitiría guardar un histórico que no concuerda con
 * la fila anterior, que es exactamente lo que la tabla existe para impedir, y encima el backend
 * los pisaría al recalcular. Por eso acá no hay un `<input disabled>`: un input deshabilitado
 * dice "esto se podría editar, ahora no"; un `<span>` dice lo que pasa.
 *
 * ⚠️ EN EL ALTA NO SE MUESTRA NINGUNO, y es a propósito. El anterior depende de la FECHA
 * EFECTIVA: con una carga retroactiva no es lo que el legajo dice hoy, sino lo que decía la
 * recategorización previa a esa fecha. Adivinarlo desde el front mostraría un valor que el
 * backend después contradice.
 */
export function CampoNuevo({
  id, label, anterior, value, onChange,
}: {
  id: string
  label: string
  /** El valor previo, si el backend ya lo resolvió (edición). `null`/ausente en el alta. */
  anterior?: string | null
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {anterior && (
        <p className="text-xs text-muted-foreground">
          Valor anterior: <span className="font-medium text-foreground">{anterior}</span>
          {" — lo calcula el sistema, no se edita."}
        </p>
      )}
      <Input
        id={id}
        value={value}
        placeholder="Dejalo vacío si no cambia"
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  )
}
