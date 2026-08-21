"use client"

import { useState } from "react"

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

      {/* ✅ EL `Accordion.Root` SE FUE. Estaba acá porque `PlantillasSection` se había mudado
          TAL CUAL desde /configuracion y seguía siendo un `Accordion.Item`; el comentario de
          entonces decía que el plegado "no aporta nada — es el único bloque de la pestaña" y que
          sacarlo era rediseñar en el mismo diff que la mudanza. Ese rediseño es el del 21/8/2026:
          las plantillas pasaron a TARJETAS (§5) y con eso el acordeón dejó de tener envoltorio
          que justificar. */}
      <TabPanel value="plantillas"><PlantillasSection editable={editable} /></TabPanel>

      <TabPanel value="historial"><HistorialMails /></TabPanel>
      </Tabs>
    </div>
  )
}
