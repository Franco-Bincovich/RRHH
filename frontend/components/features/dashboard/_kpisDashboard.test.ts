import { describe, expect, it } from "vitest"

import { RUTAS_OCULTAS } from "@/components/layout/nav-config"
import type { DashboardData, KpisExtra } from "@/services/dashboard"
import { DESTINOS, SIN_DESTINO } from "./_destinosKpi"
import { bloquesKpi, formatVariacion, masaSalarial, SIN_DATO } from "./_kpisDashboard"
import type { DatosAdmin } from "./dashboardAdminData"

/**
 * Los diez KPIs de §6: que estén los diez, en sus dos bloques y en su orden, y que ninguna card
 * afirme un dato que no tiene.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 **El payload es un PROXY que revienta al leer una clave que el backend no manda.** Es lo
 *    único que puede cazar el bug que hoy está vivo: `dashboardAdminData` leía
 *    `kpis.costo_nomina`, campo que el backend borró el 21/8/2026, y **`tsc` no lo veía** porque
 *    la interfaz de `services/dashboard.ts` es un espejo escrito a mano — decía que el campo
 *    existía, así que el front tenía razón contra sí mismo. Con un objeto literal común, leer una
 *    clave de más devuelve `undefined` y la card muestra "undefined" sin que nada rojee.
 * 2. **El fixture se escribe contra `schemas/dashboard.py`, campo por campo**, y no copiando lo
 *    que el front declara: copiar el espejo haría que el test heredara el mismo desfasaje.
 * 3. **Promedio y mediana son números DISTINTOS** (1,9 vs 1,2). Con los dos iguales, mostrar dos
 *    veces el promedio pasaría el test de la mediana.
 * 4. **La variación aparece en los DOS estados** (`null` y un `0` legítimo). Sin el segundo, un
 *    formateador que devolviera siempre "sin comparación" pasaría el test de arriba.
 */

/** Guarda: el proxy revienta al leer una clave ausente, que es todo el punto del test (e). */
function soloLoQueMandaElBackend<T extends object>(obj: T, nombre: string): T {
  return new Proxy(obj, {
    get(target, prop) {
      if (typeof prop === "string" && !(prop in target)) {
        throw new Error(
          `La card leyó \`${nombre}.${prop}\`, que el backend NO manda. ` +
          "Compará services/dashboard.ts contra backend/schemas/dashboard.py.",
        )
      }
      return Reflect.get(target, prop)
    },
  })
}

/** Espejo EXACTO de `KPIsExtraResponse` (backend/schemas/dashboard.py), con datos plausibles. */
const EXTRA: KpisExtra = {
  ausencias_activas_hoy: 3,
  ausentismo_mes_pct: 4.2,
  ausentismo_nota: "Sobre una base de 22 días hábiles",
  masa_salarial_actual: 1200,
  masa_salarial_anterior: 1000,
  masa_salarial_variacion_pct: 20,
  ingresos_proximos_30: 2,
  recategorizaciones_mes: 5,
  rotacion_12m_bajas: 4,
  rotacion_12m_pct: 11.4,
  antiguedad_promedio_anios: 1.9,
  antiguedad_mediana_anios: 1.2,   // ≠ el promedio, a propósito (ver el punto 3 del encabezado)
  distribucion_seniority: [],
  distribucion_modalidad: [],
  cumpleanos_mes: [],
  aniversarios_mes: [],
  errores: [],
}

function datos(extra: Partial<KpisExtra> = {}, resto: Partial<DashboardData> = {}): DatosAdmin {
  const dashboard: DashboardData = {
    // Espejo EXACTO de `KPIResponse`: cinco campos, sin `costo_nomina`.
    kpis: soloLoQueMandaElBackend({
      empleados_activos: 31, ingresos_mes: 1, bajas_mes: 2,
      onboardings_activos: 0, vacantes_activas: 4,
    }, "kpis"),
    headcount_por_area: [],
    headcount_por_empresa: [
      { empresa_id: "e-1", empresa: "KARSTEC", total: 19 },
      { empresa_id: "e-2", empresa: "DOSUBA", total: 12 },
    ],
    alertas: [],
    kpis_extra: soloLoQueMandaElBackend({ ...EXTRA, ...extra }, "kpis_extra"),
    ...resto,
  }
  return { dashboard: soloLoQueMandaElBackend(dashboard, "dashboard"), atencion: [], atencionError: false }
}

/**
 * El rol con el que se arman las cards en casi todo este archivo. Va explícito y no por default:
 * `bloquesKpi` lo exige justamente para que nadie se olvide de pasarlo y la pantalla quede sin
 * links en verde. Qué pasa con OTROS roles es de `_destinosKpi.test.ts`, que es donde vive esa
 * decisión — acá solo hace falta un rol que pueda leer todo, para que los diez títulos salgan.
 */
