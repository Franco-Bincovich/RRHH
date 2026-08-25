"use client"

import { Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { ErrorState } from "@/components/ui/ErrorState"
import { TablaVacia } from "@/components/ui/TablaVacia"
import { Badge } from "@/components/ui/badge"
import { Encabezado, FilasEsqueleto } from "@/components/ui/grillaTabla"
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table"
import { ROL_LABEL, type UserRol } from "@/types/auth"
import type { UsuarioOption } from "@/services/usuarios"

import { COLUMNAS } from "./_grillaUsuarios"

interface UsuariosTableProps {
  usuarios: UsuarioOption[]
  loading: boolean
  error: boolean
  onRetry: () => void
  /** `undefined` si el rol no puede escribir: entonces la fila no ofrece la baja. */
  onDelete?: (usuario: UsuarioOption) => void
  deletingId: string | null
  /** Qué ofrecer cuando no hay datos: el alta. `undefined` sin permiso de escritura. */
  accionVacio?: ReactNode
}

function rolLabel(rol: string): string {
  return ROL_LABEL[rol as UserRol] ?? rol
}

/**
 * Tabla de usuarios del sistema, con la baja por fila para quien puede escribir.
 *
 * 🔴 LA PANTALLA YA NO ES ADMIN-ONLY (25/8/2026). Tenía un guard propio que rebotaba a
 * `gerencia_lectura`, en contra del modelo de permisos que le da lectura sobre todo y del
 * backend, que ya le servía el listado. Ahora entra a MIRAR, y por eso `onDelete` es opcional:
 * sin permiso de escritura la columna de acciones queda vacía en vez de ofrecer un 403.
 *
 * 🔴 AHORA ES DUEÑA DE SUS TRES ESTADOS (carga, error, vacío) y antes no lo era: los tenía la
 * página. El patrón del bloque B los necesita acá: el vacío es una fila con `colSpan`, y para eso
 * tiene que estar adentro de la `<Table>`.
 *
 * ⚠️ `TablaVacia` SE USA CON `chips=[]` Y UN `onLimpiarTodo` QUE NO HACE NADA, y es correcto:
 * `GET /api/usuarios` no acepta ningún Query, así que el vacío sólo puede caer en la rama
 * "todavía no hay nada" — la que no usa ninguno de los dos. La ACCIÓN del vacío sí es condicional
 * (`accionVacio` llega `undefined` sin permiso): a quien sólo puede leer no se le ofrece crear.
 *
 * ⚠️ El rol va con `variant="secondary"` y NO con el default: un `<Badge>` sin variante es
 * `bg-primary`, el relleno que el patrón reserva al chip de filtro (§3). Acá ya estaba bien.
 */
export function UsuariosTable({
  usuarios, loading, error, onRetry, onDelete, deletingId, accionVacio,
}: UsuariosTableProps) {
  // El error sí reemplaza la tabla: no se sabe qué columnas tiene lo que no llegó.
  if (error) return <ErrorState description="No se pudieron cargar los usuarios." action={onRetry} />

  return (
    <Table patron="datos">
      <Encabezado columnas={COLUMNAS} />
      {loading ? (
        <FilasEsqueleto columnas={COLUMNAS} />
      ) : usuarios.length === 0 ? (
        <TablaVacia
          colSpan={COLUMNAS.length}
          chips={[]}
          sustantivo="usuarios"
          onLimpiarTodo={() => {}}
          accion={accionVacio}
        />
      ) : (
        <TableBody>
          {usuarios.map((u) => (
            <TableRow key={u.id} className="group">
              <TableCell className="font-medium">{u.nombre}</TableCell>
              <TableCell>{u.apellido}</TableCell>
              <TableCell className="text-muted-foreground">{u.email}</TableCell>
              <TableCell className="font-mono text-sm">{u.username}</TableCell>
              <TableCell><Badge variant="secondary">{rolLabel(u.rol)}</Badge></TableCell>
              <TableCell className="text-right">
                {/* 🔴 SIEMPRE VISIBLE, sólo cambia de color al apuntar (§3). El rojo aparece
                    recién con el mouse en la fila: una columna de tachos rojos en reposo se lee
                    como una lista de errores, y acá cada fila es una persona con acceso vigente. */}
                {onDelete && (
                  <button
                    type="button"
                    aria-label={`Eliminar ${u.nombre} ${u.apellido}`}
                    onClick={() => onDelete(u)}
                    disabled={deletingId === u.id}
                    className="ml-auto flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors group-hover:text-destructive hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      )}
    </Table>
  )
}
