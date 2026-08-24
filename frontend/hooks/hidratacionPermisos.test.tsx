/**
 * El rol vive en localStorage, que el SERVIDOR no tiene. Si los primitivos de permiso lo leen
 * durante el render, el HTML server-rendered sale sin los botones de escritura y el primer
 * render del cliente los agrega: mismatch de hidratación (React #418) en las 20 pantallas
 * donde el rol puede escribir, con React descartando el árbol server-rendered y regenerándolo.
 *
 * 🔴 LO QUE SE VERIFICA ACÁ ES QUE EL RENDER DE SERVIDOR SEA FAIL-CLOSED **AUNQUE HAYA SESIÓN**.
 * Ése es el hecho que elimina el mismatch: si el servidor y la hidratación coinciden en "sin
 * rol", el HTML que se emite y el que React espera son el mismo.
 *
 * ⚠️ Qué tendría que ser distinto para que este test pueda fallar: `getSession` está mockeada
 * para devolver una sesión con rol de escritura, así que `getRol()` responde "admin_rrhh"
 * incluso en Node. Con la implementación vieja —`puede(getRol(), ...)` en el cuerpo del
 * componente— el markup de servidor TRAE el botón y estos tests rojean. Verificado por
 * mutación.
 *
 * ⚠️ Lo que este archivo NO puede ver, y por eso está declarado: el camino del CLIENTE.
 * `renderToStaticMarkup` siempre toma `getServerSnapshot`, y el proyecto corre vitest sin
 * jsdom, así que no hay hidratación real que ejercitar. Que el snapshot del cliente sea el rol
 * de verdad —y no un `null` permanente, que dejaría los botones ocultos para siempre— se pinea
 * por fuente: es la mitad que un render de servidor no puede desmentir.
 */
import { readFileSync } from "node:fs"
import { join } from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import type { UserRol } from "@/types/auth"

let rolGuardado: UserRol | null = "admin_rrhh"

// Se mockea getSession y NO permisos: así `puede()` y `getRol()` son los REALES y lo único
// falseado es "hay una sesión en localStorage", que es la condición que dispara el bug.
vi.mock("@/services/api", () => ({
  getSession: () => (rolGuardado ? { user: { rol: rolGuardado } } : null),
}))
vi.mock("next/navigation", () => ({ usePathname: () => "/empleados" }))

const { useCanRead, useCanWrite } = await import("@/hooks/useCanWrite")
const { useRol } = await import("@/hooks/useRol")
const { Can } = await import("@/components/auth/Can")
const { getRol } = await import("@/services/permisos")

function BotonSiPuedeEscribir() {
  return useCanWrite() ? <button>Nuevo empleado</button> : null
}

function BloqueSiPuedeLeerCostos() {
  return useCanRead("costos") ? <section>Historial salarial</section> : null
}

function BotonPorCan() {
  return (
    <Can seccion="empleados">
      <button>Editar</button>
    </Can>
  )
}

describe("el render de servidor es fail-closed aunque haya sesión", () => {
  it("useCanWrite no pinta el botón de escritura", () => {
    expect(renderToStaticMarkup(<BotonSiPuedeEscribir />)).toBe("")
  })

  it("useCanRead no pinta el bloque gateado", () => {
    expect(renderToStaticMarkup(<BloqueSiPuedeLeerCostos />)).toBe("")
  })

  it("Can no pinta sus children", () => {
    expect(renderToStaticMarkup(<BotonPorCan />)).toBe("")
  })

  it("useRol devuelve null en el servidor, con sesión guardada y todo", () => {
    function MuestraElRol() {
      return <span>{String(useRol())}</span>
    }
    expect(renderToStaticMarkup(<MuestraElRol />)).toBe("<span>null</span>")
    // …y la sesión está ahí: si getRol() ya diera null, los tests de arriba pasarían solos.
    expect(getRol()).toBe("admin_rrhh")
  })
})

describe("la mitad que el render de servidor no puede desmentir", () => {
  const fuente = readFileSync(join(process.cwd(), "hooks", "useRol.ts"), "utf8")

  it("el snapshot del CLIENTE es getRol, no un null permanente", () => {
    // Sin esta aserción, "devolver siempre null" pasaría los tests de arriba y dejaría los
    // botones ocultos para todos los roles, para siempre.
    expect(fuente).toMatch(/useSyncExternalStore\(\s*suscribir,\s*getRol,\s*\(\)\s*=>\s*null\s*\)/)
  })

  it("nadie más lee getRol() durante un render: el rol entra por el hook", () => {
    const consumidores = ["hooks/useCanWrite.ts", "components/auth/Can.tsx"]
    for (const archivo of consumidores) {
      const texto = readFileSync(join(process.cwd(), archivo), "utf8")
      const sinComentarios = texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*/g, "")
      const llamadas = sinComentarios.match(/getRol\(\)/g) ?? []
      expect(llamadas, `${archivo} llama a getRol() en el render`).toEqual([])
    }
  })
})
