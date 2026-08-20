/**
 * La GRILLA de la tabla de empleados: qué columnas hay, cuánto miden, cómo se dibuja el
 * encabezado y cómo se dibuja el esqueleto de carga. Salió de `EmpleadosTable.tsx` para que ese
 * archivo quedara adentro del límite de 150 de un componente, y el corte no es arbitrario: acá
 * está TODO lo que el encabezado, el esqueleto y las filas tienen que compartir para que las
 * columnas no se muevan entre un estado y el otro.
 */
import { Skeleton } from "@/components/ui/skeleton"
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

/**
 * 🔴 LOS ANCHOS ESTÁN DECLARADOS PARA QUE LAS COLUMNAS NO SALTEN AL CARGAR (§3), y por eso viven
 * en UNA lista que usan el encabezado, el esqueleto y las filas reales. Si el esqueleto declarara
 * los suyos, las columnas se acomodarían solas al llegar los datos y la pantalla saltaría — que es
 * exactamente lo que el esqueleto viene a evitar.
 * `Nombre` no lleva ancho: es la columna que absorbe el espacio libre.
 */
export const COLUMNAS = [
  { clave: "nombre", label: "Nombre", ancho: "" },
  { clave: "empresa", label: "Empresa", ancho: "w-[16%]" },
  { clave: "area", label: "Área", ancho: "w-[14%]" },
  { clave: "roles", label: "Roles", ancho: "w-[20%]" },
  { clave: "modalidad", label: "Modalidad", ancho: "w-[12%]" },
  { clave: "estado", label: "Estado", ancho: "w-[10%]" },
  // La columna de acciones no lleva texto en el encabezado: el ícono de cada fila ya dice qué es,
  // y un "Acciones" en mayúsculas de 10px sobre una columna de 40px se lee como ruido.
  { clave: "acciones", label: "", ancho: "w-[48px]" },
]

export function Encabezado({ columnas }: { columnas: typeof COLUMNAS }) {
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
export function FilasEsqueleto({ columnas }: { columnas: typeof COLUMNAS }) {
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

