/**
 * Recorrido visual: cada ruta × 2 temas (claro/oscuro) × 2 anchos (1440 y 390).
 * El backend es `mock-api.mjs` en :8000 y el front es `next dev` en :3000.
 *
 * 🔴 LAS CAPTURAS NO VAN AL REPO Y POR ESO LA SALIDA ES EL TEMP DEL SISTEMA. Son ~180 PNG, unos
 * 19 MB, con datos INVENTADOS por el mock. Un PNG de una pantalla que dice `$NaN` porque el
 * backend falso no tenía ese campo, versionado, es una captura que dentro de tres meses alguien
 * va a leer como el estado real del producto. Se miran y se tiran.
 * Para cambiar el destino: `SALIDA=D:\donde\sea node scripts/shots.mjs`.
 *
 * ⚠️ `playwright` NO es dependencia del repo, a propósito: son ~120 MB de navegador para una
 * herramienta que se usa una vez por tanda de diseño. Se instala AFUERA (ver README).
 */
import { mkdirSync } from "node:fs"
import { tmpdir } from "node:os"
import { join } from "node:path"

let chromium
try {
  ;({ chromium } = await import("playwright"))
} catch {
  console.error(
    "Falta playwright. NO lo instales en el repo: seguí frontend/scripts/README.md " +
      "(se instala en una carpeta aparte y se corre con NODE_PATH apuntando ahí).",
  )
  process.exit(1)
}

const BASE = process.env.BASE ?? "http://localhost:3000"
const RAIZ = process.env.SALIDA ?? join(tmpdir(), "recorrido-visual")
const OUT = join(RAIZ, "shots")
const ID = "00000000-0000-4000-8000-000000000001"

const RUTAS = [
  ["login", "/login"],
  ["cambiar-password", "/cambiar-password"],
  ["horas-publico", "/horas"],
  ["evaluacion-token", `/evaluacion/${ID}`],
  ["dashboard", "/dashboard"],
  ["empleados", "/empleados"],
  ["empleados-ficha", `/empleados/${ID}`],
  ["organigrama", "/organigrama"],
  ["vacantes", "/vacantes"],
  ["vacantes-ficha", `/vacantes/${ID}`],
  ["candidatos", "/candidatos"],
  ["perfiles-puesto", "/perfiles-puesto"],
  ["onboarding", "/onboarding"],
  ["onboarding-templates", "/onboarding/templates"],
  ["onboarding-template-ficha", `/onboarding/templates/${ID}`],
  ["proximos-ingresos", "/proximos-ingresos"],
  ["objetivos", "/objetivos"],
  ["evaluaciones", "/evaluaciones"],
  ["capacitaciones", "/capacitaciones"],
  ["ausencias", "/ausencias"],
  ["vacaciones", "/vacaciones"],
  ["recategorizaciones", "/recategorizaciones"],
  ["comunicacion", "/comunicacion"],
  ["offboarding", "/offboarding"],
  ["bajas", "/bajas"],
  ["empresas", "/empresas"],
  ["empresas-ficha", `/empresas/${ID}`],
  ["areas", "/areas"],
  ["usuarios", "/usuarios"],
  ["periodos", "/periodos"],
  ["configuracion", "/configuracion"],
  ["costos", "/costos"],
  ["proyectos", "/proyectos"],
  ["proyectos-ficha", `/proyectos/${ID}`],
  ["clientes", "/clientes"],
  ["horas-por-cliente", "/horas-por-cliente"],
  ["reportes", "/reportes"],
  ["auditoria", "/auditoria"],
  ["eventos", "/eventos"],
  ["equipo", "/equipo"],
  ["inventario", "/inventario"],
  ["procesos", "/procesos"],
  ["assessment", "/assessment"],
  ["assessment-ficha", `/assessment/${ID}`],
  ["sucesion", "/sucesion"],
]

const SESION = {
  access_token: "falso.para.el.recorrido.visual",
  refresh_token: "falso",
  user: {
    id: "00000000-0000-4000-8000-000000000070",
    email: "rrhh@karstec.com", username: "rrhh", rol: "admin_rrhh",
    nombre: "Ana", apellido: "Molina", must_change_password: false,
  },
}

const ANCHOS = [["1440", 1440, 900], ["390", 390, 844]]
const TEMAS = ["light", "dark"]

mkdirSync(OUT, { recursive: true })

const navegador = await chromium.launch()
const problemas = []

for (const [tema] of TEMAS.map((t) => [t])) {
  for (const [etiqueta, ancho, alto] of ANCHOS) {
    const ctx = await navegador.newContext({
      viewport: { width: ancho, height: alto },
      deviceScaleFactor: 1,
      colorScheme: tema,
      locale: "es-AR",
      timezoneId: "America/Argentina/Buenos_Aires",
    })
    await ctx.addInitScript(
      ([sesion, tema]) => {
        localStorage.setItem("session", sesion)
        localStorage.setItem("theme", tema)
        // El indicador de dev de Next se dibuja encima de la pantalla y ensucia toda captura.
        document.addEventListener("DOMContentLoaded", () => {
          const st = document.createElement("style")
          st.textContent = "nextjs-portal{display:none!important}"
          document.head.appendChild(st)
        })
      },
      [JSON.stringify(SESION), tema],
    )
    const page = await ctx.newPage()
    page.on("pageerror", (e) => problemas.push(`${tema}/${etiqueta} PAGEERROR ${e.message.split("\n")[0]}`))

    const anon = await navegador.newContext({
      viewport: { width: ancho, height: alto }, colorScheme: tema, locale: "es-AR",
    })
    await anon.addInitScript((t) => {
      localStorage.setItem("theme", t)
      document.addEventListener("DOMContentLoaded", () => {
        const st = document.createElement("style")
        st.textContent = "nextjs-portal{display:none!important}"
        document.head.appendChild(st)
      })
    }, tema)
    const anonPage = await anon.newPage()
    await anonPage.goto(BASE + "/login", { waitUntil: "networkidle", timeout: 60000 }).catch(() => {})
    await anonPage.waitForTimeout(900)
    await anonPage.screenshot({ path: `${OUT}/login__${tema}__${etiqueta}.png`, fullPage: true })
    await anon.close()

    for (const [nombre, ruta] of RUTAS) {
      if (nombre === "login") continue
      try {
        await page.goto(BASE + ruta, { waitUntil: "networkidle", timeout: 60000 })
      } catch {
        try { await page.waitForTimeout(1500) } catch { /* seguimos igual */ }
      }
      await page.waitForTimeout(900)
      const final = new URL(page.url()).pathname
      if (final !== ruta) problemas.push(`${tema}/${etiqueta} REDIRECT ${ruta} -> ${final}`)
      await page.screenshot({ path: `${OUT}/${nombre}__${tema}__${etiqueta}.png`, fullPage: true })
    }
    await ctx.close()
  }
}

await navegador.close()
console.log(problemas.join("\n") || "sin redirecciones ni errores de página")
