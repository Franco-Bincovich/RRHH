import { readdirSync, statSync } from "node:fs"
import { join, resolve } from "node:path"

import { describe, expect, it } from "vitest"

import {
  ADMIN_GROUP, ITEMS_SUPERIORES, NAV_GROUPS, RUTAS_OCULTAS, TODOS_LOS_GRUPOS,
} from "@/components/layout/nav-config"
import { itemVisible } from "@/components/layout/nav-visibilidad"
import { seccionDeRuta } from "@/services/permisos"

/**
 * 🔴 BARRIDO ESTRUCTURAL — el menú contra el árbol de rutas REAL y contra permisos.ts.
 *
 * Dos ejes, y hacen falta los dos:
 *   (1) ¿la ruta a la que apunta el ítem EXISTE en app/? Se descubre leyendo el árbol, nunca
 *       contra una lista escrita a mano: un módulo nuevo entra solo, y un href con typo o una
 *       pantalla borrada rojean sin que nadie toque este archivo. Sin esto, un ítem del menú
 *       puede llevar a un 404 y solo se descubre haciéndole clic en producción.
 *   (2) ¿gatea con la MISMA sección que el guard de ruta? nav-config decide qué se VE y
 *       permisos.ts decide a qué se ENTRA. Si divergen, el resultado no es un error visible
 *       sino un ítem que aparece y rebota al hacer clic —o peor, una ruta accesible que el
 *       menú esconde y nadie audita.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · Las RUTAS se leen del disco (app/**\/page.tsx). Agregar un ítem a /ruta-que-no-existe
 *     rojea; borrar una page.tsx de una ruta que el menú enlaza, también. Verificado en las
 *     dos direcciones al escribirlo.
 *   · Las guardas de mínimo corren ANTES de comparar: si el escaneo del árbol se rompe, el
 *     conjunto de rutas queda vacío y "todo ítem apunta a una ruta viva" pasaría en el vacío
 *     al revés (rojearía todo) — la guarda hace explícito cuál de las dos cosas falló.
 *   · Los `proximamente` se verifican por lo que NO tienen (href), no por una lista de labels.
 */

const RAIZ = resolve(__dirname, "../..")

/** Rutas estáticas que app/ sirve de verdad: cada page.tsx, sin los grupos `(x)` y sin los
 *  segmentos dinámicos `[id]` (a los que el menú nunca apunta: no hay id que poner). */
function rutasDeApp(): Set<string> {
  const rutas = new Set<string>()
  const caminar = (dir: string, segmentos: string[]) => {
    for (const e of readdirSync(dir)) {
      const p = join(dir, e)
      if (statSync(p).isDirectory()) {
        if (e.startsWith("[")) continue // dinámico: no es destino de menú
        caminar(p, e.startsWith("(") && e.endsWith(")") ? segmentos : [...segmentos, e])
      } else if (e === "page.tsx") {
        rutas.add(`/${segmentos.join("/")}`)
      }
    }
  }
  caminar(join(RAIZ, "app"), [])
  return rutas
}

const RUTAS_APP = rutasDeApp()
const ITEMS = [...ITEMS_SUPERIORES, ...TODOS_LOS_GRUPOS.flatMap((g) => g.items)]
const NAVEGABLES = ITEMS.filter((i): i is typeof i & { href: string } => typeof i.href === "string")
const PROXIMAMENTE = ITEMS.filter((i) => i.proximamente)

describe("guardas del barrido", () => {
  it("el árbol de rutas se leyó", () => {
    // Sin esto, un fallo del escaneo daría "todos los hrefs son inválidos" y el diagnóstico
    // apuntaría al menú en vez de al lector del árbol.
    expect(RUTAS_APP.size).toBeGreaterThanOrEqual(30)
    expect(RUTAS_APP.has("/dashboard")).toBe(true)
  })

  it("el menú no está vacío", () => {
    expect(NAVEGABLES.length).toBeGreaterThanOrEqual(25)
  })
})

