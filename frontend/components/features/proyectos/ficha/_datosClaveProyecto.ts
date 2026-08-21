import type { DatoClave } from "@/components/ui/FichaIdentidad"
import { formatFecha } from "@/components/features/shared/fechas"
import type { Proyecto } from "@/types/proyecto"

const ARS = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  maximumFractionDigits: 0,
})

/**
 * Los CUATRO datos clave de la barra de identidad de un PROYECTO
 * (`docs/SISTEMA-DE-DISENO.md` §3).
 *
 * 🔴 POR QUÉ ESTOS CUATRO. La barra contesta **qué es este proyecto**; el panel de costeo que va
 * abajo contesta **cómo va**. Esa división es la que decide el reparto:
 *
 *   · **Empresa** — de qué sociedad del grupo es. Es multiempresa, y acá pesa más que en otras
 *     fichas: un proyecto de la empresa A puede tener gente asignada de la B (por eso
 *     `proyecto_asignaciones` lleva `empleado_empresa_id`), así que la empresa del proyecto NO se
 *     deduce mirando su equipo.
 *   · **Inicio** y **Cierre previsto** — cuándo corre. Son los dos datos que **hoy no están en
 *     ninguna parte de la pantalla**: viven sólo adentro del modal de edición, así que para saber
 *     si un proyecto ya arrancó había que abrir el formulario. Van separados y no como un rango
 *     porque cada uno se responde solo: "¿ya empezó?" y "¿cuándo termina?".
 *   · **Presupuesto** — de qué tamaño es. Es la magnitud del proyecto, no su consumo.
 *
 * Qué quedó afuera y por qué, para no rediscutirlo:
 *   · **Consumido / restante / % del presupuesto** — es el panel de costeo entero, con su barra.
 *     Subirlo acá dejaría el panel repitiendo la barra tres renglones más abajo. El presupuesto
 *     sí sube porque es contra lo que se lee todo lo demás.
 *   · **Estado** — es el chip, al lado del título.
 *   · **Descripción** — es el subtítulo.
 *   · **Equipo asignado** — es una pestaña con su propia carga; ponerlo acá pediría una consulta
 *     más sólo para el encabezado.
 */
export function datosClaveProyecto(proyecto: Proyecto): DatoClave[] {
  return [
    { label: "Empresa", valor: proyecto.empresa_nombre ?? "—" },
    { label: "Inicio", valor: formatFecha(proyecto.fecha_inicio) },
    // "Sin definir" y no "—": la diferencia entre un proyecto con final abierto y uno al que le
    // falta cargar la fecha la sabe quien lo creó, y la ficha no la puede inventar. Lo que sí
    // puede es no hacerlas parecer la misma cosa que un campo vacío cualquiera.
    { label: "Cierre previsto", valor: proyecto.fecha_fin ? formatFecha(proyecto.fecha_fin) : "Sin definir" },
    { label: "Presupuesto", valor: ARS.format(proyecto.presupuesto) },
  ]
}
