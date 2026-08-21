/**
 * 🔴 EL SELECTOR DE EMPRESA DEL SIDEBAR NO ACOTA ESTA PANTALLA, y acá el motivo es todavía más
 * fácil de leer al revés que en clientes: la empresa **es el recurso**, no el eje por el que se
 * recorta. `routers/empresa.py` no lee `X-Empresa-Id` en ninguna de sus rutas —está declarado
 * como NO APLICA en el barrido de la Fase 2, con esa misma razón—, así que el listado trae
 * siempre TODAS, activas e inactivas, tenga el sidebar lo que tenga.
 *
 * Sin decirlo, un operador que entra con "Karstec" elegido y ve cuatro empresas cree que el
 * selector se colgó; y uno que entra en modo consolidado y ve las mismas cuatro cree que filtró
 * bien. Los dos leen lo mismo y sacan conclusiones opuestas.
 *
 * Va en el SUBTÍTULO del encabezado y no en un bloque de aviso: describe **lo que la pantalla
 * ES**, no algo que va a pasar. Misma regla y mismo lugar que en clientes y en perfiles de
 * puesto.
 */
export const AVISO_CATALOGO_GLOBAL =
  "el listado es de todo el grupo: el selector de empresa del sidebar no lo filtra."
