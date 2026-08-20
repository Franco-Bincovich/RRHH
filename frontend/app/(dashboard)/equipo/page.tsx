"use client"

import { useCallback, useEffect, useState } from "react"
import { UsersRound } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarEquipo, fetchEquipo } from "@/services/equipo"
import type { EquipoMiembro } from "@/types/equipo"

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

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

      {loading && <TableSkeleton />}

      {!loading && error && <ErrorState action={load} />}

      {!loading && !error && miembros.length === 0 && (
        <EmptyState
          icon={<UsersRound />}
          title="Todavía no tenés colaboradores a cargo"
          description="Cuando se te asignen personas como responsable directo, van a aparecer acá."
        />
      )}

      {!loading && !error && miembros.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Apellido</TableHead>
              <TableHead>Nombre</TableHead>
              <TableHead>Empresa</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {miembros.map((m) => (
              <TableRow key={m.id}>
                <TableCell className="font-medium">{m.apellido}</TableCell>
                <TableCell>{m.nombre}</TableCell>
                <TableCell className="text-muted-foreground">{m.empresa ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
