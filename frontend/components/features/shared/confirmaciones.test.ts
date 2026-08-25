import { describe, expect, it } from "vitest"

import {
  confirmarCancelarVacaciones, confirmarCerrarPeriodo, confirmarEliminarAusencia,
  confirmarEliminarItem, confirmarEliminarObjetivo, fechaLegible,
} from "./confirmaciones"

/**
 * El TEXTO de las confirmaciones destructivas.
 *
 * 🔴 ES LO ÚNICO DE UN DIÁLOGO QUE ESTA SUITE PUEDE PROBAR, y no es poco: `vitest` corre con
 * `environment: "node"`, los tests de componente usan `renderToStaticMarkup` y ése no ejecuta
 * `useEffect` ni despacha clicks — un diálogo que se abre al apretar un botón es, para la suite,
 * invisible. Que EXISTA el diálogo lo cubre `components/ui/barridoConfirmacion.test.ts`; que
 * DIGA algo útil, esto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · Se le pasan VALORES REALES y se afirma que aparecen en la salida. Un test que solo mirara
 *     que el string no está vacío pasaría con un "¿Estás seguro?" pelado, que es exactamente el
 *     copy que esta tanda vino a evitar.
 *   · Las dos que NO borran se prueban contra una lista de palabras PROHIBIDAS, no contra un
 *     texto esperado: fijar el texto exacto haría que cualquier mejora de redacción rojee, y a
 *     la tercera vez alguien borra el test. Lo que no puede cambiar es que no diga "eliminar".
 */

describe("fechaLegible", () => {
  it("no usa new Date: el ISO se parte a mano", () => {
    // Con `new Date("2026-03-25")` esto daría 24/03 en cualquier huso al oeste de UTC —
    // Argentina incluida. Es el mismo bug que `filtrosChips` ya evita.
    expect(fechaLegible("2026-03-25")).toBe("25/03/2026")
    expect(fechaLegible("2026-01-01T00:00:00Z")).toBe("01/01/2026")
  })

  it("un valor ausente no produce 'undefined' en pantalla", () => {
    expect(fechaLegible(null)).toBe("")
    expect(fechaLegible(undefined)).toBe("")
  })
})

describe("Las tres que destruyen dicen QUÉ se pierde, con los valores reales", () => {
  it("la ausencia nombra a la persona y su rango", () => {
    const t = confirmarEliminarAusencia({
      empleado_nombre: "Ana Gómez", fecha_desde: "2026-03-03", fecha_hasta: "2026-03-07",
      tipo_nombre: "Enfermedad",
    })
    expect(t.description).toContain("Ana Gómez")
    expect(t.description).toContain("03/03/2026")
    expect(t.description).toContain("07/03/2026")
    expect(t.description).toContain("enfermedad")
    expect(t.description).toContain("no se puede deshacer")
  })

  it("el ítem nombra el ítem y su serie", () => {
    const t = confirmarEliminarItem({ nombre: "Notebook Lenovo", numero_serie: "SMK-9912" })
    expect(t.description).toContain("Notebook Lenovo")
    expect(t.description).toContain("SMK-9912")
  })

  it("🔴 el objetivo AVISA DEL CASCADE y cuenta los hijos", () => {
    // El caso que motivó toda la tanda: `parent_id` es ON DELETE CASCADE, así que borrar un
    // padre se lleva a los hijos. Sin este número el diálogo diría "eliminar Migrar nómina" y
    // desaparecerían cuatro cosas.
    const t = confirmarEliminarObjetivo({ titulo: "Migrar nómina", hijos: [1, 2, 3] })
    expect(t.description).toContain("Migrar nómina")
    expect(t.description).toContain("3 subobjetivos")
    expect(t.confirmLabel).toBe("Eliminar todo")
  })

  it("un objetivo con UN hijo lo dice en singular", () => {
    const t = confirmarEliminarObjetivo({ titulo: "X", hijos: [1] })
    expect(t.description).toContain("su subobjetivo")
    expect(t.description).not.toContain("subobjetivos")
  })

  it("una hoja NO inventa un arrastre que no existe", () => {
    // La contracara: sin esto, un texto que dijera siempre "y sus subobjetivos" pasaría el test
    // de arriba y mentiría en el caso más común.
    const t = confirmarEliminarObjetivo({ titulo: "X", hijos: [] })
    expect(t.description).not.toContain("subobjetivo")
    expect(t.confirmLabel).toBe("Eliminar el objetivo")
  })
})

