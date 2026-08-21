/**
 * El ENCABEZADO y el ESQUELETO de una tabla del patrón "Tabla con paginación"
 * (`docs/SISTEMA-DE-DISENO.md` §3), compartidos por todas las pantallas que lo usan.
 *
 * Nacieron dentro de `components/features/empleados/_grillaEmpleados.tsx` —la pantalla piloto—
 * y se mudaron acá al aparecer la segunda y la tercera tabla del patrón (`/proximos-ingresos` y
 * `/bajas`). Ninguna de las dos funciones sabía nada de empleados: reciben la lista de columnas
 * y dibujan. `_grillaEmpleados.tsx` las RE-EXPORTA, así que `EmpleadosTable` no cambió una línea.
 *
 * 🔴 LO QUE NO SE MUDA ES `COLUMNAS`: qué columnas hay y cuánto miden es de cada pantalla. Lo
 * único genérico es que las tres piezas —encabezado, esqueleto y filas reales— lean LA MISMA
 * lista, que es lo que evita que las columnas salten al llegar los datos.
 */
import { Skeleton } from "@/components/ui/skeleton"
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

/**
 * Una columna de la grilla. `ancho` es una clase de Tailwind (`w-[16%]`) o `""` para la columna
 * que absorbe el espacio libre — tiene que haber exactamente una así por tabla. `label` vacío es
 * la columna de acciones: el ícono de cada fila ya dice qué es, y un "ACCIONES" de 10px sobre
 * 48px de ancho se lee como ruido.
 */
export interface Columna {
  clave: string
  label: string
  ancho: string
}

export function Encabezado({ columnas }: { columnas: readonly Columna[] }) {
  return (
    <TableHeader>
      <TableRow>
        {columnas.map((c) => (
          <TableHead key={c.clave} className={c.ancho}>
            {/* La columna de acciones tiene nombre para el lector de pantalla aunque no se vea. */}
            {c.label || <span className="sr-only">Acciones</span>}
          </TableHead>
        ))}
      </TableRow>
    </TableHeader>
  )
}

/**
 * El esqueleto es LA MISMA TABLA con barras en vez de datos (§3: "mismas columnas, mismos 46px"),
 * no una pila de rectángulos aparte. Así el encabezado ya está puesto mientras carga y las
 * columnas nacen con su ancho definitivo.
 */
export function FilasEsqueleto({ columnas }: { columnas: readonly Columna[] }) {
  return (
    <TableBody>
      {Array.from({ length: 8 }).map((_, i) => (
        <TableRow key={i}>
          {columnas.map((c) => (
            <TableCell key={c.clave}>
              {/* `shimmer`: el brillo de 1,2s que pide §3 para el esqueleto, en vez del
                  `animate-pulse` de 2s que trae el componente por defecto. */}
              <Skeleton shimmer className="h-3.5 w-full rounded" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </TableBody>
  )
}
