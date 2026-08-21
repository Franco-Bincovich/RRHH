import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposAuditoria } from "./_camposAuditoria"
import { AuditTable } from "./AuditTable"

/**
 * Los cuatro puntos del patrón del bloque B sobre /auditoria, la pantalla que tenía **la barra de
 * filtros propia más rica del repo** (`AuditFilters.tsx`, borrada en esta tanda).
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que las opciones dejaran de salir de `ENTIDAD_LABEL`/`EVENTO_LABEL`: el chip diría
 *     `alta_empleado` en vez de "Alta de colaborador".
 *   · (b) que un `onChange` se olvidara de `onFiltroChange`.
 *   · (c) que el vacío volviera a reemplazar la tabla entera: desaparece `<thead>`.
 *   · (d) que la página le pasara `logs.length` a `<Pagination>`.
 */

const USUARIOS = [{ id: "u1", nombre: "Ana", apellido: "Pérez" }]

function args(over: Partial<ArgsCamposAuditoria> = {}): ArgsCamposAuditoria {
  return {
    entidad: "", setEntidad: vi.fn(),
    evento: "", setEvento: vi.fn(),
    usuarioId: "", setUsuarioId: vi.fn(),
    usuarios: USUARIOS as ArgsCamposAuditoria["usuarios"],
    rango: { desde: "", hasta: "" }, setRango: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("Sección y Evento dicen el texto de auditLabels, no la clave del backend", () => {
    const chips = chipsDeCampos(construirCampos(args({ entidad: "vacacion", evento: "alta_ausencia" })))
    expect(chips.find((c) => c.clave === "Sección")!.valor).toBe("Vacación")
    expect(chips.find((c) => c.clave === "Evento")!.valor).toBe("Alta de ausencia")
  })

  it("el Usuario dice el nombre y apellido, no el uuid", () => {
    const chips = chipsDeCampos(construirCampos(args({ usuarioId: "u1" })))
    expect(chips.find((c) => c.clave === "Usuario")!.valor).toBe("Ana Pérez")
  })

  it("🔴 'Desde' y 'Hasta' son UN solo chip, no dos", () => {
    /*
     * Eran dos campos `date` independientes en `AuditFilters`. Ahora son un `daterange`: emiten
     * el mismo par `fecha_desde`/`fecha_hasta` al backend, pero cuentan como UN filtro activo —
     * que es lo que hace que el contador de la fila inferior no diga "2" por un solo período.
     */
    const chips = chipsDeCampos(construirCampos(args({ rango: { desde: "2026-03-01", hasta: "2026-03-31" } })))
    expect(chips).toHaveLength(1)
    expect(chips[0].valor).toBe("01/03/2026 – 31/03/2026")
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("el chip de Sección llama a su setter con vacío y dispara el reset", () => {
    const a = args({ entidad: "vacacion", evento: "alta_ausencia" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Sección")!.quitar()

    expect(a.setEntidad).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setEvento).not.toHaveBeenCalled()
    expect(a.setUsuarioId).not.toHaveBeenCalled()
  })

  it("vale para TODOS los filtros con chip, no sólo para Sección", () => {
    const a = args({
      entidad: "vacacion", evento: "alta_ausencia", usuarioId: "u1",
      rango: { desde: "2026-03-01", hasta: "" },
    })
    const chips = chipsDeCampos(construirCampos(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(4)

    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("qué queda atrás de 'Más filtros': sólo Usuario, el recorte a UNA persona", () => {
    const campos = construirCampos(args())
    expect(campos.filter((c) => c.avanzado).map((c) => c.label)).toEqual(["Usuario"])
    expect(campos.filter((c) => !c.avanzado).map((c) => c.label)).toEqual(["Sección", "Evento", "Período"])
  })
})

const chip = (etiqueta: string, valor: string): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar: () => {} })

function tabla(props: Partial<Parameters<typeof AuditTable>[0]> = {}) {
  return renderToStaticMarkup(
    <AuditTable
      logs={[]} loading={false} error={false} onRetry={() => {}} onVerDetalle={() => {}}
      chips={[chip("Sección", "Vacación"), chip("Evento", "Alta de ausencia")]}
      onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos mantiene el encabezado y usa los valores reales", () => {
  it("las columnas siguen ahí y el vacío es una fila de la tabla", () => {
    const html = tabla()
    for (const columna of ["Fecha", "Usuario", "Empresa", "Sección", "Evento", "Acción", "Detalle"]) {
      expect(html, `desapareció la columna ${columna} del vacío`).toContain(columna)
    }
    expect(html).toContain("<thead")
    expect(html).toContain('colSpan="7"')
  })

  it("la frase arranca impersonal y nombra los filtros puestos", () => {
    // Sin sujeto: la empresa de esta pantalla la manda el sidebar, no un chip del panel.
    expect(tabla()).toContain("No hay registros de auditoría con sección Vacación y evento Alta de ausencia.")
  })

  it("🔴 sin filtros el copy es PROPIO: nadie carga un evento de auditoría", () => {
    /*
     * El genérico de `textoVacio` dice "Cuando se cargue el primero va a aparecer acá", y acá esa
     * frase es falsa: los eventos los escribe el sistema y la sección es de solo lectura por
     * diseño. Es el caso exacto de la regla del bloque.
     */
    const html = tabla({ chips: [] })
    expect(html).toContain("No hay registros de auditoría todavía")
    expect(html).toContain("Nadie los carga a mano")
    expect(html).not.toContain("Cuando se cargue el primero")
    // Y conserva la estructura del patrón: fila con colSpan, fuera del hover de datos.
    expect(html).toContain("<thead")
    expect(html).toContain("data-vacio")
  })

  it("el esqueleto tiene la misma cantidad de columnas que la tabla", () => {
    const cargando = tabla({ loading: true })
    expect(cargando).toContain("<thead")
    expect((cargando.match(/<th[ >]/g) ?? []).length).toBe(7)
    expect((cargando.match(/<td[ >]/g) ?? []).length).toBe(8 * 7)
    expect(cargando).toContain("animate-shimmer")
  })
})

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "auditoria", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de logs.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, y NUNCA sobre el esqueleto", () => {
    /*
     * Antes la barra vivía dentro del bloque `logs.length > 0`, que a su vez colgaba de
     * `!loading`. Al mover los estados adentro de la tabla esa protección desaparece con el
     * `return` temprano, así que la guarda pasa a ser explícita — es el caso que /areas ya pagó.
     */
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("!loading && !error && logs.length > 0 && (")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría la aserción de arriba.
    expect(sinComentarios("if (a && b) {}")).toContain("a && b")
  })

  it("🔴 `AuditFilters.tsx` ya no existe: sus cinco controles salen del primitivo", () => {
    // Cargaba una constante `FIELD_CLASS` byte-idéntica a la fórmula de altura del `size='sm'`
    // del `<Select>`, con un comentario que decía que eran "dos lugares con un solo valor". Ese
    // segundo lugar desapareció con el archivo.
    /* 🔑 SE MIRA EL CÓDIGO SIN COMENTARIOS: el docstring de la página EXPLICA que `AuditFilters`
       se borró, o sea que contiene el nombre. Un barrido por texto plano marcaría como culpable
       justo al archivo ya migrado — y el "arreglo" natural de ese falso positivo es borrar la
       explicación. Misma trampa que `paginacionTotales.test.ts` documenta. */
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).not.toContain("AuditFilters")
    expect(codigo).toContain("<FiltersBar campos={campos} panel")
    // Contracara: la prosa SÍ lo menciona, y eso es correcto.
    expect(readFileSync(PAGINA, "utf8")).toContain("AuditFilters")
  })
})
