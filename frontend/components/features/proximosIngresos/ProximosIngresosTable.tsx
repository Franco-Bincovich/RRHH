/**
 * Tabla de próximos ingresos, presentacional. Dueña de los estados de carga/error/vacío. Sin
 * fetch ni lógica de negocio: la página le pasa datos, el handler de navegación y el de activar.
 *
 * Los cinco patrones del bloque B salen enteros de las piezas compartidas —`patron="datos"` del
 * primitivo de tabla, `Encabezado`/`FilasEsqueleto` de `grillaTabla`, `TablaVacia`, `ErrorState`—;
 * acá no hay una sola clase de las del patrón.
 */
import Link from "next/link"
import { UserCheck } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Button } from "@/components/ui/button"
import type { ChipFiltro } from "@/components/ui/filtrosChips"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { diasHasta, formatFecha } from "@/components/features/shared/fechas"
import type { PersonaActivable } from "@/components/features/empleados/useActivarEmpleado"
import type { Empleado } from "@/types/empleado"

import { COLUMNAS, motivoNoSePuedeConfirmar, textoFaltan } from "./_proximosIngresos"

interface Props {
  items: Empleado[]
  loading: boolean
  error: boolean
  showEmpresa: boolean
  onRetry: () => void
  onRowClick: (id: string) => void
  chips: ChipFiltro[]
  onLimpiarTodo: () => void
  accionVacio?: ReactNode
  /** `undefined` si el rol no puede escribir: entonces no se dibuja el botón de confirmar
   *  (la columna sigue, porque lleva además el link de lectura al legajo). */
  onActivar?: (empleado: PersonaActivable) => void
  /** El id de la fila que se está confirmando ahora mismo, o `null`. */
  activandoId: string | null
}

export function ProximosIngresosTable({
  items, loading, error, showEmpresa, onRetry, onRowClick, chips, onLimpiarTodo, accionVacio,
  onActivar, activandoId,
}: Props) {
  // 🔑 LA COLUMNA DE ACCIONES YA NO DEPENDE DE `onActivar`. Antes se ocultaba entera sin permiso
  // de escritura, porque lo único que llevaba era "Confirmar ingreso"; desde que además lleva
  // "Ver legajo" —que es LECTURA— ocultarla le sacaba a `gerencia_lectura` la única forma
  // visible de abrir la ficha desde acá. El botón de escritura sigue gateado, la columna no.
  const columnas = COLUMNAS.filter((c) => c.clave !== "empresa" || showEmpresa)

  if (error) return <ErrorState action={onRetry} />

  return (
    // Una sola <Table> para los tres estados: el encabezado se renderiza SIEMPRE, así la
    // pantalla no cambia de forma entre la carga, el vacío y los datos.
    <Table patron="datos">
      <Encabezado columnas={columnas} />
      {loading ? (
        <FilasEsqueleto columnas={columnas} />
      ) : items.length === 0 ? (
        <TablaVacia
          colSpan={columnas.length}
          chips={chips}
          sustantivo="próximos ingresos"
          claveSujeto="Empresa"
          onLimpiarTodo={onLimpiarTodo}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {items.map((emp) => {
            const dias = diasHasta(emp.fecha_ingreso)
            const faltan = textoFaltan(dias)
            const motivo = motivoNoSePuedeConfirmar(dias, emp.fecha_ingreso)
            return (
              <TableRow key={emp.id} className="group cursor-pointer" onClick={() => onRowClick(emp.id)}>
                {/* 🔴 LA IDENTIDAD ES UN <Link> DE VERDAD, no sólo el `onClick` de la fila. Molde:
                    `EmpresasTable`, la única tabla que ya lo hacía. Un `<tr>` NO puede ser un `<a>`
                    —HTML inválido, y React lo rechaza— así que el ancla va en la celda que nombra
                    al registro. El `onClick` de la fila SE QUEDA: es la comodidad de clickear
                    cualquier parte. Lo que agrega el link es lo que el `onClick` no puede dar —
                    abrir en pestaña nueva, copiar la dirección, y llegar con Tab. */}
                <TableCell className="font-medium">
                  <Link href={`/empleados/${emp.id}`} onClick={(e) => e.stopPropagation()}
                        className="hover:text-primary hover:underline">
                    {emp.nombre} {emp.apellido}
                  </Link>
                </TableCell>
                {showEmpresa && <TableCell className="text-muted-foreground">{emp.empresa_nombre ?? "—"}</TableCell>}
                <TableCell className="text-muted-foreground">{emp.area_nombre ?? "—"}</TableCell>
                <TableCell className="tabular-nums">{formatFecha(emp.fecha_ingreso)}</TableCell>
                <TableCell className={faltan.destacado ? "font-medium text-warning" : "text-muted-foreground"}>
                  {faltan.texto}
                </TableCell>
                <TableCell>
                  {/* 🔑 EL "VER LEGAJO" QUE ESTABA ACÁ SE FUE: con el nombre convertido en
                      link (columna 1) eran dos accesos al mismo lugar en la misma fila, y el de
                      la identidad es el que el usuario busca. Lo que el error de "corregí la
                      fecha en su legajo" necesitaba —una forma VISIBLE y alcanzable por teclado
                      de abrir la ficha— lo da ese link igual. */}
                  <div className="flex items-center gap-2">
                    {onActivar && (
                      /*
                       * 🔴 EL BOTÓN SÍ SE DESHABILITA POR FECHA — ver el porqué (y qué decisión
                       * invierte) en `motivoNoSePuedeConfirmar`. El motivo va en `title` sobre el
                       * WRAPPER, porque un <button disabled> no dispara eventos de mouse y su
                       * propio title no llegaría a mostrarse; y va ADEMÁS a la vista en la
                       * columna "Faltan" de esta misma fila, que dice "En 14 días".
                       */
                      <span title={motivo ?? undefined}>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={Boolean(motivo) || activandoId === emp.id}
                          onClick={(e) => { e.stopPropagation(); onActivar(emp) }}
                        >
                          <UserCheck className="size-3.5" aria-hidden="true" />
                          {activandoId === emp.id ? "Confirmando..." : "Confirmar ingreso"}
                        </Button>
                      </span>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      )}
    </Table>
  )
}
