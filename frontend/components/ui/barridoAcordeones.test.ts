import { readdirSync, readFileSync } from "node:fs"
import { join, resolve, sep } from "node:path"

import { describe, expect, it } from "vitest"

/**
 * 🔴 BARRIDO ESTRUCTURAL — **ningún desplegable del producto nace desplegado**, salvo dos
 * excepciones declaradas acá abajo con su razón.
 *
 * POR QUÉ EXISTE. Al 23/8/2026 arrancaban abiertos: las dos secciones de /configuracion
 * (`["password", "perfil"]`) y los dos paneles de avisos del dashboard. Ninguno de esos cuatro
 * era una decisión sostenida —tres traían su justificación escrita y las tres se contradecían
 * entre sí— y el efecto acumulado era que en el dashboard NADA quedaba priorizado: cuando todo
 * está desplegado, estar desplegado no significa nada. Cerrar los cuatro alcanzaba para hoy; sin
 * barrido, el próximo panel nace abierto en el próximo PR porque "el mío sí es importante", que
 * es exactamente el argumento que habían escrito los cuatro.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
 *   · El descubrimiento es por lectura del árbol: no hay lista de qué mirar, así que un archivo
 *     nuevo entra solo. Verificado en las dos direcciones al escribirlo: se le puso un
 *     `defaultValue` a `HeadcountPanel` y rojeó; se le sacó el suyo a `AtencionPanel` (que está
 *     declarado como excepción) y rojeó también.
 *   · Las guardas de mínimo corren ANTES de comparar. Si el escaneo se rompiera —el `sep` de
 *     Windows, una carpeta renombrada— encontraría 0 archivos y "no hay ninguno abierto" pasaría
 *     en el vacío. Es el falso verde que este repo ya pagó con `barridoFront.test.ts`, que
 *     descubría 0 exports en la Lenovo y pasaba en verde con el mismo código que en la Mac.
 *   · Las excepciones se verifican en las DOS direcciones: que lo que hay esté declarado, y que
 *     lo declarado siga estando. Una excepción muerta es ruido que tapa el próximo caso.
 *   · Los comentarios se enmascaran antes de buscar. Los archivos que se cerraron CONSERVAN
 *     escrito en prosa el estado inicial que tenían y por qué se lo sacó —es el registro de la
 *     decisión—; un barrido por texto plano los marcaría a todos, y la salida "natural" sería
 *     borrarles justo esa explicación.
 *
 * 🚩 LO QUE NO CUBRE, dicho de frente: un desplegable escrito a mano con su propio
 * `useState(true)`. No se barre esa expresión porque en este repo es abrumadoramente el estado de
 * CARGA (`const [loading, setLoading] = useState(true)`, ~60 archivos) y un barrido que los
 * marque a todos es un barrido que nadie mira. Lo que sí se cubre de ese caso es el otro extremo:
 * el atributo `aria-expanded`, que un disclosure tiene que llevar sí o sí para ser accesible —
 * los cinco que existen están inventariados abajo. Un desplegable a mano SIN `aria-expanded` se
 * escapa, y ése ya es un bug de accesibilidad antes que de este barrido.
 */

const RAIZ = resolve(__dirname, "..", "..")
const CARPETAS = ["app", "components"]

/**
 * El desplegable que arranca abierto a propósito. La clave se escribe con `/`, como la normaliza
 * `archivosDe`. La razón larga vive también en el archivo; acá está la parte verificable.
 */
const EXCEPCIONES: Record<string, string> = {
  "components/features/dashboard/AtencionPanel.tsx":
    "Requiere tu atencion es la unica COLA DE TRABAJO de la pantalla, no contexto: trae lo " +
    "accionable de la semana sobre personas y tiene boton de Resolver. Una bandeja plegada es " +
    "una bandeja que nadie mira. Que sea el UNICO abierto es lo que hace que estar abierto " +
    "vuelva a significar algo. No crece sin techo (solo lo que esta dentro de la ventana de " +
    "aviso, con su vacio declarado), al reves que headcount y cumpleanos. Y la pantalla ya se " +
    "apoya en el: _kpisDashboard._tonoIngresos decide con su contenido cual es la unica card " +
    "de KPI que se despega, asi que plegarlo dejaria una card en ambar apuntando a algo cerrado.",
}

/**
 * Los disclosures escritos a mano (los que llevan `aria-expanded`), con qué arrancan. Es el
 * inventario que el barrido de `Accordion.Root` no puede ver, porque no usan el shell compartido.
 */
