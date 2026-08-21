"use client"

import { useState } from "react"
import { UserMinus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { OffboardingCard } from "@/components/features/offboarding/OffboardingCard"
import { useOffboardings } from "@/components/features/offboarding/useOffboardings"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarOffboardings } from "@/services/offboarding"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { OffboardingInstancia } from "@/types/offboarding"

/**
 * Listado de procesos de offboarding abiertos.
 *
 * Quedó como orquestador tras el corte del 19/8/2026 (311 → esto), que hizo falta para poder
 * sumarle la efectivización de la baja: el estado y el update optimista se fueron a
 * `useOffboardings`, la tarjeta a `OffboardingCard` y los mapas de texto a `_offboardingLabels`.
 *
 * ⚠️ NO TIENE FILTROS NI PIE, y no le faltan: `GET /api/offboarding` no acepta un solo Query y
 * devuelve la lista entera de procesos abiertos. Sin filtros no hay chips que mostrar y sin
 * `page` del backend no hay pie que armar. El recorte por empresa lo hace el header del sidebar.
 */
export default function OffboardingPage() {
  const canWrite = useCanWrite()
  const { offboardings, loading, error, recargar, saving, toggleActivo, marcarEntrevista, quitar } =
    useOffboardings()
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const [docsFor, setDocsFor] = useState<OffboardingInstancia | null>(null)

  // mostrar empresa solo cuando el topbar está en "Todas"
  const mostrarEmpresa = !empresaActivaId

  return (
    <div>
      {/* 🔴 EL ENCABEZADO SE RENDERIZA SIEMPRE. Antes había dos `return` tempranos —carga y
          error— que se llevaban la pantalla entera, así que durante la carga desaparecían el
          título y el botón de export y la pantalla cambiaba de forma dos veces seguidas.
          `offboardings.length` como conteo es correcto ACÁ Y SÓLO ACÁ: el endpoint devuelve todo,
          así que el largo del array ES el total. En un listado paginado ese mismo `.length` es el
          bug que `paginacionTotales.test.ts` persigue. */}
      <PageHeader
        title="Offboarding"
        description={loading ? "Cargando..." : `${offboardings.length} procesos activos`}
        // El archivo sale del MISMO listado que las tarjetas y esta pantalla no tiene filtros:
        // trae exactamente los procesos que se ven. Sin procesos no se ofrece exportar.
        action={!loading && !error && offboardings.length > 0
          ? <ExportMenu onExport={exportarOffboardings} />
          : undefined}
      />

      {loading ? (
        <ul className="space-y-4" role="list">
          {[1, 2].map((i) => (
            <li key={i}><Skeleton shimmer className="h-40 w-full rounded-xl" /></li>
          ))}
        </ul>
      ) : error ? (
        <ErrorState description={error} action={recargar} />
      ) : offboardings.length === 0 ? (
        /*
         * ═══════════════════════════════════════════════════════════════════════════════════
         * 🔴 COPY PROPIO, y acá el motivo es el más lindo de los cinco: **vacío es buena noticia.**
         * ═══════════════════════════════════════════════════════════════════════════════════
         * `textoVacio` diría "Todavía no hay procesos · Cuando se cargue el primero va a aparecer
         * acá", y eso trata a un cero como una carencia. Acá un cero significa que **nadie se está
         * yendo**, que es el estado deseado — y además nadie "carga" un offboarding desde esta
         * pantalla: se abre desde la ficha del colaborador. Las dos mitades de la frase genérica
         * serían falsas.
         */
        <EmptyState
          icon={<UserMinus />}
          title="No hay ninguna salida en curso"
          description="Cuando se inicie un offboarding desde la ficha de un colaborador, el proceso aparece acá con su checklist."
        />
      ) : (
        <ul className="space-y-4" role="list">
          {offboardings.map((inst) => (
            <OffboardingCard
              key={inst.id}
              instancia={inst}
              canWrite={canWrite}
              mostrarEmpresa={mostrarEmpresa}
              saving={saving}
              onToggleActivo={toggleActivo}
              onDocumentos={setDocsFor}
              onEntrevista={marcarEntrevista}
              onEfectivizada={quitar}
            />
          ))}
        </ul>
      )}

      <AdjuntosDialog
        open={!!docsFor}
        onClose={() => setDocsFor(null)}
        entidad="offboarding"
        entidadId={docsFor?.id ?? ""}
        titulo={`Offboarding · ${docsFor?.empleado_nombre ?? ""}`}
      />
    </div>
  )
}
