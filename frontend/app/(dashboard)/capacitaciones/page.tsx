"use client"

import { useState } from "react"
import { PageHeader } from "@/components/layout/PageHeader"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
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

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabList className="mb-6">
          {TABS.map((tab) => (
            <Tab key={tab.id} value={tab.id}>{tab.label}</Tab>
          ))}
        </TabList>

        <TabPanel value="catalogo"><CatalogoTab canWrite={canWrite} /></TabPanel>
        <TabPanel value="asignaciones"><AsignacionesTab canWrite={canWrite} /></TabPanel>
      </Tabs>
    </div>
  )
}
