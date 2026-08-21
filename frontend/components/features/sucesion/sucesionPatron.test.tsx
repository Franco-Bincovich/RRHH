import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"

import { construirCamposSucesion } from "./_camposSucesion"
import { NIVEL_BADGE_CLASS, readinessBarColor } from "./_sucesion_ui"
import { ZONE_BG, ZONE_TEXT } from "./_nineBoxGrilla"
import { MapaTalentoTab } from "./MapaTalentoTab"

/**
 * El patrón del bloque B sobre /sucesion, **que está APAGADA por flag y sigue apagada**: esta
 * tanda la reestiló, no la encendió. El último bloque de acá abajo es el que lo fija.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCamposSucesion`, EL CABLEADO REAL de la barra.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que el chip volviera a mostrar el uuid del área en vez de su nombre.
 *   · (c) que el vacío volviera a decir "esta área" sin nombrar cuál.
 *   · colores: que alguien reponga un `emerald-50`/`amber-100` de la escala cruda de Tailwind.
 *   · flag: que `useState(false)` pase a `true`, o que vuelva el `const` con literal.
 */

const AREAS = [
  { id: "a1", nombre: "Sistemas" },
  { id: "a2", nombre: "Ventas" },
] as Parameters<typeof construirCamposSucesion>[0]["areas"]

describe("(a) el chip del área muestra el nombre, no el uuid", () => {
  it("con el área a1 elegida, el chip dice 'Sistemas'", () => {
    const chips = chipsDeCampos(construirCamposSucesion({ areas: AREAS, area: "a1", setArea: vi.fn() }))
    expect(chips.length).toBe(1)
    expect(chips[0].clave).toBe("Área")
    expect(chips[0].valor).toBe("Sistemas")
  })

  it("sin área elegida no hay ningún chip", () => {
    const chips = chipsDeCampos(construirCamposSucesion({ areas: AREAS, area: "", setArea: vi.fn() }))
    expect(chips.length).toBe(0)
  })
})

describe("(b) quitar el chip limpia el filtro", () => {
  it("llama al setter con la cadena vacía, que es 'todas las áreas'", () => {
    const setArea = vi.fn()
    chipsDeCampos(construirCamposSucesion({ areas: AREAS, area: "a2", setArea }))[0].quitar()
    expect(setArea).toHaveBeenCalledWith("")
  })

  it("⚠️ (d) NO APLICA: el mapa no pagina ni exporta, así que no hay pie que contar", () => {
    // `GET /api/sucesion/mapa-talento` devuelve el padrón entero y la tab lo reparte en nueve
    // casilleros. Un `<Pagination>` acá no tendría páginas que recorrer.
    const src = readFileSync(path.resolve(__dirname, "MapaTalentoTab.tsx"), "utf8")
    expect(src).not.toContain("<Pagination")
    // Contracara: la barra de filtros SÍ está, y en su forma de panel con chips.
    expect(src).toContain("<FiltersBar campos={campos} panel")
  })
})

function mapa(props: Partial<Parameters<typeof MapaTalentoTab>[0]> = {}) {
  return renderToStaticMarkup(
    <MapaTalentoTab
      empleados={[]} areas={AREAS} selectedArea="" onSelectArea={() => {}}
      loading={false} error={null} onReintentar={() => {}} onAnalizar={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío usa el valor real del filtro y dice qué significa la ausencia", () => {
  it("con un área elegida, la frase la nombra", () => {
    const html = mapa({ selectedArea: "a1" })
    expect(html).toContain("Nadie de Sistemas tiene potencial y desempeño cargados.")
  })

  it("sin filtros explica por qué el mapa puede estar vacío con gente cargada", () => {
    // El 9-box cruza DOS campos: un padrón entero sin `potencial`/`desempeno` deja el mapa
    // vacío sin que falte una sola persona. Decir "no hay colaboradores" sería falso.
    expect(mapa()).toContain("El mapa cruza potencial con desempeño")
  })

  it("el filtro sigue A LA VISTA mientras carga, deshabilitado y no vaciado", () => {
    const html = mapa({ loading: true, selectedArea: "a1" })
    expect(html).toContain("Sistemas")
    expect(html).toContain("disabled")
    // Y el esqueleto tiene la forma de la grilla que va a llegar: nueve casilleros.
    expect((html.match(/min-h-\[100px\]/g) ?? []).length).toBe(9)
    expect(html).toContain("animate-shimmer")
  })

  it("🔴 el error NO se dibuja como un vacío: trae su reintento", () => {
    const html = mapa({ error: "No se pudo cargar el mapa de talento." })
    expect(html).toContain("Reintentar")
    expect(html).toContain("No se pudo cargar el mapa de talento.")
  })
})

describe("🔴 los colores salen de la paleta semántica, no de la escala cruda de Tailwind", () => {
  const CRUDOS = ["emerald", "amber", "rose", "slate", "blue", "green", "red"]

  it("las tres zonas del 9-box, los tres niveles y la barra de readiness", () => {
    const clases = [
      ...Object.values(ZONE_BG), ...Object.values(ZONE_TEXT),
      ...Object.values(NIVEL_BADGE_CLASS),
      readinessBarColor(90), readinessBarColor(50), readinessBarColor(10),
    ]
    // Guarda contra el falso verde: si los mapas quedaran vacíos, el for no compara nada.
    expect(clases.length).toBeGreaterThanOrEqual(12)
    for (const clase of clases) {
      for (const crudo of CRUDOS) {
        expect(clase, `"${clase}" volvió a la escala cruda de Tailwind`).not.toContain(crudo)
      }
    }
  })

  it("y ninguna necesita ya una variante `dark:`: el token cambia solo con el tema", () => {
    for (const clase of [...Object.values(ZONE_BG), ...Object.values(NIVEL_BADGE_CLASS)]) {
      expect(clase).not.toContain("dark:")
    }
  })

  it("los tres tramos de readiness siguen siendo tres colores distintos", () => {
    // Contracara del test de arriba: mapear todo a un mismo token pasaría la negación anterior.
    expect(new Set([readinessBarColor(90), readinessBarColor(50), readinessBarColor(10)]).size).toBe(3)
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("🔴 EL MÓDULO SIGUE APAGADO: reestilarlo no fue encenderlo", () => {
  const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "sucesion", "page.tsx")
  const NAV = path.resolve(__dirname, "..", "..", "layout", "nav-config.ts")

  it("la página sigue con el flag en false y redirige a /dashboard", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).toContain("const [moduloActivo] = useState(false)")
    expect(src).toContain('router.replace("/dashboard")')
  })

  it("y el ítem sigue fuera del sidebar", () => {
    const src = sinComentarios(readFileSync(NAV, "utf8"))
    expect(src).toContain("const SUCESION_ACTIVA: boolean = false")
    // 🔑 `: boolean` anotado NO es decoración: sin él TS colapsa el tipo al literal `false`, la
    // rama `true` del ternario deja de type-checkear y reactivar el módulo rompería el build.
    expect(src).not.toContain("const SUCESION_ACTIVA = false")
  })
})
