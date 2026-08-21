import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { CamposPerfilResponse } from "@/types/perfilPuesto"

import { PerfilFormCampos } from "./PerfilFormCampos"
import { armarPayload, indiceNotaRequisitos, valoresIniciales } from "./_perfilCampos"

/**
 * (a) y (b) del formulario de perfiles de puesto.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE (a) PUEDA FALLAR — ES TODO EL DISEÑO DEL ARCHIVO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * El catálogo de este test **NO son los 12 campos reales**: son cuatro campos INVENTADOS, con
 * labels y ayudas que no existen en ningún lado del producto (`Puesto inventado`, `zzz_extra`).
 * Esa es la única forma de que la aserción pueda fallar: un formulario que renderizara la lista
 * real escrita a mano pasaría cualquier test armado con la lista real —los labels coincidirían
 * por casualidad— y este falla en el acto, porque los campos que pide no están y los que dibuja
 * no los pidió nadie.
 *
 * Se verifican las TRES propiedades que "construirlo contra el endpoint" significa:
 *   1. aparecen los campos que el endpoint MANDÓ (aunque no existan en el modelo real);
 *   2. NO aparece un campo real que el endpoint NO mandó (si estuviera hardcodeado, aparecería);
 *   3. el ORDEN del markup es el del endpoint, no uno alfabético ni uno fijo.
 *
 * (b) compara POSICIONES en el HTML, no presencia: una nota que exista pero esté al final —o
 * metida en un tooltip— pasa cualquier `toContain` y falla acá.
 */

const NOTA = "Los avisos suelen poner todo junto bajo Requisitos. Acá va separado en cuatro."

/**
 * 🔑 CAMPOS INVENTADOS A PROPÓSITO (ver el encabezado). El único nombre real es `experiencia`, y
 * está porque es el que ABRE el bloque de requisitos: sin él, (b) no tendría contra qué medir
 * dónde va la nota. Todo lo demás —incluido un `select` con un vocabulario que el front no
 * conoce— es fauna que este test inventa.
 */
const CATALOGO: CamposPerfilResponse = {
  campos: [
    { campo: "nombre", label: "Puesto inventado", ayuda: "Ayuda del nombre inventada", tipo: "texto" },
    { campo: "zzz_extra", label: "Campo Zeta", ayuda: "Ayuda de la zeta", tipo: "textarea" },
    { campo: "experiencia", label: "Experiencia inventada", ayuda: "Ayuda de experiencia", tipo: "textarea" },
    { campo: "modalidad", label: "Modalidad inventada", ayuda: "Ayuda de modalidad", tipo: "select" },
  ],
  nota_requisitos: NOTA,
  modalidades: [{ value: "remoto", label: "Remoto inventado" }],
  tipos_contrato: [{ value: "efectivo", label: "Efectivo" }],
  niveles: [{ value: "senior", label: "Senior" }],
}

function form(valores: Record<string, string> = {}) {
  return renderToStaticMarkup(
    <PerfilFormCampos
      catalogos={CATALOGO}
      valores={valores}
      errores={{}}
      onChange={() => {}}
    />,
  )
}

