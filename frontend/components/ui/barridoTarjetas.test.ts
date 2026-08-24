/**
 * BARRIDO ESTRUCTURAL — toda TARJETA lleva el movimiento de §2, y lo saca del primitivo.
 *
 * 🔴 QUÉ DECISIÓN FIJA, Y POR QUÉ ESTÁ DADA VUELTA RESPECTO DE LO QUE HABÍA.
 * Hasta el 23/8/2026 la regla era *"una card informativa no se mueve: el hover promete un click
 * que no existe"*, y por eso perfiles, reportes, plantillas, objetivos, candidatos, offboarding
 * y las del organigrama estaban quietas mientras las de KPI con destino se elevaban. **Franco lo
 * revirtió**: en una grilla, que unas tarjetas respondan al puntero y otras no se lee como que
 * algunas están deshabilitadas. Ahora se mueven TODAS.
 *
 * 🔴 POR QUÉ HACE FALTA EL BARRIDO Y NO ALCANZA CON HABERLO APLICADO. El día que se escribió
 * esto había **10 componentes `*Card.tsx`** y sólo 1 con movimiento; seis de ellos ni siquiera
 * usaban el primitivo, tenían `rounded-xl border bg-card` escrito a mano. Aplicarlo a los diez
 * cierra el día de hoy; sin barrido, la card número once nace quieta en el próximo PR y con el
 * mismo argumento que escribieron los seis. Es la misma forma que `barridoSelect` (81 `<select>`
 * nativos con 29 constantes de estilo copiadas) y que `fieldError` (44 mensajes con 3 tamaños).
 *
 * 🔑 EL EJE ES "ES UNA TARJETA", NO "TIENE HOVER". Se pregunta por los componentes cuyo nombre
 * termina en `Card` más los nodos del organigrama, no por "quién usa `hover:`": preguntar lo
 * segundo obligaría a declarar una excepción por cada botón e ítem de menú del producto, para
 * siempre. Un PANEL —`Card as="section"`, un formulario, el historial— NO es una tarjeta y no
 * entra: ahí el movimiento no distingue nada porque no hay pares con qué compararlo.
 */
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it } from "vitest"

const RAIZ = join(__dirname, "..")

/** Enmascara comentarios: varias tarjetas explican EN PROSA la decisión vieja y la nueva, y un
 *  barrido por texto plano empujaría a borrar justo esas explicaciones. */
function sinComentarios(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "")
}

function archivos(dir: string): string[] {
  const out: string[] = []
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name)
    if (e.isDirectory()) out.push(...archivos(p))
    else if (e.name.endsWith(".tsx") && !e.name.includes(".test.")) out.push(p)
  }
  return out
}

const TODOS = archivos(RAIZ)

/** Los nodos del organigrama son tarjetas aunque no se llamen `*Card.tsx`. */
const TARJETAS_EXTRA = ["ArbolEmpresa.tsx", "ArbolProyecto.tsx"]

const TARJETAS = TODOS.filter((p) => {
  const n = p.split(/[\\/]/).pop() as string
  return n.endsWith("Card.tsx") || TARJETAS_EXTRA.includes(n)
})

/**
 * Tarjetas que a propósito NO se mueven. Vacío hoy: la decisión de Franco es "todas".
 * Una entrada acá necesita su razón escrita y el test de abajo verifica que siga existiendo.
 */
const QUIETAS: Record<string, string> = {}

describe("BARRIDO ESTRUCTURAL: toda tarjeta se mueve al apuntarla (§2)", () => {
  it("hay tarjetas que barrer (guarda de mínimo)", () => {
    expect(TARJETAS.length).toBeGreaterThanOrEqual(10)
    expect(TODOS.length).toBeGreaterThanOrEqual(200)
  })

  it("cada tarjeta renderiza <Card interactive>", () => {
    const sinMovimiento: string[] = []
    for (const ruta of TARJETAS) {
      const nombre = ruta.split(/[\\/]/).pop() as string
      if (nombre in QUIETAS) continue
      const src = sinComentarios(readFileSync(ruta, "utf8"))
      // `<Card ... interactive ...>`: la prop puede venir antes o después de las otras
      const tieneCard = /<Card[\s\n][^>]*interactive/.test(src)
      if (!tieneCard) sinMovimiento.push(nombre)
    }
    expect(sinMovimiento,
      "Estas tarjetas no se mueven al apuntarlas. Usá `<Card interactive>` de " +
      "@/components/ui/card — es el único lugar donde vive el movimiento de §2. " +
      "Si alguna NO debe moverse, declarala en QUIETAS con su razón.").toEqual([])
  })

  it("ninguna tarjeta reescribe el movimiento a mano", () => {
    const aMano = TARJETAS.filter((r) =>
      sinComentarios(readFileSync(r, "utf8")).includes("hover:-translate-y"))
      .map((r) => r.split(/[\\/]/).pop())
    expect(aMano,
      "El movimiento lo pone `card.tsx`. Escribirlo en el consumidor lo saca del alcance de " +
      "`decisionesVisuales.test.ts`, que es quien lo ata a la cita de §2.").toEqual([])
  })

  it("ninguna excepción declarada apunta a una tarjeta que ya no existe", () => {
    const nombres = new Set(TARJETAS.map((r) => r.split(/[\\/]/).pop() as string))
    const muertas = Object.keys(QUIETAS).filter((n) => !nombres.has(n))
    expect(muertas, "Una excepción muerta es ruido que tapa el próximo caso.").toEqual([])
  })
})
