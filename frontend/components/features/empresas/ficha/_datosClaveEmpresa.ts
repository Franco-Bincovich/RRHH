import type { DatoClave } from "@/components/ui/FichaIdentidad"
import type { Empresa } from "@/types/empresa"

/**
 * Los CUATRO datos clave de la barra de identidad de una EMPRESA
 * (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 POR QUÉ ESTOS CUATRO. Una empresa es una entidad RAÍZ: no cuelga de nada, así que la pregunta
 * "quién es dentro del sistema" no se contesta con su ubicación —no tiene— sino con **qué persona
 * jurídica es y cómo se la contacta**, que es exactamente lo que el modelo guarda de ella
 * (`empresas` tiene once columnas y siete son estas o derivadas):
 *
 *   · **CUIT** — es la única clave real de una sociedad. Dos empresas del grupo pueden tener
 *     nombres de fantasía parecidos y razones sociales casi iguales; el CUIT las separa, y es el
 *     dato con el que Capital Humano las cruza contra cualquier sistema de afuera.
 *   · **Email** y **Teléfono** — el contacto operativo. Están acá y no en un panel porque son lo
 *     que alguien viene a buscar cuando abre la ficha de una sociedad del grupo.
 *   · **Dirección** — dónde está. Es el domicilio de la sociedad, no el de una sucursal.
 *
 * Qué quedó afuera y por qué, para no rediscutirlo:
 *   · **Razón social** — es el subtítulo, debajo del nombre de fantasía. Gastar uno de los cuatro
 *     en repetirlo es perder un cuarto de la barra.
 *   · **Activa / inactiva** — es el chip, al lado del título.
 *   · **Logo** — es una imagen y tiene su propio panel, con el control para cambiarla.
 *   · **Cantidad de áreas y de colaboradores** — serían los dos datos más útiles de todos, y no
 *     están porque **no llegan con la empresa**: pedirlos son dos consultas más sólo para pintar
 *     el encabezado. Es la deuda anotada de esta ficha, no una omisión de criterio.
 */
export function datosClaveEmpresa(empresa: Empresa): DatoClave[] {
  return [
    { label: "CUIT", valor: empresa.cuit ?? "—" },
    { label: "Email", valor: empresa.email ?? "—" },
    { label: "Teléfono", valor: empresa.telefono ?? "—" },
    { label: "Dirección", valor: empresa.direccion ?? "—" },
  ]
}
