"use client"

import { useEffect, useMemo, useState } from "react"

import {
  direccionesInvalidas, parsearDirecciones,
} from "@/components/features/comunicacion/direccionesLibres"

/**
 * El estado del modo "direcciones escritas a mano": el texto crudo y lo que se deriva de él.
 *
 * Hook aparte y no dentro de `useEnvioPlantilla` porque aquel estaba en 70/80 líneas. El corte
 * cae bien igual: acá vive TODO lo del modo libre y nada más, así que el modo de empleados no se
 * entera de que existe.
 *
 * Se guarda el TEXTO y se derivan las direcciones, no al revés: si se guardara la lista, cada
 * tecleo la reconstruiría y el cursor saltaría al final del campo mientras alguien edita el
 * medio de una dirección.
 */
export function useEnvioLibre(open: boolean) {
  const [texto, setTexto] = useState("")

  useEffect(() => { if (open) setTexto("") }, [open])

  const direcciones = useMemo(() => parsearDirecciones(texto), [texto])
  const invalidas = useMemo(() => direccionesInvalidas(direcciones), [direcciones])

  return { texto, setTexto, direcciones, invalidas }
}
