import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import type { Vacante } from "@/types/vacantes"

import { AccionesVacante } from "./AccionesVacante"
import { BarraVacante } from "./BarraVacante"
import { datosClaveVacante } from "./_datosClaveVacante"

// `EliminarVacanteButton` pide el router para navegar a /vacantes después de borrar, y fuera de
// Next no hay ninguno montado. Se falsea lo mínimo: acá no se prueba la navegación, se prueba
// DÓNDE queda el botón dentro del grupo de acciones.
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: () => {}, push: () => {} }) }))

/**
 * La barra de identidad de la ficha de una VACANTE: los cuatro datos clave, el orden de las tres
 * acciones y el chip de estado.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR?
 *   · (a) cuenta los `<dt>` del markup real: un quinto dato lo rojea aunque no pase por
 *     `datosClaveVacante`.
 *   · (b) es la ÚNICA de las cinco fichas con tres acciones, así que acá la aserción de orden es
 *     de verdad: compara POSICIONES en el HTML, no presencia. El orden anterior era LinkedIn →
 *     agregar → eliminar; un `toContain` pasaba con los dos órdenes y esto sólo pasa con el bueno.
 *     Se verifica en los dos estados de LinkedIn, porque cambia el primer elemento del grupo.
 *   · (c) compara contra el mapa semántico del listado y contra el relleno de marca: `en_proceso`
 *     venía con `variant="default"` y volver a ponerlo mete `bg-primary` y rojea.
 *   · (d) NO HAY TEST DE HISTORIAL ACÁ, y no es un olvido: una vacante no tiene ninguno. Lo que
 *     más se le parece —el paso de un candidato por las etapas— no se guarda como serie: la base
 *     tiene la etapa ACTUAL en `candidatos.etapa_pipeline` y nada de por dónde pasó antes, así
 *     que un "de → a" habría que inventarlo. El chip "Vigente" lo cubre
 *     `components/ui/Historial.test.tsx`.
 */

const BASE: Vacante = {
  id: "v1", codigo: "VAC-0007", empresa_id: "e1", empresa_nombre: "Bodegas Tupungato",
  titulo: "Analista de datos", area_id: "a1", area_nombre: "Sistemas",
  descripcion: "Reporte a la gerencia de Sistemas", requisitos: null, tipo_contrato: "Relación de dependencia",
  estado: "en_proceso", fecha_apertura: "2026-08-12", created_at: "2026-08-01T10:00:00Z",
  linkedin_post_id: null, linkedin_url: null, email_contacto: null, copy_publicacion: null,
  hashtags: null, ubicacion: null, modalidad: null, jornada: null, funciones: null,
  formacion: null, experiencia: null, conocimientos_tecnicos: null,
}

const barra = (vacante: Vacante, candidatos = 3, acciones?: React.ReactNode) =>
  renderToStaticMarkup(<BarraVacante vacante={vacante} candidatos={candidatos} acciones={acciones} />)

const acciones = (vacante: Vacante, canWrite = true) =>
  renderToStaticMarkup(
    <AccionesVacante
      vacante={vacante}
      canWrite={canWrite}
      onPublicarLinkedin={() => {}}
      onAgregarCandidato={() => {}}
    />,
  )

