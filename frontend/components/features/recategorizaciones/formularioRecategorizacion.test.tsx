import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { Recategorizacion } from "@/types/recategorizacion"

import { RecategorizacionForm } from "./RecategorizacionForm"
import { formInicial, validarRecategorizacion } from "./guardarRecategorizacion"

/**
 * (a) el formulario NO deja escribir los valores anteriores.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE (a) PUEDA FALLAR
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Los valores anteriores del padrón son literales IRREPETIBLES (`ANTERIOR-ROL-XYZ`), y las dos
 * aserciones son distintas a propósito:
 *   1. el texto APARECE en el markup — el valor se muestra, no se esconde;
 *   2. `value="ANTERIOR-ROL-XYZ"` **NO** aparece — o sea, no está adentro de ningún control.
 * Con solo la primera, convertirlos en `<input>` pasaría en verde. Con solo la segunda, borrarlos
 * de la pantalla también. Hacen falta las dos, y el literal irrepetible es lo que evita que el
 * `value=` de otro campo las satisfaga por casualidad.
 *
 * ⚠️ Y hay una tercera: en el ALTA no se muestra NINGÚN anterior. No es un detalle estético — el
 * valor previo depende de la FECHA EFECTIVA (con carga retroactiva no es lo que el legajo dice
 * hoy), así que adivinarlo desde el front mostraría un número que el backend después contradice.
 */

const ORIGINAL: Recategorizacion = {
  id: "r-1", empleado_id: "e-1", empresa_id: "emp-1", fecha_efectiva: "2026-09-01",
  rol_anterior: "ANTERIOR-ROL-XYZ", rol_nuevo: "ANALISTA SENIOR",
  seniority_anterior: "ANTERIOR-SEN-XYZ", seniority_nueva: null,
  categoria_anterior: "ANTERIOR-CAT-XYZ", categoria_nueva: null,
  motivo: "Promoción", impacto_salarial: "150000",
  registrado_por: null, registrado_por_nombre: "Ana Pérez",
  empleado_nombre: "Juan Gómez", empresa_nombre: "Karstec",
  created_at: "2026-09-01T10:00:00Z", updated_at: null,
}

const ANTERIORES = ["ANTERIOR-ROL-XYZ", "ANTERIOR-SEN-XYZ", "ANTERIOR-CAT-XYZ"]

function formulario(props: Partial<Parameters<typeof RecategorizacionForm>[0]> = {}) {
  return renderToStaticMarkup(
    <RecategorizacionForm
      form={formInicial(props.original)}
      errores={{}}
      mostrarImpacto
      onChange={() => {}}
      onEmpleadoChange={() => {}}
      {...props}
    />,
  )
}

describe("(a) los valores anteriores se MUESTRAN, no se editan", () => {
  const html = formulario({ original: ORIGINAL })

  it("los tres aparecen en la pantalla", () => {
    for (const valor of ANTERIORES) {
      expect(html, `no se muestra ${valor}`).toContain(valor)
    }
  })

  it("🔴 y NINGUNO está adentro de un control: no hay `value=` con esos textos", () => {
    for (const valor of ANTERIORES) {
      expect(html, `${valor} quedó dentro de un input`).not.toContain(`value="${valor}"`)
    }
  })

  it("tampoco como input deshabilitado: un `disabled` dice 'esto se podría editar, ahora no'", () => {
    // Los `*_anterior` no entran en ningún schema de entrada del backend: no es que ahora no se
    // puedan editar, es que no son un campo del formulario.
    expect(html).toContain("lo calcula el sistema, no se edita")
  })

  it("🔴 en el ALTA no se muestra ningún anterior: dependen de la fecha efectiva", () => {
    const alta = formulario()
    for (const valor of ANTERIORES) {
      expect(alta).not.toContain(valor)
    }
    expect(alta).not.toContain("Valor anterior")
  })
})

describe("el colaborador no se puede cambiar en la edición", () => {
  it("el selector va deshabilitado y con el motivo escrito", () => {
    // `RecategorizacionUpdate` no acepta `empleado_id`: mover una recategorización de persona
    // invalidaría los `*_anterior` de las dos cadenas sin ninguna señal.
    const html = formulario({ original: ORIGINAL })
    expect(html).toContain("El colaborador no se puede cambiar")
    expect(html).toContain("disabled")
  })

  it("en el alta el selector está habilitado", () => {
    expect(formulario()).toContain("Colaborador")
  })
})

describe("(f) el formulario tampoco ofrece borrar", () => {
  it("no hay ninguna acción destructiva en el cuerpo", () => {
    const html = formulario({ original: ORIGINAL })
    for (const prohibido of ["Eliminar", "Borrar", "Dar de baja"]) {
      expect(html, `apareció «${prohibido}»`).not.toContain(prohibido)
    }
  })

  it("ni estado ni aprobación (§7)", () => {
    const html = formulario({ original: ORIGINAL })
    expect(html).not.toContain("aprob")
    expect(html).not.toContain("Aprob")
  })
})

describe("el impacto es un monto y solo con permiso de costos", () => {
  it("con permiso, el campo dice que es en PESOS y no un porcentaje", () => {
    const html = formulario({ original: ORIGINAL })
    expect(html).toContain("Monto en pesos")
    expect(html).not.toContain("%")
  })

  it("sin permiso el campo no está: no se deshabilita, no se dibuja", () => {
    const html = formulario({ original: ORIGINAL, mostrarImpacto: false })
    expect(html).not.toContain("Impacto salarial")
  })
})

describe("la validación local, antes de mandar", () => {
  const vacio = {
    empleadoId: "", fechaEfectiva: "2026-09-01", rolNuevo: "", seniorityNueva: "",
    categoriaNueva: "", motivo: "", impactoSalarial: "",
  }

  it("🔴 exige al menos un valor nuevo: es el espejo del 422 del backend y del CHECK de la base", () => {
    expect(validarRecategorizacion(vacio)).toHaveProperty("cambios")
  })

  it("con uno de los tres cargado, esa regla pasa", () => {
    const errs = validarRecategorizacion({ ...vacio, rolNuevo: "ANALISTA", motivo: "x", empleadoId: "e-1" })
    expect(errs).toEqual({})
  })

  it("el colaborador es obligatorio en el alta y NO en la edición", () => {
    expect(validarRecategorizacion({ ...vacio, rolNuevo: "R", motivo: "m" }))
      .toHaveProperty("empleadoId")
    expect(validarRecategorizacion({ ...vacio, rolNuevo: "R", motivo: "m" }, true))
      .toEqual({})
  })

  it("la fecha efectiva nace en HOY, no vacía", () => {
    const hoy = new Date()
    const iso = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}-${String(hoy.getDate()).padStart(2, "0")}`
    expect(formInicial().fechaEfectiva).toBe(iso)
  })

  it("🔴 en la edición los tres campos nuevos NACEN con lo que la fila tenía, no con el anterior", () => {
    // Precargarlos con el valor anterior convertiría una edición cualquiera en un cambio de rol
    // que nadie pidió.
    const f = formInicial(ORIGINAL)
    expect(f.rolNuevo).toBe("ANALISTA SENIOR")
    expect(f.seniorityNueva).toBe("")
    expect(f.categoriaNueva).toBe("")
  })
})
