/**
 * EL TEXTO de cada confirmación destructiva, con los valores reales adentro.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 POR QUÉ ES UN MÓDULO DE FUNCIONES PURAS Y NO TEXTO INLINE EN CADA PANTALLA
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Porque es lo ÚNICO de una confirmación que se puede probar sin jsdom. `vitest` corre con
 * `environment: "node"` y los tests de componente usan `renderToStaticMarkup`, que no ejecuta
 * `useEffect` ni despacha clicks: un diálogo que se abre al apretar un botón es, para la suite,
 * invisible. El texto, en cambio, es una función de sus argumentos, y es exactamente la parte
 * que el usuario lee antes de destruir algo.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 LAS DOS REGLAS DEL COPY, Y POR QUÉ LA SEGUNDA EXISTE
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 1. **Dice QUÉ VA A PASAR, con los valores reales.** El molde es el de /areas, que ya lo hacía
 *    bien: *"¿Estás seguro de que querés eliminar ADMINISTRACION? Esta acción no se puede
 *    deshacer."* Un "¿Confirmar?" pelado no es una confirmación: es un segundo click.
 *
 * 2. 🔴 **SI NO BORRA, NO DICE "ELIMINAR".** Dos de las cinco acciones de esta tanda NO destruyen
 *    nada: cancelar unas vacaciones es un `cancelada=true` —la fila sigue en el listado y los
 *    días vuelven al saldo— y cerrar un período es un candado REVERSIBLE (la pantalla tiene
 *    "Reabrir"). Escribirles el copy de un borrado le miente al usuario en la dirección cara:
 *    lo frena de hacer algo inocuo, y de paso devalúa el diálogo de los tres que sí destruyen.
 *    Cuando todo dice "no se puede deshacer", "no se puede deshacer" no significa nada.
 *
 * Cada función devuelve lo que `ConfirmDialog` necesita, y el `confirmLabel` DESCRIBE LA ACCIÓN
 * ("Eliminar la ausencia") en vez de un "Aceptar" genérico — el botón se lee solo, sin releer
 * el título.
 */

export interface TextoConfirmacion {
  title: string
  description: string
  confirmLabel: string
}

/** "2026-03-25" → "25/03/2026". Sin `new Date`: parsear un ISO suelto corre la fecha un día para
 *  atrás en cualquier huso al oeste de UTC, y acá se muestra la fecha que el usuario cargó.
 *  Es la misma decisión —y el mismo bug evitado— que `filtrosChips.fechaLegible`. */
export function fechaLegible(iso: string | null | undefined): string {
  if (!iso) return ""
  const [anio, mes, dia] = iso.slice(0, 10).split("-")
  return dia && mes && anio ? `${dia}/${mes}/${anio}` : iso
}

/** "del 3/3/2026 al 7/3/2026", o "" si no hay fechas. Rango abierto no se inventa. */
function rango(desde?: string | null, hasta?: string | null): string {
  const d = fechaLegible(desde)
  const h = fechaLegible(hasta)
  if (d && h) return d === h ? ` del ${d}` : ` del ${d} al ${h}`
  return d ? ` del ${d}` : h ? ` hasta el ${h}` : ""
}

/** El nombre de la persona, o un genérico. Nunca "undefined" ni un id crudo en pantalla. */
function persona(nombre?: string | null): string {
  return nombre?.trim() || "el colaborador"
}

// ─────────────────────────────────────────────────────────────────────────────
// LAS TRES QUE DESTRUYEN
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Baja de una ausencia. Borrado FÍSICO (`solicitudes_ausencia` no tiene baja lógica): la fila
 * desaparece y con ella los días que computaban al ausentismo del mes.
 */
export function confirmarEliminarAusencia(a: {
  empleado_nombre?: string | null; fecha_desde?: string | null; fecha_hasta?: string | null
  tipo_nombre?: string | null
}): TextoConfirmacion {
  const tipo = a.tipo_nombre?.trim() ? `la ausencia por ${a.tipo_nombre.trim().toLowerCase()}` : "la ausencia"
  return {
    title: "Eliminar la ausencia",
    description: `¿Estás seguro de que querés eliminar ${tipo} de ${persona(a.empleado_nombre)}`
      + `${rango(a.fecha_desde, a.fecha_hasta)}? Se borra el registro y deja de contar en el `
      + "ausentismo del período. Esta acción no se puede deshacer.",
    confirmLabel: "Eliminar la ausencia",
  }
}