describe("(a) todo ítem del menú apunta a una ruta que existe en app/", () => {
  it.each(NAVEGABLES)("$label → $href existe", (item) => {
    expect(RUTAS_APP.has(item.href)).toBe(true)
  })
})

describe("(b) los ítems sin pantalla no son navegables", () => {
  it("hay ítems marcados proximamente", () => {
    // Guarda: si el marcado desapareciera, las dos aserciones de abajo pasarían sin mirar nada.
    //
    // ⚠️ EL PISO BAJA A MEDIDA QUE LAS PANTALLAS SE CONSTRUYEN, y bajarlo es parte de terminar
    // una: 7 → 5 (próximos ingresos y bajas, 20/8/2026) → 4 (perfiles de puesto) → 3
    // (recategorizaciones). Quedan Documentación/Legajos, Plan de desarrollo y Carga de horas.
    // Lo que la guarda protege no es un número alto: es que el marcado siga EXISTIENDO, porque
    // el día que no quede ninguno hay que borrar este bloque, no dejarlo pasando en el vacío.
    expect(PROXIMAMENTE.length).toBeGreaterThanOrEqual(3)
  })

  it.each(PROXIMAMENTE)("$label no lleva href", (item) => {
    // Sin href, NavItem lo renderiza como <span> — no es focusable, así que el tabulado lo
    // saltea. Un href a una ruta futura sería un 404 con forma de menú.
    expect(item.href).toBeUndefined()
  })

  it("ningún ítem sin href quedó sin marcar", () => {
    const sinMarcar = ITEMS.filter((i) => !i.href && !i.proximamente)
    expect(sinMarcar.map((i) => i.label)).toEqual([])
  })
})

describe("(c) las secciones ocultas no se muestran, pero sus rutas siguen vivas", () => {
  /**
   * Hay DOS mecanismos de ocultamiento conviviendo y los dos se barren acá, porque prueban cosas
   * distintas: /inventario salió del array por completo (§4 del sistema de diseño), y las de
   * `RUTAS_OCULTAS` siguen DECLARADAS en el menú y las filtra `itemVisible`. La diferencia se
   * paga en cobertura y por eso conviene tenerla escrita: al salir del array, /inventario dejó
   * de pasar por los bloques (a) y (d) —nada verifica ya que su href exista ni que su sección
   * coincida con el guard—, mientras que las tres de `RUTAS_OCULTAS` los siguen atravesando.
   *
   * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR? El rol de prueba es `admin_rrhh`
   * y no `mandos_medios`: admin lee TODO, así que es el único rol con el que "no se ve" sólo
   * puede deberse al ocultamiento y no a un permiso. Con un rol angosto, las tres darían
   * invisibles igual con el filtro borrado. Y cada aserción de "no se ve" lleva su CONTRASTE de
   * "sí se ve" con el mismo rol, sin el cual un `itemVisible` que devolviera siempre false
   * pasaría entero.
   */
  it("guarda: hay rutas ocultas que barrer", () => {
    expect(RUTAS_OCULTAS.length).toBeGreaterThanOrEqual(1)
  })

  it.each([...RUTAS_OCULTAS])("%s sigue declarada en el menú (una entrada muerta rojea)", (ruta) => {
    // Si alguien BORRA el ítem en vez de ocultarlo, la entrada de RUTAS_OCULTAS queda apuntando
    // a la nada y "reponerlo borrándola de la lista" dejaría de funcionar en silencio.
    expect(ITEMS.filter((i) => i.href === ruta)).toHaveLength(1)
  })

  it.each([...RUTAS_OCULTAS])("%s no se le muestra ni a admin_rrhh, que lee todo", (ruta) => {
    const item = ITEMS.find((i) => i.href === ruta)!
    expect(itemVisible(item, "admin_rrhh")).toBe(false)
  })

  it("EL CONTRASTE: los ítems que NO están ocultos sí se le muestran a admin_rrhh", () => {
    const visibles = NAVEGABLES.filter((i) => !RUTAS_OCULTAS.includes(i.href))
      .filter((i) => itemVisible(i, "admin_rrhh"))
    // Todos menos "Mi equipo", que es soloRol: ["mandos_medios"].
    expect(visibles.length).toBeGreaterThanOrEqual(NAVEGABLES.length - RUTAS_OCULTAS.length - 1)
  })

  it.each([...RUTAS_OCULTAS])("%s sigue siendo alcanzable por URL, con su gate", (ruta) => {
    // Ocultarlas es reversible; borrar la ruta o su sección no lo sería, y dejaría la pantalla
    // sin gate el día que alguien la reponga.
    expect(RUTAS_APP.has(ruta)).toBe(true)
    expect(seccionDeRuta(ruta)).not.toBeNull()
  })

  it("Inventario está fuera del menú y su ruta también sigue viva", () => {
    expect(ITEMS.filter((i) => i.href === "/inventario")).toEqual([])
    expect(RUTAS_APP.has("/inventario")).toBe(true)
    expect(seccionDeRuta("/inventario")).toBe("inventario")
  })
})

