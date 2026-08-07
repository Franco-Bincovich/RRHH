"use client"

import { Button } from "@/components/ui/button"

interface Props {
  /** Cuántos van a recibir el mail. Sale del MISMO cálculo que arma el body, no de `sel.size`. */
  cantidad: number
  /** true = ya se pidió confirmación y este es el paso irreversible. */
  confirmando: boolean
  enviando: boolean
  sinEmpresa: boolean
  onPedirConfirmacion: () => void
  onVolver: () => void
  onEnviar: () => void
  onCancelar: () => void
}

export const AVISO_IRREVERSIBLE = "Esta acción no se puede deshacer."

/**
 * El pie del modal de envío: el aviso y los botones. Presentacional; extraído del
 * `<DialogFooter>` que lo envuelve —y no junto con él— por dos motivos, los mismos que
 * `AccionesDelPie`: el footer tiene que quedar como hijo LITERAL de `DialogContent` (ver
 * `partirHijos` en ui/dialog), y así el contenido se puede renderizar en la suite, que corre
 * sin jsdom y no puede montar el portal del diálogo.
 *
 * 🔴 EL ENVÍO PASA POR DOS APRETADAS, Y LA SEGUNDA DICE EL NÚMERO. Mandar mails a nombre de la
 * empresa es lo único de este módulo que no se puede deshacer: llega a gente de afuera y no hay
 * "deshacer". Un solo clic sobre un botón que dice "Enviar (17)" es demasiado poco para eso, y
 * el número tiene que estar en el TEXTO de la confirmación —no solo en el botón— porque es el
 * dato que distingue "le mando a una persona" de "le mando a toda la empresa".
 *
 * 🔴 EN MODO CONSOLIDADO NO SE PUEDE ENVIAR, y no es una limitación caprichosa: el backend
 * resuelve la plantilla con la empresa del request, y sin empresa solo encuentra la GLOBAL. O
 * sea que el mail saldría con un texto DISTINTO del que se ve en pantalla, sin ningún error —
 * el peor desenlace posible para una acción irreversible.
 */
export function EnvioPie({
  cantidad, confirmando, enviando, sinEmpresa,
  onPedirConfirmacion, onVolver, onEnviar, onCancelar,
}: Props) {
  if (sinEmpresa) {
    return (
      <p className="text-sm text-muted-foreground sm:self-center">
        Para enviar, elegí una empresa en el selector de arriba a la izquierda. En
        &quot;Todas las empresas&quot; no se sabe con qué texto saldría el mail.
      </p>
    )
  }

  if (!confirmando) {
    return (
      <>
        <Button variant="outline" onClick={onCancelar}>Cancelar</Button>
        <Button onClick={onPedirConfirmacion} disabled={cantidad === 0}>
          Enviar ({cantidad})
        </Button>
      </>
    )
  }

  return (
    <>
      <p className="text-sm text-foreground sm:mr-auto sm:self-center">
        Vas a enviar a <strong>{cantidad}</strong> persona{cantidad === 1 ? "" : "s"}.{" "}
        {AVISO_IRREVERSIBLE}
      </p>
      <Button variant="outline" onClick={onVolver} disabled={enviando}>Volver</Button>
      <Button onClick={onEnviar} disabled={enviando || cantidad === 0}>
        {/* El texto del botón ES el indicador de carga: el envío tarda hasta 120 s (presupuesto
            del backend) y un botón que no cambia se lee como un clic que no registró. */}
        {enviando ? "Enviando… puede tardar un minuto" : "Sí, enviar"}
      </Button>
    </>
  )
}
