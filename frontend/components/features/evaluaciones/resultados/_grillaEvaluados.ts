import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla del listado de evaluados de un lote. Aparte de la tabla por lo mismo que
 * `_grillaEmpleados` y `_bajas`: es lo único que el encabezado, el esqueleto y las filas reales
 * tienen que compartir para que las columnas no se muevan entre un estado y el otro.
 *
 * 🔴 LA COLUMNA SE LLAMA "PERÍODO" Y NO "CICLO" EN NINGÚN LADO DE ESTE MÓDULO, y eso es una regla
 * de vocabulario, no de estilo: **el sistema NO corre evaluaciones, IMPORTA resultados calculados
 * afuera** (`docs/SISTEMA-DE-DISENO.md` §7). "Ciclo" insinúa un proceso que la herramienta abre,
 * corre y cierra —con instancias, vencimientos y recordatorios— y nada de eso existe. Lo que hay
 * es un LOTE de importación identificado por su período.
 */
export const COLUMNAS_EVALUADOS: Columna[] = [
  { clave: "evaluado", label: "Evaluado", ancho: "" },
  { clave: "sector", label: "Sector", ancho: "w-[16%]" },
  { clave: "superior", label: "Superior", ancho: "w-[16%]" },
  { clave: "evaluadores", label: "Evaluadores", ancho: "w-[20%]" },
  { clave: "nota", label: "Nota final", ancho: "w-[10%] text-right" },
  { clave: "acciones", label: "", ancho: "w-[96px] text-right" },
]
