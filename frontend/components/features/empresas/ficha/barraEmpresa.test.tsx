import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { Button } from "@/components/ui/button"
import type { Empresa } from "@/types/empresa"

import { BarraEmpresa } from "./BarraEmpresa"
import { datosClaveEmpresa } from "./_datosClaveEmpresa"

/**
 * La barra de identidad de la ficha de una EMPRESA: los cuatro datos clave, el orden de las
 * acciones y el chip de estado.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR?
 *   · (a) cuenta los `<dt>` del markup real. Ojo: el panel de marca también usa `Campo`, que
 *     emite `<dt>`; por eso el conteo se hace sobre la BARRA sola y no sobre la página.
 *   · (b) esta ficha tiene UNA sola acción. La aserción de posición sería vacua, así que se
 *     cuentan los botones: el día que aparezca una segunda —subir el logo, desactivar la
 *     empresa— este test rojea y obliga a escribir el orden de verdad.
 *   · (c) `activa` era `variant="default"`, o sea `bg-primary`. El test compara contra el mapa
 *     semántico del listado y contra el relleno de marca, así que volver al `variant` lo rojea.
 *   · (d) NO HAY TEST DE HISTORIAL ACÁ, y no es un olvido: una empresa no acumula cambios
 *     fechados en el modelo. `empresas` tiene `updated_at` —cuándo se tocó por última vez— pero
 *     no guarda QUÉ cambió ni desde qué valor, que es lo único que un historial "de → a" puede
 *     mostrar. El chip "Vigente" lo cubre `components/ui/Historial.test.tsx`.
 */

const BASE: Empresa = {
  id: "e1",
  nombre: "Bodegas Tupungato",
  razon_social: "Bodegas Tupungato S.A.",
  cuit: "30-71234567-9",
  direccion: "Ruta 40 km 12, Tupungato",
  telefono: "+54 261 555-0100",
  email: "rrhh@tupungato.com",
  logo_url: null,
  activa: true,
  created_at: "2025-04-18",
  updated_at: null,
}

const barra = (empresa: Empresa, acciones?: React.ReactNode) =>
  renderToStaticMarkup(<BarraEmpresa empresa={empresa} acciones={acciones} />)

describe("(a) la barra de la empresa muestra EXACTAMENTE cuatro datos clave", () => {
  it("cuatro, ni tres ni cinco", () => {
    expect(datosClaveEmpresa(BASE)).toHaveLength(4)
    expect(barra(BASE).match(/<dt/g) ?? []).toHaveLength(4)
  })

  it("son CUIT, email, teléfono y dirección", () => {
    expect(datosClaveEmpresa(BASE).map((d) => d.label)).toEqual([
      "CUIT", "Email", "Teléfono", "Dirección",
    ])
  })

  it("la razón social NO gasta uno de los cuatro: va bajo el nombre", () => {
    expect(barra(BASE)).toContain("Bodegas Tupungato S.A.")
    expect(datosClaveEmpresa(BASE).map((d) => d.label)).not.toContain("Razón social")
  })

  it("una empresa sin razón social lo dice en vez de dejar el renglón vacío", () => {
    expect(barra({ ...BASE, razon_social: null })).toContain("Sin razón social cargada")
  })

  it("un campo sin cargar sale como raya, no como texto inventado", () => {
    const vacia = datosClaveEmpresa({ ...BASE, cuit: null, email: null, telefono: null, direccion: null })
    expect(vacia.map((d) => d.valor)).toEqual(["—", "—", "—", "—"])
  })

  it("el monograma sale del nombre, no del logo", () => {
    // Con logo cargado tiene que seguir diciendo BT: el círculo se pinta antes de que la imagen
    // remota llegue, y un logo que falla dejaría el encabezado con un hueco.
    expect(barra({ ...BASE, logo_url: "https://x/logo.png" })).toContain("BT")
  })

  it("las migas llevan a Empresas y la actual no es link", () => {
    const html = barra(BASE)
    expect(html).toContain('href="/empresas"')
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
  it("activa e inactiva usan los pares semánticos, no el relleno de marca", () => {
    // Sin acciones a propósito: el botón primario también trae `bg-primary`.
    expect(barra(BASE)).toContain("bg-success-wash")
    expect(barra(BASE)).not.toContain("bg-primary")
    expect(barra({ ...BASE, activa: false })).toContain("bg-secondary")
    expect(barra({ ...BASE, activa: false })).not.toContain("bg-primary")
  })

  it("el texto del chip dice cuál de los dos es", () => {
    expect(barra(BASE)).toContain("Activa")
    expect(barra({ ...BASE, activa: false })).toContain("Inactiva")
  })
})