describe("🔴 Las dos que NO destruyen no usan el vocabulario del borrado", () => {
  // La regla 2 de `confirmaciones.ts`: si no borra, no dice "eliminar". Escribirle a una acción
  // reversible el copy de un borrado frena al usuario de hacer algo inocuo y, peor, devalúa el
  // diálogo de las que sí destruyen — cuando todo dice "no se puede deshacer", deja de significar.
  // 🔴 SE MIDEN EL TÍTULO Y EL BOTÓN, NO LA DESCRIPCIÓN, y el matiz es el que hace correcta la
  // regla: el título y el `confirmLabel` son lo que el usuario lee como "qué estoy por hacer",
  // mientras que la descripción puede —y debe— nombrar el borrado para decir qué se IMPIDE.
  // "Nadie va a poder cargar, editar ni borrar registros en ese rango" es exactamente el copy
  // correcto de cerrar un período, y una regla que mirara el texto entero lo marcaría. La
  // primera versión de este test lo hizo, y la salida natural de ese falso positivo habría sido
  // empeorar el copy para complacer al test.
  const PROHIBIDAS = ["eliminar", "borrar", "eliminación", "permanente"]
  const accion = (t: { title: string; confirmLabel: string }) =>
    `${t.title} ${t.confirmLabel}`.toLowerCase()

  it("cancelar vacaciones no habla de borrar, y dice qué pasa con el saldo", () => {
    const t = confirmarCancelarVacaciones({
      empleado_nombre: "Ana Gómez", fecha_desde: "2026-01-01", fecha_hasta: "2026-01-15", dias: 10,
    })
    for (const p of PROHIBIDAS) expect(accion(t), `el título o el botón dicen "${p}"`).not.toContain(p)
    // Y la descripción tampoco puede prometer irreversibilidad, porque esto SÍ se deshace.
    expect(t.description.toLowerCase()).not.toContain("no se puede deshacer")
    expect(t.description).toContain("Ana Gómez")
    expect(t.description).toContain("10 días")
    expect(t.description).toContain("saldo")
    expect(t.description).toContain("no se borra")   // lo dice explícitamente
  })

  it("cerrar período no habla de borrar, dice qué se bloquea y que es reversible", () => {
    const t = confirmarCerrarPeriodo({
      empresa_nombre: "Karstec", desde: "2026-01-01", hasta: "2026-01-31", modulo_label: "Costos",
    })
    for (const p of PROHIBIDAS) expect(accion(t), `el título o el botón dicen "${p}"`).not.toContain(p)
    expect(t.description.toLowerCase()).not.toContain("no se puede deshacer")
    expect(t.description).toContain("Karstec")
    expect(t.description).toContain("01/01/2026")
    expect(t.description).toContain("Costos")
    expect(t.description).toContain("reabrir")
  })

  it("sin módulo elegido, el período dice que alcanza a TODO", () => {
    // El default del form es "Todos los módulos" y ése es el caso más peligroso: un texto que
    // omitiera el alcance dejaría creer que se cierra sólo una parte.
    const t = confirmarCerrarPeriodo({ desde: "2026-01-01", hasta: "2026-01-31" })
    expect(t.description).toContain("todos los módulos")
  })
})

describe("La contracara: las que SÍ destruyen sí usan ese vocabulario", () => {
  // Sin esto, un copy que nunca dijera "eliminar" en ningún lado pasaría el bloque de arriba y
  // le escondería al usuario que está por destruir algo. La regla es que el vocabulario coincida
  // con el efecto, en las dos direcciones — no que "eliminar" esté prohibido.
  it("las tres nombran el borrado en el título y en el botón", () => {
    for (const t of [confirmarEliminarAusencia({}), confirmarEliminarItem({}),
                     confirmarEliminarObjetivo({})]) {
      expect(t.title.toLowerCase()).toContain("eliminar")
      expect(t.confirmLabel.toLowerCase()).toContain("eliminar")
      expect(t.description.toLowerCase()).toContain("no se puede deshacer")
    }
  })
})

describe("Ningún texto muestra 'undefined' ni un id crudo", () => {
  it("con el objeto vacío —el estado inicial del diálogo— sigue siendo legible", () => {
    // Las pantallas spreadean `confirmarX(pendiente ?? {})`, así que este caso se renderiza de
    // verdad en el primer render, antes de que el usuario elija una fila.
    const vacios = [
      confirmarEliminarAusencia({}), confirmarEliminarItem({}), confirmarEliminarObjetivo({}),
      confirmarCancelarVacaciones({}), confirmarCerrarPeriodo({}),
    ]
    for (const t of vacios) {
      const texto = `${t.title} ${t.description} ${t.confirmLabel}`
      expect(texto).not.toContain("undefined")
      expect(texto).not.toContain("null")
      expect(texto).not.toContain("NaN")
      expect(t.description.length).toBeGreaterThan(20)
    }
  })
})
