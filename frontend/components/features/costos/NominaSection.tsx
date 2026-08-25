"use client"

import { Pencil, Users } from "lucide-react"

import { EmptyState } from "@/components/ui/EmptyState"
import { Card } from "@/components/ui/card"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Pagination } from "@/components/ui/Pagination"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { COLUMNAS_NOMINA } from "@/components/features/costos/_grillaNomina"
import { EditarNominaModal } from "@/components/features/costos/EditarNominaModal"
import { MESES_LARGOS, pesos } from "@/components/features/costos/formatos"
import { useEdicionNomina } from "@/components/features/costos/useEdicionNomina"
import { useNominaLista } from "@/components/features/costos/useNominaLista"
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
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 EL VACÍO ACÁ NO ES `TablaVacia`, Y NO ES UN OLVIDO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * `TablaVacia` arma su texto con los CHIPS del panel de filtros, y esta pantalla no tiene panel:
 * su único filtro es el PERÍODO, que el backend exige (`mes` y `anio` son `Query(...)` sin
 * default) y que por eso no puede ser un chip — un chip promete "esto se puede quitar", y acá
 * quitarlo rompe la consulta. El porqué completo está en el encabezado de `costos/page.tsx`.
 *
 * Lo que sí se conserva es lo que el patrón busca: el texto nombra el VALOR REAL del filtro ("No
 * hay nómina cargada para Marzo 2026"), que es exactamente lo que `textoVacio` hace con los
 * chips, y la ESTRUCTURA —fila con `colSpan`, `data-vacio` y el encabezado intacto— es la del
 * patrón.
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

  const columnas = COLUMNAS_NOMINA
    .filter((c) => c.clave !== "empresa" || mostrarEmpresa)
    .filter((c) => c.clave !== "acciones" || canWrite)

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

      {n.error ? (
        <ErrorState description="No se pudo cargar el detalle de nómina." action={n.load} />
      ) : (
        <>
          <Table patron="datos">
            <Encabezado columnas={columnas} />
            {n.loading ? (
              <FilasEsqueleto columnas={columnas} />
            ) : n.filas.length === 0 ? (
              <TableBody>
                <TableRow data-vacio="" className="hover:bg-transparent">
                  <TableCell colSpan={columnas.length} className="h-auto whitespace-normal p-0">
                    <EmptyState
                      icon={<Users />}
                      title="Sin registros"
                      description={`No hay nómina cargada para ${MESES_LARGOS[mes - 1]} ${anio}.`}
                    />
                  </TableCell>
                </TableRow>
              </TableBody>
            ) : (
              <TableBody>
                {n.filas.map((f) => (
                  <TableRow key={f.id} className="group">
                    <TableCell className="font-medium">{f.empleado_nombre}</TableCell>
                    {mostrarEmpresa && (
                      <TableCell className="text-muted-foreground">{f.empresa_nombre ?? "—"}</TableCell>
                    )}
                    <TableCell className="text-muted-foreground">{f.area_nombre}</TableCell>
                    <TableCell className="text-right tabular-nums">{pesos(f.monto_bruto)}</TableCell>
                    <TableCell className="text-right tabular-nums">{pesos(f.monto_neto)}</TableCell>
                    {canWrite && (
                      <TableCell className="text-right">
                        {/* Siempre visible, sólo cambia de color al apuntar la fila (§3). */}
                        <button
                          type="button"
                          onClick={() => ed.open(f)}
                          aria-label={`Editar la nómina de ${f.empleado_nombre}`}
                          className="ml-auto flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors group-hover:text-primary hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                        >
                          <Pencil className="size-4" aria-hidden="true" />
                        </button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            )}
          </Table>

          {/* 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS (era `n.total > pageSize`) y sólo después de
              cargar: sin la guarda, al cambiar de mes la barra queda mostrando el total del
              período ANTERIOR sobre el esqueleto. El total es el del backend, no `filas.length`. */}
          {!n.loading && n.filas.length > 0 && (
            <Pagination page={n.page} total={n.total} pageSize={n.pageSize}
                        onPageSizeChange={n.setPageSize} onPageChange={n.setPage} />
          )}
        </>
      )}

      <EditarNominaModal ed={ed} />
    </Card>
  )
}
