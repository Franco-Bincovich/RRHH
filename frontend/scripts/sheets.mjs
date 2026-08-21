/**
 * Arma una HOJA DE CONTACTO por ruta: 1440 claro/oscuro arriba, 390 claro/oscuro abajo, en una
 * sola imagen. Es lo que se mira y lo que se manda: 45 archivos en vez de 180, y con los dos
 * temas al lado uno del otro, que es donde se ven las diferencias.
 *
 * Corre DESPUÉS de `shots.mjs` y lee su salida. Mismo criterio: nada de esto va al repo.
 */
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { join, resolve } from "node:path"

let chromium
try {
  ;({ chromium } = await import("playwright"))
} catch {
  console.error("Falta playwright. Ver frontend/scripts/README.md.")
  process.exit(1)
}

const RAIZ = process.env.SALIDA ?? join(tmpdir(), "recorrido-visual")
const DIR = resolve(RAIZ, "shots")
const OUT = resolve(RAIZ, "sheets")
mkdirSync(OUT, { recursive: true })

const nombres = [...new Set(readdirSync(DIR).map((f) => f.split("__")[0]))].sort()
const b = await chromium.launch()
const ctx = await b.newContext({ viewport: { width: 1500, height: 800 }, deviceScaleFactor: 1 })
const page = await ctx.newPage()

for (const n of nombres) {
  const url = (t, w) => `file:///${DIR.replace(/\\/g, "/")}/${n}__${t}__${w}.png`
  const html = `<!doctype html><meta charset="utf-8">
  <style>
    body{margin:0;background:#6b7280;font:13px/1.4 system-ui,sans-serif;color:#fff}
    h1{margin:0;padding:10px 14px;background:#111827;font-size:16px}
    .fila{display:flex;gap:10px;padding:10px}
    .caja{flex:1;min-width:0}
    .caja.mob{flex:0 0 420px}
    .cap{padding:3px 6px;background:#111827;font-weight:600}
    img{display:block;width:100%;background:#fff;border:1px solid #111827}
  </style>
  <h1>${n}</h1>
  <div class="fila">
    <div class="caja"><div class="cap">1440 · claro</div><img src="${url("light", "1440")}"></div>
    <div class="caja"><div class="cap">1440 · oscuro</div><img src="${url("dark", "1440")}"></div>
  </div>
  <div class="fila">
    <div class="caja mob"><div class="cap">390 · claro</div><img src="${url("light", "390")}"></div>
    <div class="caja mob"><div class="cap">390 · oscuro</div><img src="${url("dark", "390")}"></div>
    <div class="caja"></div>
  </div>`
  // El andamio HTML se borra: lo único que queda en la carpeta son las 45 hojas.
  const tmp = resolve(OUT, `_${n}.html`)
  writeFileSync(tmp, html, "utf-8")
  await page.goto(`file:///${tmp.replace(/\\/g, "/")}`)
  await page.waitForTimeout(250)
  await page.screenshot({ path: resolve(OUT, `${n}.png`), fullPage: true })
  rmSync(tmp, { force: true })
}
await b.close()
console.log(`${nombres.length} hojas`)
