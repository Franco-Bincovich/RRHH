import { FileDown, FileSpreadsheet } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { HistorialItem } from "@/services/reportes"

function formatFecha(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
  } catch {
    return iso
  }
}

// Reportes Ad Hoc IA legacy que ya estén en el historial siguen mostrándose con su etiqueta;
// solo se ocultó la forma de GENERAR nuevos (ver ReportesCatalogo).
function TipoCell({ tipo }: { tipo: string }) {
  return tipo === "adhoc" ? (
    <div className="flex items-center gap-1.5">
      <span className="text-sm text-muted-foreground">Ad Hoc IA</span>
      <Badge className="bg-primary text-primary-foreground text-[10px] px-1.5 py-0">IA</Badge>
    </div>
  ) : (
    <span className="text-sm capitalize text-muted-foreground">{tipo}</span>
  )
}

export function HistorialReportesTable({
  historial,
  loading,
  mostrarEmpresa,
  exportLoading,
  onExportar,
}: {
  historial: HistorialItem[]
  loading: boolean
  mostrarEmpresa: boolean
  exportLoading: Set<string>
  onExportar: (id: string, nombre: string, formato: "pdf" | "excel") => void
}) {
  return (
    <Card as="section" aria-label="Historial de reportes">
      <h2 className="mb-4 text-base font-semibold text-foreground">Historial</h2>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-md bg-muted" />
          ))}
        </div>
      ) : historial.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          Aún no se generaron reportes.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              {mostrarEmpresa && <TableHead>Empresa</TableHead>}
              <TableHead>Tipo</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Generado por</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {historial.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{r.nombre}</TableCell>
                {mostrarEmpresa && (
                  <TableCell className="text-muted-foreground">
                    {r.empresa_nombre ?? <span className="italic text-muted-foreground/60">Consolidado</span>}
                  </TableCell>
                )}
                <TableCell><TipoCell tipo={r.tipo} /></TableCell>
                <TableCell className="text-muted-foreground">{formatFecha(r.created_at)}</TableCell>
                <TableCell className="text-muted-foreground">{r.generado_por}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost" size="sm" className="min-h-[2.75rem] gap-1.5 text-xs"
                      disabled={exportLoading.has(`${r.id}-pdf`)}
                      onClick={() => onExportar(r.id, r.nombre, "pdf")}
                    >
                      <FileDown className="size-3.5" />
                      {exportLoading.has(`${r.id}-pdf`) ? "…" : "PDF"}
                    </Button>
                    <Button
                      variant="ghost" size="sm" className="min-h-[2.75rem] gap-1.5 text-xs"
                      disabled={exportLoading.has(`${r.id}-excel`)}
                      onClick={() => onExportar(r.id, r.nombre, "excel")}
                    >
                      <FileSpreadsheet className="size-3.5" />
                      {exportLoading.has(`${r.id}-excel`) ? "…" : "Excel"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Card>
  )
}
