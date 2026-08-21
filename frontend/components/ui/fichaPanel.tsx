import { Card } from "@/components/ui/card"

/**
 * Una fila etiqueta-valor de una ficha, con el patrón "Ficha de detalle"
 * (`docs/SISTEMA-DE-DISENO.md` §3): **fila de 30px, valor a la derecha, cifras tabulares**.
 *
 * 🔴 EL VALOR A LA DERECHA NO ES DECORATIVO: alinea todos los valores de un panel en una columna,
 * y eso es lo que permite barrer trece campos de un vistazo en vez de leerlos uno por uno. Antes
 * la etiqueta iba arriba y el valor abajo, en una grilla de tres columnas: cada dato ocupaba dos
 * renglones y los valores quedaban desparramados en nueve posiciones distintas.
 *
 * `tabular-nums` va SIEMPRE, no solo en los campos numéricos: sin él, una fecha y un CUIT de la
 * misma columna tienen dígitos de distinto ancho y la columna se ve temblorosa. En el texto que
 * no tiene dígitos no cambia nada.
 *
 * Muestra "—" cuando el valor es nulo o vacío.
 *
 * ⚠️ Vive en `components/ui/` y no en la carpeta de una feature porque lo usan las seis fichas.
 * `empleados/ficha/_primitives.tsx` lo re-exporta como `Field` para no tocar a sus nueve
 * consumidores; el nombre canónico es este.
 */
export function Campo({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex min-h-[30px] items-center justify-between gap-4 border-b border-border/60 py-1 last:border-0">
      <dt className="shrink-0 text-xs text-muted-foreground">{label}</dt>
      <dd className="truncate text-right text-sm tabular-nums text-foreground">{value || "—"}</dd>
    </div>
  )
}

/**
 * Un PANEL de la ficha: título y contenido. Los paneles son independientes y la página los
 * reparte en columnas (§3).
 *
 * La grilla interna es de UNA columna: las columnas son las del LAYOUT —paneles al lado— y meter
 * otras tres adentro de cada uno daría nueve columnas de datos en una pantalla de escritorio, con
 * los valores desalineados entre sí. El `col-span-full` que usan las secciones anchas sigue
 * funcionando.
 *
 * 🔴 NO TIENE PROP DE "EDITAR", y es una ausencia declarada, no un olvido: el patrón pide un
 * "Editar" de 11px POR PANEL, y las fichas de hoy tienen un solo modal que abre el formulario
 * completo. Un "Editar" en un panel que abriera los treinta campos de los dos paneles sería
 * mentir sobre el alcance de la acción. Habilitarlo pide modales por panel; el `PUT` del backend
 * ya acepta payloads parciales, así que es trabajo de front. Queda anotado.
 */
export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card as="section" className="h-fit">
      <h2 className="mb-3 text-base font-semibold text-foreground">{title}</h2>
      <dl className="grid grid-cols-1">{children}</dl>
    </Card>
  )
}
