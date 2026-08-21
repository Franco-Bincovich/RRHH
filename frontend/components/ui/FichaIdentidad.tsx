import Link from "next/link"
import { ChevronRight } from "lucide-react"
import type { ReactNode } from "react"

import { Card } from "@/components/ui/card"

/**
 * La BARRA DE IDENTIDAD del patrón "Ficha de detalle" (`docs/SISTEMA-DE-DISENO.md` §3), genérica:
 * migas de pan, monograma de 46px, título, chip de estado, **cuatro** datos clave en una línea y
 * las acciones a la derecha con la primaria al final.
 *
 * 🔴 POR QUÉ ES GENÉRICA Y NO UNA POR FICHA. Nació dentro de `/empleados` y la segunda ficha que
 * la copiara habría dejado dos barras que se ven iguales hasta que una cambia. Lo que difiere
 * entre fichas es **qué son los cuatro datos** y **cómo se dice el estado**, no la forma: por eso
 * los datos llegan ya resueltos (un `_datosClave*.ts` por entidad, con su justificación escrita) y
 * el chip llega como nodo, ya vestido con los pares semánticos de la entidad.
 *
 * 🔴 EL CHIP LLEGA HECHO, Y NO SE CONSTRUYE ACÁ A PROPÓSITO. Cada entidad tiene su vocabulario de
 * estados y su mapa de colores ya escrito y ya testeado (`_grillaVacantes`, `ProyectoCard`,
 * `_grillaEmpresas`, `_grillaAssessment`, `_estadoEmpleado`). Recibirlo como nodo es lo que
 * impide que esta barra invente un sexto mapa de colores — y ninguno de esos usa
 * `variant="default"`: **un relleno azul acá compite con el botón primario que está al lado**.
 *
 * 🔴 EL ORDEN DE LAS ACCIONES LO PONE EL LLAMADOR, y la primaria va ÚLTIMA (§3). No se ordena acá
 * porque esta barra no sabe cuál es la primaria de cada ficha; lo que sí hace es ponerlas todas
 * juntas a la derecha, alineadas al final.
 *
 * `titulo` y `subtitulo` son nodos, no strings: la ficha de un template de onboarding los edita
 * en línea, y forzarlos a texto habría obligado a esa pantalla a quedarse fuera del patrón.
 */
export interface DatoClave {
  label: string
  valor: string
}

/**
 * Las iniciales de un nombre, para el monograma: hasta dos palabras.
 *
 * ⚠️ ES PARA CUANDO EL NOMBRE LLEGA COMO UN SOLO STRING. Si la entidad tiene el nombre y el
 * apellido en campos separados —el legajo de un empleado—, las iniciales salen de esos dos campos
 * y no de acá: partir por espacios dejaría el resultado a merced de cómo esté escrito
 * ("Pérez, Juan" daría PJ, "Juan Pérez" daría JP) cuando el modelo ya sabe cuál es cuál. Con un
 * string único —una vacante, un proyecto, una empresa, un template, el evaluado de un
 * assessment— partir por espacios es lo único que hay y es correcto.
 *
 * Con una sola palabra devuelve sus dos primeras letras, que es mejor que una letra sola en un
 * círculo de 46px. Un nombre vacío devuelve "—" antes que un círculo en blanco.
 */
export function iniciales(nombre: string): string {
  const palabras = nombre.trim().split(/\s+/).filter(Boolean)
  if (palabras.length === 0) return "—"
  if (palabras.length === 1) return palabras[0].slice(0, 2).toUpperCase()
  return (palabras[0][0] + palabras[1][0]).toUpperCase()
}

export function FichaIdentidad({
  volverA,
  volverLabel,
  actual,
  monograma,
  titulo,
  subtitulo,
  chip,
  datos,
  acciones,
}: {
  /** Href del listado padre, para la primera miga. */
  volverA: string
  /** Texto de esa miga: el nombre del listado, no el de la entidad. */
  volverLabel: string
  /** Texto de la miga actual. Es texto y no nodo: es la etiqueta de la posición, no el título. */
  actual: string
  /** Una o dos letras. Se calcula afuera porque cada entidad las saca de campos distintos. */
  monograma: string
  titulo: ReactNode
  subtitulo?: ReactNode
  chip?: ReactNode
  datos: DatoClave[]
  acciones?: ReactNode
}) {
  return (
    <div className="mb-4">
      <nav aria-label="Migas de pan" className="mb-3 flex items-center gap-1 text-xs text-muted-foreground">
        <Link href={volverA} className="rounded-sm underline-offset-2 hover:text-foreground hover:underline">
          {volverLabel}
        </Link>
        <ChevronRight className="size-3" aria-hidden="true" />
        {/* La miga actual NO es un link: llevaría a la página en la que ya estás. */}
        <span className="truncate text-foreground" aria-current="page">{actual}</span>
      </nav>

      <Card as="section" aria-label="Identidad" className="flex flex-wrap items-start gap-4">
        {/* Monograma de 46px. Neutro a propósito: el único relleno fuerte de la barra es el botón
            primario, y un círculo azul de 46px al lado le gana por tamaño. */}
        <div
          aria-hidden="true"
          className="flex size-[46px] shrink-0 items-center justify-center rounded-full bg-secondary text-base font-semibold text-secondary-foreground"
        >
          {monograma}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-semibold text-foreground">{titulo}</h1>
            {chip}
          </div>
          {subtitulo && <p className="mt-0.5 text-sm text-muted-foreground">{subtitulo}</p>}

          {/* Los cuatro datos clave, en UNA línea. El porqué de cuáles son, en el
              `_datosClave*.ts` de cada entidad. */}
          <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
            {datos.map((d) => (
              <div key={d.label} className="min-w-0">
                <dt className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {d.label}
                </dt>
                <dd className="truncate text-sm text-foreground">{d.valor}</dd>
              </div>
            ))}
          </dl>
        </div>

        {acciones && <div className="flex flex-wrap items-center gap-2 sm:ml-auto">{acciones}</div>}
      </Card>
    </div>
  )
}
