import { describe, expect, it } from "vitest"

import {
  SIN_CAMBIOS_AUDITADOS,
  campoLabel,
  clavesVisibles,
  formatCampoValor,
  resumenDiff,
  soloTraiaDerivados,
} from "@/components/features/auditoria/auditLabels"

/**
 * Los 93 eventos que dicen que el área y la empresa de un empleado se vaciaron NO se borran
 * —un log del que se sacan filas deja de ser auditoría— pero tampoco se muestran como si
 * hubieran pasado. Acá se fija ese comportamiento.
 *
 * El diff fantasma nacía de comparar el registro leído CON joins contra el devuelto por un
 * UPDATE SIN joins. El backend ya no lo escribe (ver tests/test_audit_diff_derivados.py);
 * esto cubre lo que quedó guardado.
 */

// Un evento real de producción, copiado tal cual.
const EVENTO_FANTASMA = {
  antes: { area_nombre: "SALUD", empresa_nombre: "SERVICIOS Y CONSULTORIA SA KARSTEC SA" },
  nuevos: { area_nombre: null, empresa_nombre: null },
}

describe("eventos previos al fix", () => {
  it("un diff 100% derivado no deja ninguna clave visible", () => {
    expect(clavesVisibles(EVENTO_FANTASMA.antes, EVENTO_FANTASMA.nuevos)).toEqual([])
  })

  it("se reconoce como 'se editó sin cambios auditados'", () => {
    expect(soloTraiaDerivados(EVENTO_FANTASMA.antes, EVENTO_FANTASMA.nuevos)).toBe(true)
  })

  it("el resumen de la tabla NO dice '2 cambios'", () => {
    // Era lo que mostraba antes: dos cambios que no ocurrieron.
    expect(resumenDiff(EVENTO_FANTASMA.antes, EVENTO_FANTASMA.nuevos)).toBe(SIN_CAMBIOS_AUDITADOS)
  })

  it("el mensaje no afirma que algo se vació", () => {
    expect(SIN_CAMBIOS_AUDITADOS).not.toMatch(/vac[íi]|null|—/i)
  })

  it("un evento sin ningún dato NO se confunde con uno fantasma", () => {
    // cambio_password no guarda payload: eso es "sin detalle", no "se editó sin cambios".
    expect(soloTraiaDerivados(null, null)).toBe(false)
    expect(soloTraiaDerivados({}, {})).toBe(false)
  })
})

describe("eventos posteriores al fix", () => {
  it("un cambio real se muestra completo", () => {
    expect(resumenDiff({ seniority: "Ssr" }, { seniority: "Sr" })).toBe("Seniority: Ssr → Sr")
  })

  it("los tres campos comprometidos tienen etiqueta legible", () => {
    expect(campoLabel("roles")).toBe("Roles")
    expect(campoLabel("area_id")).toBe("Área")
    expect(campoLabel("seniority")).toBe("Seniority")
  })

  it("las columnas que el fix volvió a auditar también", () => {
    expect(campoLabel("manager_id")).toBe("Superior")
    expect(campoLabel("email_corporativo")).toBe("Email corporativo")
  })

  it("un cambio real mezclado con claves derivadas muestra solo el real", () => {
    // Puede pasar en un evento viejo donde SÍ se editó algo: el fantasma no debe sumar ruido.
    const antes = { area_nombre: "SALUD", email_corporativo: "a@x.com" }
    const nuevos = { area_nombre: null, email_corporativo: "b@x.com" }
    expect(clavesVisibles(antes, nuevos)).toEqual(["email_corporativo"])
    expect(resumenDiff(antes, nuevos)).toBe("Email corporativo: a@x.com → b@x.com")
  })

  it("varios cambios reales se cuentan sin los derivados", () => {
    const antes = { area_nombre: "SALUD", roles: ["Dev"], seniority: "Ssr" }
    const nuevos = { area_nombre: null, roles: ["Lead"], seniority: "Sr" }
    expect(resumenDiff(antes, nuevos)).toBe("2 cambios")
  })
})

describe("altas y bajas", () => {
  it("un alta muestra sus datos, no un diff", () => {
    expect(resumenDiff(null, { legajo: "A-12" })).toBe("Legajo: A-12")
  })

  it("un alta con derivados tampoco los cuenta", () => {
    expect(resumenDiff(null, { legajo: "A-12", area_nombre: "SALUD" })).toBe("Legajo: A-12")
  })
})

describe("area_id legible", () => {
  const AREAS = { "09ae1f7b-923f-42a0-9d22-939f7414c6d9": "FACTURACION" }

  it("resuelve el id al nombre del área", () => {
    expect(formatCampoValor("area_id", "09ae1f7b-923f-42a0-9d22-939f7414c6d9", AREAS))
      .toBe("FACTURACION")
  })

  it("nunca muestra el UUID crudo entero", () => {
    const uuid = "11111111-2222-3333-4444-555555555555"
    expect(formatCampoValor("area_id", uuid, AREAS)).not.toBe(uuid)
  })

  it("un área borrada se dice, no se deja en blanco", () => {
    // Un guion haría parecer que el campo estaba vacío, que es justo lo que no pasó.
    const out = formatCampoValor("area_id", "11111111-2222-3333-4444-555555555555", AREAS)
    expect(out).toMatch(/eliminada/i)
    expect(out).not.toBe("—")
  })

  it("mientras no cargaron las áreas no afirma que se borró", () => {
    expect(formatCampoValor("area_id", "09ae1f7b-923f-42a0-9d22-939f7414c6d9", null))
      .toBe("Cargando…")
  })

  it("un area_id nulo sigue siendo vacío, no 'eliminada'", () => {
    expect(formatCampoValor("area_id", null, AREAS)).toBe("—")
  })

  it("los otros campos no se tocan", () => {
    expect(formatCampoValor("seniority", "Sr", AREAS)).toBe("Sr")
    expect(formatCampoValor("dias", 5, AREAS)).toBe("5")
    expect(formatCampoValor("es_lider", true, AREAS)).toBe("Sí")
  })
})
