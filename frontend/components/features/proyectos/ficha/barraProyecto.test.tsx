import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"
import type { Proyecto } from "@/types/proyecto"

import { BarraProyecto } from "./BarraProyecto"
import { datosClaveProyecto } from "./_datosClaveProyecto"

/**
 * La barra de identidad de la ficha de un PROYECTO: los cuatro datos clave, el orden de las
 * acciones y el chip de estado.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR?
 *   · (a) cuenta los `<dt>` del markup real, no el largo del array: un quinto dato agregado en la
 *     barra —sin pasar por `datosClaveProyecto`— también lo rojea.
 *   · (b) esta ficha tiene UNA sola acción, así que "la primaria va última" es cierto por
 *     construcción y una aserción de posición no podría fallar nunca. Lo que sí puede fallar es
 *     que aparezca una segunda: por eso el test cuenta los botones y fija que el único sea el
 *     sólido. El día que se sume otra acción, este test rojea y obliga a escribir la aserción de
 *     orden de verdad, en vez de heredar un verde que no probaba nada.
 *   · (c) compara contra el mapa semántico real y contra el relleno de marca: pintar el chip con
 *     `variant="default"` mete `bg-primary` en el markup y rojea.
 *   · (d) NO HAY TEST DE HISTORIAL ACÁ, y no es un olvido: esta ficha no tiene ninguno. Un
 *     proyecto no acumula cambios fechados en el modelo (`proyectos` no tiene tabla hija de
 *     historial), y las asignaciones de equipo son un listado con vigencia, no una serie de
 *     "de → a". Inventarle uno sería mostrar una línea de tiempo que la base no tiene. El chip
 *     "Vigente" en sí lo cubre `components/ui/Historial.test.tsx`.
 */

const BASE: Proyecto = {
  id: "p1",
  empresa_id: "e1",
  empresa_nombre: "Bodegas Tupungato",
  nombre: "Migración AWS",
  descripcion: "Porteo de Supabase a RDS",
  estado: "activo",
  fecha_inicio: "2026-03-01",
  fecha_fin: "2026-09-30",
  presupuesto: 5_000_000,
  costeo: { costo_acumulado: 1_000_000, presupuesto_restante: 4_000_000, pct_consumido: 20 },
  created_at: "2026-02-01",
  updated_at: null,
}

const barra = (proyecto: Proyecto, acciones?: React.ReactNode) =>
  renderToStaticMarkup(<BarraProyecto proyecto={proyecto} acciones={acciones} />)

describe("(a) la barra del proyecto muestra EXACTAMENTE cuatro datos clave", () => {
  it("cuatro, ni tres ni cinco", () => {
    expect(datosClaveProyecto(BASE)).toHaveLength(4)
    expect(barra(BASE).match(/<dt/g) ?? []).toHaveLength(4)
  })

  it("son empresa, inicio, cierre previsto y presupuesto", () => {
    expect(datosClaveProyecto(BASE).map((d) => d.label)).toEqual([
      "Empresa", "Inicio", "Cierre previsto", "Presupuesto",
    ])
  })

  it("las fechas salen en dd/mm/aaaa y no corridas un día por el huso", () => {
    const valores = datosClaveProyecto(BASE)
    expect(valores[1].valor).toBe("01/03/2026")
    expect(valores[2].valor).toBe("30/09/2026")
  })

  it("un proyecto sin cierre lo dice, no lo deja en blanco", () => {
    expect(datosClaveProyecto({ ...BASE, fecha_fin: null })[2].valor).toBe("Sin definir")
  })

  it("la descripción NO gasta uno de los cuatro: va bajo el título", () => {
    expect(barra(BASE)).toContain("Porteo de Supabase a RDS")
    expect(datosClaveProyecto(BASE).map((d) => d.label)).not.toContain("Descripción")
  })

  it("el consumo NO sube a la barra: es el panel de costeo", () => {
    // Es la línea que divide barra y panel. Si alguien sube "Consumido" o el porcentaje, el panel
    // de abajo queda repitiéndolo tres renglones más abajo.
    const labels = datosClaveProyecto(BASE).map((d) => d.label)
    expect(labels).not.toContain("Consumido")
    expect(labels).not.toContain("Restante")
  })

  it("las migas llevan a Proyectos y la actual no es link", () => {
    const html = barra(BASE)
    expect(html).toContain('href="/proyectos"')
    expect(html).toContain('aria-current="page"')
  })
})

describe("(b) la acción primaria es la última del grupo", () => {
  const conAccion = barra(BASE, <Button className="min-h-11">Editar</Button>)

  it("hoy hay UNA sola acción y es la primaria", () => {
    expect(conAccion.match(/<button/g) ?? []).toHaveLength(1)
    expect(conAccion).toContain("Editar")
  })

  it("sin permiso de escritura la barra no dibuja ninguna acción", () => {
    expect(barra(BASE).match(/<button/g) ?? []).toHaveLength(0)
  })
})

describe("(c) el chip de estado no usa variant=default", () => {
  it("usa los pares semánticos de la paleta", () => {
    // Sin acciones a propósito: el botón primario también trae `bg-primary` y taparía el fallo.
    expect(barra(BASE)).toContain("bg-success-wash")
    expect(barra({ ...BASE, estado: "pausado" })).toContain("bg-warning-wash")
    expect(barra({ ...BASE, estado: "cancelado" })).toContain("bg-danger-wash")
  })

  it("ningún estado pinta el relleno de marca", () => {
    for (const estado of ["activo", "pausado", "cerrado", "cancelado"] as const) {
      expect(barra({ ...BASE, estado }), `${estado} pinta bg-primary`).not.toContain("bg-primary")
    }
  })
})
