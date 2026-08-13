import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

/**
 * Los catálogos del alta de vacante: las empresas activas y las áreas de la empresa elegida.
 *
 * Salió de VacanteModal.tsx junto con su estado. Es el tercer corte del modal y el que le dio
 * margen de verdad: con los campos y lo puro afuera seguía en 140/150, o sea diez líneas para
 * una feature que necesita unas ocho. Molde: `useEmpleadoFormData` y `useCandidatosProyecto`.
 *
 * 🔴 EL SEAM ES REAL, NO DE CONVENIENCIA: estas tres piezas de estado y sus dos efectos no tocan
 * el form — solo LEEN `empresa_id` para saber qué áreas pedir. El modal, al revés, no necesita
 * saber cómo se cargan. Es la única parte del archivo que se podía sacar sin partir nada al
 * medio: los cuatro campos comparten un contenedor y el DOM los alterna (ver VacanteCamposBase).
 *
 * ⚠️ EL `setAreas([])` AL ABRIR SE VINO ACÁ, y hay que saber qué preserva. En el modal vivía
 * dentro del efecto de reset; si se hubiera quedado allá, el modal tendría que recibir el setter
 * del hook y `exhaustive-deps` lo pediría en el array de dependencias (no sabe que un setter de
 * `useState` es estable). Traerlo evita eso y deja el mismo resultado observable en los dos
 * caminos: reabrir con OTRA empresa recarga, y reabrir con la MISMA deja el select vacío porque
 * el efecto de áreas no se vuelve a disparar.
 *
 * 🚩 Ese "reabrir con la misma empresa deja el select vacío" ES UN BUG PREEXISTENTE, y se
 * conserva TAL CUAL a propósito: esto fue un refactor puro. Arreglarlo es cambiar la dependencia
 * del segundo efecto, y eso es una decisión de producto, no una división de archivo.
 */
export function useVacanteCatalogos(open: boolean, empresaId: string) {
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [areasLoading, setAreasLoading] = useState(false)

  // Limpiar las áreas al abrir (vivía en el efecto de reset del modal)
  useEffect(() => {
    if (!open) return
    setAreas([])
  }, [open])

  // Cargar empresas al abrir
  useEffect(() => {
    if (!open) return
    fetchEmpresas()
      .then((res) => setEmpresas(res.items.filter((e) => e.activa)))
      .catch(() => setEmpresas([]))
  }, [open])

  // Recargar áreas cuando cambia la empresa seleccionada
  useEffect(() => {
    if (!empresaId) {
      setAreas([])
      return
    }
    setAreasLoading(true)
    fetchAreas(empresaId)
      .then(setAreas)
      .catch(() => setAreas([]))
      .finally(() => setAreasLoading(false))
  }, [empresaId])

  return { empresas, areas, areasLoading }
}
