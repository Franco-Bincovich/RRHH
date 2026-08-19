"use client"

import { useState } from "react"
import { Accordion } from "@base-ui/react/accordion"

import { HistorialMails } from "@/components/features/comunicacion/HistorialMails"
import { PlantillasSection } from "@/components/features/comunicacion/PlantillasSection"
import { PageHeader } from "@/components/layout/PageHeader"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"
import { useCanWrite } from "@/hooks/useCanWrite"

type Tab = "plantillas" | "historial"

const TABS: { id: Tab; label: string }[] = [
  { id: "plantillas", label: "Plantillas" },
  { id: "historial", label: "Historial" },
]

/**
 * /comunicacion — el texto con el que la empresa le escribe a su gente, y el registro de lo que
 * ya salió.
 *
 * 🔴 POR QUÉ NO ESTÁ MÁS EN /configuracion. Mientras fue el ABM de un texto que se toca dos
 * veces al año, vivir dentro de configuración era lo correcto y así estaba argumentado. Lo que
 * cambió no es el criterio: es que desde acá ahora se MANDAN MAILS a la gente. Un envío es
 * irreversible, sale a nombre de la empresa, deja rastro en `mail_enviado` y se repite todos los
 * meses. Eso es operación, no configuración.
 *
 * 🔒 GATE: la ruta se gatea por `configuracion` (ver `RUTA_SECCION` en services/permisos.ts), el
 * MISMO permiso que ya exigía el backend para plantillas, envío e historial. NO se creó una
 * `Seccion` nueva: `puede()` es genérica —admin escribe, gerencia lee, mandos_medios no entra—
 * así que una sección propia daba exactamente el mismo resultado a cambio de tocar el espejo
 * manual `permisos.py` ↔ `permisos.ts`. Cuando el permiso tenga que diferir de configuración,
 * ahí sí vale la sección propia.
 *
 * Las dos pestañas se ven con permiso de LECTURA. Lo que `editable` gobierna adentro es editar
 * plantillas y el botón de enviar — el historial es información, y quien puede leer los reportes
 * debería poder saber qué se le mandó a la gente.
 */
export default function ComunicacionPage() {
  const editable = useCanWrite("configuracion")
  const [tab, setTab] = useState<Tab>("plantillas")

  return (
    <div>
      <PageHeader
        title="Comunicación"
        description="Las plantillas de mail y el registro de lo que se envió"
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabList className="mb-6">
          {TABS.map((t) => (
            <Tab key={t.id} value={t.id}>{t.label}</Tab>
          ))}
        </TabList>

      {/* `PlantillasSection` se mudó TAL CUAL y sigue siendo un `Accordion.Item`, así que
          necesita su Root. `defaultValue` lo deja ABIERTO: acá el plegado no aporta nada — es
          el único bloque de la pestaña. Que el acordeón sobre en este contexto es real y quedó
          anotado en el componente; sacarlo era rediseñar en el mismo diff que la mudanza. */}
      <TabPanel value="plantillas">
        <Accordion.Root defaultValue={["plantillas"]} multiple className="flex flex-col gap-4">
          <PlantillasSection editable={editable} />
        </Accordion.Root>
      </TabPanel>

      <TabPanel value="historial"><HistorialMails /></TabPanel>
      </Tabs>
    </div>
  )
}