const A_MANO: Record<string, string> = {
  // El atributo vive acá; el ESTADO que lo alimenta vive en `Sidebar.tsx` (`openGroup`), y por
  // eso hay abajo una aserción aparte sobre el valor inicial. Separarlos era el punto del corte
  // de ese componente, no un descuido.
  "components/layout/NavGroup.tsx":
    "ABIERTO, y declarado: el grupo del sidebar no esta abierto por defecto, esta abierto " +
    "PORQUE EL USUARIO ESTA ADENTRO (grupoDeRuta(pathname)). Plegarlo esconde la pantalla en " +
    "la que esta y con ella el indicador de aca estoy, que es la unica orientacion de un menu " +
    "de siete grupos. Y no ahorra nada: openGroup es UN valor, asi que nunca hay mas de un " +
    "grupo desplegado — el costo que esta regla ataca (N paneles empujando el contenido hacia " +
    "abajo) aca no existe.",
  "components/ui/FiltersBar.tsx":
    "ABIERTO SOLO SI HAY DATO: Mas filtros se despliega cuando algun filtro avanzado YA tiene " +
    "valor. No es un default, es evitar mostrar el chip de un filtro cuyo control esta " +
    "escondido. Sin filtros avanzados puestos arranca plegado, que es el caso normal.",
  "components/features/horasCliente/ClientesColapsables.tsx": "PLEGADO: useState({}).",
  "components/layout/AIPanel.tsx": "PLEGADO: useState(false).",
  "components/features/sucesion/NineBox.tsx":
    "No es un desplegable: aria-expanded marca la tarjeta SELECCIONADA, y arranca sin ninguna.",
}

/** Rutas relativas a la raíz del front, SIEMPRE con `/` como separador (ver `barridoSelect`). */
function archivosDe(carpeta: string): string[] {
  const salida: string[] = []
  const recorrer = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === "node_modules" || e.name.startsWith(".")) continue
      const p = join(dir, e.name)
      if (e.isDirectory()) recorrer(p)
      // Los `.test.*` quedan fuera: no pintan pantalla, y este mismo archivo escribe
      // `defaultValue` y `aria-expanded` muchas veces, así que sin esto se marca a sí mismo.
      else if (!e.name.includes(".test.") && (e.name.endsWith(".tsx") || e.name.endsWith(".ts"))) {
        salida.push(p.slice(RAIZ.length + 1).split(sep).join("/"))
      }
    }
  }
  recorrer(join(RAIZ, carpeta))
  return salida
}

/** Reemplaza el CONTENIDO de los comentarios por espacios, conservando los saltos de línea. */
function sinComentarios(texto: string): string {
  let salida = ""
  let i = 0
  while (i < texto.length) {
    if (texto.startsWith("/*", i)) {
      const fin = texto.indexOf("*/", i + 2)
      const corte = fin < 0 ? texto.length : fin + 2
      salida += texto.slice(i, corte).replace(/[^\n]/g, " ")
      i = corte
    } else if (texto.startsWith("//", i)) {
      const fin = texto.indexOf("\n", i)
      const corte = fin < 0 ? texto.length : fin
      salida += " ".repeat(corte - i)
      i = corte
    } else {
      salida += texto[i]
      i++
    }
  }
  return salida
}

const ARCHIVOS = CARPETAS.flatMap(archivosDe)
const codigo = (f: string) => sinComentarios(readFileSync(join(RAIZ, f), "utf-8"))

/** Los archivos que montan un acordeón del shell compartido. */
const CON_ACORDEON = ARCHIVOS.filter((f) => codigo(f).includes("<Accordion.Root"))

/** Los que además le declaran un estado inicial NO vacío. */
const NACEN_ABIERTOS = CON_ACORDEON.filter((f) => /defaultValue=\{(?!ABIERTAS\})/.test(codigo(f)))

describe("guardas: el barrido está mirando algo", () => {
  it("recorre el front entero", () => {
    expect(ARCHIVOS.length).toBeGreaterThanOrEqual(300)
  })

  it("y encuentra los acordeones que existen", () => {
    expect(CON_ACORDEON.length).toBeGreaterThanOrEqual(4)
  })

  it("el enmascarado no se comió los archivos", () => {
    expect(sinComentarios("const a = 1 // x")).toContain("const a = 1")
    expect(sinComentarios("/* defaultValue={x} */")).not.toContain("defaultValue")
  })
})

