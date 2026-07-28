import { describe, expect, it } from "vitest"

import { NAV_GROUPS } from "@/components/layout/nav-config"
import { seccionDeRuta } from "@/services/permisos"

/**
 * El sidebar y el guard de ruta tienen que gatear con la MISMA sección.
 *
 * Son dos mapas escritos a mano en archivos distintos: nav-config decide qué se VE y
 * permisos.ts decide a qué se ENTRA. Si divergen, el resultado no es un error visible sino un
 * ítem que aparece en el menú y rebota al hacer clic —o peor, una ruta accesible que el menú
 * esconde y nadie audita. Este test los compara enteros, así que cubre también al próximo
 * módulo que se agregue, no solo a Áreas.
 */

const ITEMS = NAV_GROUPS.flatMap((g) => g.items)

describe("nav-config ↔ permisos", () => {
  it("el barrido no está vacío", () => {
    // Guarda contra el falso verde: con la lista vacía todo lo de abajo pasaría sin comparar.
    expect(ITEMS.length).toBeGreaterThanOrEqual(20)
  })

  it.each(ITEMS.filter((i) => i.seccion !== null))(
    "$href gatea con la misma sección en el sidebar y en el guard",
    (item) => {
      expect(seccionDeRuta(item.href)).toBe(item.seccion)
    },
  )

  it("Áreas está en el sidebar", () => {
    // Existía la página y el gate, pero no el punto de entrada: solo se llegaba tipeando la URL.
    expect(ITEMS.find((i) => i.href === "/areas")?.seccion).toBe("areas")
  })

  it("ningún ítem apunta a una ruta sin sección conocida", () => {
    // Un href con typo devolvería null acá y quedaría fuera del filtro de permisos del sidebar.
    const huerfanos = ITEMS.filter((i) => i.seccion !== null && seccionDeRuta(i.href) === null)
    expect(huerfanos.map((i) => i.href)).toEqual([])
  })
})
