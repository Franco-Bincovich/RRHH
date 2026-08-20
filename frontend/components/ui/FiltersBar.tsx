"use client"

import { SlidersHorizontal } from "lucide-react"
import { useState } from "react"

import { FiltrosActivos } from "@/components/ui/FiltrosActivos"
import { Campo, alternar } from "@/components/ui/FiltrosCampo"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { FiltroCampo } from "@/components/ui/filtrosTipos"

/**
 * Barra de filtros genérica, presentacional y controlada. Cada campo trae su propio `onChange`:
 * la página conserva su estado (useState), su fetch y su debounce — este componente SOLO renderiza
 * los controles con label visible. No fetchea, no debouncea, no tiene estado propio salvo el
 * abierto/cerrado del "Más filtros", que es estado de la BARRA y de nada más.
 *
 * El molde para el hook que la alimenta está en components/features/shared/filtros.ts, y el patrón
 * visual completo en `docs/SISTEMA-DE-DISENO.md` §3.
 *
 * 🔴 `panel` ES OPCIONAL Y ESO NO ES INDECISIÓN: ES EL ALCANCE.
 * Sin `panel` la barra renderiza exactamente lo que renderizaba antes del patrón — una fila de
 * controles y nada más. Con `panel` toma la forma del sistema de diseño: caja propia entre el
 * encabezado y la tabla, "Más filtros" para los campos `avanzado`, y la fila de chips abajo.
 * Este componente lo usan 8 pantallas: hacer el panel obligatorio habría migrado a las 8 de una,
 * sin que nadie mirara si sus campos están bien repartidos entre visibles y avanzados ni si sus
 * chips se leen. Hoy la única que lo pide es /empleados, la pantalla piloto. Propagarlo es sumar
 * `panel` en cada pantalla, de a una y mirándola.
 */

export type { FiltroCampo, OpcionFiltro, RangoFechas } from "@/components/ui/filtrosTipos"
export { alternar }

interface FiltersBarProps {
  campos: FiltroCampo[]
  /** Ver el 🔴 de arriba. Sin esto, la barra queda como estaba. */
  panel?: boolean
  /**
   * Deshabilita todos los controles y los chips, sin ocultarlos ni vaciarlos: es el estado de
   * CARGA del patrón (§3, "filtros presentes pero deshabilitados"). Vaciarlos mientras llega la
   * respuesta le sacaría al usuario de la vista justo el filtro cuyo resultado está esperando, y
   * dejarlos activos permite disparar tres pedidos encima del que ya está en vuelo.
   */
  disabled?: boolean
}

const LABEL_CLASS = "flex flex-col gap-1 text-xs text-muted-foreground"

/*
 * El buscador OCUPA EL ANCHO LIBRE de la fila (§3: "buscador que ocupa el ancho libre, selectores
 * de 30px"). `[&_input]:w-full` porque el `<input type="search">` tiene ancho propio por defecto y
 * no lo hereda del contenedor; `min-w-` para que con muchos selectores no quede una ranura.
 */
const CRECE_CLASS = "flex-1 min-w-[14rem] [&_input]:w-full"

function Etiquetado({ campo, crece, disabled }: { campo: FiltroCampo; crece?: boolean; disabled?: boolean }) {
  const clase = crece ? `${LABEL_CLASS} ${CRECE_CLASS}` : LABEL_CLASS
  // daterange y multiselect renderizan VARIOS controles, así que su etiqueta va como texto: un
  // <label> no puede apuntar a más de un control, y envolverlos a todos haría que un lector de
  // pantalla anuncie la etiqueta en cada uno.
  if (campo.tipo === "daterange" || campo.tipo === "multiselect") {
    return (
      <div className={clase}>
        <span>{campo.label}</span>
        <Campo campo={campo} disabled={disabled} />
      </div>
    )
  }
  return (
    <label className={clase}>
      {campo.label}
      <Campo campo={campo} disabled={disabled} />
    </label>
  )
}

export function FiltersBar({ campos, panel, disabled }: FiltersBarProps) {
  const chips = chipsDeCampos(campos)
  const avanzados = campos.filter((c) => c.avanzado)
  const visibles = panel ? campos.filter((c) => !c.avanzado) : campos
  /*
   * Arranca ABIERTO si algún filtro avanzado ya viene puesto. El caso real: la alerta del
   * dashboard linkea a /empleados?estado=activo&sin_manager=true, y "Superior" es un filtro
   * avanzado — con el panel cerrado, el usuario aterriza en un listado recortado y el control que
   * lo recorta está atrás de un botón. El chip igual lo delata, pero el control tiene que estar
   * donde el usuario lo va a buscar. Sólo se evalúa al montar: a partir de ahí manda el usuario.
   */
  const [abierto, setAbierto] = useState(() => avanzados.some((c) => chipsDeCampos([c]).length > 0))

  const fila = (
    <div className="flex flex-wrap items-end gap-3">
      {visibles.map((campo) => (
        <Etiquetado key={campo.label} campo={campo} crece={panel && campo.tipo === "search"} disabled={disabled} />
      ))}
      {panel && avanzados.length > 0 && (
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          aria-expanded={abierto}
          className="flex h-11 items-center gap-1.5 rounded-lg border border-input px-2.5 text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 md:h-[30px]"
        >
          <SlidersHorizontal className="size-3.5" aria-hidden="true" />
          Más filtros
        </button>
      )}
    </div>
  )

  if (!panel) return <div className="mb-4">{fila}</div>

  return (
    // El panel va ENTRE el encabezado y la tabla, nunca flotando sobre ella (§3): es una caja
    // opaca en la superficie de tarjeta, no un popover.
    <div className="mb-4 flex flex-col gap-3 rounded-lg border border-border bg-card p-3">
      {fila}
      {abierto && avanzados.length > 0 && (
        <div className="flex flex-wrap items-end gap-3 border-t border-border pt-3">
          {avanzados.map((campo) => <Etiquetado key={campo.label} campo={campo} disabled={disabled} />)}
        </div>
      )}
      <FiltrosActivos chips={chips} disabled={disabled} />
    </div>
  )
}
