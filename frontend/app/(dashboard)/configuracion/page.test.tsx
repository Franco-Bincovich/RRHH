import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"

/**
 * /configuracion mezcla bloques con tres dueños distintos: reglas de negocio, credenciales
 * por usuario, y la identidad de uno mismo. El gate va POR BLOQUE, con DOS criterios:
 *
 *   integraciones            → se OCULTAN sin permiso de escritura (no hay nada que leer).
 *   reglas / tipos ausencia  → se muestran en SOLO LECTURA (el valor SÍ es información).
 *   contraseña / perfil      → visibles para todos, siempre.
 *
 * Antes de esto, gerencia_lectura veía los formularios de API key y recibía 403 al guardar.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * NO se mockea `puede`: corre el de verdad, y lo único falseado es la SESIÓN. Con un `puede`
 * mockeado a un único booleano, "lee pero no escribe" sería imposible de distinguir de "no
 * puede nada" y los dos criterios de gate colapsarían en uno. Acá cada rol recorre la lógica
 * real de permisos, así que mover una sección de sección, cambiar READ por WRITE o borrar un
 * gate cambia el markup y rojea.
 *
 * El gate es un `if` de RENDER, no un efecto — por eso se ve en el markup. Se renderiza a
 * string con react-dom/server porque el proyecto corre vitest SIN jsdom; alcanza, porque lo
 * que se verifica es qué sale y qué no, y los efectos (los fetch) no corren.
 */

const sesion = vi.fn()
vi.mock("@/services/api", () => ({ getSession: () => sesion() }))
vi.mock("next/navigation", () => ({
  usePathname: () => "/configuracion",
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}))
vi.mock("@/services/integraciones", () => ({
  fetchIntegraciones: vi.fn(() => new Promise(() => {})),
  getGoogleAuthUrl: vi.fn(),
  saveAnthropicKey: vi.fn(),
  saveZernioKey: vi.fn(),
  disconnectIntegracion: vi.fn(),
}))
vi.mock("@/services/configuracion", () => ({
  fetchConfiguracion: vi.fn(() => new Promise(() => {})),
  guardarParametros: vi.fn(),
  guardarEscala: vi.fn(),
}))
vi.mock("@/services/ausencias", () => ({
  fetchTiposAusencia: vi.fn(() => new Promise(() => {})),
  createTipoAusencia: vi.fn(),
  updateTipoAusencia: vi.fn(),
}))
vi.mock("@/services/auth", () => ({ logout: vi.fn() }))

const ConfiguracionPage = (await import("@/app/(dashboard)/configuracion/page")).default

afterEach(() => sesion.mockReset())

function render(rol: string | null): string {
  sesion.mockReturnValue(rol ? { user: { rol } } : null)
  return renderToStaticMarkup(<ConfiguracionPage />)
}

/*
 * ALCANCE DE ESTE ARCHIVO: qué BLOQUES aparecen para cada rol.
 *
 * Lo de adentro de cada bloque no se puede mirar acá: el contenido de las reglas llega por
 * fetch y, sin jsdom, los efectos no corren — las secciones se quedan en su estado de carga
 * para siempre. Que un bloque sea EDITABLE o de SOLO LECTURA se verifica un escalón más
 * abajo, en VacacionesReglas.test.tsx, que recibe los datos por props.
 */

describe("admin_rrhh", () => {
  it("ve todos los bloques", () => {
    const html = render("admin_rrhh")
    expect(html).toContain("Zernio")
    expect(html).toContain("Vacaciones")
    expect(html).toContain("Ausentismo")
    expect(html).toContain("Tipos de ausencia")
    expect(html).toContain("Cambiar contraseña")
  })
})

describe("gerencia_lectura", () => {
  it("NO ve las integraciones: son formularios de escritura y no hay nada que leer", () => {
    const html = render("gerencia_lectura")
    expect(html).not.toContain("Zernio")
    expect(html).not.toContain("Anthropic")
    expect(html).not.toContain("Google / Gmail")
  })

  it("SÍ ve las reglas, porque el valor es información", () => {
    // Tiene lectura sobre todos los reportes: ocultarle con qué reglas se calcularon lo
    // dejaría sin poder explicar un solo número.
    const html = render("gerencia_lectura")
    expect(html).toContain("Vacaciones")
    expect(html).toContain("Tipos de ausencia")
  })

  it("y sí puede cambiar su contraseña", () => {
    expect(render("gerencia_lectura")).toContain("Cambiar contraseña")
  })
})

describe("mandos_medios", () => {
  it("no accede a la configuración: ni las reglas ni los tipos de ausencia", () => {
    // 🔴 Este es el motivo de que CONFIGURACION sea una sección propia. mandos_medios tiene
    // WRITE en VACACIONES y AUSENCIAS; si las reglas colgaran de cualquiera de esas dos,
    // podría cambiar la escala de toda la empresa desde donde carga una licencia.
    const html = render("mandos_medios")
    expect(html).not.toContain("Escala por antigüedad")
    expect(html).not.toContain("Tipos de ausencia")
    expect(html).not.toContain("Base de días hábiles")
  })

  it("tampoco a las integraciones", () => {
    expect(render("mandos_medios")).not.toContain("Zernio")
  })

  it("pero sí cambia su contraseña y ve su perfil", () => {
    const html = render("mandos_medios")
    expect(html).toContain("Cambiar contraseña")
    expect(html).toContain("Mi perfil")
  })
})

describe("fail-closed", () => {
  it("sin sesión no se renderiza ningún bloque de configuración", () => {
    const html = render(null)
    expect(html).not.toContain("Zernio")
    expect(html).not.toContain("Tipos de ausencia")
  })

  it("un rol desconocido tampoco", () => {
    expect(render("rol_inventado")).not.toContain("Tipos de ausencia")
  })

  it("pero el cierre de sesión sigue disponible: si no, quedaría encerrado", () => {
    expect(render("rol_inventado")).toContain("Cerrar sesión")
  })
})
