/**
 * Las clases del panel del sidebar, con el porqué de las que no son obvias.
 *
 * Vive aparte por el mismo motivo que `components/ui/dialogClases.ts`: la decisión de superficie
 * y su explicación son más largas que el JSX que las usa, y metidas en el `cn()` empujaban
 * `Sidebar.tsx` sobre las 150 líneas de un componente.
 *
 * 🔴 VIDRIO EN EL SIDEBAR (`docs/SISTEMA-DE-DISENO.md` §2). §2 permite vidrio en DOS lugares
 * —el sidebar y los modales— y hasta el 23/8/2026 sólo lo tenían los modales: el sidebar era
 * opaco. Con el fondo de §2 detrás (las dos manchas de `app/globals.css`) el vidrio ahora tiene
 * algo que mostrar, que es la condición que §2 pone para usarlo: "comunica 'esto está adelante'
 * y hay algo detrás que importa".
 *
 * ⚠️ EL `bg-sidebar` OPACO QUEDA DE BASE y lo translúcido va bajo `supports-backdrop-filter:`,
 * igual que en `dialogClases.ts` y por el mismo motivo: sin soporte de `backdrop-filter`, un
 * fondo al 85% sin desenfoque no es vidrio — es el menú dejando pasar el texto de atrás.
 *
 * ⚠️ EL 85% ES ALTO A PROPÓSITO. El sidebar lleva texto sobre `--sidebar`, y
 * `app/contrasteTokens.test.ts` mide ese par SOBRE EL TOKEN, no sobre lo que queda al mezclarlo
 * con lo que hay detrás: o sea que ese test no puede ver esta decisión. Bajar el porcentaje
 * mueve el contraste real sin que nada rojee.
 */
export const CLASES_PANEL_SIDEBAR = [
  "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-sidebar ring-1 ring-sidebar-border transition-transform duration-200",
  "supports-backdrop-filter:bg-sidebar/85 supports-backdrop-filter:backdrop-blur-xl",
  "lg:relative lg:z-auto lg:translate-x-0",
].join(" ")
