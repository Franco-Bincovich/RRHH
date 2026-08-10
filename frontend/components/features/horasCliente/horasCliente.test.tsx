import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ClientesColapsables } from "@/components/features/horasCliente/ClientesColapsables"
import { KPIsHorasPanel } from "@/components/features/horasCliente/KPIsHorasPanel"
import { formatFechaCorta, textoDeCarga } from "@/components/features/horasCliente/detalleFormato"
import type { ClienteConHoras } from "@/types/horasCliente"
import type { Hora } from "@/types/proyecto"

/**
 * "Horas por cliente" en el front.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. La guarda de markup no vacío.** Se renderiza con `renderToStaticMarkup` porque el proyecto
 * corre vitest SIN jsdom. Si un componente devolviera "" —porque revienta, porque lo envuelve un
 * portal, porque cambia a `return null`— todas las aserciones NEGATIVAS pasarían igual y el test
 * estaría afirmando que un componente ROTO no muestra cosas. Por eso cada render pasa por
 * `_render`, que exige contenido antes de devolverlo.
 *
 * **2. Más de un cliente y más de un empleado.** Con uno solo, "agrupa" y "no agrupa" dan el
 * mismo markup. El fixture trae DOS clientes (uno de ellos el bucket "Sin cliente") y DOS
 * empleados, y se afirma que los dos aparecen.
 *
 * **3. `DetalleEmpleadoModal` NO se renderiza acá, y no es un olvido:** usa `Dialog` de Radix,
 * que monta por PORTAL, así que a string sale "" SIEMPRE. Un test suyo pasaría con el contenido
 * entero borrado. Lo que se prueba son sus dos decisiones puras (`detalleFormato`).
 *
 * **4. La trampa del `disabled`.** En los componentes que usan el `Button` de shadcn, el markup
 * trae la clase `disabled:` con y sin la prop, así que `not.toContain("disabled")` no puede
 * fallar NUNCA (queda demostrado en `ClientesTabla.test.tsx`). Acá el markup alcanzable es un
 * `<button>` plano; hay un test que lo deja constatado para que nadie copie la aserción
 * equivocada de un archivo al otro.
 */

const CLIENTES: ClienteConHoras[] = [
  {
    cliente_id: "c1", cliente_nombre: "Acme", horas: 9, registros: 3,
    lineas: [
      { empleado_id: "e1", empleado_nombre: "Ana Pérez", proyecto_texto: null,
        tarea_texto: "Reunión", modalidad: "home_office", horas: 6, registros: 2 },
      { empleado_id: "e2", empleado_nombre: "Bruno Gómez", proyecto_texto: "Migración",
        tarea_texto: "Soporte", modalidad: "on_site", horas: 3, registros: 1 },
    ],
  },
  {
    cliente_id: null, cliente_nombre: "Sin cliente", horas: 6, registros: 1,
    lineas: [
      { empleado_id: null, empleado_nombre: null, proyecto_texto: "Interno",
        tarea_texto: null, modalidad: null, horas: 6, registros: 1 },
    ],
  },
]

function _render(nodo: React.ReactElement): string {
  const html = renderToStaticMarkup(nodo)
  // 🔴 GUARDA: sin esto, un componente que devuelve "" pasa todas las aserciones negativas.
  expect(html.length).toBeGreaterThan(80)
  return html
}

afterEach(() => vi.restoreAllMocks())

describe("KPIsHorasPanel", () => {
  const KPIS = {
    horas_totales: 20, clientes_con_carga: 2, empleados_que_cargaron: 4, registros: 5,
  }

  it("muestra los cuatro KPIs", () => {
    const html = _render(<KPIsHorasPanel kpis={KPIS} />)
    for (const label of ["Horas del mes", "Clientes con carga",
                         "Empleados que cargaron", "Registros"]) {
      expect(html).toContain(label)
    }
  })

  it("con todo en cero SIGUE renderizando", () => {
    // Un mes sin cargas tiene que verse como "0 horas", no como una pantalla en la que no se
    // sabe si falló algo. Es el criterio del dashboard con sus KPIs fail-safe.
    const html = _render(<KPIsHorasPanel kpis={{ horas_totales: 0, clientes_con_carga: 0,
                                                 empleados_que_cargaron: 0, registros: 0 }} />)
    expect(html).toContain("Horas del mes")
  })

  it("los valores son los recibidos y no constantes", () => {
    const html = _render(<KPIsHorasPanel kpis={KPIS} />)
    expect(html).toContain("20")
    expect(html).toContain(">4<")
  })
})

