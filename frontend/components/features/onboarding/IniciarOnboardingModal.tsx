"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { IniciarOnboardingFields } from "./IniciarOnboardingFields"
import { fetchTemplates, iniciarOnboarding } from "@/services/onboarding"
import type { Empleado } from "@/types/empleado"
import type { OnboardingInstancia, OnboardingTemplate } from "@/types/onboarding"

/**
 * El modal de "Iniciar onboarding": elegir la persona y el template con el que arranca su proceso.
 *
 * Salió de `app/(dashboard)/onboarding/page.tsx` al migrar esa pantalla al patrón del bloque B.
 * Ese archivo estaba en **396 líneas contra un límite de 150** —deuda anotada en CLAUDE.md— y los
 * estados nuevos (esqueleto, error con reintento, vacío con acción) lo llevaban a 404: hacerlo
 * crecer no era una opción. El corte es por responsabilidad: la página LISTA procesos, el modal
 * INICIA uno.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 ERA UN DIÁLOGO ESCRITO A MANO, Y ESO NO ERA UN DETALLE DE ESTILO.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Tenía su propio `<div className="fixed inset-0 z-50 bg-black/40">` de scrim, su propio
 * `role="dialog" aria-modal` y sus propios botones con `bg-primary` escrito a mano. O sea: una
 * reimplementación parcial de `components/ui/dialog.tsx`, **sin lo que ese primitivo resuelve** —
 * el foco atrapado adentro del popup, el cierre con Escape, el `max-h` en `dvh` (con `vh` en
 * mobile el modal queda más alto que la pantalla porque la barra de direcciones cuenta), y el
 * ancho de 560px del patrón de formulario. Ahora sale del primitivo, con `patron="formulario"`.
 *
 * ⚠️ NO TIENE LA VALIDACIÓN EN DOS NIVELES DEL PATRÓN, y no es un olvido: tampoco tiene el
 * segundo. No hay un mensaje por campo — hay un único `error` que sale del servidor y se muestra
 * abajo, y el botón queda deshabilitado hasta que haya persona y template. Un banner
 * `<FormErrores>` diría "Revisá 0 campos" siempre, que es peor que no tenerlo.
 */
interface IniciarOnboardingModalProps {
  activos: OnboardingInstancia[]
  onClose: () => void
  onSuccess: (instancia: OnboardingInstancia) => void
}

export function IniciarOnboardingModal({ activos, onClose, onSuccess }: IniciarOnboardingModalProps) {
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([])
  // 🔴 El empleado se guarda ENTERO, no solo su id: la lista de la que antes se lo recuperaba
  // (`empleados.find`) ya no existe —el combobox busca contra el backend— y `empresa_id` es lo
  // que filtra los templates. Con solo el id, ese filtro se caería a "todos los templates".
  const [selected, setSelected] = useState<Empleado | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState("")
  const [iniciando, setIniciando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const selectedId = selected?.id ?? ""

  useEffect(() => {
    fetchTemplates().then(setTemplates).catch(() => setError("No se pudieron cargar los datos"))
  }, [])

  // Quienes ya tienen uno en curso no se pueden elegir: el backend los rechaza con 409.
  const yaTienen = activos.map((o) => o.empleado_id)

  // Filtra templates para mostrar solo los de la misma empresa que el empleado elegido
  const filteredTemplates =
    selected?.empresa_id
      ? templates.filter((t) => t.empresa_id === selected.empresa_id)
      : templates

  useEffect(() => {
    setSelectedTemplateId(filteredTemplates.length > 0 ? filteredTemplates[0].id : "")
  }, [selectedId])  // eslint-disable-line react-hooks/exhaustive-deps

  async function handleIniciar() {
    if (!selectedId || iniciando) return
    setIniciando(true)
    setError(null)
    try {
      const instancia = await iniciarOnboarding(selectedId, selectedTemplateId || undefined)
      onSuccess(instancia)
    } catch {
      setError("No se pudo iniciar el onboarding. Verificá que el colaborador no tenga uno activo.")
      setIniciando(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>Iniciar onboarding</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que el
              usuario no puede deducir de dos selectores es que el template elegido **fija el
              checklist entero** del proceso: las tareas se copian al iniciarlo, así que cambiar
              el template después no cambia los onboardings ya abiertos. */}
          <DialogDescription>
            Las tareas del template se copian al proceso en el momento de iniciarlo: editar el
            template después no toca los onboardings que ya estén en curso.
          </DialogDescription>
        </DialogHeader>

        <IniciarOnboardingFields
          selectedId={selectedId}
          onSelectEmpleado={setSelected}
          yaTienen={yaTienen}
          templates={filteredTemplates}
          selectedTemplateId={selectedTemplateId}
          onSelectTemplate={setSelectedTemplateId}
          error={error}
        />

        <DialogFooter>
          <Button variant="outline" className="min-h-11" onClick={onClose} disabled={iniciando}>
            Cancelar
          </Button>
          <Button
            className="min-h-11"
            onClick={handleIniciar}
            disabled={!selectedId || !selectedTemplateId || iniciando}
          >
            {iniciando ? "Iniciando…" : "Iniciar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
