"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { PageHeader } from "@/components/layout/PageHeader"
import { CatalogoTab } from "@/components/features/capacitaciones/CatalogoTab"
import { AsignacionesTab } from "@/components/features/capacitaciones/AsignacionesTab"
import { useCanWrite } from "@/hooks/useCanWrite"

type Tab = "catalogo" | "asignaciones"

const TABS: { id: Tab; label: string }[] = [
  { id: "catalogo", label: "Catálogo de cursos" },
  { id: "asignaciones", label: "Asignaciones" },
]

export default function CapacitacionesPage() {
  const [activeTab, setActiveTab] = useState<Tab>("catalogo")
  const canWrite = useCanWrite()

  return (
    <div>
      <PageHeader
        title="Formación"
        description="Gestión del catálogo de cursos y asignaciones a empleados"
      />

      {/* Tab bar */}
      <div className="mb-6 flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 pb-3 pt-1 text-sm font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              activeTab === tab.id
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "catalogo" && <CatalogoTab canWrite={canWrite} />}
      {activeTab === "asignaciones" && <AsignacionesTab canWrite={canWrite} />}
    </div>
  )
}
