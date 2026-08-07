"use client"

interface Props {
  texto: string
  /** Las direcciones ya parseadas: es el número que se va a enviar. */
  direcciones: string[]
  /** Las que no tienen forma de mail. Bloquean el envío. */
  invalidas: string[]
  onCambio: (v: string) => void
}

const AREA_CLS = "min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

/**
 * El campo de direcciones escritas a mano. Presentacional puro.
 *
 * 🔴 EL CONTEO QUE SE MUESTRA ES EL DE DIRECCIONES PARSEADAS, no el largo del texto: es el mismo
 * número que va a viajar en el body y el mismo que dice la confirmación. Mostrar otra cosa —"3
 * líneas"— haría que el usuario confirme un número y se mande otro.
 *
 * Las inválidas se listan UNA POR UNA, no con un "hay direcciones inválidas": con diez pegadas de
 * un Excel, saber que una está mal sin saber cuál obliga a revisarlas a ojo.
 *
 * Un `<textarea>` y no un campo por dirección: lo que la gente hace de verdad es copiar y pegar
 * una lista. El parseo acepta coma, punto y coma y salto de línea (ver `envioLibre.ts`).
 */
export function EnvioLibre({ texto, direcciones, invalidas, onCambio }: Props) {
  return (
    <div className="space-y-2">
      <textarea
        className={AREA_CLS}
        value={texto}
        aria-label="Direcciones de mail"
        placeholder={"Una por línea, o separadas por coma:\nana@empresa.com, beto@empresa.com"}
        onChange={(e) => onCambio(e.target.value)}
      />

      {invalidas.length > 0 ? (
        <p className="text-xs text-destructive">
          Revisá {invalidas.length === 1 ? "esta dirección" : "estas direcciones"}:{" "}
          {invalidas.join(", ")}
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">
          {direcciones.length === 0
            ? "Escribí o pegá las direcciones."
            : `${direcciones.length} ${direcciones.length === 1 ? "dirección" : "direcciones"}.`}
        </p>
      )}
    </div>
  )
}
