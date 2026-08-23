import { puede, seccionDeRuta } from "@/services/permisos"
import type { UserRol } from "@/types/auth"

/**
 * A dónde lleva cada KPI del dashboard, y quién puede llegar.
 *
 * Los diez KPIs eran informativos: un número y su explicación, sin salida. Ahora cada uno lleva a
 * la pantalla de donde SALE el dato, con el filtro puesto donde la pantalla sabe leerlo.
 *
 * 🔴 EL PERMISO SE RESUELVE CON EL MISMO PAR QUE USA EL AuthGuard —`seccionDeRuta(ruta)` +
 * `puede(rol, seccion, "read")`— Y ESO ES TODO EL DISEÑO DE ESTE ARCHIVO. No hay una segunda
 * tabla de "qué sección gatea a qué card": la sección sale de la RUTA, leída del mismo
 * `RUTA_SECCION` que `components/layout/AuthGuard.tsx:33` consulta para decidir si rebota. Así un
 * link que el guard rebotaría no se puede escribir: para que aparezca, `puede()` tuvo que
 * devolver `true` sobre exactamente la sección que el guard va a mirar un instante después.
 * Es la regla que ya se aplicó en /equipo y /usuarios — un link que rebota es peor que ninguno.
 *
 * ⚠️ Y por eso `destino()` CORTA LA QUERYSTRING antes de preguntar. `seccionDeRuta` parte por "/"
 * y se queda con el primer segmento: sin el corte, "empleados?estado=activo" no matchea ninguna
 * clave de `RUTA_SECCION`, la función devuelve `null` —que ahí significa "ruta no gateada, pasá"—
 * y la card linkearía SIN chequear nada, que es el bug exacto que este archivo viene a impedir.
 * El AuthGuard no tiene el problema porque `usePathname()` ya viene sin query.
 */

/**
 * KPI → ruta. La clave es el `title` de la card, que es lo que se ve en pantalla.
 *
 * 🔴 UN TÍTULO QUE NO ESTÁ ACÁ ES UNA CARD SIN DESTINO, y eso es una decisión declarada, no un
 * olvido: `_destinosKpi.test.ts` compara este mapa contra los títulos reales de `bloquesKpi()` en
 * LAS DOS DIRECCIONES, así que un KPI nuevo sin destino tiene que declararse en `SIN_DESTINO` con
 * su razón, y una clave de acá que deje de existir como card rojea en vez de quedar muerta.
 *
 * ⚠️ EL FILTRO EN LA URL SOLO VA DONDE LA PANTALLA LO SABE LEER. Hoy la única que siembra sus
 * filtros desde la querystring es `/empleados` (`useFiltrosEmpleados` → `useSearchParams`), así
 * que es la única con `?`. `/ausencias`, `/recategorizaciones`, `/bajas` y `/reportes` reciben la
 * ruta pelada: agregarles un `?fecha_desde=...` las dejaría exactamente igual que sin él, con la
 * diferencia de que la URL AFIRMARÍA un recorte que la pantalla no hizo. El día que alguna
 * siembre —se copia la barrera de Suspense de `/empleados`— el filtro se agrega acá y en ningún
 * otro lado.
 */
export const DESTINOS: Readonly<Record<string, string>> = {
  // El KPI cuenta `estado = activo`; el listado arranca con ese mismo filtro puesto, así que el
  // número de la card y las filas de la pantalla dicen lo mismo. Mismo criterio que el
  // `href_listado` de las alertas agregadas (backend/services/_dashboard_alertas_catalogo.py).
  "Colaboradores activos": "/empleados?estado=activo",
  "Búsquedas abiertas": "/vacantes",
  // Los que todavía no entraron son legajos en `preingreso`, y esa pantalla ES esa lista: no
  // necesita filtro porque no muestra otra cosa.
  "Ingresos próximos 30 días": "/proximos-ingresos",
  "Ausencias en curso": "/ausencias",
  "Recategorizaciones del mes": "/recategorizaciones",
  // La rotación se cuenta por `empleados.fecha_egreso`, y /bajas es la lista de esas personas.
  // (El reporte R6 las cuenta por `offboarding_instancias`, que es otro criterio — ver la deuda
  // declarada en CLAUDE.md. Se linkea al que comparte criterio con el número de la card.)
  "Rotación 12 meses": "/bajas",
  "Masa salarial del mes": "/costos",
  // Al CATÁLOGO de reportes, no al reporte de ausentismo ya generado: /reportes no siembra nada
  // de la querystring, así que un `?reporte=ausentismo` sería una URL que promete un recorte
  // inexistente. Deep-linkear un reporte concreto es su propia tanda (ver el reporte de sesión).
  "Ausentismo del mes": "/reportes",
  // El promedio se calcula sobre la dotación ACTIVA, que es exactamente el universo al que este
  // filtro lleva. ⚠️ El listado no tiene columna "Ingreso" —la fecha vive en cada ficha—, así
  // que esto lleva a la POBLACIÓN del número, no al cálculo. Es lo más cerca que hay hoy.
  "Antigüedad promedio": "/empleados?estado=activo",
}

/**
 * Los KPIs SIN destino, con su razón. Declarar es obligatorio: el barrido no deja que una card
 * quede sin link por descuido, solo por decisión.
 */
export const SIN_DESTINO: Readonly<Record<string, string>> = {
  "Headcount por empresa":
    "No hay pantalla que conteste lo que la card ya contesta. El reparto por sociedad está " +
    "ADENTRO de la card (`detalle`), /empresas lista nombre/CUIT/email/estado y no muestra " +
    "ningún headcount, y el corte por empresa del padrón NO es un filtro de URL —la empresa es " +
    "el selector del sidebar, o sea VISTA— así que un `/empleados?empresa=...` no existe y " +
    "escribirlo sería un parámetro que la pantalla ignora en silencio.",
}

/**
 * La ruta a la que lleva ese KPI, o `undefined` si no tiene destino o si el rol no puede leer la
 * sección destino. Fail-closed: con `rol === null` no linkea nada.
 */
export function destino(rol: UserRol | null, title: string): string | undefined {
  const ruta = DESTINOS[title]
  if (!ruta) return undefined
  // Ver el ⚠️ del encabezado: sin este corte, `seccionDeRuta` devuelve null y el gate no corre.
  const seccion = seccionDeRuta(ruta.split("?")[0])
  if (seccion && !puede(rol, seccion, "read")) return undefined
  return ruta
}
