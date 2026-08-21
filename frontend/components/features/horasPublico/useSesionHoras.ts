"use client"

import { useCallback, useEffect, useState } from "react"

import { fetchClientes, fetchSemana } from "@/services/horasPublico"
import type { ClientePublico, Semana } from "@/types/horasPublico"

import { esSesionMuerta, mensajeDeError } from "./logica"
import { borrarToken, guardarToken, leerToken } from "./sesionHoras"

/**
 * La sesión del link público y los datos que dependen de ella: el token, el nombre de la persona,
 * el catálogo de clientes y lo cargado en la semana.
 *
 * 🔴 SEPARA "CARGANDO" DE "SIN DATOS", que es lo que la pantalla no distinguía. Al volver a la
 * pestaña con un token guardado, `clientes` arranca en `[]` y `semana` en `null` mientras las dos
 * consultas viajan: el formulario se dibujaba con el selector de clientes VACÍO, que es
 * exactamente lo que se ve cuando de verdad no hay ninguno cargado. La persona elegía "Elegí uno"
 * sobre una lista sin opciones y no tenía forma de saber si esperar o avisar.
 *
 * 🔴 Y SEPARA "SE MURIÓ LA SESIÓN" DE "NO SE PUDO CONECTAR". Antes el `catch` sólo miraba lo
 * primero: `if (esSesionMuerta(e)) cerrar(...)` y nada en el `else`. Una caída de red al montar
 * dejaba la pantalla con el formulario vacío y **sin un solo mensaje**. Ahora prende `errorCarga`,
 * que la página resuelve con `ErrorState` y su reintento.
 */
export function useSesionHoras() {
  const [token, setToken] = useState<string | null>(null)
  const [nombre, setNombre] = useState("")
  const [clientes, setClientes] = useState<ClientePublico[]>([])
  const [semana, setSemana] = useState<Semana | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState("")
  const [errorCarga, setErrorCarga] = useState(false)

  const cerrar = useCallback((mensaje: string) => {
    borrarToken()
    setToken(null); setNombre(""); setSemana(null); setClientes([]); setErrorCarga(false)
    setError(mensaje)
  }, [])

  const refrescar = useCallback(async (t: string) => {
    setErrorCarga(false)
    try {
      const [cs, sem] = await Promise.all([fetchClientes(t), fetchSemana(t)])
      setClientes(cs.items); setSemana(sem)
    } catch (e) {
      if (esSesionMuerta(e)) cerrar(mensajeDeError(e))
      else setErrorCarga(true)
    } finally {
      setCargando(false)
    }
  }, [cerrar])

  // El token sobrevive al refresh de la página: se relee de sessionStorage al montar. Ver
  // `sesionHoras.ts` para por qué sessionStorage y no las otras dos opciones.
  useEffect(() => {
    const guardado = leerToken()
    if (guardado) { setToken(guardado); void refrescar(guardado) }
    else setCargando(false)
  }, [refrescar])

  /** Paso 1 resuelto: se guarda el token y se traen los datos que dependen de él. */
  const abrir = useCallback(async (t: string, quien: string) => {
    guardarToken(t); setToken(t); setNombre(quien); setError("")
    await refrescar(t)
  }, [refrescar])

  return { token, nombre, clientes, semana, cargando, error, errorCarga,
           setError, abrir, refrescar, cerrar }
}