const ADMIN = "admin_rrhh" as const

const titulos = (d: DatosAdmin) => bloquesKpi(d, ADMIN).map((b) => b.kpis.map((k) => k.title))
const card = (d: DatosAdmin, title: string) =>
  bloquesKpi(d, ADMIN).flatMap((b) => b.kpis).find((k) => k.title === title)!
/**
 * 🔴 LA CARD DE LA MASA SALARIAL SE ARMA DIRECTO, NO SE BUSCA EN LA PANTALLA, porque hoy NO se
 * pinta: se fue de la vista con Costos (`_ocultoEnDashboard`). Sus reglas —"$0" vs "sin cargar",
 * la variación sin base— se siguen probando enteras, y por eso siguen abajo: son lo que tiene
 * que seguir sabiendo el día que Costos vuelva al menú. Buscarla con `card()` habría dejado
 * cinco tests reventando en `undefined`, y borrarlos habría tirado las reglas con la card.
 */
const cardMasa = (d: DatosAdmin) => masaSalarial(d.dashboard.kpis_extra)

/** Las cards cuyo destino cayó en `RUTAS_OCULTAS`: se DERIVA, igual que en `_destinosKpi.test.ts`
 *  y en `_ocultoEnDashboard.test.ts`. Reponer una sección la saca de acá sola. */
const OCULTAS = Object.keys(DESTINOS)
  .filter((t) => RUTAS_OCULTAS.includes(DESTINOS[t].split("?")[0]))

// ── (a) los diez, en los dos bloques, en el orden de §6 ───────────────────────────

describe("los diez KPIs de §6", () => {
  it("salen en dos bloques con sus títulos", () => {
    expect(bloquesKpi(datos(), ADMIN).map((b) => b.titulo)).toEqual(["Operación", "Indicadores del período"])
  })

  it("salen los que no están ocultos, en el orden del documento", () => {
    // La lista está escrita a mano CONTRA §6 (no derivada del código): es lo que hace que
    // agregar, sacar o mover una card rompa el test en vez de pasar sola.
    // 🔴 "Masa salarial del mes" NO está: se fue de la vista con Costos. Que falte JUSTO ella se
    // afirma abajo contra `RUTAS_OCULTAS`, no acá — acá lo que se fija es el orden del resto.
    expect(titulos(datos())).toEqual([
      ["Colaboradores activos", "Búsquedas abiertas", "Ingresos próximos 30 días",
       "Ausencias en curso", "Recategorizaciones del mes", "Rotación 12 meses"],
      ["Ausentismo del mes", "Antigüedad promedio", "Headcount por empresa"],
    ])
  })

  it("y NO hay una card de bajas del mes ni de onboardings activos", () => {
    // Los dos campos siguen llegando y se usan —`bajas_mes` como contraste de la rotación—, pero
    // como card serían la once y la doce. §6 pide diez, de los que hoy se pintan nueve.
    const todas = titulos(datos()).flat()
    expect(todas).toHaveLength(10 - OCULTAS.length)
    expect(todas.some((t) => t.includes("Bajas"))).toBe(false)
    expect(todas.some((t) => t.includes("Onboarding"))).toBe(false)
  })

  it("bajas_mes viaja en la línea de contraste de la rotación", () => {
    expect(card(datos(), "Rotación 12 meses").description).toBe("4 bajas en 12 meses · 2 este mes")
  })

  it("ingresos_mes viaja en la línea de contraste de los ingresos próximos", () => {
    expect(card(datos(), "Ingresos próximos 30 días").description).toBe("1 ya ingresaron este mes")
  })
})

// ── (b) la variación sin base NO dice 0 % ─────────────────────────────────────────

