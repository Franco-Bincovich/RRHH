import { AlertCircle } from "lucide-react"
import type { ReactNode } from "react"

/**
 * El aviso ROJO de un error que vino de AFUERA: lo que respondió el backend, o que no se pudo
 * llegar a él. Tercer miembro de la familia de bloques con ícono del sistema, junto a
 * `AvisoImpacto` (ámbar, "esto va a pasar") y `NotaInfo` (neutro, "así funciona esto").
 *
 * 🔴 POR QUÉ EXISTE. La misma caja roja estaba escrita a mano en TRES pantallas, con tres
 * versiones distintas del mismo color: `border-destructive/30 bg-destructive/10` en `/login`,
 * `border-destructive/30 bg-destructive/10` en el form de cambio de contraseña y
 * `border-destructive/40 bg-destructive/10` en `/horas` — tres opacidades para decir lo mismo,
 * ninguna de ellas medida. Ahora usa los pares `--danger-*` de la paleta, que sí están medidos en
 * los dos temas por `app/contrasteTokens.test.ts`. Las tres pantallas son públicas o de acceso, y
 * son las que más gente de afuera del equipo ve.
 *
 * 🔴 NO ES `FormErrores`, Y NO SE PISAN. `FormErrores` cuenta los errores LOCALES de validación
 * ("Revisá 2 campos"); esto muestra un mensaje que el sistema no escribió. Nunca aparecen juntos
 * por construcción: si la validación local falla, no se manda el request, así que no puede haber
 * respuesta del servidor todavía.
 *
 * 🔴 NO ES `ErrorState` TAMPOCO. `ErrorState` reemplaza la pantalla —"no se pudieron traer los
 * datos, reintentá"—; esto convive con el formulario, que sigue en pantalla con lo que la persona
 * ya escribió. Poner `ErrorState` ante una contraseña equivocada borraría el formulario.
 *
 * `role="alert"` para que el lector de pantalla lo anuncie al aparecer, que es el mismo momento en
 * que el usuario vidente lo ve.
 */
export function AvisoError({ children, ayuda }: {
  children: ReactNode
  /**
   * Segunda línea, en gris, para lo que se puede hacer al respecto. Se separa del mensaje porque
   * el mensaje lo escribe el backend y esto lo escribe la pantalla: mezclarlos haría creer que la
   * ayuda también vino del servidor y cambia según el caso.
   */
  ayuda?: ReactNode
}) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-md border border-danger-line bg-danger-wash px-3 py-2.5 text-sm text-destructive"
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
      <span className="min-w-0">
        <span className="block">{children}</span>
        {ayuda && <span className="mt-1 block text-xs text-muted-foreground">{ayuda}</span>}
      </span>
    </div>
  )
}
