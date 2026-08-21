import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { CampoPerfil, OpcionPerfil } from "@/types/perfilPuesto"

import { MAX_NOMBRE } from "./guardarPerfil"

/**
 * UN campo del formulario de perfil, dibujado con lo que dijo el backend: su `label`, su `ayuda`
 * y su `tipo`. No conoce ningún nombre de campo salvo `nombre`, que es el único obligatorio.
 *
 * 🔴 LA AYUDA VA ENTRE EL LABEL Y EL CONTROL, NO DEBAJO Y NO EN UN TOOLTIP. El backend explica
 * por qué existe cada texto (`schemas/_perfil_puesto_campos.py`): son lo ÚNICO que evita que los
 * cuatro campos del bloque de requisitos se llenen mal, y solo sirven si se leen **antes** de
 * escribir. Debajo del control se lee al terminar, que es tarde; en un tooltip no se lee nunca.
 *
 * ⚠️ UN `select` SIN VOCABULARIO SE DIBUJA COMO TEXTO. Pasa si el backend agrega un cuarto
 * vocabulario y `vocabularioDe` todavía no lo conoce. La alternativa —un `<select>` vacío— es un
 * control imposible de usar que además no dice qué le falta; así el campo sigue siendo editable
 * y, si el valor no pertenece al `Literal`, el backend responde 422 nombrando el campo.
 */
export function PerfilCampoControl({
  campo, opciones, valor, error, onChange,
}: {
  campo: CampoPerfil
  opciones: OpcionPerfil[]
  valor: string
  error?: string
  onChange: (valor: string) => void
}) {
  const id = `perfil-${campo.campo}`
  const obligatorio = campo.campo === "nombre"
  const esSelect = campo.tipo === "select" && opciones.length > 0

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>
        {campo.label}
        {obligatorio && <span className="text-destructive" aria-hidden> *</span>}
      </Label>
      <p id={`${id}-ayuda`} className="text-xs leading-relaxed text-muted-foreground">
        {campo.ayuda}
      </p>

      {esSelect ? (
        <Select
          id={id}
          value={valor}
          aria-describedby={`${id}-ayuda`}
          onChange={(e) => onChange(e.target.value)}
        >
          {/* Sin elegir es un valor VÁLIDO: los once campos que no son el nombre son opcionales
              en el backend. El vacío se omite del body — ver `armarPayload`. */}
          <option value="">Sin especificar</option>
          {opciones.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </Select>
      ) : campo.tipo === "textarea" ? (
        <Textarea
          id={id}
          rows={4}
          value={valor}
          aria-describedby={`${id}-ayuda`}
          aria-invalid={Boolean(error)}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <Input
          id={id}
          value={valor}
          // El `maxLength` solo aplica al nombre: es el único campo con tope de producto. Los
          // demás son `text` sin límite en la base y textos de aviso que pueden ser largos.
          maxLength={obligatorio ? MAX_NOMBRE : undefined}
          aria-required={obligatorio || undefined}
          aria-describedby={`${id}-ayuda`}
          aria-invalid={Boolean(error)}
          onChange={(e) => onChange(e.target.value)}
        />
      )}

      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
    </div>
  )
}