describe("ClientesColapsables", () => {
  const render = (cs = CLIENTES) =>
    _render(<ClientesColapsables clientes={cs} onVerDetalle={() => {}} />)

  it("muestra un grupo por cliente, no todo junto", () => {
    const html = render()
    expect(html).toContain("Acme")
    expect(html).toContain("Sin cliente")
  })

  it("arranca colapsado: el detalle no está en el markup inicial", () => {
    // El estado inicial es cerrado, y sin jsdom no se puede clickear. Lo que se verifica es que
    // el detalle NO se filtre igual (un `hidden` con CSS lo dejaría en el HTML).
    const html = render()
    expect(html).not.toContain("Ana Pérez")
    expect(html).toContain('aria-expanded="false"')
  })

  it("el encabezado del grupo muestra sus horas y registros", () => {
    const html = render()
    expect(html).toContain("9 h")
    expect(html).toContain("3 registros")
  })

  it("singulariza 'registro' cuando es uno solo", () => {
    expect(render()).toContain("1 registro<")
  })

  it("el grupo Sin cliente aparece como cualquier otro", () => {
    // 🔴 Son las cargas del camino viejo. Si se filtraran, 6 horas válidas desaparecerían.
    const html = render()
    expect(html).toContain("Sin cliente")
    expect(html).toContain("6 h")
  })

  it("el toggle no es un Button de shadcn, y por eso la trampa del disabled no aplica acá", () => {
    // 🔴 En los componentes que SÍ usan el Button de shadcn (ver ClientesTabla.test.tsx),
    // `not.toContain("disabled")` es una aserción que NO PUEDE FALLAR: el markup trae la clase
    // `disabled:` con y sin la prop. Acá el markup alcanzable es un <button> plano, así que la
    // clase no está. Queda constatado para que nadie copie la aserción equivocada de un archivo
    // al otro creyendo que prueba algo.
    const html = render()
    expect(html).toContain('<button type="button"')
    expect(html).not.toContain("disabled")
  })
})

describe("detalleFormato", () => {
  const H = (kw: Partial<Hora>): Hora => ({
    id: "h1", empresa_id: null, asignacion_id: null, proyecto_id: null, empleado_id: "e1",
    empleado_nombre: "Ana", empleado_empresa_nombre: null, fecha: "2026-08-10", horas: 4,
    valor_hora_snapshot: null, costo: null, descripcion: null, cliente_id: "c1",
    cliente_nombre: "Acme", modalidad: "home_office", proyecto_texto: null, tarea_texto: null,
    created_at: "2026-08-10T00:00:00Z", ...kw,
  })

  it("arma la línea con lo que hay y descarta los vacíos", () => {
    expect(textoDeCarga(H({ tarea_texto: "Reunión" })))
      .toBe("Acme · Reunión · Home Office")
  })

  it("nombra 'Sin cliente' en vez de dejar un hueco", () => {
    // Un blanco se lee como un dato que falta; acá significa algo concreto.
    expect(textoDeCarga(H({ cliente_nombre: null }))).toContain("Sin cliente")
  })

  it("nunca devuelve vacío", () => {
    // Un renglón con solo fecha y horas parece cortado a la mitad.
    expect(textoDeCarga(H({ cliente_nombre: null, modalidad: null }))).toBe("Sin cliente")
  })

  it("la fecha no se corre un día por zona horaria", () => {
    // Sin el `T00:00:00`, `new Date("2026-08-10")` se interpreta en UTC y en AR muestra el 09.
    expect(formatFechaCorta("2026-08-10")).toBe("10/08")
    expect(formatFechaCorta("2026-01-01")).toBe("01/01")
    // Y el mes va PADDEADO: `toLocaleDateString` devolvía "10/8" en un Node sin ICU completo.
    expect(formatFechaCorta("2026-08-01")).toBe("01/08")
  })
})
