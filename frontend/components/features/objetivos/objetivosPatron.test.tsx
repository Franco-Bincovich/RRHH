import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposObjetivos } from "./_camposObjetivos"
import { ESTADO_ESTILO, PRIORIDAD_ESTILO } from "./_grillaObjetivos"
import { ListView } from "./ListView"

/**
 * Los cuatro puntos del patrón del bloque B sobre /objetivos, más la regla propia del módulo:
 * **el avance son TRES ESTADOS, no un porcentaje** (§7).
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que el chip volviera a mostrar el `value` crudo: diría "por_hacer" en vez de "Por hacer".
 *   · (b) que un `quitar()` llamara al setter de otro campo, o que dejara de avisar del cambio.
 *   · (c) que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · (d) que el pie contara `objetivos.length` en vez de `total`.
 *   · §7: que alguien reponga un "%" o una barra de progreso en la fila.
 */

const USUARIOS = [{ id: "u1", nombre: "Ana", apellido: "Gómez", email: "ana@x.com" }]
const EMPRESAS = [{ id: "e1", nombre: "Karstec" }] as ArgsCamposObjetivos["empresas"]

function args(over: Partial<ArgsCamposObjetivos> = {}): ArgsCamposObjetivos {
  return {
    mostrarEmpresa: true, empresas: EMPRESAS,
    empresaFiltro: "", setEmpresaFiltro: vi.fn(),
    estadoFiltro: "", setEstadoFiltro: vi.fn(),
    prioridadFiltro: "", setPrioridadFiltro: vi.fn(),
    usuarios: USUARIOS as ArgsCamposObjetivos["usuarios"],
    responsableFiltro: "", setResponsableFiltro: vi.fn(),
    areas: ["Sistemas", "Comercial"], areaFiltro: "", setAreaFiltro: vi.fn(),
    periodicidadFiltro: "", setPeriodicidadFiltro: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Estado dice 'Por hacer' y Prioridad dice 'Alta', no 'por_hacer' ni 'alta'", () => {
    const chips = chipsDeCampos(construirCampos(args({ estadoFiltro: "por_hacer", prioridadFiltro: "alta" })))
    expect(chips.find((c) => c.clave === "Estado")!.valor).toBe("Por hacer")
    expect(chips.find((c) => c.clave === "Prioridad")!.valor).toBe("Alta")
  })

  it("Responsable dice el nombre de la persona y no el uuid", () => {
    const chips = chipsDeCampos(construirCampos(args({ responsableFiltro: "u1" })))
    expect(chips.find((c) => c.clave === "Responsable")!.valor).toBe("Ana Gómez")
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros", () => {
  it("quitar Estado no toca Prioridad", () => {
    const a = args({ estadoFiltro: "haciendo", prioridadFiltro: "alta" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Estado")!.quitar()
    expect(a.setEstadoFiltro).toHaveBeenCalledWith("")
    expect(a.setPrioridadFiltro).not.toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip, y cada uno avisa del cambio", () => {
    const a = args({ empresaFiltro: "e1", estadoFiltro: "terminado", prioridadFiltro: "baja", responsableFiltro: "u1" })
    const chips = chipsDeCampos(construirCampos(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(4)
    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no avisó del cambio`).toBe(antes + 1)
    }
  })

  it("qué queda atrás de 'Más filtros': los tres recortes de segunda vuelta", () => {
    // La barra visible contesta la pregunta diaria —qué hay que hacer y con qué urgencia— y los
    // recortes finos quedan atrás. Área y Periodicidad entraron el 25/8/2026 (bloque N8) y
    // entraron AVANZADOS por eso: subirlos empujaría a Prioridad fuera del primer vistazo.
    const campos = construirCampos(args())
    expect(campos.filter((c) => c.avanzado).map((c) => c.label))
      .toEqual(["Responsable", "Área involucrada", "Periodicidad"])
    expect(campos.filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Empresa", "Estado", "Prioridad"])
  })

  it("el filtro de área NO se dibuja sin catálogo, salvo que ya tenga un valor puesto", () => {
    // 🔴 La segunda mitad es la regla del barrido nº45: un filtro CON VALOR siempre tiene su
    // chip. Si el catálogo llega vacío y el campo desaparece, el valor sigue vivo en el estado y
    // sigue viajando al backend, y "Limpiar todo" no tiene nada que quitar.
    expect(construirCampos(args({ areas: [] })).map((c) => c.label)).not.toContain("Área involucrada")
    expect(construirCampos(args({ areas: [], areaFiltro: "Sistemas" })).map((c) => c.label))
      .toContain("Área involucrada")
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

type Fila = Parameters<typeof ListView>[0]["objetivos"][number]

const OBJETIVO = {
  id: "o1", titulo: "Cerrar el trimestre", estado: "haciendo", prioridad: "media",
  responsables: [], responsable_nombre: "Ana", fecha_entrega: null, empresa_nombre: null,
  hijos: [],
} as unknown as Fila

function lista(props: Partial<Parameters<typeof ListView>[0]> = {}) {
  return renderToStaticMarkup(
    <ListView
      objetivos={[]} loading={false} total={0} showEmpresa={false} canWrite={false}
      onEdit={() => {}} onDelete={() => {}} deletingId={null}
      chips={[chip("Estado", "Por hacer")]} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = lista()
    for (const columna of ["Título", "Responsable", "Prioridad", "Estado", "Fecha entrega"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
  })

  it("la frase nombra el filtro real que está puesto, no 'los filtros'", () => {
    expect(lista()).toContain("Por hacer")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla", () => {
    const cargando = lista({ loading: true })
    // 5 columnas: sin empresa (showEmpresa=false) y sin acciones (canWrite=false).
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(5)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 5)
    expect(cargando).toContain("animate-shimmer")
  })
})

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de objetivos.length", () => {
  it("con 3 objetivos en pantalla y 40 del otro lado, el pie dice 40", () => {
    const html = lista({
      objetivos: [OBJETIVO, { ...OBJETIVO, id: "o2" }, { ...OBJETIVO, id: "o3" }],
      total: 40,
    })
    expect(html).toContain("40 objetivos principales")
    // Y avisa que está mostrando una parte, en vez de dejar creer que ve todo.
    expect(html).toContain("se muestran 3")
  })

  it("🔴 el pie NO se dibuja sobre el esqueleto ni sobre el vacío", () => {
    expect(lista({ loading: true, total: 40 })).not.toContain("objetivos principales")
    expect(lista({ total: 0 })).not.toContain("objetivos principales")
  })

  it("el código no deriva el total de la lista que dibujó", () => {
    const fuente = readFileSync(path.resolve(__dirname, "ListView.tsx"), "utf8")
    const codigo = sinComentarios(fuente)
    expect(codigo).toContain("{total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(codigo)).toBe(false)
    // Contracara: la prosa SÍ habla de `objetivos.length`, y eso es correcto — explica por qué no.
    expect(fuente).toContain("objetivos.length")
  })
})

describe("🔴 §7: el avance son TRES ESTADOS, no un porcentaje", () => {
  it("ni la fila ni la grilla insinúan una fracción de avance", () => {
    const html = lista({ objetivos: [OBJETIVO], total: 1 })
    // 🔑 Se mira el TEXTO, no el markup: los anchos de columna son clases de Tailwind (`w-[16%]`)
    // y un `%` ahí no es un porcentaje de avance. Buscarlo sobre el HTML crudo daría un rojo que
    // empuja a cambiar los anchos de la grilla, que no tienen nada que ver con §7.
    const texto = html.replace(/<[^>]*>/g, " ")
    expect(texto).not.toContain("%")
    expect(html).not.toContain("progressbar")
    // Contracara: lo que sí se ve es la etiqueta del estado.
    expect(html).toContain("Haciendo")
  })

  it("🔴 'Haciendo' y 'Media' dejaron de pintarse con el color de la marca", () => {
    // `bg-primary` está reservado para el chip de filtro activo y la acción principal: una
    // etiqueta que se repite en cada fila con ese color le roba el énfasis a lo accionable.
    for (const estilo of [...Object.values(ESTADO_ESTILO), ...Object.values(PRIORIDAD_ESTILO)]) {
      expect(estilo).not.toContain("bg-primary")
      expect(estilo).not.toContain("text-primary")
    }
    // Guarda contra el falso verde: si los mapas quedaran vacíos, el for no compara nada.
    expect(Object.keys(ESTADO_ESTILO).length).toBe(3)
    expect(Object.keys(PRIORIDAD_ESTILO).length).toBe(3)
  })
})
