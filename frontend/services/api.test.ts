import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, expect, it } from "vitest"

import { ApiError, toApiError } from "@/services/api"

/**
 * EL OTRO EXTREMO DEL CONTRATO DE ERRORES. La función REAL de `services/api.ts`, alimentada con
 * `Response` REALES cuyo cuerpo es el que el backend EMITE de verdad.
 *
 * 🔗 LOS CUERPOS NO ESTÁN ESCRITOS ACÁ: salen de `backend/tests/_contrato_errores.json`, que
 * genera `backend/tests/test_validacion_422.py` capturando respuestas reales del app.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS FALLEN?
 *
 * **1. 🔴 Los cuerpos tendrían que estar COPIADOS A MANO acá.** Es lo primero que se intentó, y
 * se midió que NO sirve: renombrando `message` a `mensaje` en el handler del backend, el backend
 * rojeaba y **este archivo seguía en verde**, porque comía su propia copia. Un test que se
 * alimenta de su propia constante afirma algo sobre sí mismo. Leyendo el archivo generado, un
 * cambio de contrato de UN solo lado rompe el OTRO, que es lo único que hace de esto un test de
 * contrato y no dos tests paralelos.
 *
 * **2. 🔴 `toApiError` tendría que estar REIMPLEMENTADA acá.** Es lo que hacía la versión previa
 * —copiaba `body.message ?? "Error del servidor"`— y por eso no podía fallar por la razón que
 * importa: la COPIA del test se corrige y el código de producción sigue roto. Se importa la
 * función real; para eso se la exportó.
 *
 * **3. 🔴 El input tendría que ser un objeto plano.** Se le pasa un `Response` de verdad. Con un
 * `{message, code}` suelto, un `toApiError` que dejara de hacer `await res.json()` —o que mirara
 * `res.ok`, o que leyera `res.status`— pasaría igual: el objeto plano esquiva justo la parte que
 * hace de puente entre HTTP y el front.
 *
 * **4. Faltaría el caso de body NO-JSON.** Sin él, un `toApiError` sin el `try/catch` pasaría
 * todos los demás y explotaría en producción ante un 502 con HTML del proxy — que es cuándo esa
 * rama corre de verdad. Ese caso NO viene del archivo: no lo produce el backend, lo produce un
 * proxy, así que construirlo acá es lo correcto.
 *
 * ⚠️ ORDEN DE EJECUCIÓN: el archivo lo regenera la suite de backend. Si alguien cambia el
 * handler y corre SOLO vitest, ve verde hasta que corra pytest. Es la limitación conocida de
 * cualquier contrato generado; a cambio, no hay forma de que las dos puntas se separen en
 * silencio para siempre.
 */

const CONTRATO: Record<string, { error: boolean; message: string; code: string }> =
  JSON.parse(readFileSync(
    resolve(__dirname, "../../backend/tests/_contrato_errores.json"), "utf-8"))

/** Response real, como la que devuelve `fetch`. */
function respuesta(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  })
}

const CONTRATO_422_BODY = CONTRATO["422_body"]
const CONTRATO_422_QUERY = CONTRATO["422_query"]
const CONTRATO_401 = CONTRATO["401_control"]

describe("el contrato publicado por el backend está entero", () => {
  it("guarda: si el archivo no se generó, todo lo de abajo sería vacuo", () => {
    for (const clave of ["422_body", "422_query", "401_control"]) {
      expect(CONTRATO[clave], `falta ${clave} en _contrato_errores.json`).toBeTruthy()
    }
  })
})

describe("toApiError contra el contrato real del backend", () => {
  it("🔴 422 de BODY: conserva el mensaje y el code, no cae al genérico", async () => {
    const e = await toApiError(respuesta(CONTRATO_422_BODY, 422))

    expect(e).toBeInstanceOf(ApiError)
    expect(e.message).toBe("Revisá los datos del formulario: empresa (falta).")
    expect(e.code).toBe("VALIDACION_INVALIDA")
    expect(e.status).toBe(422)
    // Lo que pasaba ANTES del handler: el `{"detail": [...]}` de Pydantic caía acá.
    expect(e.message).not.toBe("Error del servidor")
    expect(e.code).not.toBe("UNKNOWN")
  })

  it("🔴 422 de QUERY: llega el mensaje que no nombra el campo", async () => {
    const e = await toApiError(respuesta(CONTRATO_422_QUERY, 422))

    expect(e.message).toBe("No se pudo completar el pedido. Actualizá la pantalla y volvé a intentar.")
    expect(e.code).toBe("PEDIDO_INVALIDO")
    expect(e.status).toBe(422)
    // El caso `page_size=200`: el usuario no tiene ningún "page size" que corregir.
    expect(e.message).not.toContain("page")
  })

  it("los dos 422 son distinguibles por code", async () => {
    const body = await toApiError(respuesta(CONTRATO_422_BODY, 422))
    const query = await toApiError(respuesta(CONTRATO_422_QUERY, 422))
    expect(body.code).not.toBe(query.code)
  })

  it("401 de AppError: el control, que ya funcionaba antes de este arreglo", async () => {
    const e = await toApiError(respuesta(CONTRATO_401, 401))
    expect(e.message).toBe(CONTRATO_401.message)
    expect(e.code).toBe(CONTRATO_401.code)
    expect(e.status).toBe(401)
    expect(e.message).not.toBe("Error del servidor")
  })

  it("body no-JSON: cae al genérico sin explotar", async () => {
    // Un 502 con HTML del proxy no tiene body JSON. `res.json()` tira y el catch lo cubre.
    const res = new Response("<html>502 Bad Gateway</html>", {
      status: 502, headers: { "content-type": "text/html" },
    })
    const e = await toApiError(res)

    expect(e).toBeInstanceOf(ApiError)
    expect(e.message).toBe("Error del servidor")
    expect(e.code).toBe("UNKNOWN")
    expect(e.status).toBe(502)
  })

  it("422 con JSON válido pero sin las claves del contrato: genérico", async () => {
    // Es EXACTAMENTE lo que devolvía FastAPI antes del handler. Que siga cayendo al genérico es
    // correcto — lo que se arregló es que el backend ya no manda esto.
    const e = await toApiError(respuesta(
      { detail: [{ type: "uuid_parsing", loc: ["body", "empresa_id"] }] }, 422))
    expect(e.message).toBe("Error del servidor")
    expect(e.code).toBe("UNKNOWN")
  })
})
