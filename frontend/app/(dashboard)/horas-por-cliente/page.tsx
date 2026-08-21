"use client"

import { useCallback, useEffect, useState } from "react"
import { Clock } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { PeriodSelector } from "@/components/features/shared/PeriodSelector"
import { MESES_LARGOS } from "@/components/features/costos/formatos"
import { KPIsHorasPanel } from "@/components/features/horasCliente/KPIsHorasPanel"
import { ClientesColapsables } from "@/components/features/horasCliente/ClientesColapsables"
import { DetalleEmpleadoModal } from "@/components/features/horasCliente/DetalleEmpleadoModal"
import { cargarHorasCliente } from "@/components/features/horasCliente/cargarHorasCliente"
import { exportarHorasPorCliente } from "@/services/horasCliente"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { HorasPorCliente } from "@/types/horasCliente"

/**
 * "Horas por cliente" — solo RRHH. ORQUESTADOR: estado y navegación; los KPIs, el árbol y el
 * detalle viven en `components/features/horasCliente/`, y la carga en `cargarHorasCliente.ts`
 * (testeable sin jsdom).
 *
 * ⚠️ El filtro de EMPRESA no está acá: lo pone el selector del sidebar (header `X-Empresa-Id`),
 * porque esto es una VISTA. Mirar = manda el sidebar; hacer = manda el form. El único "hacer" de
 * esta pantalla es el borrado, que va por id y no necesita empresa.
 */
export default function HorasPorClientePage() {
  const canWrite = useCanWrite()
  const hoy = new Date()
  const [mes, setMes] = useState(hoy.getMonth() + 1)
  const [anio, setAnio] = useState(hoy.getFullYear())
  const [datos, setDatos] = useState<HorasPorCliente | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detalle, setDetalle] = useState<{ id: string; nombre: string } | null>(null)

  const filtros = { mes, anio }
  const load = useCallback(
    () => cargarHorasCliente({ mes, anio }, { setDatos, setLoading, setError }),
    [mes, anio],
  )
  useEffect(() => { void load() }, [load])

  /*
   * 🔴 EL PERÍODO NO VA EN UN PANEL DE CHIPS, Y ES UNA DECISIÓN. `mes` y `anio` son `Query(...)`
   * **sin default** en `/api/horas-cliente`: un chip promete que el filtro se puede quitar y acá
   * quitarlo no deja la pantalla sin filtrar, deja la consulta rota. Mismo caso que /costos, y
   * desde el 21/8/2026 el MISMO control — antes eran dos `<Input type="number">`, o sea que había
   * que tipear "3" para ver marzo y nada impedía escribir 13.
   */
  const filtrosUI = (
    <div className="flex items-center gap-2">
      <PeriodSelector mes={mes} anio={anio} onChangeMes={setMes} onChangeAnio={setAnio} />
      {/* El MISMO filtro que el listado: el archivo no puede traer filas que no se ven. */}
      <ExportMenu onExport={(formato) => exportarHorasPorCliente(formato, filtros)} />
    </div>
  )

  return (
    <div>
      {/* 🔴 EL ENCABEZADO Y EL SELECTOR DE PERÍODO SE RENDERIZAN SIEMPRE. Antes había dos `return`
          tempranos —uno de carga y otro de error— que se llevaban la pantalla entera: mientras
          cargaba desaparecían el título, el aviso y el propio control con el que se elige el mes,
          justo cuando el usuario está esperando el resultado de haberlo movido. */}
      <PageHeader title="Horas por cliente"
                  description={loading || !datos
                    ? `${MESES_LARGOS[mes - 1]} ${anio}`
                    : `${datos.kpis.horas_totales} horas cargadas · ${MESES_LARGOS[mes - 1]} ${anio}`}
                  action={filtrosUI} />
      {/* 🔴 En todas las demás pantallas el selector de empresa del sidebar filtra; acá no.
          Sin decirlo, un operador que cambia de empresa y ve el mismo número cree que se
          colgó. Lenguaje llano: los usuarios son cuatro personas de RRHH. */}
      <p className="mb-4 rounded-lg border bg-muted/40 px-4 py-2.5 text-sm text-muted-foreground">
        Acá ves las horas completas de cada cliente, sumando todas las empresas. El selector de
        empresa del menú no cambia estos números. Abrí un cliente para ver cuántas horas puso
        cada empresa.
      </p>
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} shimmer className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : error || !datos ? (
        <ErrorState description={error ?? "No se pudieron cargar las horas."} action={load} />
      ) : (
        <>
          <KPIsHorasPanel kpis={datos.kpis} />
          {datos.clientes.length === 0 ? (
            /* Copy propio con el VALOR REAL del filtro, que es lo que el patrón busca aunque acá
               no haya chips de dónde sacarlo: nombrar el período convierte la pantalla vacía en
               la respuesta a la pregunta que trajo hasta acá. */
            <EmptyState icon={<Clock />} title="Sin cargas en el período"
                        description={`Nadie cargó horas en ${MESES_LARGOS[mes - 1]} ${anio}.`} />
          ) : (
            <ClientesColapsables
              clientes={datos.clientes}
              onVerDetalle={(id, nombre) => setDetalle({ id, nombre })}
            />
          )}
        </>
      )}
      <DetalleEmpleadoModal
        empleadoId={detalle?.id ?? null}
        empleadoNombre={detalle?.nombre ?? ""}
        filtros={filtros}
        canWrite={canWrite}
        onClose={() => setDetalle(null)}
        onBorrado={load}
      />
    </div>
  )
}