describe("(a) el formulario se arma con los campos que devuelve /campos", () => {
  const html = form()

  it("dibuja los campos que mandó el endpoint, aunque no existan en el modelo real", () => {
    for (const label of ["Puesto inventado", "Campo Zeta", "Experiencia inventada", "Modalidad inventada"]) {
      expect(html, `falta el campo ${label}, que el endpoint mandó`).toContain(label)
    }
  })

  it("y también sus textos de ayuda, que son lo único que evita que se llenen mal", () => {
    // El backend es explícito: "NO HAY VALIDACIÓN QUE SUSTITUYA ESTO". Un formulario que
    // mostrara los labels y se comiera las ayudas dejaría el bloque de requisitos sin defensa.
    for (const ayuda of ["Ayuda del nombre inventada", "Ayuda de la zeta", "Ayuda de modalidad"]) {
      expect(html).toContain(ayuda)
    }
  })

  it("🔴 NO dibuja un campo real que el endpoint no mandó", () => {
    // Si la lista estuviera escrita en el front, estos aparecerían igual. Es la mitad del test
    // que caza el hardcodeo, y sin ella la de arriba pasa con las dos listas mezcladas.
    for (const ausente of ["Ofrecemos", "Jornada", "Formación académica", "Tipo de contrato"]) {
      expect(html, `apareció ${ausente}, que el endpoint NO mandó`).not.toContain(ausente)
    }
  })

  it("respeta el ORDEN del endpoint, que es el orden en que se llenan", () => {
    const pos = CATALOGO.campos.map((c) => html.indexOf(c.label))
    expect(pos.every((p) => p >= 0)).toBe(true)
    expect(pos).toEqual([...pos].sort((x, y) => x - y))
  })

  it("el select usa las etiquetas del vocabulario del endpoint, no un catálogo propio", () => {
    // Los `value` son los mismos `Literal` con los que valida Pydantic: una copia en el front
    // que derive ofrecería un valor que el backend rechaza con 422.
    expect(html).toContain('value="remoto"')
    expect(html).toContain("Remoto inventado")
  })

  it("un select cuyo vocabulario el front no conoce cae a campo de texto, no a un select vacío", () => {
    const raro: CamposPerfilResponse = {
      ...CATALOGO,
      campos: [{ campo: "zzz_nuevo", label: "Vocabulario nuevo", ayuda: "x", tipo: "select" }],
    }
    const html2 = renderToStaticMarkup(
      <PerfilFormCampos catalogos={raro} valores={{}} errores={{}} onChange={() => {}} />,
    )
    expect(html2).toContain("Vocabulario nuevo")
    expect(html2).not.toContain("<select")
    expect(html2).toContain("<input")
  })
})

describe("(b) nota_requisitos se renderiza ARRIBA del bloque", () => {
  const html = form()

  it("la nota está", () => {
    expect(html).toContain(NOTA)
  })

  it("🔴 y está ANTES del primer campo del bloque de requisitos", () => {
    // La posición es el punto entero: una nota puesta abajo se lee después de haber escrito, que
    // es cuando el bloque del aviso ya se pegó entero en un solo campo.
    expect(html.indexOf(NOTA)).toBeLessThan(html.indexOf("Experiencia inventada"))
  })

  it("pero DESPUÉS de los campos que no son del bloque: no está al principio de todo", () => {
    // Contracara: una nota puesta arriba de todo pasaría la aserción de arriba sin estar donde
    // corresponde, y encima se leería como un cartel general del formulario.
    expect(html.indexOf(NOTA)).toBeGreaterThan(html.indexOf("Campo Zeta"))
  })

  it("si ninguno de los campos del bloque llegara, la nota NO desaparece: va al principio", () => {
    // Una nota que se esfuma en silencio porque alguien renombró un campo es peor que una puesta
    // un poco más arriba de lo ideal.
    expect(indiceNotaRequisitos([
      { campo: "nombre", label: "N", ayuda: "a", tipo: "texto" },
    ])).toBe(0)
  })
})

describe("el body que se manda sale de los mismos campos", () => {
  it("un campo de texto vacío VIAJA: es la única forma de vaciar uno ya cargado", () => {
    // El service del backend arma el patch con `exclude_none`, así que `null` significa "no lo
    // toques". Omitir el texto vacío dejaría el contenido viejo guardado.
    const body = armarPayload({ nombre: "Analista", zzz_extra: "", experiencia: "" }, CATALOGO.campos)
    expect(body).toHaveProperty("zzz_extra", "")
    expect(body).toHaveProperty("experiencia", "")
  })

  it("🔴 un select vacío NO viaja: `\"\"` no pertenece a ningún Literal y saldría 422", () => {
    const body = armarPayload({ nombre: "Analista", modalidad: "" }, CATALOGO.campos)
    expect(body).not.toHaveProperty("modalidad")
  })

  it("y un select elegido sí", () => {
    const body = armarPayload({ nombre: "A", modalidad: "remoto" }, CATALOGO.campos)
    expect(body).toHaveProperty("modalidad", "remoto")
  })

  it("los valores iniciales salen de los campos del endpoint, con `null` traducido a vacío", () => {
    const valores = valoresIniciales(CATALOGO.campos)
    expect(Object.keys(valores).sort()).toEqual(["experiencia", "modalidad", "nombre", "zzz_extra"])
    expect(Object.values(valores).every((v) => v === "")).toBe(true)
  })
})
