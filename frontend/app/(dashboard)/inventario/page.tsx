"use client"

import { useState } from "react"
import { PageHeader } from "@/components/layout/PageHeader"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { ItemsTab } from "@/components/features/inventario/ItemsTab"
import { AsignacionesTab } from "@/components/features/inventario/AsignacionesTab"
import { useCanWrite } from "@/hooks/useCanWrite"

type Tab = "items" | "asignaciones"

const TABS: { id: Tab; label: string }[] = [
  { id: "items",        label: "Ítems"        },
  { id: "asignaciones", label: "Asignaciones" },
]

export default function InventarioPage() {
  const [activeTab, setActiveTab] = useState<Tab>("items")
  const canWrite = useCanWrite()

  return (
    <div>
      <PageHeader
        title="Inventario"
        description="Gestión de ítems asignados a empleados"
      />
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabList className="mb-6">
          {TABS.map((tab) => (
            <Tab key={tab.id} value={tab.id}>{tab.label}</Tab>
          ))}
        </TabList>
        <TabPanel value="items"><ItemsTab canWrite={canWrite} /></TabPanel>
        <TabPanel value="asignaciones"><AsignacionesTab canWrite={canWrite} /></TabPanel>
      </Tabs>
    </div>
  )
}
