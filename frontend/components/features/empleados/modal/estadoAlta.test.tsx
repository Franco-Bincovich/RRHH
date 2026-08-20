import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { EMPTY, type FormData } from "./_constants"
import { DatosLaboralesFields } from "./DatosLaboralesFields"
import { ESTADO_ALTA_OPCIONES } from "./EstadoAltaField"
import { estadoSegunFecha, hoyISO } from "./form-utils"
import { guardarEmpleado } from "./_guardar"

/**
 * (a) y (b): el alta puede nacer en `preingreso`, y en edición el campo no existe.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR?
 *  · (a) mira el BODY que sale al servicio, no el estado del form: `guardarEmpleado` se ejecuta
 *    con `createEmpleado` mockeado y se afirma sobre lo que recibió. Un `estado` que se quedara
 *    en el formulario sin viajar —que es el bug exacto que esta tanda cierra— rojea.
 *  · (b) renderiza el componente REAL de los campos laborales en los dos modos. Si el `!isEdit`
 *    desapareciera, el select aparece en edición y el test lo ve.
 */

vi.mock("@/services/empleados", () => ({
  createEmpleado: vi.fn(async (body: unknown) => body),
  updateEmpleado: vi.fn(async (_id: string, body: unknown) => body),
}))

const { createEmpleado, updateEmpleado } = await import("@/services/empleados")

const FUTURO = "2099-01-15"
const PASADO = "2020-03-01"

function form(over: Partial<FormData> = {}): FormData {
  return { ...EMPTY, nombre: "Ana", apellido: "Pérez", empresa_id: "e1", area_id: "a1", ...over }
}

describe("el default de estado sale de la fecha de ingreso", () => {
  it("fecha futura → preingreso", () => {
    expect(estadoSegunFecha(FUTURO, "2026-08-19")).toBe("preingreso")
  })

  it("fecha de hoy → activo: hoy ya entró", () => {
    expect(estadoSegunFecha("2026-08-19", "2026-08-19")).toBe("activo")
  })

  it("fecha pasada → activo", () => {
    expect(estadoSegunFecha(PASADO, "2026-08-19")).toBe("activo")
  })

  it("sin fecha → activo, no adivina al revés", () => {
    expect(estadoSegunFecha("", "2026-08-19")).toBe("activo")
  })

  it("🔴 `hoyISO` es la fecha LOCAL, no la de UTC", () => {
    // `toISOString()` en Argentina (UTC-3) devuelve el día siguiente desde las 21:00: un alta
    // cargada de noche con fecha "mañana" se leería como "hoy" y nacería activa. Es un bug de una
    // hora por día, que no se reproduce en la sesión que lo escribe.
    const d = new Date()
    const local = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
    expect(hoyISO()).toBe(local)
  })
})

describe("(a) el alta con fecha futura manda estado='preingreso'", () => {
  it("el body lleva el estado elegido", async () => {
    vi.mocked(createEmpleado).mockClear()
    await guardarEmpleado(form({ fecha_ingreso: FUTURO, estado: "preingreso" }), undefined)

    const body = vi.mocked(createEmpleado).mock.calls[0][0]
    expect(body.estado).toBe("preingreso")
    expect(body.empresa_id).toBe("e1")
  })

  it("con 'Ya está trabajando' manda activo, aunque la fecha sea futura", () => {
    // El default se puede perder a propósito: la persona ya firmó y trabaja en otra sede.
    vi.mocked(createEmpleado).mockClear()
    guardarEmpleado(form({ fecha_ingreso: FUTURO, estado: "activo" }), undefined)
    expect(vi.mocked(createEmpleado).mock.calls[0][0].estado).toBe("activo")
  })

  it("🔴 la EDICIÓN no manda estado por ningún camino", async () => {
    // Es la otra mitad de la regla de A3: si viajara en el PUT, una edición cualquiera podría
    // devolver a `activo` a alguien en licencia salteándose la guarda de `/activar`.
    vi.mocked(updateEmpleado).mockClear()
    await guardarEmpleado(form({ estado: "preingreso" }), { id: "x" } as never)

    const body = vi.mocked(updateEmpleado).mock.calls[0][1] as Record<string, unknown>
    expect("estado" in body).toBe(false)
  })
})

describe("(b) en edición el select de estado no se renderiza", () => {
  const props = {
    form: form(), errors: {}, empresas: [], empresasLoading: false, areas: [], areasLoading: false,
    seleccionables: [], rolesSugeridos: [], field: () => () => {}, onEmpresaChange: () => {},
    onRolesChange: () => {}, onValue: () => () => {}, onLider: () => {}, onEstadoAlta: () => {},
  }

  it("en ALTA está, con las dos opciones en castellano", () => {
    const html = renderToStaticMarkup(<DatosLaboralesFields {...props} isEdit={false} />)
    expect(html).toContain("¿La persona ya empezó?")
    for (const o of ESTADO_ALTA_OPCIONES) expect(html).toContain(o.label)
    // Y no con los valores crudos a la vista.
    expect(html).not.toContain(">preingreso<")
  })

  it("en EDICIÓN no está", () => {
    const html = renderToStaticMarkup(<DatosLaboralesFields {...props} isEdit />)
    expect(html).not.toContain("¿La persona ya empezó?")
    expect(html).not.toContain("Todavía no ingresó")
  })
})
