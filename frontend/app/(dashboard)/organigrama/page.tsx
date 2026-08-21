"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { FileDown, Network } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { ArbolEmpresa } from "@/components/features/organigrama/ArbolEmpresa"
import { ArbolProyecto, type ArbolProyectoRef } from "@/components/features/organigrama/ArbolProyecto"
import { CardsProyecto } from "@/components/features/organigrama/CardsProyecto"
import { fetchOrgProyectos } from "@/services/organigrama"
import type { OrgProyectosResponse } from "@/types/organigrama"

type Vista = "empresa" | "proyecto-arbol" | "proyecto-cards"

// Solo se muestran las vistas con `visible: true`. Para reactivar una vista oculta,
// poné su `visible` en true (una sola línea) — el código de cada vista queda intacto.
const TABS: { id: Vista; label: string; visible: boolean }[] = [
  { id: "empresa", label: "Por empresa", visible: false },
  { id: "proyecto-arbol", label: "Por proyecto · árbol", visible: false },
  { id: "proyecto-cards", label: "Por proyecto · cards", visible: true },
]
const TABS_VISIBLES = TABS.filter((t) => t.visible)

/**
 * El esqueleto tiene la FORMA del organigrama —una raíz y sus hijos— y no una pila de barras: así
 * la pantalla no cambia de forma cuando llegan los datos. Usa el shimmer de 1,2s que pide §3, no
 * el `animate-pulse` de 2s.
 */
function OrgSkeleton() {
  return (
    <div className="flex flex-col items-center gap-4 pt-6">
      <Skeleton shimmer className="h-12 w-40 rounded-xl" />
      <div className="flex gap-6">
        {[1, 2, 3].map((i) => <Skeleton key={i} shimmer className="h-28 w-40 rounded-xl" />)}
      </div>
    </div>
  )
}

export default function OrganigramaPage() {
  const [vista, setVista]         = useState<Vista>("proyecto-cards")
  const [orgData, setOrgData]     = useState<OrgProyectosResponse | null>(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)
  const arbolRef                  = useRef<ArbolProyectoRef>(null)

  // Carga idempotente de los proyectos (compartida por árbol y cards): fetch una sola vez.
  const cargarProyectos = useCallback(async (forzar = false) => {
    if (orgData && !forzar) return
    setLoading(true); setError(null)
    try { setOrgData(await fetchOrgProyectos()) }
    catch { setError("No se pudieron cargar los proyectos.") }
    finally { setLoading(false) }
  }, [orgData])

  // Dispara el fetch al estar en una vista de proyecto — incluye el montaje inicial
  // (default = cards) y el cambio de tab si se reactivan las otras vistas.
  useEffect(() => {
    if (vista === "proyecto-arbol" || vista === "proyecto-cards") void cargarProyectos()
  }, [vista, cargarProyectos])

  function handleExportarPDF() {
    if (vista === "proyecto-arbol" && arbolRef.current) {
      arbolRef.current.expandAll()
    }
    document.body.classList.add("printing")
    const cleanup = () => {
      document.body.classList.remove("printing")
      if (vista === "proyecto-arbol" && arbolRef.current) {
        arbolRef.current.restore()
      }
      window.removeEventListener("afterprint", cleanup)
    }
    window.addEventListener("afterprint", cleanup)
    window.print()
  }

  const mostrarProyectos = vista === "proyecto-arbol" || vista === "proyecto-cards"

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <PageHeader title="Organigrama" description="Estructura organizacional" />
        <Button variant="outline" className="min-h-11 shrink-0 print:hidden" onClick={handleExportarPDF}>
          <FileDown className="size-4" />
          Exportar PDF
        </Button>
      </div>

      <Tabs value={vista} onValueChange={setVista} variant="pill">
        {/* La barra se oculta si hay una sola vista visible (evita un botón solitario). El
            `<Tabs>` de afuera se monta igual: es lo que ata cada panel con su solapa, y hoy
            dos de las tres vistas están apagadas por `visible: false`. */}
        {TABS_VISIBLES.length > 1 && (
          <TabList className="print:hidden">
            {TABS_VISIBLES.map((tab) => (
              <Tab key={tab.id} value={tab.id}>{tab.label}</Tab>
            ))}
          </TabList>
        )}

        {/* Tab content — las 3 vistas quedan en el código; hoy solo renderiza cards. */}
        <TabPanel value="empresa"><ArbolEmpresa /></TabPanel>

        {/* Carga y error quedan FUERA de los paneles: son de la consulta de proyectos, que las
            dos vistas comparten. Duplicarlos adentro de cada panel los haría divergir. */}
        {mostrarProyectos && loading && <OrgSkeleton />}
        {mostrarProyectos && !loading && error && (
          <ErrorState description={error} action={() => void cargarProyectos(true)} />
        )}
        {/*
         * 🔴 EL VACÍO LLEVA COPY PROPIO, y no `textoVacio`: acá "vacío" no es un dato que falte
         * cargar en ESTA pantalla. El organigrama por proyecto se DERIVA de las asignaciones —
         * `proyecto_asignaciones`—, así que sin proyectos con gente asignada no hay árbol que
         * dibujar, y el lugar donde eso se arregla es /proyectos, no acá. Decir "cuando se cargue
         * el primero va a aparecer acá" mandaría a buscar un alta que esta pantalla no tiene.
         */}
        {mostrarProyectos && !loading && !error && orgData && orgData.proyectos.length === 0 && (
          <EmptyState
            icon={<Network />}
            title="Todavía no hay nada que dibujar"
            description="El organigrama por proyecto se arma con las asignaciones: aparece en cuanto un proyecto tenga colaboradores asignados, desde la pantalla de Proyectos."
          />
        )}

        <TabPanel value="proyecto-arbol">
          {!loading && orgData && <ArbolProyecto ref={arbolRef} data={orgData} />}
        </TabPanel>
        <TabPanel value="proyecto-cards">
          {!loading && orgData && <CardsProyecto data={orgData} />}
        </TabPanel>
      </Tabs>
    </div>
  )
}
