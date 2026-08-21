import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { describe, expect, it } from "vitest"

import { puede, seccionDeRuta, type Seccion } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

/**
 * (f) las dos rutas nuevas TIENEN GATE.
 *
 * 🔴 POR QUÉ ESTO NECESITA UN TEST PROPIO, teniendo `nav-config.test.ts`. Aquel barrido compara
 * el sidebar contra `seccionDeRuta`, pero solo mira ítems CON href — y una pantalla puede existir
 * y ser alcanzable por URL sin estar en el menú (es literalmente el caso de /inventario). Lo que
 * se verifica acá es lo otro: que el AuthGuard, para ESTAS rutas, no las deje pasar a cualquiera.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * El modo de falla es MUDO y por eso hace falta la forma exacta de estas aserciones:
 * `seccionDeRuta` devuelve `null` para las rutas que no gatea, y el guard lee ese `null` como
 * "pasá" (`if (seccion && !puede(...))`). O sea que **olvidarse de la entrada en `RUTA_SECCION`
 * no rompe nada visible: deja la pantalla abierta para todos**. Por eso:
 *
 *   · No alcanza con `expect(seccionDeRuta(r)).not.toBeNull()`: se afirma la sección EXACTA, así
 *     un mapeo a la sección equivocada tampoco pasa.
 *   · Se reproduce la decisión COMPLETA del guard (`decisionDelGuard`, copiada de AuthGuard) y se
 *     afirma contra un rol que NO tiene que entrar. Si alguien borra la entrada del mapa, la
 *     sección se vuelve `null`, el guard deja pasar y este test rojea — que es la mutación que
 *     importa. La aserción sobre la sección sola no la cazaría en el caso de `mandos_medios`,
 *     porque el resultado "no entra" es el mismo por dos caminos distintos.
 *   · Y se verifica que estén en `RUTAS_ORDENADAS`, que NO se exporta —exportarla solo para un
 *     test la dejaría en el bucket "solo-tests" de `barridoFront.test.ts`—, leyendo el archivo.
 *     Sin esa lista, el redirect de un rol sin permiso nunca puede aterrizar acá.
 */

const RUTAS: ReadonlyArray<{ ruta: string; seccion: Seccion }> = [
  { ruta: "/proximos-ingresos", seccion: "empleados" },
  { ruta: "/bajas", seccion: "offboarding" },
]

/** La MISMA decisión que toma `AuthGuard`, incluida la rama `null` = "pasá". */
function decisionDelGuard(pathname: string, rol: UserRol | null): boolean {
  const seccion = seccionDeRuta(pathname)
  return seccion ? puede(rol, seccion, "read") : true
}

describe("(f) las dos rutas nuevas tienen gate", () => {
  it.each(RUTAS)("$ruta gatea con la sección $seccion, no con null", ({ ruta, seccion }) => {
    expect(seccionDeRuta(ruta)).toBe(seccion)
  })

  it.each(RUTAS)("$ruta deja entrar a admin_rrhh", ({ ruta }) => {
    // Contracara: sin esto, un gate que devolviera `false` para todos pasaría el test de abajo.
    expect(decisionDelGuard(ruta, "admin_rrhh")).toBe(true)
  })

  it.each(RUTAS)("$ruta NO deja entrar a mandos_medios", ({ ruta }) => {
    // mandos_medios solo ve VACACIONES y AUSENCIAS. Si la entrada del mapa desapareciera, la
    // sección sería `null`, el guard devolvería `true` y esto rojea.
    expect(decisionDelGuard(ruta, "mandos_medios")).toBe(false)
  })

  it.each(RUTAS)("$ruta NO deja entrar sin sesión (fail-closed)", ({ ruta }) => {
    expect(decisionDelGuard(ruta, null)).toBe(false)
  })

  it("gerencia_lectura puede LEERLAS pero no escribir: las dos son de consulta", () => {
    for (const { ruta, seccion } of RUTAS) {
      expect(decisionDelGuard(ruta, "gerencia_lectura")).toBe(true)
      expect(puede("gerencia_lectura", seccion, "write")).toBe(false)
    }
  })

  it("las dos están en RUTAS_ORDENADAS, o el redirect por falta de permiso no las alcanza", () => {
    const permisos = readFileSync(fileURLToPath(new URL("./permisos.ts", import.meta.url)), "utf8")
    const ordenadas = permisos.slice(permisos.indexOf("const RUTAS_ORDENADAS"))
    for (const { ruta, seccion } of RUTAS) {
      expect(ordenadas, `${ruta} falta en RUTAS_ORDENADAS`)
        .toContain(`{ ruta: "${ruta}", seccion: "${seccion}" }`)
    }
  })
})
