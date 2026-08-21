"use client"

import { useCallback, useEffect, useState } from "react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EquipoTable } from "@/components/features/equipo/EquipoTable"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarEquipo, fetchEquipo } from "@/services/equipo"
import type { EquipoMiembro } from "@/types/equipo"

/**
 * "Mi equipo": el roster de ownership de quien está mirando.
 *
 * ⚠️ ES LA ÚNICA PANTALLA DE ESTA TANDA SIN FILTROS NI PIE, y no le faltan: `GET /api/equipo` no
 * acepta un solo Query y devuelve la lista entera —"sin paginación: lista corta", dice su
 * router—, así que no hay chips que mostrar ni `total` del backend que poner en un pie. Lo que sí
 * toma del patrón es la tabla: `patron="datos"`, los anchos declarados, el esqueleto con la misma
 * grilla y el vacío adentro de la tabla. Ver `EquipoTable`.
 *
 * 🔴 `miembros.length` COMO CONTEO ES CORRECTO **ACÁ Y SÓLO ACÁ**: el endpoint devuelve TODO, así
 * que el largo del array ES el total. En cualquier listado paginado ese mismo `.length` es el bug
 * que ya apareció tres veces en el repo (`paginacionTotales.test.ts`).
 */
export default function EquipoPage() {
  const [miembros, setMiembros] = useState<EquipoMiembro[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setMiembros(await fetchEquipo())
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <PageHeader
        title="Mi equipo"
        description={
          loading
            ? "Cargando..."
            : `${miembros.length} ${miembros.length === 1 ? "persona" : "personas"} a cargo`
        }
        action={<ExportMenu onExport={exportarEquipo} />}
      />

      <EquipoTable items={miembros} loading={loading} error={error} onRetry={load} />
    </div>
  )
}
