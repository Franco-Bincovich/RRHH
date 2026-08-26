import { RUTAS_OCULTAS } from "@/components/layout/nav-config"
import type { AlertaDashboard } from "@/services/dashboard"

import { DESTINOS } from "./_destinosKpi"

/**
 * QUÉ DEL DASHBOARD SE ESCONDE PORQUE SU SECCIÓN SALIÓ DEL MENÚ.
 *
 * 🔴 NO HAY UNA LISTA DE "COSTOS" ACÁ ADENTRO, Y ESE ES TODO EL DISEÑO DEL ARCHIVO. Las dos
 * funciones DERIVAN de `RUTAS_OCULTAS` (`components/layout/nav-config.ts`), que es donde Franco
 * ya había decidido que /costos, /periodos y /horas-por-cliente salían de la vista. Escribir acá
 * un `const OCULTAR_MASA_SALARIAL = true` sería un segundo interruptor para la misma decisión, y
 * el día que Costos vuelva habría que acordarse de los dos — que es exactamente cómo se pudren
 * los flags en este repo.
 *
 * 🟢 **CÓMO SE REVIERTE, ENTERO: sacando `"/costos"` de `RUTAS_OCULTAS`.** Ese único movimiento
 * devuelve, a la vez, el ítem al sidebar, el link de la card, la card al segundo bloque y las
 * dos alertas al panel. Este archivo no se toca.
 *
 * ⚠️ ES OCULTAMIENTO, NO BORRADO, en los dos casos: el backend sigue calculando la masa salarial
 * y sigue emitiendo las alertas (`_dashboard_alertas_catalogo.py`), y `masaSalarial()` sigue
 * armando su card con todas sus reglas —"$0" vs "sin cargar", la variación sin base— y sigue
 * testeada. Lo único que cambia es qué se pinta. Que el contrato del backend no mienta es a
 * propósito: el día que se reponga, no hay nada que volver a escribir.
 *
 * 🔑 POR QUÉ LA ALERTA SE ESCONDE ENTERA Y LA CARD NO SE QUEDA SIN LINK. Una card sin link sigue
 * diciendo algo verdadero (un número). Una alerta es una INSTRUCCIÓN —"Importalos en Costos"—
 * hacia una pantalla que el menú ya no ofrece: dejarla sin link la convierte en un reproche sin
 * salida, y dejarla con link deshace lo que ocultar la sección buscaba. Es el mismo razonamiento
 * que ya está escrito en `_destinosKpi.destino()`, llevado un paso más.
 */

/**
 * ¿Esta card muestra el número de una sección que salió del menú?
 *
 * Se pregunta por el DESTINO de la card, no por su título: el destino es lo que dice de qué
 * pantalla sale ese número. Una card sin destino declarado (hoy "Headcount por empresa") no
 * puede quedar oculta por accidente — no apunta a ninguna sección.
 */
export function kpiOculto(title: string): boolean {
  const ruta = DESTINOS[title]
  return Boolean(ruta) && RUTAS_OCULTAS.includes(ruta.split("?")[0])
}

/**
 * Las alertas que se pintan: las que no empujan a una pantalla escondida.
 *
 * ⚠️ Filtra por `href`, que lo arma el BACKEND (el front no arma rutas de alertas — ver el
 * comentario de `href` en `services/dashboard.ts`), y no por `tipo`: una lista de tipos acá
 * sería un espejo manual de `_dashboard_alertas_catalogo.py`. Hoy caen las DOS que apuntan a
 * /costos —`sin_costos_nomina` y `sin_presupuesto`— sin nombrarlas.
 *
 * Una alerta SIN href se muestra siempre: no empuja a ninguna parte, así que no hay a dónde no
 * poder llegar. Es el caso de `empleado_sin_email`.
 */
export function alertasVisibles(alertas: AlertaDashboard[]): AlertaDashboard[] {
  return alertas.filter((a) => !a.href || !RUTAS_OCULTAS.includes(a.href.split("?")[0]))
}
