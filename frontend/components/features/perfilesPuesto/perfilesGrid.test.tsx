import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { ChipFiltro } from "@/components/ui/filtrosChips"
import type { CamposPerfilResponse, PerfilPuesto } from "@/types/perfilPuesto"

import { PerfilCard } from "./PerfilCard"
import { PerfilesGrid } from "./PerfilesGrid"

/**
 * (d) el vacío y (e) los cuatro campos de la tarjeta.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * (d) el perfil del padrón NO se usa en este bloque: se renderiza con `perfiles: []`, que es el
 * estado REAL de producción (0 filas). Los dos casos —sin filtros y con `search`— son textos
 * distintos que salen del MISMO helper (`textoVacio`), así que un componente que escribiera un
 * "No hay resultados" fijo falla en los dos.
 *
 * (e) el padrón trae un perfil con los 12 campos LLENOS, incluidos los ocho que la tarjeta NO
 * tiene que mostrar. Con un perfil a medias, una tarjeta que volcara `requisitos` o `ofrecemos`
 * pasaría en verde por no tener qué volcar — que es exactamente el falso verde que §7 del sistema
 * de diseño existe para evitar ("lo que el equipo ve, lo da por hecho").
 */

const CATALOGOS: CamposPerfilResponse = {
  campos: [],
  nota_requisitos: "",
  modalidades: [{ value: "hibrido", label: "Híbrido" }],
  tipos_contrato: [{ value: "efectivo", label: "Efectivo" }],
  niveles: [{ value: "semi_senior", label: "Semi Senior" }],
}

/** 🔑 LOS DOCE CAMPOS LLENOS, con textos reconocibles uno por uno (ver el encabezado). */
const PERFIL: PerfilPuesto = {
  id: "p-1",
  nombre: "Analista SQL",
  descripcion: "Resumen del puesto para el aviso.",
  funciones: "FUNCIONES-QUE-NO-VAN",
  experiencia: "EXPERIENCIA-QUE-NO-VA",
  formacion: "FORMACION-QUE-NO-VA",
  conocimientos_tecnicos: "CONOCIMIENTOS-QUE-NO-VAN",
  requisitos: "REQUISITOS-QUE-NO-VAN",
  ofrecemos: "OFRECEMOS-QUE-NO-VA",
  modalidad: "hibrido",
  tipo_contrato: "efectivo",
  nivel: "semi_senior",
  jornada: "JORNADA-QUE-NO-VA",
  activo: true,
  created_by: null,
  created_at: "2026-08-20T10:00:00Z",
  updated_at: null,
}

const chip = (etiqueta: string, valor: string): ChipFiltro => ({
  clave: etiqueta, etiqueta, valor, quitar: () => {},
})

function grilla(props: Partial<Parameters<typeof PerfilesGrid>[0]> = {}) {
  return renderToStaticMarkup(
    <PerfilesGrid
      perfiles={[]} catalogos={CATALOGOS} loading={false} error={null} canWrite
      chips={[]} onRetry={() => {}} onEdit={() => {}} onBaja={() => {}} onReactivar={() => {}}
      {...props}
    />,
  )
}

function tarjeta(perfil: PerfilPuesto = PERFIL, canWrite = true) {
  return renderToStaticMarkup(
    <PerfilCard
      perfil={perfil} catalogos={CATALOGOS} canWrite={canWrite}
      onEdit={() => {}} onBaja={() => {}} onReactivar={() => {}}
    />,
  )
}

