"use client"

import { useEffect, useMemo, useState } from "react"

import { destinatarios, enviarAhora } from "@/components/features/configuracion/envioAcciones"
import { useDestinatarios } from "@/components/features/configuracion/useDestinatarios"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { EnvioResponse } from "@/types/plantillas"

/** Elegir → confirmar → resultado. La confirmación es un PASO, no un `window.confirm`: tiene que
 *  poder decir a cuántas personas, y quedarse en pantalla mientras se lee. */
export type PasoEnvio = "seleccion" | "confirmar" | "resultado"

export function useEnvioPlantilla(open: boolean, clave: string) {
  // 🔴 TRI-ESTADO: `null` = todavía no se leyó el selector. Con un `false` inicial, el efecto de
  // `useDestinatarios` corre ANTES que el de acá (orden de declaración) y dispara el request de
  // empleados aun en modo consolidado, donde el envío ni siquiera se puede hacer.
  const [sinEmpresa, setSinEmpresa] = useState<boolean | null>(null)
  const [search, setSearch] = useState("")
  const [sel, setSel] = useState<Set<string>>(new Set())
  const [paso, setPaso] = useState<PasoEnvio>("seleccion")
  const [enviando, setEnviando] = useState(false)
  const [resultado, setResultado] = useState<EnvioResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { empleados, cargando } = useDestinatarios(open, sinEmpresa === false)

  useEffect(() => {
    if (!open) return
    setSearch(""); setSel(new Set()); setPaso("seleccion"); setResultado(null); setError(null)
    // Se lee AL ABRIR y no al montar: el modal vive montado con `open=false` y el usuario puede
    // cambiar el selector del sidebar entre una apertura y la siguiente (igual que PlantillaModal).
    setSinEmpresa(getEmpresaActivaId() === null)
  }, [open])

  const visibles = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? empleados.filter((e) => `${e.nombre} ${e.apellido}`.toLowerCase().includes(q)) : empleados
  }, [empleados, search])

  // El conteo sale del MISMO cálculo que arma el body, no de `sel.size`: así el número que se
  // confirma ("vas a enviar a N") no puede diferir del que se manda.
  const elegidos = destinatarios(empleados, sel)

  function toggle(id: string) {
    setSel((prev) => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  async function confirmar() {
    setEnviando(true)
    setError(null)
    const r = await enviarAhora(clave, empleados, sel)
    if (r.ok) { setResultado(r.res); setPaso("resultado") } else setError(r.error)
    setEnviando(false)
  }

  return {
    empleados, visibles, cargando, sinEmpresa: sinEmpresa === true, search, setSearch,
    sel, toggle, elegidos, paso, setPaso, enviando, resultado, error, confirmar,
  }
}
