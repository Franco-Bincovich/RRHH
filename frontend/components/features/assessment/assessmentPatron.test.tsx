import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { CampanasTabla } from "./CampanasTabla"
import { ResultadosTabla } from "./ResultadosTabla"
import { COLUMNAS_CAMPANAS, COLUMNAS_RESULTADOS, ESTADO_ESTILO } from "./_grillaAssessment"

/**
 * El patrón del bloque B sobre /assessment, **que está APAGADA por flag y sigue apagada**: esta
 * tanda la reestiló, no la encendió. El último bloque de acá abajo es el que lo fija.
 *
 * ⚠️ (a) (b) y (d) NO APLICAN, y no es un olvido: ni `GET /api/assessment/campanas` ni
 * `/resultados` aceptan un solo Query — devuelven la lista entera. Sin filtros no hay chips y sin
 * paginado no hay pie. Hay un test abajo que lo fija en las dos direcciones.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (c) que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · que el vacío de resultados vuelva a pedirle a RRHH que "cargue el primero".
 *   · que "activa" vuelva a `variant="default"`, o sea al relleno `bg-primary`.
 *   · flag: que `useState(false)` pase a `true`.
 */

type Campana = Parameters<typeof CampanasTabla>[0]["campanas"][number]

const CAMPANA = {
  id: "c1", nombre: "Assessment Q2", tipo: "completo", estado: "activa",
  created_at: "2026-04-01T00:00:00Z", links_enviados: 4, completados: 4, empresa_nombre: null,
} as unknown as Campana

function campanas(props: Partial<Parameters<typeof CampanasTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <CampanasTabla
      campanas={[]} loading={false} error={false} onReintentar={() => {}} mostrarEmpresa={false}
      {...props}
    />,
  )
}