describe("(d) el vacío", () => {
  it("sin filtros dice que TODAVÍA no hay, que es el estado real de producción", () => {
    // Con 0 filas cargadas, "ningún resultado" mandaría a revisar filtros que nadie puso.
    const html = grilla()
    expect(html).toContain("Todavía no hay perfiles de puesto")
    expect(html).toContain("Cuando se cargue el primero va a aparecer acá.")
  })

  it("y ofrece cargar el primero, sin ningún filtro que quitar", () => {
    const html = grilla({ accionVacio: <button>Cargar el primero</button> })
    expect(html).toContain("Cargar el primero")
    expect(html).not.toContain("Quitar")
  })

  it("🔴 con una búsqueda puesta, el vacío DICE EL TÉRMINO BUSCADO", () => {
    // Es la diferencia entre "no hay resultados" —verdadero e inútil— y la respuesta a la
    // pregunta que trajo al usuario hasta acá.
    const html = grilla({ chips: [chip("Nombre", "analista")] })
    expect(html).toContain("analista")
    expect(html).toContain("No hay perfiles de puesto con nombre analista.")
  })

  it("y ofrece quitar ese filtro, en vez de limpiarlo solo", () => {
    const html = grilla({ chips: [chip("Nombre", "analista")] })
    expect(html).toContain("Quitar nombre: analista")
  })

  it("sin sujeto: el catálogo es del grupo, no hay empresa que nombrar", () => {
    // La frase con sujeto es "Bodegas Tupungato no tiene…", y acá ninguna empresa acota nada.
    const html = grilla({ chips: [chip("Nombre", "analista")] })
    expect(html).not.toContain("no tiene perfiles de puesto")
  })
})

describe("(e) la tarjeta muestra los cuatro campos de §5 y ninguno más", () => {
  const html = tarjeta()

  it("los cuatro: nombre, nivel, modalidad y resumen", () => {
    expect(html).toContain("Analista SQL")
    expect(html).toContain("Semi Senior")   // el nivel, con la ETIQUETA del catálogo
    expect(html).toContain("Híbrido")       // la modalidad, idem
    expect(html).toContain("Resumen del puesto para el aviso.")
  })

  it("🔴 y NINGUNO de los otros ocho campos, aunque el perfil los traiga llenos", () => {
    for (const ausente of [
      "FUNCIONES-QUE-NO-VAN", "EXPERIENCIA-QUE-NO-VA", "FORMACION-QUE-NO-VA",
      "CONOCIMIENTOS-QUE-NO-VAN", "REQUISITOS-QUE-NO-VAN", "OFRECEMOS-QUE-NO-VA",
      "JORNADA-QUE-NO-VA", "Efectivo",
    ]) {
      expect(html, `la tarjeta volcó ${ausente}`).not.toContain(ausente)
    }
  })

  it("🔴 ni competencias, ni ubicación, ni contador de ocupantes o vacantes (§7)", () => {
    // Las tres las inventó un prototipo y no están en el modelo. No se agregan ni como "0": un
    // "0 vacantes" se lee como una afirmación que el sistema no puede hacer.
    for (const inventado of ["ompetencia", "bicación", "bicacion", "acante", "cupante"]) {
      expect(html, `apareció «${inventado}», que no existe en el modelo`).not.toContain(inventado)
    }
  })

  it("usa el valor crudo si el catálogo de etiquetas no llegó, en vez de dejar el nivel en blanco", () => {
    const html2 = renderToStaticMarkup(
      <PerfilCard perfil={PERFIL} catalogos={null} canWrite={false}
                  onEdit={() => {}} onBaja={() => {}} onReactivar={() => {}} />,
    )
    expect(html2).toContain("semi_senior")
  })

  it("un perfil sin descripción lo dice, no deja el hueco", () => {
    expect(tarjeta({ ...PERFIL, descripcion: null })).toContain("Sin descripción.")
  })
})

describe("la baja lógica se ve y se puede deshacer", () => {
  it("un perfil dado de baja se marca: sin el chip, 'Ver bajas' sumaría tarjetas indistinguibles", () => {
    const html = tarjeta({ ...PERFIL, activo: false })
    expect(html).toContain("Baja")
    expect(html).toContain("Reactivar")
    expect(html).not.toContain("Dar de baja")
  })

  it("y un perfil activo NO lleva ese chip: es el quinto dato solo cuando dice algo", () => {
    expect(tarjeta()).not.toContain(">Baja<")
    expect(tarjeta()).toContain("Dar de baja")
  })

  it("sin permiso de escritura no hay acciones que terminen en 403", () => {
    const html = tarjeta(PERFIL, false)
    expect(html).not.toContain("Dar de baja")
    expect(html).not.toContain("Editar")
    expect(html).toContain("Analista SQL")
  })
})
