import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { Empleado } from "@/types/empleado"

import { AccionesFicha } from "./AccionesFicha"
import { BarraIdentidad } from "./BarraIdentidad"
import { antiguedad, datosClave } from "./_datosClave"

/**
 * (c), (d) y (e) del patrón "Ficha de detalle": los cuatro datos clave, cuándo aparece "Confirmar
 * ingreso" y que la acción primaria vaya última.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDAN FALLAR? (c) cuenta los `<dt>` del markup real,
 * así que un quinto dato lo rojea sin tocar el test. (e) compara POSICIONES en el HTML, no
 * presencia: un "Editar" que se mueva al principio pasa cualquier `toContain` y falla acá.
 */

const BASE: Empleado = {
  id: "1", nombre: "Ana", apellido: "Pérez", email_corporativo: "a@k.com",
  empresa_id: "e1", empresa_nombre: "Bodegas Tupungato", area_id: "a1", area_nombre: "Sistemas",
  roles: ["Analista"], modalidad_trabajo: "remoto", tipo_contrato: "Relación de dependencia",
  fecha_ingreso: "2020-03-01", telefono: null, fecha_nacimiento: null, dni: null, cuil: null,
  legajo: null, manager_id: "m1", manager_nombre: "Pérez, Juan", estado: "activo",
  dias_vacaciones_asignados: 14, email_personal: null, tipo_documento: null, sexo: null,
  telefono_alternativo: null, domicilio: null, domicilio_calle: null, domicilio_numero: null,
  domicilio_piso_depto: null, domicilio_localidad: null, domicilio_provincia: null,
  domicilio_cp: null, estudios: null, ubicacion: null, turno: null, horas_contrato: null,
  organismo: null, gerencia: null, sector: null, seniority: null, perfil: null, categoria: null,
  referido: null, es_lider: false, created_at: "2020-03-01",
}

const barra = (empleado: Empleado, acciones?: React.ReactNode) =>
  renderToStaticMarkup(<BarraIdentidad empleado={empleado} acciones={acciones} />)

describe("(c) la barra muestra EXACTAMENTE cuatro datos clave", () => {
  it("cuatro, ni tres ni cinco", () => {
    expect(datosClave(BASE)).toHaveLength(4)
    expect((barra(BASE).match(/<dt/g) ?? [])).toHaveLength(4)
  })

  it("son empresa, área, superior y antigüedad", () => {
    expect(datosClave(BASE).map((d) => d.label)).toEqual(["Empresa", "Área", "Superior", "Antigüedad"])
  })

  it("el rol NO gasta uno de los cuatro: va bajo el nombre", () => {
    const html = barra(BASE)
    expect(html).toContain("Analista")
    expect(datosClave(BASE).map((d) => d.label)).not.toContain("Rol")
  })

  it("un superior sin asignar se dice, no se deja en blanco", () => {
    expect(datosClave({ ...BASE, manager_nombre: null })[2].valor).toBe("Sin asignar")
  })

  it("el monograma sale de las iniciales y no se lee dos veces", () => {
    const html = barra(BASE)
    expect(html).toContain("AP")
    // `aria-hidden`: el lector de pantalla ya lee el nombre completo al lado.
    expect(html).toContain('aria-hidden="true"')
  })

  it("las migas de pan llevan a Empleados y la actual no es link", () => {
    const html = barra(BASE)
    expect(html).toContain('href="/empleados"')
    expect(html).toContain('aria-current="page"')
  })
})

describe("la antigüedad, y por qué un preingreso no tiene", () => {
  it("años y meses", () => {
    expect(antiguedad("2020-03-01", "2026-08-19")).toBe("6 años y 5 meses")
    expect(antiguedad("2025-08-19", "2026-08-19")).toBe("1 año")
    expect(antiguedad("2026-06-01", "2026-08-19")).toBe("2 meses")
    expect(antiguedad("2026-08-15", "2026-08-19")).toBe("Menos de un mes")
  })

  it("🔴 con fecha futura dice cuándo entra, no '0 meses'", () => {
    expect(antiguedad("2026-09-01", "2026-08-19")).toBe("Ingresa el 01/09/2026")
  })

  it("sin fecha no inventa", () => {
    expect(antiguedad(null, "2026-08-19")).toBe("—")
  })
})

describe("(d) 'Confirmar ingreso' aparece SOLO en preingreso", () => {
  const acciones = (estado: Empleado["estado"]) =>
    renderToStaticMarkup(
      <AccionesFicha
        empleado={{ ...BASE, estado }}
        onActivado={() => {}} onOffboarding={() => {}} onEditar={() => {}}
      />,
    )

  it("en preingreso está, y NO está la baja", () => {
    const html = acciones("preingreso")
    expect(html).toContain("Confirmar ingreso")
    expect(html).not.toContain("Iniciar offboarding")
  })

  it("en activo está la baja y NO el confirmar", () => {
    const html = acciones("activo")
    expect(html).toContain("Iniciar offboarding")
    expect(html).not.toContain("Confirmar ingreso")
  })

  it("en baja y en licencia no hay ninguna de las dos: solo Editar", () => {
    for (const estado of ["baja", "licencia"] as const) {
      const html = acciones(estado)
      expect(html).not.toContain("Confirmar ingreso")
      expect(html).not.toContain("Iniciar offboarding")
      expect(html).toContain("Editar")
    }
  })

  it("el chip de estado no es azul: usa los pares semánticos", () => {
    expect(barra({ ...BASE, estado: "preingreso" })).toContain("bg-warning-wash")
    expect(barra(BASE)).toContain("bg-success-wash")
    expect(barra(BASE)).not.toContain("bg-primary")
  })
})

describe("(e) la acción primaria es la ÚLTIMA del grupo", () => {
  it("Editar va después de la acción de ciclo, en los dos estados", () => {
    for (const estado of ["preingreso", "activo"] as const) {
      const html = renderToStaticMarkup(
        <AccionesFicha
          empleado={{ ...BASE, estado }}
          onActivado={() => {}} onOffboarding={() => {}} onEditar={() => {}}
        />,
      )
      const otra = estado === "preingreso" ? "Confirmar ingreso" : "Iniciar offboarding"
      expect(html.indexOf("Editar"), `en ${estado} la primaria no quedó última`)
        .toBeGreaterThan(html.indexOf(otra))
    }
  })
})