function resultados(props: Partial<Parameters<typeof ResultadosTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <ResultadosTabla
      resultados={[]} loading={false} error={false} onReintentar={() => {}} mostrarEmpresa={false} onAbrir={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío mantiene el encabezado: es una fila de la tabla, no su reemplazo", () => {
  it("campañas conserva sus columnas", () => {
    const html = campanas()
    for (const columna of ["Nombre", "Tipo", "Creada", "Links", "Completados", "Estado"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
  })

  it("resultados también, y con su propia cantidad de columnas", () => {
    const html = resultados()
    for (const columna of ["Evaluado", "Tipo", "Fecha", "Perfil dominante", "Score"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
  })

  it("🔴 el vacío de RESULTADOS no le pide a nadie que cargue el primero", () => {
    /*
     * Un resultado aparece cuando la persona TERMINA de responder el link de su campaña: nadie lo
     * carga a mano. La frase genérica de `textoVacio` —"cuando se cargue el primero va a aparecer
     * acá"— mandaría al usuario de RRHH a buscar un botón que no existe y que no debería existir.
     * Por eso esta tabla es la única de la pantalla que no usa `TablaVacia`.
     */
    const html = resultados()
    expect(html).toContain("Todavía no completó nadie")
    expect(html).not.toContain("Cuando se cargue el primero")
  })

  it("el de CAMPAÑAS sí usa la frase del sistema, y concuerda en femenino", () => {
    // Acá la campaña SÍ la crea alguien de RRHH, así que la frase genérica es la correcta.
    const html = campanas()
    expect(html).toContain("Todavía no hay campañas")
    expect(html).toContain("la primera")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla", () => {
    const html = campanas({ loading: true })
    // 6 columnas: sin la de empresa, que sólo existe con el sidebar en consolidado.
    expect((html.match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((html.match(/<td[ >]/g) ?? []).length).toBe(8 * 6)
    expect(html).toContain("animate-shimmer")
  })

  it("la columna de empresa aparece SÓLO en modo consolidado, en las dos tablas", () => {
    expect((campanas({ mostrarEmpresa: true, loading: true }).match(/<th[ >]/g) ?? []).length).toBe(7)
    expect((resultados({ mostrarEmpresa: true, loading: true }).match(/<th[ >]/g) ?? []).length).toBe(6)
    expect((resultados({ loading: true }).match(/<th[ >]/g) ?? []).length).toBe(5)
  })

  it("🔴 el error NO se dibuja como un vacío: trae su reintento", () => {
    const html = campanas({ error: true })
    expect(html).toContain("No se pudieron cargar las campañas")
    expect(html).toContain("Reintentar")
    // Y no finge una tabla vacía debajo del cartel.
    expect(html).not.toContain("<thead")
  })
})

describe("🔴 ninguna etiqueta de estado se pinta con el color de la marca", () => {
  it("los cuatro estados salen de la paleta semántica y ninguno es `bg-primary`", () => {
    const estilos = Object.values(ESTADO_ESTILO)
    // Guarda contra el falso verde: si el mapa quedara vacío, el for no compara nada.
    expect(estilos.length).toBe(4)
    for (const estilo of estilos) {
      expect(estilo).not.toContain("bg-primary")
      expect(estilo).not.toContain("emerald")
    }
    // Contracara: "cerrada" y "activa" SÍ se distinguen entre sí — no se resolvió pintando todo gris.
    expect(ESTADO_ESTILO.activa).not.toBe(ESTADO_ESTILO.cerrada)
  })

  it("la fila tampoco usa el verde crudo para 'completados = enviados'", () => {
    const html = campanas({ campanas: [CAMPANA] })
    expect(html).toContain("text-success")
    expect(html).not.toContain("emerald")
  })

  it("y 4/4 se marca sólo si hubo links enviados: 0/0 no es un logro", () => {
    const cero = campanas({ campanas: [{ ...CAMPANA, links_enviados: 0, completados: 0 }] })
    expect(cero).not.toContain("text-success")
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("⚠️ (a) (b) y (d) no aplican, y está declarado en el código", () => {
  it("ninguna de las dos tablas monta FiltersBar ni Pagination", () => {
    for (const archivo of ["CampanasTabla.tsx", "ResultadosTabla.tsx"]) {
      const src = sinComentarios(readFileSync(path.resolve(__dirname, archivo), "utf8"))
      expect(src, `${archivo} montó una barra de filtros que el backend no puede honrar`).not.toContain("<FiltersBar")
      expect(src, `${archivo} montó un pie sin backend paginado`).not.toContain("<Pagination")
    }
  })

  it("las dos grillas declaran sus columnas en un módulo compartido, con una sola flexible", () => {
    // Exactamente una columna con `ancho: ""` por tabla: es la que absorbe el espacio libre.
    for (const columnas of [COLUMNAS_CAMPANAS, COLUMNAS_RESULTADOS]) {
      expect(columnas.filter((c) => c.ancho === "").length).toBe(1)
    }
  })
})

describe("🔴 EL MÓDULO SIGUE APAGADO: reestilarlo no fue encenderlo", () => {
  const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "assessment", "page.tsx")

  it("la página sigue con el flag en false y redirige a /dashboard", () => {
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).toContain("const [moduloActivo] = useState(false)")
    expect(src).toContain('router.replace("/dashboard")')
  })

  it("🔴 y ya NO hay hooks después de un return incondicional", () => {
    /*
     * Antes la página hacía `useEffect(redirigir); return null` y seguía con SIETE `useState` y
     * otro `useEffect` debajo, tapados con `// eslint-disable-next-line no-unreachable`. Eran
     * hooks que no corrían nunca y que cambiarían de orden el día que alguien sacara el return:
     * reactivar el módulo era una línea que rompía las reglas de hooks sin avisar. Ahora el
     * contenido vive en un componente aparte, que además no se monta —así la pantalla apagada no
     * dispara sus dos llamadas al backend antes de redirigir—.
     */
    const src = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(src).not.toContain("no-unreachable")
    expect(src).toContain("function AssessmentContenido()")
    expect(src).toContain("return <AssessmentContenido />")
  })
})
