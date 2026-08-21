import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { Recategorizacion } from "@/types/recategorizacion"

import { RecategorizacionesTabla } from "./RecategorizacionesTabla"

/**
 * (c) la columna de impacto sin permiso de costos, (f) que no haya borrar, y el vacío.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE (c) PUEDA FALLAR
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * La fila del padrón **tiene un impacto cargado** (`"150000.00"`). Con una fila sin monto, una
 * tabla que dibujara la columna vacía pasaría cualquier aserción sobre el valor: no habría valor
 * que mostrar ni con permiso ni sin él. Y se comparan las DOS direcciones —con permiso aparece,
 * sin permiso no— más el CONTEO DE COLUMNAS del encabezado, que es lo que distingue "columna
 * ausente" de "columna presente y vacía". Esa diferencia es el punto entero: una columna vacía se
 * lee como "no había monto", que es una afirmación distinta de "no lo podés ver".
 */

const FILA: Recategorizacion = {
  id: "r-1", empleado_id: "e-1", empresa_id: "emp-1", fecha_efectiva: "2026-09-01",
  rol_anterior: "ANALISTA", rol_nuevo: "ANALISTA SENIOR",
  seniority_anterior: null, seniority_nueva: null,
  categoria_anterior: null, categoria_nueva: null,
  motivo: "Promoción por antigüedad", impacto_salarial: "150000.00",
  registrado_por: null, registrado_por_nombre: "Ana Pérez",
  empleado_nombre: "Juan Gómez", empresa_nombre: "Karstec",
  created_at: "2026-09-01T10:00:00Z", updated_at: null,
}

const chip = (etiqueta: string, valor: string): ChipFiltro => ({
  clave: etiqueta, etiqueta, valor, quitar: () => {},
})

function tabla(props: Partial<Parameters<typeof RecategorizacionesTabla>[0]> = {}) {
  return renderToStaticMarkup(
    <RecategorizacionesTabla
      items={[FILA]} loading={false} error={false} mostrarImpacto canWrite
      chips={[]} onRetry={() => {}} onLimpiarTodo={() => {}} onEditar={() => {}}
      {...props}
    />,
  )
}

const encabezados = (html: string) => (html.match(/<th[ >]/g) ?? []).length

describe("(c) la columna de impacto no existe sin permiso de costos", () => {
  it("con permiso, la columna Y el monto están", () => {
    const html = tabla()
    expect(html).toContain("Impacto")
    expect(html).toContain("$150.000")
  })

  it("🔴 sin permiso NO se renderiza: ni el encabezado, ni una celda vacía", () => {
    const html = tabla({ mostrarImpacto: false })
    expect(html).not.toContain("Impacto")
    expect(html).not.toContain("150.000")
  })

  it("y la tabla tiene UNA COLUMNA MENOS, no una columna en blanco", () => {
    // Es lo que distingue "sacada" de "vacía". Con la columna presente el conteo no cambiaría.
    expect(encabezados(tabla())).toBe(encabezados(tabla({ mostrarImpacto: false })) + 1)
  })

  it("el resto de la fila sigue entero: lo que se oculta es el monto, no el registro", () => {
    // El listado NO se gatea con costos: el historial de rol y seniority es el 90% del valor.
    const html = tabla({ mostrarImpacto: false })
    expect(html).toContain("Juan Gómez")
    expect(html).toContain("ANALISTA SENIOR")
    expect(html).toContain("Promoción por antigüedad")
  })
})

describe("(f) no hay acción de borrar en ninguna superficie", () => {
  it("la tabla ofrece editar y nada más", () => {
    const html = tabla()
    expect(html).toContain("Editar la recategorización")
    for (const prohibido of ["Eliminar", "Borrar", "Dar de baja"]) {
      expect(html, `apareció «${prohibido}»`).not.toContain(prohibido)
    }
  })

  it("🔴 y el service NO tiene ninguna función de borrado ni ningún DELETE", () => {
    // El backend directamente no publica el verbo: borrar rompería la cadena de `*_anterior`.
    // Un botón acá prometería una operación que el servidor rechaza con 405.
    const src = readFileSync(
      fileURLToPath(new URL("../../../services/recategorizaciones.ts", import.meta.url)), "utf8")
    expect(src).not.toContain('method: "DELETE"')
    expect(src).not.toMatch(/export\s+(async\s+)?function\s+(delete|borrar|eliminar)/i)
  })

  it("sin permiso de escritura tampoco hay editar", () => {
    const html = tabla({ canWrite: false })
    expect(html).not.toContain("Editar la recategorización")
    expect(html).toContain("Juan Gómez")
  })
})

describe("sin estado ni aprobación (§7)", () => {
  it("no hay columna de estado ni palabra de aprobación en la tabla", () => {
    // Un prototipo anterior prometió un flujo de aprobación que no existe. Una columna
    // "Estado: Registrada" insinuaría que hay otros estados posibles.
    const html = tabla()
    for (const prohibido of ["Aprob", "aprob", "Pendiente", "Rechaz"]) {
      expect(html, `apareció «${prohibido}»`).not.toContain(prohibido)
    }
  })
})

describe("el vacío", () => {
  it("sin filtros dice que todavía no hay, que es el estado real de producción", () => {
    const html = tabla({ items: [], chips: [] })
    expect(html).toContain("Todavía no hay recategorizaciones")
  })

  it("🔴 con un colaborador filtrado, ÉL es el sujeto de la frase", () => {
    const html = tabla({
      items: [],
      chips: [chip("Colaborador", "Juan Gómez"), chip("Período", "desde 01/03/2026")],
      sujetoVacio: "Colaborador",
    })
    expect(html).toContain("Juan Gómez no tiene recategorizaciones con período desde 01/03/2026.")
  })

  it("y sin colaborador la frase queda impersonal: la empresa acá no es un filtro", () => {
    const html = tabla({ items: [], chips: [chip("Período", "desde 01/03/2026")] })
    expect(html).toContain("No hay recategorizaciones con período desde 01/03/2026.")
  })

  it("el encabezado sigue puesto en el vacío y en la carga: la forma no cambia", () => {
    for (const html of [tabla({ items: [] }), tabla({ loading: true })]) {
      expect(html).toContain("<thead")
      expect(html).toContain("Qué cambió")
    }
  })
})