describe("ningún acordeón nace desplegado", () => {
  it("los que declaran un estado inicial abierto son exactamente los declarados", () => {
    expect(NACEN_ABIERTOS.sort()).toEqual(Object.keys(EXCEPCIONES).sort())
  })

  it("y ninguna excepción declarada quedó muerta", () => {
    // Contracara de la de arriba: si a `AtencionPanel` se le saca el `defaultValue`, la entrada
    // de EXCEPCIONES pasa a describir algo que ya no pasa y hay que borrarla.
    for (const f of Object.keys(EXCEPCIONES)) {
      expect(ARCHIVOS, `${f} ya no existe`).toContain(f)
      expect(/defaultValue=\{/.test(codigo(f)), `${f} ya no nace abierto: sacalo de EXCEPCIONES`).toBe(true)
    }
  })

  it("cada excepción trae una razón de verdad, no una etiqueta", () => {
    for (const [f, razon] of Object.entries(EXCEPCIONES)) {
      expect(razon.length, `${f}: la razón tiene que explicar, no nombrar`).toBeGreaterThan(120)
    }
  })
})

describe("los que se cerraron siguen cerrados", () => {
  const CERRADOS = [
    "components/features/dashboard/AlertasPanel.tsx",
    "components/features/dashboard/HeadcountPanel.tsx",
    "components/features/dashboard/DashboardExtras.tsx",
  ]

  it("montan su acordeón y no le pasan estado inicial", () => {
    for (const f of CERRADOS) {
      expect(CON_ACORDEON, `${f} dejó de montar un acordeón`).toContain(f)
      expect(codigo(f)).not.toContain("defaultValue")
    }
  })

  it("/configuracion conserva el punto de decisión, con la lista vacía", () => {
    // Acá el `defaultValue` SIGUE existiendo —es el único lugar donde se decidiría abrir una
    // sección— pero la lista está vacía. Por eso el filtro de arriba lo excluye por nombre y por
    // eso este archivo no está en EXCEPCIONES: no nace ninguna abierta.
    const f = "app/(dashboard)/configuracion/page.tsx"
    expect(codigo(f)).toContain("const ABIERTAS: string[] = []")
    expect(NACEN_ABIERTOS).not.toContain(f)
  })
})

describe("los desplegables escritos a mano están inventariados", () => {
  const CON_ARIA = ARCHIVOS.filter((f) => codigo(f).includes("aria-expanded={"))

  it("guarda: hay disclosures a mano que mirar", () => {
    expect(CON_ARIA.length).toBeGreaterThanOrEqual(4)
  })

  it("son exactamente los declarados en A_MANO, con lo que arranca cada uno", () => {
    expect(CON_ARIA.sort()).toEqual(Object.keys(A_MANO).sort())
  })

  it("el grupo del sidebar arranca en el de la RUTA ACTIVA, no en uno fijo", () => {
    // Es lo que hace que esta excepción sea lo que dice ser: si pasara a `useState("Personas")`
    // o a un `defaultValue` cualquiera, sería un desplegable abierto por defecto como los que
    // esta regla cierra, y la razón declarada en A_MANO dejaría de ser cierta.
    expect(codigo("components/layout/Sidebar.tsx"))
      .toContain("useState<string | null>(() => grupoDeRuta(pathname))")
  })

  it("los que arrancan plegados lo siguen haciendo", () => {
    expect(codigo("components/layout/AIPanel.tsx")).toContain("useState(false)")
    expect(codigo("components/features/horasCliente/ClientesColapsables.tsx"))
      .toContain("useState<Record<string, boolean>>({})")
  })

  it("y 'Más filtros' se abre sólo si YA hay un filtro avanzado puesto", () => {
    // Si esto pasara a `useState(true)`, el panel avanzado nacería abierto en todas las pantallas
    // del sistema — es el único de los cinco que se repite en 30 pantallas.
    expect(codigo("components/ui/FiltersBar.tsx"))
      .toContain("useState(() => avanzados.some((c) => chipsDeCampos([c]).length > 0))")
  })
})

describe("nadie usa <details>, que arranca cerrado pero no comparte el shell", () => {
  it("no hay ninguno en el producto", () => {
    const con = ARCHIVOS.filter((f) => /<details[\s>]/.test(codigo(f)))
    expect(con, "usá ConfigSection: el mecanismo de plegado vive en un solo lugar").toEqual([])
  })
})
