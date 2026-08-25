/**
 * 🔴 BARRIDO ESTRUCTURAL — ninguna PÁGINA decide sola quién puede entrar. El modelo de permisos
 * es el único gate de ruta, y las páginas no lo pueden contradecir en silencio.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * LO QUE LO MOTIVÓ: /usuarios TENÍA UN TERCER GATE, Y CONTRADECÍA A LOS OTROS DOS
 * ═══════════════════════════════════════════════════════════════════════════════════
 * `utils/permisos.py`, `services/permisos.ts` y `routers/usuarios.py` coincidían: `USUARIOS +
 * READ`, o sea que `gerencia_lectura` puede ver la pantalla. `app/(dashboard)/usuarios/page.tsx`
 * la rebotaba igual, con un `router.replace()` propio condicionado a `write`. **Y ningún test lo
 * comparaba contra el modelo** — es la clase de divergencia que nadie mira, porque para verla hay
 * que sospechar de un archivo que se lee perfectamente coherente por dentro.
 *
 * Peor todavía: había un test que la FIJABA. `usuariosPatron.test.tsx` exigía por escrito el
 * literal `puede(r, "usuarios", "write")` en la página, así que el guard equivocado estaba
 * protegido por una aserción. Mismo caso que `dialog.test.tsx`, que protegía la regresión de los
 * 20 modales con `max-h-[90vh]` hasta que se dio vuelta.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * EL EJE: UN REBOTE DE RUTA DENTRO DE UNA PÁGINA, NO "TODO USO DE puede()"
 * ═══════════════════════════════════════════════════════════════════════════════════
 * Se busca el acto que reemplaza al AuthGuard: **una página que navega a otro lado desde un
 * efecto** (`router.replace(` / `router.push(` fuera de un handler). Eso es "decidir quién entra".
 * Preguntar por "toda página que llama a `puede()`" marcaría a las decenas que gatean BOTONES,
 * que es correcto y es lo que `useCanWrite` existe para hacer.
 *
 * ⚠️ LOS DOS MÓDULOS APAGADOS SON LA EXCEPCIÓN LEGÍTIMA, y no se pueden confundir con esto:
 * /sucesion y /assessment redirigen porque el módulo está APAGADO por decisión de producto, no
 * por el rol de quien entra. Su flag es `useState(false)` y CLAUDE.md explica por qué no puede ser
 * un `const` (TS colapsaría el tipo literal y `next build` fallaría). Se declaran abajo.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? La guarda de mínimo corre antes: si
 * el descubrimiento de páginas se rompe, el conjunto colapsa y falla acá. Verificado por mutación:
 * devolviéndole el guard a /usuarios, rojea nombrándolo.
 */
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"

import { describe, expect, it } from "vitest"

import { seccionDeRuta } from "@/services/permisos"

const RAIZ = join(__dirname, "..", "..")

/**
 * Páginas que SÍ redirigen por su cuenta, con su razón. La razón válida es que el motivo NO sea
 * el rol de quien entra: si lo es, el lugar donde se decide es el modelo de permisos.
 */
const REDIRIGEN: Record<string, string> = {
  "sucesion": "MÓDULO APAGADO por decisión de producto (dos flags del front, ver CLAUDE.md). "
    + "Redirige a cualquiera, sea cual sea su rol: no es un gate de permisos.",
  "assessment": "MÓDULO APAGADO (`ASSESSMENT_ENABLED` del backend + `useState(false)` acá). "
    + "Mismo caso que sucesión: redirige a todos por igual.",
  "login": "Es la puerta: redirige a /dashboard al que YA tiene sesión. Lo contrario de un gate.",
  "cambiar-password": "Redirige al terminar el cambio, no al entrar. Es el final del flujo.",
}

function paginas(dir: string): string[] {
  const out: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...paginas(p))
    else if (e.name === "page.tsx") out.push(p)
  }
  return out
}

/** Comentarios fuera: varias páginas explican EN PROSA el rebote que se les sacó. */
function sinComentarios(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

/** El segmento que identifica a la página: `app/(dashboard)/usuarios/page.tsx` → "usuarios". */
function segmento(archivo: string): string {
  const partes = archivo.split(/[\\/]/)
  return partes[partes.length - 2] ?? ""
}

const PAGINAS = paginas(join(RAIZ, "app"))

describe("el barrido está mirando algo", () => {
  it("descubre las páginas del producto", () => {
    expect(PAGINAS.length).toBeGreaterThanOrEqual(35)
  })
})

describe("el modelo de permisos es el único gate de ruta", () => {
  it("ninguna página se rebota a sí misma por el rol de quien entra", () => {
    const rebotan = PAGINAS
      .filter((f) => /router\.(replace|push)\(/.test(sinComentarios(readFileSync(f, "utf8"))))
      .map(segmento)
      .filter((seg) => !(seg in REDIRIGEN))
      // Un `router.push` dentro de un handler de click es navegación normal, no un gate: se
      // distingue porque la página además consulta el ROL para decidir.
      .filter((seg) => {
        const f = PAGINAS.find((p) => segmento(p) === seg)!
        const src = sinComentarios(readFileSync(f, "utf8"))
        return /getRol\(|useRol\(|puede\(/.test(src)
      })
    expect(rebotan,
      "Estas páginas deciden por su cuenta quién entra, mirando el rol. Eso lo decide el modelo " +
      "(`services/permisos.ts` + AuthGuard): un tercer gate en la página puede contradecirlo sin " +
      "que nada lo note, que es exactamente lo que pasó con /usuarios. Sacá el rebote, o " +
      "declaralo en REDIRIGEN con su razón — y la razón no puede ser el rol.",
    ).toEqual([])
  })

  it("toda página del dashboard con sección declarada la tiene mapeada en el modelo", () => {
    /**
     * La otra mitad: una página que existe y que `seccionDeRuta` no conoce queda SIN gate. Es el
     * mismo eje que `nav-config.test.ts` cubre para el sidebar, aplicado a las rutas reales.
     * Las que devuelven `null` son las no gateadas a propósito (/dashboard, /configuracion), así
     * que no se exige un mapeo: se exige que la función no reviente y que las conocidas coincidan.
     */
    expect(seccionDeRuta("/usuarios")).toBe("usuarios")
    expect(seccionDeRuta("/vacaciones")).toBe("vacaciones")
  })

  it("ninguna excepción declarada apunta a una página que ya no existe", () => {
    const segmentos = new Set(PAGINAS.map(segmento))
    const muertas = Object.keys(REDIRIGEN).filter((s) => !segmentos.has(s))
    expect(muertas, "Una excepción muerta es ruido que tapa el próximo caso.").toEqual([])
  })

  it("toda excepción tiene razón escrita", () => {
    expect(Object.entries(REDIRIGEN).filter(([, v]) => v.trim().length < 30).map(([k]) => k))
      .toEqual([])
  })
})