describe("variación sin base de comparación", () => {
  it("`null` no se formatea como un porcentaje", () => {
    const texto = formatVariacion(null)
    expect(texto).not.toMatch(/\d/)          // ni "0%", ni "+0%", ni "0,0%"
    expect(texto).toBe("Sin mes anterior para comparar")
  })

  it("la card lo dice cuando hay mes actual pero no anterior", () => {
    const c = cardMasa(datos({ masa_salarial_actual: 900, masa_salarial_anterior: 0,
                               masa_salarial_variacion_pct: null }))
    expect(c.description).not.toMatch(/%/)
    expect(c.description).toBe("Sin mes anterior para comparar")
  })

  it("EL CONTRASTE: un 0 legítimo sí dice 0 %", () => {
    // Sin esto, devolver siempre "sin comparación" pasaría los dos tests de arriba. Con base y
    // sin movimiento, "0,0% vs mes anterior" es verdad y tiene que salir.
    const c = cardMasa(datos({ masa_salarial_variacion_pct: 0 }))
    expect(c.description).toBe("0,0% vs mes anterior")
  })

  it("con costos_nomina VACÍA la card no dice $0: dice que no hay nada cargado", () => {
    // Es el estado de producción hoy. "$0" afirmaría que 31 personas activas cuestan cero.
    const c = cardMasa(datos({ masa_salarial_actual: 0, masa_salarial_anterior: 0,
                               masa_salarial_variacion_pct: null }))
    expect(c.value).toBe(SIN_DATO)
    expect(c.description).toBe("Sin costos cargados")
  })

  it("pero un mes que CAE a cero teniendo base sí muestra $0", () => {
    const c = cardMasa(datos({ masa_salarial_actual: 0, masa_salarial_anterior: 1000,
                               masa_salarial_variacion_pct: -100 }))
    expect(c.value).toContain("0")
    expect(c.value).not.toBe(SIN_DATO)
  })
})

// ── (d) la mediana al lado del promedio ───────────────────────────────────────────

describe("antigüedad", () => {
  it("el número grande es el promedio y la mediana va de contraste", () => {
    const c = card(datos(), "Antigüedad promedio")
    expect(c.value).toBe("1,9 años")
    expect(c.description).toBe("Mediana: 1,2 años")
  })

  it("los dos números son distintos, así que no se puede mostrar uno dos veces", () => {
    const c = card(datos(), "Antigüedad promedio")
    expect(c.description).not.toContain("1,9")
  })
})

// ── (e) ninguna card lee un campo que el backend ya no manda ──────────────────────

describe("el payload es el del backend y nada más", () => {
  it("construir las diez cards no toca ninguna clave inexistente", () => {
    // El proxy revienta ante `kpis.costo_nomina` (el bug real del 21/8) o cualquier otro campo
    // que el front crea que existe. Sin él, esto pasaría con la card mostrando "undefined".
    expect(() => bloquesKpi(datos(), ADMIN)).not.toThrow()
  })

  it("y ninguna card renderiza undefined ni NaN", () => {
    // La contracara: el proxy caza el ACCESO, esto caza el RESULTADO — un campo opcional que
    // llegue vacío y termine formateado como "$NaN" no rompe ninguna lectura.
    const cards = bloquesKpi(datos(), ADMIN).flatMap((b) => b.kpis)
    expect(cards).toHaveLength(10 - OCULTAS.length)   // guarda: sin cards, el forEach no compara nada
    cards.forEach((c) => {
      expect(`${c.title} ${c.value} ${c.description}`).not.toMatch(/undefined|NaN/)
    })
  })

  it("la guarda del proxy funciona de verdad", () => {
    // Sin este test, un proxy roto (o un `in` que siempre diera true) dejaría el test de arriba
    // pasando en el vacío, que es exactamente el modo de falla que se persigue.
    const d = datos()
    expect(() => (d.dashboard.kpis as unknown as Record<string, number>).costo_nomina)
      .toThrow(/costo_nomina/)
  })
})

// ── KPIs que el backend no pudo calcular ──────────────────────────────────────────

describe("un KPI caído no se pinta como un cero medido", () => {
  it("muestra un guion y lo dice", () => {
    // `errores` existe en el backend desde la Sesión 5 y el front NUNCA lo declaró: el fail-safe
    // devuelve 0 y sin leer esto un KPI ROTO se ve igual que uno que midió cero.
    const c = card(datos({ errores: ["rotacion_12m"], rotacion_12m_pct: 0 }), "Rotación 12 meses")
    expect(c.value).toBe(SIN_DATO)
    expect(c.description).toBe("No se pudo calcular")
  })

  it("y solo cae el que falló", () => {
    const d = datos({ errores: ["rotacion_12m"] })
    expect(card(d, "Ausencias en curso").value).toBe("3")
  })
})

// ── headcount por empresa ─────────────────────────────────────────────────────────

describe("headcount por empresa", () => {
  it("el total cierra con el reparto y el reparto va en el detalle", () => {
    const c = card(datos(), "Headcount por empresa")
    expect(c.value).toBe("31")
    expect(c.detalle).toEqual([
      { etiqueta: "KARSTEC", valor: "19" }, { etiqueta: "DOSUBA", valor: "12" },
    ])
  })

  it("sin empresas no inventa un cero", () => {
    const c = card(datos({}, { headcount_por_empresa: [] }), "Headcount por empresa")
    expect(c.value).toBe(SIN_DATO)
  })
})

