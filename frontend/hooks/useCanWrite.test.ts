import { describe, expect, it, vi } from "vitest"

import { puede, seccionDeRuta } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

// usePathname se mockea porque `useCanWrite` lo usa; la DECISIÓN se ejercita sobre
// `decidirCanWrite`, que es pura y no toca React. El hook en sí ya no se puede llamar en
// bucle: desde el arreglo de hidratación usa useSyncExternalStore, o sea un hook real.
// Que el rol salga del store de forma segura para la hidratación lo cubre hidratacion.test.tsx.
vi.mock("next/navigation", () => ({ usePathname: () => "/empleados" }))

const { decidirCanWrite } = await import("@/hooks/useCanWrite")

const ROLES: UserRol[] = ["admin_rrhh", "gerencia_lectura", "mandos_medios"]

describe("puede (espejo backend) — matriz de los 3 roles", () => {
  it("admin_rrhh escribe en cualquier sección", () => {
    expect(puede("admin_rrhh", "empleados", "write")).toBe(true)
    expect(puede("admin_rrhh", "costos", "write")).toBe(true)
    expect(puede("admin_rrhh", "vacaciones", "write")).toBe(true)
  })

  it("gerencia_lectura nunca escribe, siempre lee", () => {
    for (const sec of ["empleados", "vacaciones", "costos"] as const) {
      expect(puede("gerencia_lectura", sec, "write")).toBe(false)
      expect(puede("gerencia_lectura", sec, "read")).toBe(true)
    }
  })

  it("mandos_medios escribe solo en vacaciones y ausencias", () => {
    expect(puede("mandos_medios", "vacaciones", "write")).toBe(true)
    expect(puede("mandos_medios", "ausencias", "write")).toBe(true)
    expect(puede("mandos_medios", "empleados", "write")).toBe(false)
    expect(puede("mandos_medios", "objetivos", "write")).toBe(false)
  })

  it("fail-closed ante rol nulo o desconocido", () => {
    expect(puede(null, "empleados", "read")).toBe(false)
    expect(puede("otro" as UserRol, "empleados", "write")).toBe(false)
  })
})

describe("seccionDeRuta", () => {
  it("mapea el primer segmento a su sección", () => {
    expect(seccionDeRuta("/empleados")).toBe("empleados")
    expect(seccionDeRuta("/empresas/123")).toBe("empresa")
    expect(seccionDeRuta("/inventario")).toBe("inventario")
  })

  it("devuelve null en rutas no gateadas", () => {
    expect(seccionDeRuta("/configuracion")).toBeNull()
    expect(seccionDeRuta("/dashboard")).toBeNull()
    expect(seccionDeRuta("/")).toBeNull()
  })
})

describe("decidirCanWrite", () => {
  it("sección explícita: respeta la matriz por rol", () => {
    for (const rol of ROLES) {
      expect(decidirCanWrite(rol, "empleados")).toBe(puede(rol, "empleados", "write"))
      expect(decidirCanWrite(rol, "vacaciones")).toBe(puede(rol, "vacaciones", "write"))
    }
  })

  it("la sección derivada del pathname es la que decide", () => {
    expect(decidirCanWrite("admin_rrhh", seccionDeRuta("/inventario"))).toBe(true)
    expect(decidirCanWrite("gerencia_lectura", seccionDeRuta("/inventario"))).toBe(false)
  })

  it("ruta no gateada (sección null) → true para cualquier rol", () => {
    for (const rol of ROLES) {
      expect(decidirCanWrite(rol, seccionDeRuta("/configuracion"))).toBe(true)
    }
  })

  it("rol nulo → no puede escribir en sección gateada", () => {
    expect(decidirCanWrite(null, "empleados")).toBe(false)
  })
})
