import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { ImportObjetivosPreviewTabla } from "./ImportObjetivosPreview"
import { ImportObjetivosResultadoDetalle } from "./ImportObjetivosResultado"
import { ImportarObjetivosBoton } from "./ImportarObjetivosBoton"
import type {
  FilaObjetivoPreview, ImportacionObjetivosPreview, ImportacionObjetivosResultado,
} from "@/types/importacionObjetivos"

/**
 * La pantalla de import de objetivos: preview, resultado y el botón.
 *
 * 🔴 POR QUÉ SE TESTEAN LAS PIEZAS Y NO EL MODAL. `Dialog` monta por PORTAL y vitest corre con
 * `environment: "node"`, sin jsdom: renderizar `ImportarObjetivosModal` devuelve **string
 * vacío** y todo `expect(html).not.toContain(...)` pasaría en el aire. Por eso las dos vistas y
 * el botón son componentes propios y exportados — es lo que los hace afirmables. Molde:
 * `PlantillaAcciones.test.tsx`, que resolvió lo mismo para el modal de plantillas.
 *
 * ⚠️ LAS TRES TRAMPAS DE ESTE ARNÉS, y cómo se esquivan acá:
 *   1. Portal → cada test empieza por `noVacio(html)`: si el markup viniera vacío, las
 *      aserciones negativas pasarían solas.
 *   2. `not.toContain("disabled")` PASA SIEMPRE: la clase de shadcn trae `disabled:opacity-50`,
 *      así que la palabra está en el HTML aunque el botón esté habilitado. Se mira el ATRIBUTO
 *      (`disabled=""`) sobre el botón concreto, con el helper del repo.
 *   3. Sin jsdom no corren los `useEffect` ni los handlers: acá no se prueba interacción, se
 *      prueba QUÉ SE RENDERIZA con cada dato.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS DATOS PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 *   1. 🔴 EL PREVIEW TRAE FILAS VÁLIDAS **Y** CON PROBLEMAS. Con solo válidas, un componente
 *      que ignore por completo `errores` renderizaría lo mismo y pasaría — que es exactamente
 *      el caso #1 de la regla del repo.
 *   2. 🔴 EL RESULTADO PARCIAL TIENE `importados > 0` **Y** `errores.length > 0` A LA VEZ. Con
 *      un resultado todo-éxito o todo-error, "no lo muestra como éxito completo" no se puede
 *      distinguir de "lo muestra bien por casualidad".
 *   3. Los títulos y motivos son distintos entre sí, así que se puede afirmar QUÉ fila se
 *      renderizó y no solo cuántas.
 */

function noVacio(html: string): string {
  // Trampa 1: sin esta guarda, un componente que renderice vacío haría pasar todo lo negativo.
  expect(html.length, "el componente renderizó vacío — ¿se montó por portal?").toBeGreaterThan(50)
  return html
}

/** El `<button>` que contiene ese texto, o null. */
function boton(html: string, texto: string): string | null {
  for (const m of html.matchAll(/<button[\s\S]*?<\/button>/g)) {
    if (m[0].includes(texto)) return m[0]
  }
  return null
}

/** ¿Ese botón está deshabilitado? Por el ATRIBUTO, no por la clase — ver la trampa 2. */
function deshabilitado(html: string, texto: string): boolean {
  const b = boton(html, texto)
  expect(b, `no se encontró el botón "${texto}"`).not.toBeNull()
  return b!.includes('disabled=""')
}

function fila(over: Partial<FilaObjetivoPreview> & { fila: number; titulo: string }): FilaObjetivoPreview {
  return {
    responsable: "ana@karstec.com", responsable_id: "u-1", responsable_nombre: "Ana Gómez",
    prioridad: "media", fecha_entrega: "2026-06-30", descripcion: null,
    responsables_ids: [], faltantes: [],
    ...over,
  }
}

// 🔴 Punto 1: DOS válidas y DOS con problemas, con motivos distintos.
const PREVIEW: ImportacionObjetivosPreview = {
  filas_validas: [
    fila({ fila: 2, titulo: "Migrar nómina" }),
    fila({ fila: 4, titulo: "Auditar licencias", responsables_ids: ["u-2"], fecha_entrega: null }),
  ],
  errores: [
    { fila: 3, identificador: "Cerrar búsqueda", motivo: "El responsable «nadie@x.com» no existe o no está activo." },
    { fila: 5, identificador: "(sin título)", motivo: "Falta el título, que es obligatorio." },
  ],
  hoja_leida: "Objetivos",
  total_hojas: 1,
}

