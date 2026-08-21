"use client"

import { useEffect, useState } from "react"

import { fetchProyectos } from "@/services/proyectos"
import type { Proyecto } from "@/types/proyecto"

import { construirCamposEvaluados } from "@/components/features/evaluaciones/resultados/_camposEvaluados"

/**
 * Filtros del listado de evaluados. LOS CUATRO SON SERVER-SIDE.
 *
 * 🔴 CAMBIÓ EL 15/8/2026 Y EL CAMBIO ES EL PUNTO DEL MÓDULO. Antes este hook recibía el array
 * completo (`todos: EvaluadoListadoItem[]`), derivaba de ahí las opciones de sector y devolvía
 * un `filtrados` calculado en memoria; sólo `proyecto_id` iba al backend. Con ~30 evaluados por
 * lote eso funcionaba. Al paginar, "filtrar por sector" pasaría a significar "buscar el sector
 * entre las 20 filas que estás viendo": alguien que está en la página 3 no aparece nunca.
 *
 * Ahora el hook no ve datos. Sólo produce `campos` (la UI) y `filtros` (lo que viaja), y el
 * panel se los pasa al backend en el listado Y en el export, por el mismo traductor.
 *
 * ⚠️ El ARMADO de los campos se mudó a `_camposEvaluados.ts` al migrar la pantalla al patrón del
 * bloque B: es lo único que un test puede ejercitar sin DOM, y ahí vive la decisión de qué filtro
 * queda detrás de "Más filtros".
 *
 * @param sectores opciones del desplegable, del LOTE ENTERO — vienen en la respuesta, no de la
 *   página. Derivarlas de lo visible dejaría fuera del desplegable a los sectores que no
 *   aparecen en la página 1, y esos serían justo los que hay que ir a buscar.
 * @param onFiltroChange se dispara con CUALQUIER cambio; la pantalla lo cablea a volver a la
 *   página 1 (invariante 4 del Bloque B). El hook no conoce `page`, a propósito.
 */
export function useFiltrosEvaluadosResultados(sectores: string[], onFiltroChange: () => void) {
  const [sector, setSector] = useState("")
  const [perfil, setPerfil] = useState("")
  const [conNota, setConNota] = useState("")
  const [proyecto, setProyecto] = useState("")
  const [proyectos, setProyectos] = useState<Proyecto[]>([])

  useEffect(() => {
    fetchProyectos().then((r) => setProyectos(r.items)).catch(() => setProyectos([]))
  }, [])

  const campos = construirCamposEvaluados({
    sectores, sector, setSector, perfil, setPerfil, conNota, setConNota,
    proyectos, proyecto, setProyecto, onFiltroChange,
  })

  return {
    campos,
    filtros: {
      sector: sector || undefined, perfil: perfil || undefined,
      con_nota: conNota || undefined, proyecto_id: proyecto || undefined,
    },
  }
}
