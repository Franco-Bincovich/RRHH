import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { conRefresh } from "@/services/authRefresh"

/**
 * El interceptor de 401: cuándo desloguea y cuándo no.
 *
 * 🔴 ESTE ARCHIVO NO EXISTÍA. `services/authRefresh.ts` es el único lugar del front que puede
 * destruir una sesión sin que el usuario apriete nada, y no tenía UN SOLO test. Lo que costó:
 * el interceptor decidía por `res.status` a secas, así que **cualquier** 401 deslogueaba —
 * incluido el `GMAIL_TOKEN_EXPIRED` que /vacantes recibía al montar, en cada carga, porque la
 * casilla del sistema había perdido el acceso a Google. Un usuario perfectamente autenticado
 * terminaba en /login por una integración caída.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · Las respuestas son `Response` REALES con body JSON real, no un objeto `{status}`. Es la
 *     única forma de que el test pueda desmentir el `res.clone()`: un fake con un `.json()`
 *     reentrante aceptaría leer el body dos veces y el bug del stream consumido sería invisible.
 *     Por eso el caso 401-ajeno además LEE el body después de pasar por el interceptor.
 *   · `localStorage` y `window.location` son dobles observables, así que "deslogueó" se
 *     verifica por sus DOS efectos (sesión borrada + navegación), no por uno.
 *   · `fetch` está falseado y CUENTA las llamadas: el single-flight se mide contando refreshes,
 *     no confiando en que la promesa se comparta.
 *   · `construir` cuenta sus invocaciones: así "no reintentó" y "reintentó una vez" se
 *     distinguen, en vez de deducirse del resultado.
 */

const SESION = {
  access_token: "access-viejo",
  refresh_token: "refresh-viejo",
  user: {
    id: "u1", email: "a@b.c", username: "a", rol: "admin_rrhh" as const,
    nombre: "A", apellido: "B", must_change_password: false,
  },
}

class LocalStorageFalso {
  private datos = new Map<string, string>()
  getItem(k: string): string | null { return this.datos.get(k) ?? null }
  setItem(k: string, v: string): void { this.datos.set(k, v) }
  removeItem(k: string): void { this.datos.delete(k) }
  clear(): void { this.datos.clear() }
  key(): string | null { return null }
  get length(): number { return this.datos.size }
}

let almacen: LocalStorageFalso
let ventana: { location: { href: string } }
let refreshes: number

/** Una respuesta HTTP real, con el contrato de error del backend. */
function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status, headers: { "Content-Type": "application/json" },
  })
}

/** El body del backend ante un error: `middleware/error_handler.py:36-40`. */
function error(status: number, code: string, message = "algo pasó"): Response {
  return json(status, { error: true, message, code })
}

/** Un `construir` que devuelve las respuestas dadas, en orden, y cuenta sus invocaciones. */
function constructor(...respuestas: Response[]) {
  const fn = vi.fn(async () => respuestas[Math.min(fn.mock.calls.length - 1, respuestas.length - 1)])
  return fn
}

/** ¿Se destruyó la sesión? Los DOS efectos de `irALogin`, no uno. */
function deslogueo(): boolean {
  return almacen.getItem("session") === null && ventana.location.href === "/login"
}

/**
 * 🔴 EL INVARIANTE COMPLETO DE UN 401 AJENO: el interceptor no lo toca. No deslogueó, **no
 * gastó un refresh y no reintentó**.
 *
 * Las tres cosas juntas y no solo la primera, porque medido: con el criterio viejo
 * (`status === 401` a secas) un 401 ajeno igual terminaba SIN deslogueo —el reintento lo
 * salvaba— así que un test que solo mirara `deslogueo() === false` pasaba con el bug puesto.
 * Verificado por mutación al escribir este archivo: cuatro de estos casos sobrevivían.
 * Y "gastó un refresh" no es cosmético: el backend ROTA el refresh token en cada llamada
 * (`services/auth_service.py:84`), así que un refresh de más es un token invalidado de más.
 */
function sinTocarLaSesion(construir: { mock: { calls: unknown[] } }): boolean {
  return !deslogueo() && refreshes === 0 && construir.mock.calls.length === 1
}

beforeEach(() => {
  almacen = new LocalStorageFalso()
  almacen.setItem("session", JSON.stringify(SESION))
  ventana = { location: { href: "/vacantes" } }
  refreshes = 0
  vi.stubGlobal("localStorage", almacen)
  vi.stubGlobal("window", ventana)
  vi.stubGlobal("fetch", vi.fn(async () => {
    refreshes += 1
    return json(200, { access_token: "access-nuevo", refresh_token: "refresh-nuevo" })
  }))
})

afterEach(() => { vi.unstubAllGlobals() })

