"use client"

import { Pencil, Users } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Card } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Pagination } from "@/components/ui/Pagination"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { MESES_LARGOS, pesos } from "@/components/features/costos/formatos"
import { useEdicionNomina } from "@/components/features/costos/useEdicionNomina"
import { PAGE_SIZE, useNominaLista } from "@/components/features/costos/useNominaLista"
import { exportarNomina } from "@/services/costos"

/**
 * El "Detalle de nómina": la tabla paginada del período y la edición de una fila.
 *
 * Salió de `costos/page.tsx` al partirla. Se llevó su estado, su carga y su modal de edición
 * (todo en `useNominaLista`) porque es la única parte de esa pantalla que PAGINA — y por eso es
 * también la única que no puede alimentar ningún total.
 *
 * 🔴 NO LLEVA PIE DE TOTALES, al revés que la tabla por área de al lado. `filas` es una página:
 * un pie que la sumara diría el total de 20 personas presentado como la masa salarial del mes.
 * El costo total del período ya está arriba, en los KPIs, y sale de `/api/costos/dashboard`.
 *
 * El contador del encabezado usa `total` (del backend) y NO `filas.length`: en la página 2 el
 * largo de la página no dice cuántos registros tiene el mes.
 */
interface Props {
  mes: number
  anio: number
  canWrite: boolean
  mostrarEmpresa: boolean
  /** Recarga el dashboard: los KPIs son otra consulta y editar un sueldo los mueve. */
  onGuardado: () => void
}

export function NominaSection({ mes, anio, canWrite, mostrarEmpresa, onGuardado }: Props) {
  const n = useNominaLista(mes, anio)
  // Al guardar hay que recargar LAS DOS cosas: esta lista y el dashboard de arriba, que es
  // otra consulta. Refrescar solo una deja la tabla y los KPIs diciendo números distintos.
  const ed = useEdicionNomina(mes, anio, async () => { await n.load(); onGuardado() })

  return (
    <Card as="section" aria-label="Detalle de nómina">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-foreground">
          Detalle de nómina
          {!n.loading && !n.error && n.total > 0 && (
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              {n.total} registro{n.total !== 1 ? "s" : ""}
            </span>
          )}
        </h2>
        {!n.loading && !n.error && n.total > 0 && (
          <ExportMenu onExport={(f) => exportarNomina(f, mes, anio)} />
        )}
      </div>

      {n.loading ? (
        <Skeleton className="h-40 rounded-lg" />
      ) : n.error ? (
        <ErrorState description="No se pudo cargar el detalle de nómina." action={n.load} />
      ) : n.total === 0 ? (
        <EmptyState
          icon={<Users />}
          title="Sin registros"
          description={`No hay nómina cargada para ${MESES_LARGOS[mes - 1]} ${anio}.`}
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Colaborador</TableHead>
                {mostrarEmpresa && <TableHead>Empresa</TableHead>}
                <TableHead>Área</TableHead>
                <TableHead className="text-right">Monto bruto</TableHead>
                <TableHead className="text-right">Monto neto</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {n.filas.map((f) => (
                <TableRow key={f.id}>
                  <TableCell className="font-medium">{f.empleado_nombre}</TableCell>
                  {mostrarEmpresa && (
                    <TableCell className="text-muted-foreground">{f.empresa_nombre ?? "—"}</TableCell>
                  )}
                  <TableCell className="text-muted-foreground">{f.area_nombre}</TableCell>
                  <TableCell className="text-right">{pesos(f.monto_bruto)}</TableCell>
                  <TableCell className="text-right">{pesos(f.monto_neto)}</TableCell>
                  <TableCell className="text-right">
                    {canWrite && (
                      <Button variant="ghost" size="sm" className="min-h-9 gap-1"
                        onClick={() => ed.open(f)}>
                        <Pencil className="size-3.5" />
                        Editar
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {n.total > PAGE_SIZE && (
            <Pagination page={n.page} total={n.total} pageSize={PAGE_SIZE} onPageChange={n.setPage} />
          )}
        </>
      )}

      <Dialog open={ed.item !== null} onOpenChange={(open) => { if (!open) ed.setItem(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar nómina — {ed.item?.empleado_nombre}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-bruto">Monto bruto</Label>
              <Input id="edit-bruto" type="number" min={0} value={ed.bruto}
                onChange={(e) => ed.setBruto(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-neto">Monto neto</Label>
              <Input id="edit-neto" type="number" min={0} value={ed.neto}
                onChange={(e) => ed.setNeto(e.target.value)} />
            </div>
            {ed.error && <p className="text-sm text-destructive">{ed.error}</p>}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => ed.setItem(null)} disabled={ed.saving}>
              Cancelar
            </Button>
            <Button onClick={ed.save} disabled={ed.saving}>
              {ed.saving ? "Guardando…" : "Guardar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
