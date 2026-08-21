import { AvisoImpacto } from "@/components/ui/AvisoImpacto"

import { DIAS_HACIA_ATRAS, MAX_HORAS_DIA } from "@/components/features/horasPublico/logica"

/**
 * Los avisos del mockup. PRESENTACIONAL y sin props: es un texto fijo.
 *
 * 🔴 EL DE "NO SE PUEDE EDITAR" NO ES DECORATIVO. Es la única advertencia que el usuario recibe
 * antes de una acción IRREVERSIBLE para él: el backend no expone ningún update ni delete para el
 * empleado, por decisión de producto. Sin este cartel, la primera vez que alguien se equivoque
 * va a buscar el botón de editar, no lo va a encontrar, y va a creer que la pantalla está rota.
 *
 * 🔴 AHORA ES UN `AvisoImpacto` Y ANTES ERA UN ÁMBAR ESCRITO A MANO (`border-amber-500/40
 * bg-amber-500/10 text-amber-600`). Encaja exactamente en la definición de ese primitivo —"una
 * consecuencia real de apretar el botón que el usuario no puede deducir de lo que ve"— y el ámbar
 * a mano tenía dos problemas: no pasa por los pares `--warning-*` que `app/contrasteTokens.test.ts`
 * mide en los dos temas, y `text-amber-600` sobre `bg-amber-500/10` en el tema OSCURO es casi
 * ilegible, que es justo donde este cartel tiene que leerse.
 *
 * Los límites se leen de `logica.ts`, que los espeja del backend: escribirlos a mano acá los
 * dejaría diciendo "12" el día que el tope cambie.
 *
 * ⚠️ Las dos líneas van como `<span className="block">` y no como `<p>`: `AvisoImpacto` envuelve
 * su contenido en un `<span>`, y un `<p>` adentro de un `<span>` es markup inválido.
 */
export function AvisoIrreversible() {
  return (
    <div className="mb-4">
      <AvisoImpacto>
        <span className="block font-medium">
          Revisá bien antes de cargar. Una vez enviado no se puede editar ni borrar.
        </span>
        <span className="mt-1 block">
          Si te equivocaste, avisale a Capital Humano. Podés cargar hasta{" "}
          {DIAS_HACIA_ATRAS} días hacia atrás, con un máximo de {MAX_HORAS_DIA} horas por día.
        </span>
      </AvisoImpacto>
    </div>
  )
}
