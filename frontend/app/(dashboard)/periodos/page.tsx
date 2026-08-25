"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { fechaLegible } from "@/components/features/shared/confirmaciones"
import { PeriodoForm } from "@/components/features/periodos/PeriodoForm"
import { PeriodoList } from "@/components/features/periodos/PeriodoList"
import { useCanWrite } from "@/hooks/useCanWrite"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarPeriodos, fetchPeriodos, reabrirPeriodo } from "@/services/periodos"
import { fetchUsuariosActivos } from "@/services/objetivos"
import type { Periodo } from "@/types/periodo"

export default function PeriodosPage() {
  const [periodos, setPeriodos] = useState<Periodo[]>([])
  const [usuarios, setUsuarios] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const canWrite = useCanWrite("periodos")

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const [per, us] = await Promise.all([fetchPeriodos(), fetchUsuariosActivos()])
      setPeriodos(per.items)
      setUsuarios(Object.fromEntries(us.items.map((u) => [u.id, `${u.nombre} ${u.apellido}`])))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function nombreUsuario(id: string | null): string {
    return (id && usuarios[id]) || "—"
  }

  /* 🔴 SALIÓ DEL `confirm()` NATIVO DEL NAVEGADOR (24/8/2026), y no es cosmético. Ese diálogo
     no se puede estilar, no respeta el tema, en mobile aparece pegado a la barra del navegador
     con la URL del sitio arriba, y —lo que decide— era el ÚNICO de todo el producto: la misma
     pantalla que pedía confirmación con la caja gris del sistema para reabrir, cerraba un
     período sin pedir nada. Dos gestos opuestos para dos acciones del mismo par.
     ⚠️ Reabrir NO destruye —saca un candado— así que va con `destructive={false}` y su texto no
     habla de borrar; ver la regla 2 de `confirmaciones.ts`. */
  const aReabrir = useConfirmacion<Periodo>()

  async function handleReabrir() {
    const p = aReabrir.pendiente
    if (!p) return
    aReabrir.cerrar()
    try {
      await reabrirPeriodo(p.id)
      toast.success("Período reabierto")
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "No se pudo reabrir el período")
    }
  }

  return (
    <div>
      <PageHeader
        title="Períodos"
        /* ⚠️ NO HAY FILTROS NI PIE, y no faltan: `GET /api/periodos` no acepta un solo Query y
           devuelve la lista entera de la empresa activa. Sin filtros no hay chips que mostrar y
           sin `page` del backend no hay pie que armar. El recorte por empresa lo hace el header
           `X-Empresa-Id` del sidebar, como en el resto del sistema. */
        description="Cerrá un período para impedir cambios en registros con fecha dentro de ese rango."
        action={<ExportMenu onExport={exportarPeriodos} />}
      />
      <div className="space-y-4">
        {canWrite && <PeriodoForm onCreated={load} />}
        {/* 🔴 LOS TRES ESTADOS SON DE LA TABLA, no de la página: el vacío tiene que ser una fila
            con `colSpan` adentro de la `<Table>` para que el encabezado siga puesto (§3). Y ese
            vacío lleva COPY PROPIO —"mientras no haya ninguno, todo se puede editar"— porque el
            genérico del patrón le diría a `gerencia_lectura` que cargue el primero, cosa que no
            puede hacer. El porqué completo está en `PeriodoList`. */}
        <PeriodoList
          periodos={periodos}
          loading={loading}
          error={error}
          nombreUsuario={nombreUsuario}
          canWrite={canWrite}
          onRetry={load}
          onReabrir={aReabrir.pedir}
        />
      </div>

      <ConfirmDialog
        open={aReabrir.abierto}
        onClose={aReabrir.cerrar}
        onConfirm={handleReabrir}
        destructive={false}
        title="Reabrir el período"
        description={`¿Reabrir el período del ${fechaLegible(aReabrir.pendiente?.desde)} al `
          + `${fechaLegible(aReabrir.pendiente?.hasta)}? Se van a poder volver a cargar, editar `
          + "y borrar registros con fecha dentro de ese rango."}
        confirmLabel="Reabrir el período"
      />
    </div>
  )
}
