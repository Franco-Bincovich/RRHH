/**
 * EL NOMBRE DE LA PLATAFORMA, EN UN SOLO LUGAR.
 *
 * 🔴 POR QUÉ EXISTE (bloque N9, 25/8/2026). El nombre va a cambiar y todavía no está confirmado.
 * Hasta hoy "HR Karstec" estaba escrito literal en SEIS archivos del front —el título del
 * navegador, el sidebar, la pantalla de login, el pie de la evaluación pública y tres lugares del
 * panel de IA— más dos del backend. Cambiarlo era buscar y reemplazar sobre un literal corto en un
 * repo que además lo menciona en decenas de comentarios y en datos de prueba: la clase de
 * operación en la que se cambia de más o de menos y nadie se entera hasta que un usuario lo ve.
 *
 * ⚠️ NO SE CAMBIÓ NADA: el default es exactamente el nombre de hoy. Esto deja el cambio en UNA
 * variable de entorno.
 *
 * 🔴 `NEXT_PUBLIC_` Y POR LO TANTO **BUILD-TIME**, no runtime. Next inlinea estas variables al
 * compilar, así que cambiar el valor en Vercel **exige un redeploy del front** — igual que
 * `NEXT_PUBLIC_API_URL`, que ya funciona así. No es una limitación evitable: el nombre se
 * renderiza también en componentes de servidor (el `metadata` del layout) y en el prerender
 * estático, así que no hay un momento "de runtime" común a todos los usos.
 *
 * ⚠️ EL DOMINIO NO ESTÁ ACÁ Y NO PUEDE ESTARLO: `hrkarstec.site` es una compra de dominio y una
 * configuración de DNS, no un string del código. Cambiarlo es comprar otro, apuntarlo, sumarlo a
 * `ALLOWED_ORIGINS` del backend y reemitir el certificado. Lo mismo con los datos que ya están en
 * la base (nombres de empresa, plantillas de mail que escribió Capital Humano, el template de
 * onboarding de la migración 027) y con las migraciones ya corridas, que son historia y no se
 * reescriben.
 */
export const MARCA = process.env.NEXT_PUBLIC_MARCA || "HR Karstec"
