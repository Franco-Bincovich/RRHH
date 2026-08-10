import { AlertTriangle } from "lucide-react"

import { DIAS_HACIA_ATRAS, MAX_HORAS_DIA } from "@/components/features/horasPublico/logica"

/**
 * Los avisos del mockup. PRESENTACIONAL y sin props: es un texto fijo.
 *
 * 🔴 EL DE "NO SE PUEDE EDITAR" NO ES DECORATIVO. Es la única advertencia que el usuario recibe
 * antes de una acción IRREVERSIBLE para él: el backend no expone ningún update ni delete para el
 * empleado, por decisión de producto. Sin este cartel, la primera vez que alguien se equivoque
 * va a buscar el botón de editar, no lo va a encontrar, y va a creer que la pantalla está rota.
 *
 * Los límites se leen de `logica.ts`, que los espeja del backend: escribirlos a mano acá los
 * dejaría diciendo "12" el día que el tope cambie.
 */
export function AvisoIrreversible() {
  return (
    <div className="mb-4 flex gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600" />
      <div className="space-y-1 text-sm">
        <p className="font-medium text-foreground">
          Revisá bien antes de cargar. Una vez enviado no se puede editar ni borrar.
        </p>
        <p className="text-muted-foreground">
          Si te equivocaste, avisale a Recursos Humanos. Podés cargar hasta{" "}
          {DIAS_HACIA_ATRAS} días hacia atrás, con un máximo de {MAX_HORAS_DIA} horas por día.
        </p>
      </div>
    </div>
  )
}
