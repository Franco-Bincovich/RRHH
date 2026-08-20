"use client"

import { useEffect, useState } from "react"

import { buscarEmpleados } from "@/components/features/shared/buscarEmpleados"
import { ResultadosEmpleados } from "@/components/features/shared/ResultadosEmpleados"
import { Input } from "@/components/ui/input"
import type { Empleado } from "@/types/empleado"

/**
 * EL selector de empleados del sistema: se escribe, el BACKEND filtra, vuelven los que coinciden.
 *
 * 🔴 POR QUÉ EXISTE. Los seis selectores de empleado del producto pedían una página de 100 y
 * pintaban un `<select>` plano. Con 400 colaboradores en una empresa eso significa que **300 no
 * se pueden elegir y la pantalla no lo dice**: el usuario no lo reporta como bug, cree que el
 * dato no está cargado. Se escribe UNA vez y se cablea en los seis; si hubiera dos versiones, la
 * próxima pantalla inventaría la tercera.
 *
 * Vive en `components/features/shared/` y NO en `components/ui/`: `ui/` es la biblioteca
 * PRESENTACIONAL y genérica (Button, Table, FiltersBar, Pagination) — ningún archivo de ahí
 * fetchea ni conoce un concepto del dominio. Éste hace las dos cosas. Su vecino natural es
 * `cargarEmpleados.ts`, el loader compartido que reusa.
 *
 * ⚠️ NO reemplaza al selector de `mandos_medios` (`SeleccionEmpleado`, rama `isMando`): ése lee
 * `/api/equipo`, que devuelve el roster por OWNERSHIP y sin paginar, y un mando **no tiene
 * permiso** sobre `Seccion.EMPLEADOS`. Cablearlo ahí daría 403 donde hoy funciona.
 */

interface Props {
  id: string
  /** `empleado_id` elegido. `""` = ninguno. */
  value: string
  /** Recibe el empleado ENTERO (o null al limpiar): hay pantallas que necesitan su empresa. */
  onChange: (empleado: Empleado | null) => void
  /** Acota la búsqueda a una empresa. `undefined` = lo que resuelva el header. */
  empresaId?: string
  /**
   * Nombre del ya elegido, para la EDICIÓN: al abrir con un valor seteado no hay lista de dónde
   * sacar el rótulo, y sin esto el campo mostraría un id o un hueco.
   */
  etiquetaInicial?: string
  /** Ids que no se pueden elegir (p. ej. quien ya tiene un onboarding en curso). */
  excluirIds?: string[]
  disabled?: boolean
  /** Qué decir cuando está deshabilitado ("Seleccioná primero una empresa"). */
  mensajeDeshabilitado?: string
  invalid?: boolean
}

export function EmpleadoCombobox({
  id, value, onChange, empresaId, etiquetaInicial, excluirIds, disabled,
  mensajeDeshabilitado, invalid,
}: Props) {
  const [termino, setTermino] = useState("")
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [total, setTotal] = useState(0)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(false)
  // Cambiarlo re-dispara el efecto: es lo que hace que "Reintentar" sea una línea y no un segundo
  // camino de carga que pueda divergir del primero. Molde: `useDestinatarios`.
  const [intento, setIntento] = useState(0)
  const [etiqueta, setEtiqueta] = useState(etiquetaInicial ?? "")

  // El rótulo del ya elegido llega DESPUÉS del primer render cuando el padre lo carga por red
  // (una edición que fetchea su entidad). Sin esto, el campo se queda con el hueco del inicio.
  useEffect(() => { if (etiquetaInicial) setEtiqueta(etiquetaInicial) }, [etiquetaInicial])

  useEffect(() => {
    if (disabled || value) return
    // Debounce: sin esto cada tecla es un request y llegan desordenados, así que la lista puede
    // terminar mostrando el resultado de un término anterior.
    const t = setTimeout(() => {
      void buscarEmpleados({ termino, empresaId }, { setEmpleados, setCargando, setError, setTotal })
    }, 250)
    return () => clearTimeout(t)
  }, [termino, empresaId, disabled, value, intento])

  function elegir(e: Empleado) {
    setEtiqueta(`${e.nombre} ${e.apellido}`)
    setTermino("")
    onChange(e)
  }

  if (disabled) {
    return (
      <p className="rounded-lg border border-input px-2.5 py-2 text-sm text-muted-foreground">
        {mensajeDeshabilitado ?? "No disponible"}
      </p>
    )
  }

  if (value) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-input px-2.5 py-1.5">
        <span className="flex-1 truncate text-sm">{etiqueta || "Colaborador seleccionado"}</span>
        <button
          type="button"
          className="text-xs text-muted-foreground underline hover:text-primary"
          onClick={() => { setEtiqueta(""); onChange(null) }}
        >
          Cambiar
        </button>
      </div>
    )
  }

  // El `excluir` se aplica sobre la tanda ya traída, no en la consulta: son unos pocos ids y
  // mandarlos por query string haría una URL que crece con los datos. Si los excluidos vaciaran
  // la tanda, el usuario ve "sin resultados" y escribe — no un silencio.
  const visibles = excluirIds?.length
    ? empleados.filter((e) => !excluirIds.includes(e.id))
    : empleados

  return (
    <div className="flex flex-col gap-1.5">
      <Input
        id={id}
        value={termino}
        onChange={(e) => setTermino(e.target.value)}
        placeholder="Buscar por nombre o apellido"
        aria-invalid={invalid}
        autoComplete="off"
      />
      <ResultadosEmpleados
        empleados={visibles} total={total} cargando={cargando} error={error} termino={termino}
        onElegir={elegir} onReintentar={() => setIntento((n) => n + 1)}
      />
    </div>
  )
}