describe("(d) espejo con permisos.ts", () => {
  it.each(NAVEGABLES.filter((i) => i.seccion !== null))(
    "$href gatea con la misma sección en el sidebar y en el guard",
    (item) => {
      expect(seccionDeRuta(item.href)).toBe(item.seccion)
    },
  )

  it("ningún ítem apunta a una ruta sin sección conocida", () => {
    // Un href con typo devolvería null acá y quedaría fuera del filtro de permisos del sidebar.
    const huerfanos = NAVEGABLES.filter((i) => i.seccion !== null && seccionDeRuta(i.href) === null)
    expect(huerfanos.map((i) => i.href)).toEqual([])
  })
})

describe("estructura del sistema de diseño §4", () => {
  it("son 6 grupos, con Administración aparte y al final", () => {
    expect(NAV_GROUPS.map((g) => g.label)).toEqual([
      "Personas", "Reclutamiento", "Incorporación", "Talento y Desarrollo", "Gestión", "Egresos",
    ])
    expect(ADMIN_GROUP.label).toBe("Administración")
    expect(TODOS_LOS_GRUPOS.at(-1)).toBe(ADMIN_GROUP)
  })

  it("Dashboard · Reportes · Auditoría van fuera de los grupos", () => {
    expect(ITEMS_SUPERIORES.map((i) => i.href)).toEqual(["/dashboard", "/reportes", "/auditoria"])
    const dentro = TODOS_LOS_GRUPOS.flatMap((g) => g.items).map((i) => i.href)
    for (const href of ["/dashboard", "/reportes", "/auditoria"]) expect(dentro).not.toContain(href)
  })

  it("cada grupo y cada ítem tienen ícono", () => {
    for (const g of TODOS_LOS_GRUPOS) {
      expect(g.icon, `grupo ${g.label} sin ícono`).toBeTruthy()
      for (const i of g.items) expect(i.icon, `${i.label} sin ícono`).toBeTruthy()
    }
    for (const i of ITEMS_SUPERIORES) expect(i.icon).toBeTruthy()
  })

  it("Áreas está en el sidebar", () => {
    // Existía la página y el gate, pero no el punto de entrada: solo se llegaba tipeando la URL.
    expect(NAVEGABLES.find((i) => i.href === "/areas")?.seccion).toBe("areas")
  })

  it("mandos_medios sigue teniendo por dónde entrar", () => {
    // Ve solo VACACIONES y AUSENCIAS: si el reparto de grupos le dejara el menú vacío, el
    // rol quedaría sin punto de entrada y el síntoma sería un sidebar en blanco.
    const suyos = ITEMS.filter((i) => itemVisible(i, "mandos_medios"))
    expect(suyos.map((i) => i.href)).toEqual(
      expect.arrayContaining(["/vacaciones", "/ausencias", "/equipo"]),
    )
  })
})
