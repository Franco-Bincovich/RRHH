import type { Semana } from "@/types/horasPublico"

const MODALIDAD: Record<string, string> = { home_office: "Home Office", on_site: "On site" }

/** dd/mm sin `new Date`: cortar el ISO es determinístico y no tiene zona horaria. */
function ddmm(iso: string): string {
  const [, mm, dd] = iso.split("-")
  return `${dd}/${mm}`
}

/**
 * La tabla de SOLO LECTURA de lo cargado esta semana. Sin botones: el empleado no puede editar
 * ni borrar, así que no hay ninguna acción que ofrecer.
 *
 * Muestra las licencias JUNTO a las horas, como el mockup: para la persona son dos formas del
 * mismo día de trabajo, y separarlas en dos tablas la obligaría a cruzarlas de memoria.
 */
export function SemanaTabla({ semana }: { semana: Semana }) {
  const vacia = semana.cargas.length === 0 && semana.licencias.length === 0
  return (
    <section className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="font-medium text-foreground">Lo que cargaste esta semana</h2>
        <span className="text-sm tabular-nums text-muted-foreground">
          {ddmm(semana.desde)} al {ddmm(semana.hasta)} · {semana.total_horas} h
        </span>
      </div>
      {vacia ? (
        <p className="text-sm text-muted-foreground">Todavía no cargaste nada esta semana.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {semana.cargas.map((c, i) => (
            <li key={`h${i}`} className="flex items-baseline justify-between gap-3 border-b py-1.5">
              <span className="min-w-0">
                <span className="tabular-nums font-medium">{ddmm(c.fecha)}</span>
                <span className="ml-2">{c.cliente_nombre ?? "Sin cliente"}</span>
                <span className="ml-2 text-xs text-muted-foreground">
                  {[c.proyecto_texto, c.tarea_texto,
                    c.modalidad ? MODALIDAD[c.modalidad] : null].filter(Boolean).join(" · ")}
                </span>
              </span>
              <span className="shrink-0 tabular-nums">{c.horas} h</span>
            </li>
          ))}
          {semana.licencias.map((l, i) => (
            <li key={`l${i}`} className="flex items-baseline justify-between gap-3 border-b py-1.5">
              <span className="min-w-0">
                <span className="tabular-nums font-medium">
                  {ddmm(l.fecha_desde)}–{ddmm(l.fecha_hasta)}
                </span>
                <span className="ml-2">Licencia</span>
                {l.observaciones && (
                  <span className="ml-2 text-xs text-muted-foreground">{l.observaciones}</span>
                )}
              </span>
              <span className="shrink-0 tabular-nums">{l.dias} día{l.dias !== 1 ? "s" : ""}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
