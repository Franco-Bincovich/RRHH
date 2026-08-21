import { Info } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/**
 * Una nota informativa: **neutra**, con ícono, en el flujo de la pantalla.
 *
 * 🔴 QUÉ LA DIFERENCIA DE `AvisoImpacto`, que es el otro bloque con ícono del sistema. Aquel es
 * **ámbar** y dice *"esto va a PASAR cuando aprietes Guardar"* — una consecuencia que el usuario
 * no puede deducir de lo que ve. Esto es lo otro: una explicación de **cómo funciona lo que está
 * mirando**, o un límite del sistema que conviene saber ANTES de cargar veinte cosas.
 *
 * Neutra y no ámbar a propósito: el ámbar es la señal que la pantalla reserva para las
 * consecuencias reales, y gastarla en instrucciones la vuelve ruido. Si todo es amarillo, nada
 * lo es.
 *
 * Nació con dos consumidores, que es la condición para que valga la pena ser un primitivo: la
 * nota que explica por qué el bloque de requisitos está partido en cuatro campos (adentro del
 * formulario de perfiles) y el aviso de que el puente perfil → vacante todavía no existe (arriba
 * del listado). Los dos dicen "así funciona esto", ninguno de los dos dice "cuidado".
 */
export function NotaInfo({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-md border bg-muted/50 px-3 py-2.5 text-xs leading-relaxed text-muted-foreground",
        className,
      )}
    >
      <Info className="mt-px size-4 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}