describe("(a) la barra de la vacante muestra EXACTAMENTE cuatro datos clave", () => {
  it("cuatro, ni tres ni cinco", () => {
    expect(datosClaveVacante(BASE, 3)).toHaveLength(4)
    expect(barra(BASE).match(/<dt/g) ?? []).toHaveLength(4)
  })

  it("son empresa, área, apertura y candidatos", () => {
    expect(datosClaveVacante(BASE, 3).map((d) => d.label)).toEqual([
      "Empresa", "Área", "Apertura", "Candidatos",
    ])
  })

  it("la apertura sale en dd/mm/aaaa y no corrida un día por el huso", () => {
    // El encabezado viejo usaba `new Date(iso).toLocaleDateString`, que parsea a medianoche UTC y
    // en Argentina muestra el día anterior. Ahora pasa por el formateador compartido.
    expect(datosClaveVacante(BASE, 3)[2].valor).toBe("12/08/2026")
  })

  it("sin fecha de apertura usa la de creación en vez de una raya", () => {
    expect(datosClaveVacante({ ...BASE, fecha_apertura: null }, 3)[2].valor).toBe("01/08/2026")
  })

  it("una vacante sin candidatos dice cero, no queda en blanco", () => {
    expect(datosClaveVacante(BASE, 0)[3].valor).toBe("0")
  })

  it("la descripción NO gasta uno de los cuatro: va bajo el título", () => {
    expect(barra(BASE)).toContain("Reporte a la gerencia de Sistemas")
    expect(datosClaveVacante(BASE, 3).map((d) => d.label)).not.toContain("Descripción")
  })

  it("el código no gasta uno de los cuatro: vive con el texto que se copia", () => {
    expect(datosClaveVacante(BASE, 3).map((d) => d.label)).not.toContain("Código")
  })

  it("las migas llevan a Vacantes y la actual no es link", () => {
    const html = barra(BASE)
    expect(html).toContain('href="/vacantes"')
    expect(html).toContain('aria-current="page"')
  })
})

describe("(b) la acción primaria es la ÚLTIMA del grupo", () => {
  it("con LinkedIn sin publicar: publicar → eliminar → agregar", () => {
    const html = acciones(BASE)
    expect(html.indexOf("Publicar en LinkedIn")).toBeLessThan(html.indexOf("Eliminar vacante"))
    expect(html.indexOf("Eliminar vacante")).toBeLessThan(html.indexOf("Agregar candidato"))
  })

  it("con LinkedIn ya publicado: el enlace → eliminar → agregar", () => {
    const html = acciones({ ...BASE, linkedin_post_id: "p1", linkedin_url: "https://li/p1" })
    expect(html.indexOf("Publicada en LinkedIn")).toBeLessThan(html.indexOf("Eliminar vacante"))
    expect(html.indexOf("Eliminar vacante")).toBeLessThan(html.indexOf("Agregar candidato"))
  })

  it("🔴 la acción irreversible NO queda última", () => {
    // El orden anterior era LinkedIn → agregar → eliminar: el botón destructivo en el borde de la
    // barra, que es donde termina el recorrido del ojo y donde va el pulgar.
    const html = acciones(BASE)
    expect(html.lastIndexOf("Eliminar vacante")).toBeLessThan(html.lastIndexOf("Agregar candidato"))
  })

  it("sin permiso de escritura sólo queda el enlace al aviso publicado", () => {
    const publicada = acciones({ ...BASE, linkedin_post_id: "p1", linkedin_url: "https://li/p1" }, false)
    expect(publicada).toContain("Publicada en LinkedIn")
    expect(publicada).not.toContain("Eliminar vacante")
    expect(publicada).not.toContain("Agregar candidato")
    // Y sin publicar, no queda ninguna acción.
    expect(acciones(BASE, false).match(/<button/g) ?? []).toHaveLength(0)
  })
})

describe("(c) el chip de estado no usa variant=default", () => {
  it("los cuatro estados usan los pares semánticos", () => {
    // Sin acciones a propósito: el botón primario también trae `bg-primary`.
    expect(barra({ ...BASE, estado: "nueva" })).toContain("bg-warning-wash")
    expect(barra({ ...BASE, estado: "en_proceso" })).toContain("bg-secondary")
    expect(barra({ ...BASE, estado: "con_candidatos" })).toContain("bg-success-wash")
    expect(barra({ ...BASE, estado: "cerrada" })).toContain("bg-danger-wash")
  })

  it("ninguno pinta el relleno de marca", () => {
    for (const estado of ["nueva", "en_proceso", "con_candidatos", "cerrada"] as const) {
      expect(barra({ ...BASE, estado }), `${estado} pinta bg-primary`).not.toContain("bg-primary")
    }
  })
})
