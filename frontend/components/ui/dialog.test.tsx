import { twMerge } from "tailwind-merge"
import { describe, expect, it } from "vitest"

import {
  CLASES_CUERPO,
  CLASES_POPUP,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  partirHijos,
} from "./dialog"

/**
 * El diálogo tiene que entrar en pantalla con el encabezado y los botones SIEMPRE visibles, y
 * scrollear solo el medio. Antes no: el popup está centrado con `-translate-y-1/2` y sin techo
 * de altura, así que un modal largo se desbordaba por arriba Y por abajo a la vez — se perdían
 * el título y los botones juntos. Pasaba en 20 de los 35 modales del repo.
 *
 * ⚠️ LO QUE ESTE ARCHIVO **NO** PUEDE PROBAR, Y POR QUÉ NO SE FINGE QUE SÍ.
 * `Dialog` de base-ui monta por PORTAL y vitest corre sin jsdom: `renderToStaticMarkup(<Dialog
 * open>…)` devuelve string **vacío**. Verificado, no supuesto — la primera versión de este
 * archivo renderizaba el diálogo entero y los 9 tests fallaban con `expected '' to contain …`.
 * O sea que el DOM final del diálogo es INVERIFICABLE en esta suite, y agregar jsdom es una
 * dependencia nueva que excede esta tanda.
 *
 * Lo que sí queda cubierto, que es donde está el riesgo real de regresión:
 *   · `partirHijos` — el reparto de hijos. **Si el footer nunca cae en `cuerpo`, no puede
 *     terminar adentro del contenedor scrollable**, porque `cuerpo` es lo ÚNICO que se le pasa.
 *     Esa implicación es la que sostiene el arreglo entero.
 *   · Las clases de las que depende el scroll, y que el className del consumidor las pise bien.
 * Lo que queda sin red son las 3 líneas de JSX que arman el popup.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * `partirHijos` se ejercita con los componentes REALES (`DialogHeader`, `DialogFooter`), no con
 * stubs: el reparto es por identidad de tipo, así que un doble con el mismo nombre pasaría a
 * `cuerpo` y el test no probaría el criterio real. Y el caso del `<div>` disfrazado de footer
 * está puesto a propósito para fijar que el criterio es el TIPO y no el `data-slot`.
 */

describe("partirHijos — de qué lado cae cada hijo", () => {
  const header = <DialogHeader key="h"><DialogTitle>T</DialogTitle></DialogHeader>
  const footer = <DialogFooter key="f"><button>Guardar</button></DialogFooter>
  const suelto = <p key="p">contenido</p>

  it("🔴 el footer NUNCA cae en el cuerpo — es lo que impide que se scrollee", () => {
    const { cuerpo, footer: pie } = partirHijos([header, suelto, footer])
    expect(pie).toHaveLength(1)
    expect(cuerpo).toHaveLength(1)
    expect(cuerpo).not.toContainEqual(footer)
  })

  it("el header tampoco", () => {
    const { cuerpo, header: cab } = partirHijos([header, suelto, footer])
    expect(cab).toHaveLength(1)
    expect(cuerpo).not.toContainEqual(header)
  })

  it("todo lo demás va al cuerpo, en orden", () => {
    const a = <p key="a">uno</p>
    const b = <p key="b">dos</p>
    const { cuerpo } = partirHijos([header, a, b, footer])
    expect(cuerpo).toHaveLength(2)
    expect(cuerpo.map((c) => (c as React.ReactElement<{ children: string }>).props.children))
      .toEqual(["uno", "dos"])
  })

  it("el orden de los hijos no importa: un footer al principio sigue siendo footer", () => {
    // Para que falle: repartir por POSICIÓN (primero/último) en vez de por tipo.
    const { cuerpo, footer: pie } = partirHijos([footer, suelto, header])
    expect(pie).toHaveLength(1)
    expect(cuerpo).toHaveLength(1)
  })

  it("un <div> con el data-slot del footer NO cuenta como footer", () => {
    // El criterio es el tipo del componente, no el atributo: un div disfrazado va al cuerpo.
    const impostor = <div key="x" data-slot="dialog-footer">no soy el footer</div>
    const { cuerpo, footer: pie } = partirHijos([header, impostor])
    expect(pie).toHaveLength(0)
    expect(cuerpo).toHaveLength(1)
  })

  it("sin header ni footer, todo es cuerpo y las otras dos listas quedan vacías", () => {
    const { header: cab, footer: pie, cuerpo } = partirHijos(suelto)
    expect(cab).toEqual([])
    expect(pie).toEqual([])
    expect(cuerpo).toHaveLength(1)
  })

  it("sin cuerpo, la lista queda vacía y el div scrollable no se renderiza", () => {
    // El `cuerpo.length > 0` del JSX depende de esto: sin él saldría un div vacío con gap.
    const { cuerpo } = partirHijos([header, footer])
    expect(cuerpo).toEqual([])
  })
})

describe("las clases que sostienen el scroll", () => {
  it("el popup tiene techo de altura y es columna flex", () => {
    expect(CLASES_POPUP).toContain("max-h-[calc(100dvh-2rem)]")
    expect(CLASES_POPUP).toContain("flex-col")
  })

  it("usa dvh y no vh", () => {
    // `vh` cuenta la barra de direcciones del navegador mobile aunque esté desplegada: el modal
    // queda más alto que lo que se ve, que es el bug que esto viene a cerrar.
    expect(CLASES_POPUP).not.toMatch(/max-h-\[[^\]]*\dvh\b/)
  })

  it("los extremos no encogen", () => {
    expect(CLASES_POPUP).toContain("[&>[data-slot=dialog-footer]]:shrink-0")
    expect(CLASES_POPUP).toContain("[&>[data-slot=dialog-header]]:shrink-0")
  })

  it("el cuerpo scrollea y puede encoger", () => {
    // `min-h-0` sin `overflow-y-auto` no scrollea, y al revés no encoge: van los dos o ninguno.
    expect(CLASES_CUERPO).toContain("min-h-0")
    expect(CLASES_CUERPO).toContain("overflow-y-auto")
  })
})

describe("los 15 modales que YA traían max-h y overflow siguen andando", () => {
  /**
   * ImportarNominaCSVModal, VacanteModal, EmpleadoModal, ObjetivoModal y 11 más pasan
   * `max-h-[90vh] overflow-y-auto` en el className. Lo que hay que garantizar es que su clase
   * siga ganando: `cn()` usa tailwind-merge, y dos `max-h` en el mismo elemento sin merge es un
   * empate que se resuelve por orden en el string — frágil de leer y fácil de romper.
   */
  const CONSUMIDOR = "max-h-[90vh] overflow-y-auto"
  const resultado = twMerge(CLASES_POPUP, CONSUMIDOR)

  it("el max-h del consumidor PISA al del primitivo", () => {
    expect(resultado).toContain("max-h-[90vh]")
    expect(resultado).not.toContain("max-h-[calc(100dvh-2rem)]")
  })

  it("y el resto del layout del primitivo sobrevive", () => {
    // El consumidor solo pisa `max-h` y agrega `overflow-y-auto`: flex, columna y los shrink-0
    // de los extremos tienen que seguir ahí, o el modal vuelve a scrollear entero.
    expect(resultado).toContain("flex-col")
    expect(resultado).toContain("[&>[data-slot=dialog-footer]]:shrink-0")
  })
})
