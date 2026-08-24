/**
 * BARRIDO ESTRUCTURAL — todo `<DropdownMenuLabel>` vive dentro de un `<DropdownMenuGroup>`.
 *
 * 🔴 POR QUÉ ESTE ARCHIVO EXISTE. `DropdownMenuLabel` es `Menu.GroupLabel` de Base UI, que se
 * registra contra el contexto de su `Menu.Group`. Sin un Group arriba **lanza**, el popup no
 * llega a renderizarse y el menú NO ABRE. El 23/8/2026 eso dejaba el menú de usuario muerto:
 * Configuración, Cambiar contraseña y Cerrar sesión inalcanzables, y el logout no tiene otra
 * puerta. Era el ÚNICO uso de ese componente en todo el front y el ÚNICO dropdown que fallaba,
 * o sea que nada lo vigilaba y el síntoma no se parecía a su causa.
 *
 * 🔴 Y POR QUÉ ES UN BARRIDO DE FUENTE Y NO UN RENDER. Medido: `renderToStaticMarkup` sobre el
 * menú abierto devuelve SOLO el trigger — el contenido vive detrás de `Menu.Portal`, que en un
 * render de servidor no emite nada. O sea que un test de render NO PUEDE tocar la línea que
 * falla, ni con `defaultOpen`. La única forma de que esto se vea antes de producción es leer
 * la estructura. (Lo que sí se puede renderizar es la PIEZA suelta, y eso es lo que hace el
 * primer bloque: ahí sí se ve el throw.)
 */
import { readFileSync } from "node:fs"
import { readdirSync } from "node:fs"
import { join } from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import {
  DropdownMenuGroup,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"

describe("el contrato del primitivo", () => {
  it("un label suelto LANZA: es el modo de falla que rompió el menú", () => {
    expect(() => renderToStaticMarkup(<DropdownMenuLabel>rol</DropdownMenuLabel>)).toThrow()
  })

  it("dentro de un group renderiza", () => {
    const html = renderToStaticMarkup(
      <DropdownMenuGroup>
        <DropdownMenuLabel>Administrador RRHH</DropdownMenuLabel>
      </DropdownMenuGroup>
    )
    expect(html).toContain("Administrador RRHH")
  })
})

const RAIZ = process.cwd()
const IGNORAR = new Set(["node_modules", ".next", ".git", "public"])

function archivosDe(dir: string): string[] {
  const salida: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (IGNORAR.has(e.name)) continue
    const completo = join(dir, e.name)
    if (e.isDirectory()) salida.push(...archivosDe(completo))
    else if (/\.tsx$/.test(e.name) && !/\.test\.tsx$/.test(e.name)) salida.push(completo)
  }
  return salida
}

/** Enmascara comentarios: un archivo puede EXPLICAR la regla en prosa sin ser un uso. */
function sinComentarios(texto: string): string {
  return texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*/g, "")
}

/** ¿Cada `<DropdownMenuLabel` cae entre la apertura y el cierre de un `<DropdownMenuGroup`? */
function labelsHuerfanos(codigo: string): number {
  let profundidad = 0
  let huerfanos = 0
  const tokens = codigo.match(/<\/?DropdownMenu(?:Group|Label)\b/g) ?? []
  for (const t of tokens) {
    if (t === "<DropdownMenuGroup") profundidad++
    else if (t === "</DropdownMenuGroup") profundidad = Math.max(0, profundidad - 1)
    else if (t === "<DropdownMenuLabel" && profundidad === 0) huerfanos++
  }
  return huerfanos
}

const ARCHIVOS = archivosDe(RAIZ)
const CON_LABEL = ARCHIVOS.filter((f) =>
  sinComentarios(readFileSync(f, "utf8")).includes("<DropdownMenuLabel")
)

describe("barrido: ningún label huérfano en el producto", () => {
  it("guardas de mínimo", () => {
    // Sin esto, un descubrimiento roto devolvería 0 archivos y el barrido pasaría en el vacío.
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)
    expect(CON_LABEL.length).toBeGreaterThanOrEqual(1)
  })

  it("todo <DropdownMenuLabel> está dentro de un <DropdownMenuGroup>", () => {
    const rotos = CON_LABEL.filter(
      (f) => labelsHuerfanos(sinComentarios(readFileSync(f, "utf8"))) > 0
    ).map((f) => f.slice(RAIZ.length + 1))
    expect(rotos, "labels sin group: el dropdown no abre").toEqual([])
  })

  it("el detector reconoce un label huérfano (si no, el barrido no prueba nada)", () => {
    expect(labelsHuerfanos("<DropdownMenuContent><DropdownMenuLabel>x</DropdownMenuLabel>")).toBe(1)
    expect(
      labelsHuerfanos("<DropdownMenuGroup><DropdownMenuLabel>x</DropdownMenuLabel></DropdownMenuGroup>")
    ).toBe(0)
    // Un group que ya cerró no cubre a un label posterior.
    expect(
      labelsHuerfanos("<DropdownMenuGroup></DropdownMenuGroup><DropdownMenuLabel>x</DropdownMenuLabel>")
    ).toBe(1)
  })
})
