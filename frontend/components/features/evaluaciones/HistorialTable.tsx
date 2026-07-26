/**
 * Tabla del historial de importaciones, presentacional (sin fetch ni lógica de borrado).
 * Desktop: tabla; mobile: cards. Multi-selección controlada desde el padre (Set de ids).
 */
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { LoteEvaluacion } from "@/types/evaluacionReportes"

const CHECKBOX_CLASS = "size-4 shrink-0 cursor-pointer rounded border-input accent-primary"

function formatFecha(iso: string): string {
  return new Date(iso).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

interface Props {
  items: LoteEvaluacion[]
  seleccion: Set<string>
  onToggle: (id: string) => void
  onToggleAll: () => void
}

export function HistorialTable({ items, seleccion, onToggle, onToggleAll }: Props) {
  const allChecked = items.length > 0 && items.every((l) => seleccion.has(l.id))

  return (
    <>
      {/* Desktop */}
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <input type="checkbox" className={CHECKBOX_CLASS} checked={allChecked}
                       onChange={onToggleAll} aria-label="Seleccionar todo" />
              </TableHead>
              <TableHead>Período</TableHead>
              <TableHead>Empresa</TableHead>
              <TableHead>Evaluados</TableHead>
              <TableHead>Importado por</TableHead>
              <TableHead>Fecha</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((l) => (
              <TableRow key={l.id} data-state={seleccion.has(l.id) ? "selected" : undefined}>
                <TableCell>
                  <input type="checkbox" className={CHECKBOX_CLASS} checked={seleccion.has(l.id)}
                         onChange={() => onToggle(l.id)} aria-label={`Seleccionar ${l.periodo}`} />
                </TableCell>
                <TableCell className="font-medium text-foreground">{l.periodo}</TableCell>
                <TableCell>{l.empresa_nombre ?? "—"}</TableCell>
                <TableCell>{l.evaluados}</TableCell>
                <TableCell>{l.importado_por_nombre ?? "—"}</TableCell>
                <TableCell className="text-muted-foreground">{formatFecha(l.created_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile */}
      <div className="space-y-3 md:hidden">
        {items.map((l) => (
          <label key={l.id} className="flex gap-3 rounded-lg border border-border p-3">
            <input type="checkbox" className={`${CHECKBOX_CLASS} mt-0.5`} checked={seleccion.has(l.id)}
                   onChange={() => onToggle(l.id)} aria-label={`Seleccionar ${l.periodo}`} />
            <div className="min-w-0 flex-1">
              <p className="font-medium text-foreground">{l.periodo}</p>
              <p className="truncate text-sm text-muted-foreground">{l.empresa_nombre ?? "—"}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {l.evaluados} evaluados · {l.importado_por_nombre ?? "—"} · {formatFecha(l.created_at)}
              </p>
            </div>
          </label>
        ))}
      </div>
    </>
  )
}