/** Baja de un ítem de inventario. Borrado FÍSICO. */
export function confirmarEliminarItem(i: {
  nombre?: string | null; numero_serie?: string | null
}): TextoConfirmacion {
  const serie = i.numero_serie?.trim() ? ` (serie ${i.numero_serie.trim()})` : ""
  return {
    title: "Eliminar el ítem",
    description: `¿Estás seguro de que querés eliminar ${i.nombre?.trim() || "este ítem"}`
      + `${serie}? Se borra del inventario junto con su historial de asignaciones, y no se `
      + "puede deshacer.",
    confirmLabel: "Eliminar el ítem",
  }
}

/**
 * Baja de un objetivo. Borrado FÍSICO **y con CASCADE sobre los subobjetivos** (la FK
 * `parent_id` es ON DELETE CASCADE, migración 095).
 *
 * 🔴 EL CONTEO DE HIJOS VA EN EL TEXTO Y ES LA RAZÓN PRINCIPAL DE QUE ESTA PANTALLA NECESITARA
 * UN DIÁLOGO. Sin él, un click borra un objetivo Y las cuatro tareas que colgaban de él sin
 * nombrarlas en ningún lado. Es el caso que ya ocurrió: entre el 17/8 y el 24/8/2026 desapareció
 * un objetivo real de Karstec y nadie pudo saber siquiera cuánto se llevó puesto.
 */
export function confirmarEliminarObjetivo(o: {
  titulo?: string | null; hijos?: unknown[] | null
}): TextoConfirmacion {
  const n = o.hijos?.length ?? 0
  const arrastre = n === 0 ? ""
    : n === 1 ? " Se borra también su subobjetivo."
      : ` Se borran también sus ${n} subobjetivos.`
  return {
    title: "Eliminar el objetivo",
    description: `¿Estás seguro de que querés eliminar ${o.titulo?.trim() || "este objetivo"}?`
      + `${arrastre} Esta acción no se puede deshacer.`,
    confirmLabel: n > 0 ? "Eliminar todo" : "Eliminar el objetivo",
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// LAS DOS QUE **NO** DESTRUYEN — ver la regla 2 del encabezado
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Cancelación de una solicitud de vacaciones. **NO borra**: `_vacaciones_write.cancel` setea
 * `cancelada=true`, la fila sigue en el listado con estado "cancelada", y como el cálculo de
 * saldo filtra por `cancelada=false` (`vacaciones_repo:70-73`), los días vuelven a estar
 * disponibles. Las tres cosas se le dicen al usuario, porque las tres cambian su decisión.
 */
export function confirmarCancelarVacaciones(v: {
  empleado_nombre?: string | null; fecha_desde?: string | null; fecha_hasta?: string | null
  dias?: number | null
}): TextoConfirmacion {
  const dias = v.dias && v.dias > 0 ? ` Los ${v.dias} día${v.dias === 1 ? "" : "s"} vuelven al saldo disponible.` : ""
  return {
    title: "Cancelar las vacaciones",
    description: `¿Cancelar las vacaciones de ${persona(v.empleado_nombre)}`
      + `${rango(v.fecha_desde, v.fecha_hasta)}?${dias} La solicitud no se borra: queda en el `
      + "listado marcada como cancelada.",
    confirmLabel: "Cancelar las vacaciones",
  }
}

/**
 * Cierre de un período. **NO borra nada y es REVERSIBLE**: pone un candado sobre un rango de
 * fechas y la misma pantalla ofrece "Reabrir". Por eso el texto dice qué deja de poder hacerse
 * —que es lo que el usuario necesita saber— y que se puede volver atrás.
 */
export function confirmarCerrarPeriodo(p: {
  empresa_nombre?: string | null; desde?: string | null; hasta?: string | null
  modulo_label?: string | null
}): TextoConfirmacion {
  const alcance = p.modulo_label?.trim() ? `de ${p.modulo_label.trim()}` : "de todos los módulos"
  const empresa = p.empresa_nombre?.trim() ? ` de ${p.empresa_nombre.trim()}` : ""
  return {
    title: "Cerrar el período",
    description: `¿Cerrar el período${empresa}${rango(p.desde, p.hasta)}? Nadie va a poder `
      + `cargar, editar ni borrar registros ${alcance} con fecha dentro de ese rango. `
      + "Se puede reabrir después desde esta misma pantalla.",
    confirmLabel: "Cerrar el período",
  }
}
