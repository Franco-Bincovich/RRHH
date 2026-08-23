import { describe, expect, it } from "vitest"

import { armarFiltros, type ValoresFiltroObjetivos } from "./_filtrosObjetivos"

/**
 * El puente entre lo que el usuario elige y lo que viaja a la red.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. 🔴 **Este archivo existe PORQUE UNA MUTACIÓN SOBREVIVIÓ.** Con el armado adentro del hook,
 *    reemplazar `tipo: tipoFiltro || undefined` por `tipo: undefined` dejaba el selector de vista
 *    sin ningún efecto —la pantalla mostraba una vista y el backend devolvía las dos— y los 153
 *    tests del módulo seguían en verde: `filtros-export` prueba el service y `TipoObjetivoTabs`
 *    prueba el selector, y el cable entre los dos no lo miraba nadie.
 * 2. **Los cinco valores del fixture son distintos entre sí y ninguno es `true`/`1`.** Con dos
 *    campos del mismo valor, cruzarlos —mandar la prioridad donde va el estado— pasaría el test.
 * 3. **Cada aserción de "se cae del objeto" tiene su contraria de "viaja".** Sin eso, una función
 *    que devolviera `{}` siempre pasaría la mitad del archivo.
 */

const TODO: ValoresFiltroObjetivos = {
  mostrarEmpresa: true,
  empresaFiltro: "emp-7",
  estadoFiltro: "haciendo",
  prioridadFiltro: "alta",
  responsableFiltro: "usr-3",
  tipoFiltro: "anual",
}

const VACIO: ValoresFiltroObjetivos = {
  mostrarEmpresa: true, empresaFiltro: "", estadoFiltro: "",
  prioridadFiltro: "", responsableFiltro: "", tipoFiltro: "",
}

describe("todo lo elegido llega al objeto de filtros", () => {
  it("los cinco, cada uno en su campo", () => {
    expect(armarFiltros(TODO)).toEqual({
      empresaIdOverride: "emp-7",
      estado: "haciendo",
      prioridad: "alta",
      responsableId: "usr-3",
      tipo: "anual",
    })
  })

  it("la VISTA en particular: es el filtro que llegó último y el que no puede faltar", () => {
    // Si `tipo` no llega acá, el selector de vista no hace nada y el export trae las dos vistas.
    expect(armarFiltros({ ...VACIO, tipoFiltro: "operativo" }).tipo).toBe("operativo")
    expect(armarFiltros({ ...VACIO, tipoFiltro: "anual" }).tipo).toBe("anual")
  })
})

describe("lo no elegido se cae del objeto en vez de viajar vacío", () => {
  it("sin nada puesto, ningún campo tiene valor", () => {
    expect(Object.values(armarFiltros(VACIO)).filter(Boolean)).toEqual([])
  })

  it('"Todas" saca `tipo` del objeto: un `tipo=""` da 422 y un `tipo=todas` da cero filas', () => {
    expect(armarFiltros({ ...TODO, tipoFiltro: "" }).tipo).toBeUndefined()
    // EL CONTRASTE: los otros cuatro siguen ahí, o sea que se cayó sólo el que se vació.
    expect(armarFiltros({ ...TODO, tipoFiltro: "" }).estado).toBe("haciendo")
  })
})

describe("la empresa sólo se pisa en modo consolidado", () => {
  it("con empresa activa en el sidebar, el override NO viaja aunque haya filtro escrito", () => {
    // El header ya lo pone `apiFetch`; mandarlo desde acá sería que el filtro de pantalla le gane
    // al selector global, que es al revés de la regla Vista vs Acción.
    expect(armarFiltros({ ...TODO, mostrarEmpresa: false }).empresaIdOverride).toBeUndefined()
  })

  it("EL CONTRASTE: en consolidado sí viaja", () => {
    expect(armarFiltros(TODO).empresaIdOverride).toBe("emp-7")
  })
})