describe("el preview muestra las dos mitades", () => {
  it("🔴 lista las filas CON PROBLEMAS, no solo las válidas", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={PREVIEW} />))

    expect(html).toContain("Cerrar búsqueda")
    expect(html).toContain("no existe o no está activo")
    expect(html).toContain("Falta el título")
  })

  it("y también las que sí se van a cargar", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={PREVIEW} />))

    expect(html).toContain("Migrar nómina")
    expect(html).toContain("Auditar licencias")
  })

  it("cuenta las dos cosas por separado", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={PREVIEW} />))

    expect(html).toContain("2 objetivos se van a cargar")
    expect(html).toContain("2 filas con problemas")
  })

  it("dice que las buenas entran igual: el lote no aborta", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={PREVIEW} />))

    expect(html).toContain("El resto sí")
  })

  it("contrapeso: sin errores no aparece el bloque de problemas", () => {
    const limpio = { ...PREVIEW, errores: [] }
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={limpio} />))

    expect(html).toContain("Migrar nómina")
    expect(html).not.toContain("filas con problemas")
    expect(html).not.toContain("NO se van a cargar")
  })

  it("avisa cuándo el archivo tenía más de una hoja", () => {
    const varias = { ...PREVIEW, total_hojas: 3, hoja_leida: "Primera" }
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={varias} />))

    expect(html).toContain("3 hojas")
    expect(html).toContain("Primera")
  })

  it("y con una sola hoja NO avisa nada", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={PREVIEW} />))

    expect(html).not.toContain("hojas y se leyó")
  })

  it("declara que todo se carga como objetivo principal", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosPreviewTabla preview={PREVIEW} />))

    expect(html).toContain("se cargan como principales")
  })
})

describe("🔴 el resultado no miente sobre lo que entró", () => {
  const PARCIAL: ImportacionObjetivosResultado = {
    importados: 12,
    errores: [
      { fila: 3, identificador: "Cerrar búsqueda", motivo: "El responsable no está activo." },
      { fila: 9, identificador: "Otra", motivo: "Falta el título, que es obligatorio." },
    ],
  }

  it("un parcial NO se muestra como éxito completo", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosResultadoDetalle resultado={PARCIAL} />))

    expect(html).toContain("Se cargaron 12 de 14")
    expect(html).toContain("2 quedaron sin cargar")
    // El cartel de éxito limpio dice "los N objetivos del archivo": no puede aparecer acá.
    expect(html).not.toContain("del archivo.")
  })

  it("un parcial lista CUÁLES no entraron y por qué", () => {
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosResultadoDetalle resultado={PARCIAL} />))

    expect(html).toContain("Cerrar búsqueda")
    expect(html).toContain("El responsable no está activo")
  })

  it("un éxito completo sí se muestra limpio", () => {
    const todo: ImportacionObjetivosResultado = { importados: 12, errores: [] }
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosResultadoDetalle resultado={todo} />))

    expect(html).toContain("Se cargaron los 12 objetivos")
    expect(html).not.toContain("quedaron sin cargar")
    expect(html).not.toContain("Filas que no se cargaron")
  })

  it("y cuando no entró nada, lo dice sin adornos", () => {
    const nada: ImportacionObjetivosResultado = { importados: 0, errores: PARCIAL.errores }
    const html = noVacio(renderToStaticMarkup(<ImportObjetivosResultadoDetalle resultado={nada} />))

    expect(html).toContain("No se cargó ningún objetivo")
    expect(html).not.toContain("Se cargaron")
  })
})

describe("el botón de importar y el modo consolidado", () => {
  const render = (sinEmpresa: boolean) =>
    noVacio(renderToStaticMarkup(<ImportarObjetivosBoton sinEmpresa={sinEmpresa} onClick={() => {}} />))

  it("🔴 en consolidado el botón está DESHABILITADO", () => {
    // Trampa 2: por el atributo. `not.toContain("disabled")` pasaría siempre.
    expect(deshabilitado(render(true), "Importar")).toBe(true)
  })

  it("y el motivo se lee, sin jerga de backend", () => {
    const html = render(true)

    expect(html).toContain("Elegí una empresa")
    expect(html).not.toContain("empresa_id")
  })

  it("contrapeso: con una empresa elegida está HABILITADO", () => {
    expect(deshabilitado(render(false), "Importar")).toBe(false)
  })

  it("y ahí el aviso no aparece", () => {
    expect(render(false)).not.toContain("Elegí una empresa")
  })
})