// ── el tono semántico ─────────────────────────────────────────────────────────────

describe("el fondo semántico", () => {
  it("hoy se despega UNA sola card, y solo si hay un ingreso en la ventana de aviso", () => {
    const d = datos()
    const conAviso: DatosAdmin = {
      ...d,
      atencion: [{ origen: "calculada", tipo: "ingreso_proximo", mensaje: "x", fecha: null,
                   href: null, evento_id: null, creado_por_nombre: null }],
    }
    const conTono = bloquesKpi(conAviso, ADMIN).flatMap((b) => b.kpis).filter((k) => k.tono !== "neutro")
    expect(conTono.map((k) => [k.title, k.tono])).toEqual([["Ingresos próximos 30 días", "atencion"]])
  })

  it("sin alertas de ingreso, la pantalla entera queda neutra", () => {
    // Si se despegan cinco cards no se despega ninguna. El umbral no es "hay preingresos": es
    // "hay uno dentro de la ventana de aviso", que es el que el backend ya trata como accionable.
    const todas = bloquesKpi(datos(), ADMIN).flatMap((b) => b.kpis)
    expect(todas.every((k) => k.tono === "neutro")).toBe(true)
  })

  it("si /atencion falló, no se inventa la alerta", () => {
    const d = { ...datos(), atencionError: true, atencion: [] }
    expect(card(d, "Ingresos próximos 30 días").tono).toBe("neutro")
  })
})

// ── el destino de cada card ───────────────────────────────────────────────────────

/**
 * 🔴 ESTE BLOQUE EXISTE PORQUE UNA MUTACIÓN SOBREVIVIÓ. `_destinosKpi.test.ts` prueba el MAPA y
 * el permiso, y `KpiCard.test.tsx` prueba que una card CON href linkee; entre los dos quedaba
 * suelto el cable: sacarle a `bloquesKpi` el `href: destino(rol, k.title)` dejaba las 33
 * aserciones de los otros dos archivos en verde y el dashboard entero sin un solo link.
 * Es el único lugar donde el cable se puede afirmar, porque es el único que tiene el fixture.
 *
 * Y por eso se afirma contra `DESTINOS` en vez de contra rutas escritas a mano: una lista propia
 * acá sería una tercera copia del mapa, que es lo que hace que las copias diverjan.
 */
describe("cada card llega con su destino ya resuelto", () => {
  it("las que tienen destino declarado y visible lo traen, y son las mismas del mapa", () => {
    const cards = bloquesKpi(datos(), ADMIN).flatMap((b) => b.kpis)
    const conHref = cards.filter((k) => k.href).map((k) => k.title).sort()
    expect(conHref).toEqual(Object.keys(DESTINOS).filter((t) => !OCULTAS.includes(t)).sort())
    cards.forEach((k) => {
      expect(k.href).toBe(OCULTAS.includes(k.title) ? undefined : DESTINOS[k.title])
    })
  })

  it("una card cuya sección salió del menú NO LLEGA, ni siquiera para admin", () => {
    // 🔴 CAMBIÓ EL 26/8/2026 y antes decía lo contrario: "llega SIN href". Esa era la primera
    // mitad del ocultamiento —el link— y la decisión de Franco fue la segunda: la card entera
    // sale de la vista. Un número de una sección que el menú esconde no es "informativo": es un
    // número del que no se puede hacer nada, ocupando una de las tres columnas de la fila.
    // La card SIGUE DECLARADA en `_kpisDashboard` (por eso `DESTINOS` la conserva y por eso
    // `masaSalarial` se sigue probando abajo): lo que se fue es su lugar en la grilla.
    expect(OCULTAS.length).toBeGreaterThanOrEqual(1) // guarda: si no hay ninguna, no mira nada
    const cards = bloquesKpi(datos(), ADMIN).flatMap((b) => b.kpis)
    OCULTAS.forEach((t) => expect(cards.find((k) => k.title === t), t).toBeUndefined())
  })

  it("EL CONTRASTE: con un rol que no puede leer casi nada, casi ninguna trae href", () => {
    // Sin este contraste, un `href` cableado como constante pasaría el test de arriba.
    const cards = bloquesKpi(datos(), "mandos_medios").flatMap((b) => b.kpis)
    expect(cards.filter((k) => k.href).map((k) => k.title)).toEqual(["Ausencias en curso"])
  })

  it("y la card declarada SIN destino no trae href con ningún rol", () => {
    expect(Object.keys(SIN_DESTINO).length).toBeGreaterThanOrEqual(1) // guarda
    Object.keys(SIN_DESTINO).forEach((t) => {
      expect(card(datos(), t).href).toBeUndefined()
    })
  })
})
