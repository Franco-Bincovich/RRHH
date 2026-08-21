import type { DatoClave } from "@/components/ui/FichaIdentidad"
import type { OnboardingTemplate } from "@/types/onboarding"

import { SEMANAS } from "../_templates_ui"

/**
 * Los CUATRO datos clave de la barra de identidad de un TEMPLATE DE ONBOARDING
 * (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 POR QUÉ ESTOS CUATRO. Un template es una PLANTILLA: no describe a nadie, describe un plan
 * que se va a copiar sobre cada persona que entre. Las preguntas que hay que contestar antes de
 * usarlo son de quién es, si se puede usar y si está terminado:
 *
 *   · **Empresa** — de qué sociedad es el plan. Es multiempresa y un template puede no tener
 *     empresa (los transversales), así que la ficha lo dice en vez de dejarlo en blanco.
 *   · **Autor** — quién lo creó. No es un dato de color: **la visibilidad sólo la puede cambiar
 *     el autor** (el backend rechaza al resto con `TEMPLATE_NO_SOS_AUTOR`), así que es la
 *     explicación de por qué el control de al lado está deshabilitado.
 *   · **Tareas** — de qué tamaño es el plan. Sale de `tareas_total`, el número del backend, y no
 *     del largo del array que la pantalla tiene a mano.
 *   · **Semanas con tareas** — si está TERMINADO. Es el único de los cuatro que se deriva, y es
 *     el que más decide: un template con las cuatro semanas cubiertas se puede usar tal cual, y
 *     uno con tareas sólo en la semana 1 es un borrador. Sin este dato hay que bajar y mirar las
 *     cuatro secciones para saberlo.
 *
 * Qué quedó afuera y por qué, para no rediscutirlo:
 *   · **Descripción** — es el subtítulo, y además se edita ahí mismo.
 *   · **Compartida / privada** — es el chip, al lado del título.
 *   · **Cuántos onboardings se iniciaron con este template** — sería el dato más útil de todos y
 *     no está porque no llega con el template: es otra consulta, y hoy no hay endpoint que la
 *     conteste. Queda anotado.
 */
export function datosClaveTemplate(template: OnboardingTemplate): DatoClave[] {
  const semanasConTareas = SEMANAS.filter((s) => template.tareas.some((t) => t.semana === s)).length
  return [
    // "Todas las empresas" y no "—": un template sin empresa no es uno al que le falta el dato,
    // es uno que sirve para el grupo entero. La raya haría parecer que hay algo sin cargar.
    { label: "Empresa", valor: template.empresa_nombre ?? "Todas las empresas" },
    // "Sin autor" es un estado REAL y no un dato faltante: son las plantillas anteriores al
    // cableado del autor, o aquellas cuyo usuario se borró. La regla de producto las trata
    // distinto —a una huérfana le puede cambiar la visibilidad cualquiera—, así que decirlo acá
    // es lo que explica que el control esté habilitado para alguien que no la creó.
    { label: "Autor", valor: template.created_by_nombre ?? "Sin autor" },
    { label: "Tareas", valor: String(template.tareas_total) },
    { label: "Semanas con tareas", valor: `${semanasConTareas} de ${SEMANAS.length}` },
  ]
}
