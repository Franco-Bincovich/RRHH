"use client"

import { Plus } from "lucide-react"

import { AccionBloqueada } from "@/components/ui/AccionBloqueada"
import { Button } from "@/components/ui/button"
import { useEmpresaConcreta } from "@/hooks/useEmpresaConcreta"

/**
 * El botón de alta de un recordatorio, con su bloqueo en vista consolidada.
 *
 * 🔴 SALIÓ DE `eventos/page.tsx` POR DOS RAZONES, y la segunda es la que lo justifica.
 * La primera es de líneas: la página estaba en 150/150 y envolver sus DOS altas —la del
 * encabezado y la de "Crear el primero" del estado vacío— en `AccionBloqueada` la dejaba en 166.
 * La segunda es que esas dos altas son **el mismo botón dicho dos veces**, y hasta ahora estaban
 * escritas dos veces: cualquier cambio en una (el bloqueo, justamente) había que acordarse de
 * hacerlo en la otra. Con un componente, el estado vacío no puede quedar ofreciendo un alta que
 * el encabezado ya bloqueó.
 *
 * 🔑 EL HOOK VIVE ACÁ Y NO EN LA PÁGINA. Es lo contrario de lo que hace `/configuracion` —donde
 * los gates se deciden en la página— y la diferencia es real: allá el motivo lo consumen tres
 * componentes distintos y hay que verlos juntos para entender por qué uno se oculta y otro se
 * muestra en solo lectura; acá lo consume una sola cosa, que es este botón. Bajarlo por props
 * desde la página sería atarla a un detalle que no decide.
 *
 * ⚠️ SÓLO EL ALTA SE BLOQUEA. `PUT /{id}`, `PUT /{id}/resuelta` y `DELETE /{id}` usan
 * `get_empresa_id` (aceptan `None`), así que editar, resolver y borrar funcionan igual en modo
 * consolidado — y tiene sentido: esas tres se hacen sobre un recordatorio que ya tiene empresa.
 * Bloquear la fila entera "por consistencia" sacaría acciones que sí andan.
 */
export function AltaRecordatorioBoton({
  onClick,
  children = "Nuevo recordatorio",
  conIcono = true,
}: {
  onClick: () => void
  /** El texto del botón. El estado vacío dice "Crear el primero". */
  children?: React.ReactNode
  conIcono?: boolean
}) {
  const { motivo } = useEmpresaConcreta()

  return (
    <AccionBloqueada motivo={motivo}>
      {(bloqueada) => (
        <Button className="min-h-11" disabled={bloqueada} onClick={onClick}>
          {conIcono && <Plus />}
          {children}
        </Button>
      )}
    </AccionBloqueada>
  )
}
