"use client"

import { useEffect, useState } from "react"

import { enviarAhora } from "@/components/features/comunicacion/envioAcciones"
import { useDestinatarios } from "@/components/features/comunicacion/useDestinatarios"
import { useEnvioLibre } from "@/components/features/comunicacion/useEnvioLibre"
import { useSeleccionEmpleados } from "@/components/features/comunicacion/useSeleccionEmpleados"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { EnvioResponse } from "@/types/plantillas"

/** Elegir → confirmar → resultado. La confirmación es un PASO, no un `window.confirm`: tiene que
 *  poder decir a cuántas personas, y quedarse en pantalla mientras se lee. */
export type PasoEnvio = "seleccion" | "confirmar" | "resultado"

/**
 * 🔴 LOS DOS MODOS SON EXCLUYENTES, no acumulativos. Es una decisión, no un límite técnico:
 * la regla de las variables aplica a uno y no al otro (un lote mixto sería mitad permitido), y
 * la confirmación dice "vas a enviar a N personas" — con dos fuentes sumando, ese N deja de
 * decir a quién se le manda. Cambiar de modo NO arrastra lo elegido en el otro, y el backend
 * rechaza el body mixto (422 ENVIO_MODO_MIXTO) por si alguien lo arma a mano.
 */
export type ModoEnvio = "empleados" | "libre"

/** Orquesta los dos modos; el estado de cada uno vive en su propio hook (`useSeleccionEmpleados`
 *  y `useEnvioLibre`), que es lo que mantiene a este por debajo del límite y sin ramas cruzadas. */
export function useEnvioPlantilla(open: boolean, clave: string, usaVariables = false) {
  // 🔴 TRI-ESTADO: `null` = todavía no se leyó el selector. Con un `false` inicial, el efecto de
  // `useDestinatarios` corre ANTES que el de acá (orden de declaración) y dispara el request de
  // empleados aun en modo consolidado, donde el envío ni siquiera se puede hacer.
  const [sinEmpresa, setSinEmpresa] = useState<boolean | null>(null)
  const [modo, setModo] = useState<ModoEnvio>("empleados")
  const [paso, setPaso] = useState<PasoEnvio>("seleccion")
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<EnvioResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // `errorCarga` (no se pudo TRAER la lista) es distinto de `error` (falló el ENVÍO): el primero
  // se resuelve reintentando la consulta, el segundo hablando con el backend. Fusionarlos daría
  // un "reintentar" que no se sabe qué reintenta.
  const { empleados, cargando, error: errorCarga, recargar } =
    useDestinatarios(open, sinEmpresa === false)
  const seleccion = useSeleccionEmpleados(open, empleados)
  const libre = useEnvioLibre(open)

  useEffect(() => {
    if (!open) return
    setPaso("seleccion"); setResultado(null); setError(null)
    setModo("empleados")   // el modo por defecto es el seguro: el que resuelve las variables
    // Se lee AL ABRIR y no al montar: el modal vive montado con `open=false` y el usuario puede
    // cambiar el selector del sidebar entre una apertura y la siguiente (igual que PlantillaModal).
    setSinEmpresa(getEmpresaActivaId() === null)
  }, [open])

  const elegidos = modo === "libre" ? libre.direcciones : seleccion.elegidos
  // Con una dirección mal escrita NO se habilita el envío: el backend rechaza el lote entero
  // (422 EMAIL_INVALIDO), así que dejar apretar solo cambia "no se puede" por "no se pudo".
  const bloqueado = modo === "libre" && libre.invalidas.length > 0

  async function confirmar() {
    setEnviando(true)
    setError(null)
    const r = modo === "libre"
      ? await enviarAhora(clave, [], new Set(), libre.direcciones)
      : await enviarAhora(clave, empleados, seleccion.sel)
    if (r.ok) { setResultado(r.res); setPaso("resultado") } else setError(r.error)
    setEnviando(false)
  }

  return {
    empleados, cargando, errorCarga, recargar, sinEmpresa: sinEmpresa === true,
    visibles: seleccion.visibles, search: seleccion.search, setSearch: seleccion.setSearch,
    sel: seleccion.sel, toggle: seleccion.toggle,
    elegidos, paso, setPaso, enviando, resultado, error, confirmar,
    modo, setModo, libre, bloqueado, usaVariables,
  }
}
