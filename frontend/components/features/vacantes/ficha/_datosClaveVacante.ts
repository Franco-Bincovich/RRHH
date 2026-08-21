import type { DatoClave } from "@/components/ui/FichaIdentidad"
import { formatFecha } from "@/components/features/shared/fechas"
import type { Vacante } from "@/types/vacantes"

/**
 * Los CUATRO datos clave de la barra de identidad de una VACANTE
 * (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 POR QUÉ ESTOS CUATRO. El título es el puesto que se busca; lo que la barra contesta es
 * **para quién se busca y cómo va la búsqueda**:
 *
 *   · **Empresa** — para qué sociedad del grupo se contrata. Es multiempresa.
 *   · **Área** — a qué área entra la persona. Era el subtítulo de la ficha y sube acá: como
 *     subtítulo competía con la descripción, que no se veía en ninguna parte.
 *   · **Apertura** — desde cuándo está abierta. Es la fecha con la que se mide si una búsqueda se
 *     está estirando, y la única señal de presión que la ficha da.
 *   · **Candidatos** — cuántos hay en el pipeline. Es el número que dice si la búsqueda avanza.
 *     Bajaba del tablero, donde había que scrollear para verlo.
 *
 * 🔴 EL CONTEO DE CANDIDATOS SÍ SALE DEL LARGO DEL ARRAY, Y ACÁ ESO ES CORRECTO — no es el bug de
 * siempre. `fetchCandidatos` devuelve `Candidato[]` pelado, sin envoltorio paginado: no hay
 * `total` del backend distinto del largo porque **no hay páginas**. El día que ese endpoint pase a
 * devolver `{items, total}`, este número tiene que pasar a leer `total` y el largo del array se
 * vuelve el conteo de UNA página. Está escrito acá para que ese día se vea.
 *
 * Qué quedó afuera y por qué, para no rediscutirlo:
 *   · **Descripción** — es el subtítulo.
 *   · **Estado** (nueva / en proceso / con candidatos / cerrada) — es el chip.
 *   · **Código `VAC-0001`** — es un identificador para buscar, no para entender, y además ya está
 *     a la vista en su propio bloque: es lo que el candidato tiene que escribir en el mail, así
 *     que vive junto al texto que se copia y se pega.
 *   · **Modalidad, jornada, ubicación, tipo de contrato** — son atributos del puesto y hoy no se
 *     muestran en ninguna parte de la ficha (se editan desde el modal). Subir uno solo de los
 *     cuatro sería arbitrario y subirlos todos no entra: piden un panel propio, que es otra tanda.
 */
export function datosClaveVacante(vacante: Vacante, candidatos: number): DatoClave[] {
  return [
    { label: "Empresa", valor: vacante.empresa_nombre ?? "—" },
    { label: "Área", valor: vacante.area_nombre ?? "—" },
    // `created_at` como respaldo: `fecha_apertura` es opcional y una vacante sin ella igual se
    // creó un día. Es el mismo criterio que ya usaba el encabezado viejo.
    { label: "Apertura", valor: formatFecha(vacante.fecha_apertura ?? vacante.created_at) },
    { label: "Candidatos", valor: String(candidatos) },
  ]
}
