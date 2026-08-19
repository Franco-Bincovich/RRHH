"use client"

/*
 * ─── 🔴 LOS COLORES DE ESTE ARCHIVO SON UNA COPIA MANUAL DE `app/paleta.css` ──────────────────
 *
 * **Si cambia la paleta, HAY QUE TOCAR ESTE ARCHIVO TAMBIÉN.** No hay ninguna herramienta que lo
 * avise: no es CSS, son literales dentro de `style={{}}`, y ni el barrido de contraste
 * (`app/contrasteTokens.test.ts`, que solo lee `paleta.css`) ni Tailwind los ven.
 *
 * POR QUÉ NO PUEDE LEER LOS TOKENS. `global-error` **reemplaza al root layout**: define su propio
 * `<html>` y `<body>`, no monta `app/layout.tsx` y por lo tanto **no importa `globals.css`** ni
 * queda dentro del `ThemeProvider`. Es el boundary que se dibuja cuando la aplicación no pudo
 * cargar, así que depender de la hoja de estilos sería depender justo de lo que puede haber
 * fallado. Por eso los valores van a mano, y por eso esta nota existe.
 *
 * LOS CINCO VALORES Y SU TOKEN DE ORIGEN — modo CLARO de `docs/SISTEMA-DE-DISENO.md` §1:
 *   #F5F7FA  ← `--background`         (fondo de la página)
 *   #0E1726  ← `--foreground`         (texto principal)
 *   #59657A  ← `--muted-foreground`   (texto secundario)
 *   #1B4FD8  ← `--primary`            (fondo del botón)
 *   #FFFFFF  ← `--primary-foreground` (texto del botón)
 * Y el radio de 10px es `--radius` (0.625rem), el mismo que `rounded-lg` en el resto del producto.
 *
 * ⚠️ ESTA PANTALLA ES SIEMPRE CLARA, incluso para alguien que tiene el producto en oscuro: sin
 * `ThemeProvider` no hay clase `.dark` que aplicar. Es la conducta anterior y se mantiene. Si
 * alguna vez molesta, la salida es un `<style>` inline con `@media (prefers-color-scheme: dark)`
 * y los valores del bloque oscuro — pero eso duplica cinco valores más, así que se decide, no se
 * agrega de paso.
 *
 * Los valores anteriores, para que se reconozca el cambio en un diff viejo: #F8FAFC, #0F172A,
 * #64748B, #1A56DB (el azul de marca previo) y #FFFFFF.
 */

export default function GlobalError({
  unstable_retry,
}: {
  error: Error & { digest?: string }
  unstable_retry: () => void
}) {
  return (
    // global-error reemplaza el root layout: define su propio <html> y <body>
    // y no hereda el ThemeProvider, por eso usa estilos inline autocontenidos.
    <html lang="es">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "Inter, system-ui, -apple-system, sans-serif",
          background: "#F5F7FA",
          color: "#0E1726",
        }}
      >
        <div style={{ maxWidth: "28rem", padding: "1rem", textAlign: "center" }}>
          <h1 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 600 }}>
            Error crítico
          </h1>
          <p style={{ marginTop: "0.5rem", fontSize: "0.875rem", color: "#59657A" }}>
            Ocurrió un error que impidió cargar la aplicación.
          </p>
          <button
            onClick={() => unstable_retry()}
            style={{
              marginTop: "1.5rem",
              minHeight: "44px",
              padding: "0 1.5rem",
              border: "none",
              borderRadius: "10px",
              background: "#1B4FD8",
              color: "#FFFFFF",
              fontSize: "0.875rem",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Recargar
          </button>
        </div>
      </body>
    </html>
  )
}