describe("un 401 de NUESTRA sesión desloguea", () => {
  it("SESION_EXPIRADA que sobrevive al reintento manda al login", async () => {
    const construir = constructor(error(401, "SESION_EXPIRADA", "Tu sesión venció por inactividad"))
    await conRefresh(construir)
    expect(refreshes).toBe(1)
    expect(construir).toHaveBeenCalledTimes(2) // el original y UN reintento
    expect(deslogueo()).toBe(true)
  })

  it("si el refresh falla, ni siquiera se reintenta", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { refreshes += 1; return json(401, { code: "INVALID_REFRESH_TOKEN" }) }))
    const construir = constructor(error(401, "INVALID_TOKEN"))
    await conRefresh(construir)
    expect(construir).toHaveBeenCalledTimes(1)
    expect(deslogueo()).toBe(true)
  })

  it("si el refresh anda y el reintento sale bien, NO desloguea", async () => {
    const construir = constructor(error(401, "SESION_EXPIRADA"), json(200, { items: [] }))
    const res = await conRefresh(construir)
    expect(res.status).toBe(200)
    expect(deslogueo()).toBe(false)
    expect(JSON.parse(almacen.getItem("session")!).access_token).toBe("access-nuevo")
  })
})

describe("🔴 un 401 AJENO a nuestra sesión NO desloguea", () => {
  it("GMAIL_TOKEN_EXPIRED —el bug de /vacantes— se devuelve tal cual, sin refrescar", async () => {
    const construir = constructor(error(401, "GMAIL_TOKEN_EXPIRED", "No se pudo renovar el token de Google"))
    const res = await conRefresh(construir)
    expect(res.status).toBe(401)
    expect(sinTocarLaSesion(construir)).toBe(true)
  })

  it("🔴 y el body sigue siendo legible después: el interceptor clona, no consume", async () => {
    // Sin `res.clone()` esto rompe, y con él rompería `toApiError` —que lee esta MISMA
    // Response un escalón más arriba— convirtiendo TODO error del backend en "Error del
    // servidor / UNKNOWN". El arreglo del logout se llevaría puestos todos los mensajes.
    const res = await conRefresh(constructor(error(401, "GMAIL_TOKEN_EXPIRED", "La casilla perdió el acceso")))
    expect(await res.json()).toMatchObject({ code: "GMAIL_TOKEN_EXPIRED", message: "La casilla perdió el acceso" })
  })

  it("INVALID_CREDENTIALS al cambiar la contraseña NO te echa", async () => {
    // `POST /api/usuarios/cambiar-password` pasa por el interceptor (no está en
    // RUTAS_SIN_REFRESH), y su 401 significa "escribiste mal tu contraseña ACTUAL".
    const construir = constructor(error(401, "INVALID_CREDENTIALS", "Contraseña actual incorrecta"))
    const res = await conRefresh(construir)
    expect(res.status).toBe(401)
    expect(sinTocarLaSesion(construir)).toBe(true)
  })

  it("un 403 sigue pasando derecho, como antes", async () => {
    const construir = constructor(error(403, "FORBIDDEN"))
    const res = await conRefresh(construir)
    expect(res.status).toBe(403)
    expect(sinTocarLaSesion(construir)).toBe(true)
  })
})

describe("🔴 un 401 que no se puede clasificar NO desloguea", () => {
  it("sin `code` en el body", async () => {
    const construir = constructor(json(401, { error: true, message: "No autorizado" }))
    await conRefresh(construir)
    expect(sinTocarLaSesion(construir)).toBe(true)
  })

  it("con un body que ni siquiera es JSON (un proxy, la protección de deployment)", async () => {
    const construir = constructor(new Response("<html>401</html>", {
      status: 401, headers: { "Content-Type": "text/html" },
    }))
    await conRefresh(construir)
    expect(sinTocarLaSesion(construir)).toBe(true)
  })

  it("con un `code` que este front no conoce", async () => {
    const construir = constructor(error(401, "CODE_QUE_NADIE_ESCRIBIO_TODAVIA"))
    await conRefresh(construir)
    expect(sinTocarLaSesion(construir)).toBe(true)
  })

  it("y tampoco si el 401 ajeno aparece recién EN EL REINTENTO", async () => {
    // El reintento se juzga con el mismo criterio que el original: el token nuevo es válido y
    // lo que falla es otra cosa.
    const construir = constructor(error(401, "SESION_EXPIRADA"), error(401, "GMAIL_TOKEN_EXPIRED"))
    await conRefresh(construir)
    expect(construir).toHaveBeenCalledTimes(2)
    expect(deslogueo()).toBe(false)
  })
})

describe("single-flight: N requests que dan 401 a la vez comparten UN refresh", () => {
  it("dos 401 concurrentes disparan un solo POST /api/auth/refresh", async () => {
    let soltar: () => void = () => {}
    const espera = new Promise<void>((r) => { soltar = r })
    vi.stubGlobal("fetch", vi.fn(async () => {
      refreshes += 1
      await espera
      return json(200, { access_token: "access-nuevo", refresh_token: "refresh-nuevo" })
    }))

    const a = conRefresh(constructor(error(401, "SESION_EXPIRADA"), json(200, { a: 1 })))
    const b = conRefresh(constructor(error(401, "SESION_EXPIRADA"), json(200, { b: 2 })))
    // Dejar drenar la cola de microtareas: los dos tienen que llegar al refresh ANTES de que
    // el primero resuelva, que es la única situación en la que el single-flight se ejerce.
    await new Promise((r) => setTimeout(r, 0))
    soltar()

    const [resA, resB] = await Promise.all([a, b])
    expect(refreshes).toBe(1)
    expect([resA.status, resB.status]).toEqual([200, 200])
    expect(deslogueo()).toBe(false)
  })
})
