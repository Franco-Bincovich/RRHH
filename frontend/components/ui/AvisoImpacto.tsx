import { AlertTriangle } from "lucide-react"

/**
 * El aviso de impacto del patrón de modal de formulario (`docs/SISTEMA-DE-DISENO.md` §3):
 * **ámbar, sobre el pie**. Se pasa por la prop `aviso` de `<DialogFooter>`, que lo ancla arriba
 * de los botones — el cuerpo del modal scrollea y un aviso ahí adentro desaparece justo en el
 * formulario largo, que es donde más falta hace.
 *
 * 🔴 QUÉ ES UN AVISO DE IMPACTO Y QUÉ NO. No es una advertencia de validación —eso es el borde
 * rojo del campo— ni un cartel de ayuda. Es **una consecuencia real de apretar Guardar que el
 * usuario no puede deducir de lo que ve en pantalla**: que el alta va a contar en la dotación
 * del mes, que el mail se manda a 40 personas, que la baja libera la licencia. Si el aviso
 * describe lo que el formulario ES en vez de lo que va a PASAR, no es un aviso de impacto y no
 * va en ámbar: va en el subtítulo del encabezado.
 *
 * Ámbar y no rojo: no hay nada mal. El rojo del formulario es exclusivamente del error.
 */
export function AvisoImpacto({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-warning-line bg-warning-wash px-3 py-2 text-xs text-warning">
      <AlertTriangle className="mt-px size-4 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}
