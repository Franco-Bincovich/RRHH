"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { TipoAusencia, TipoAusenciaUpdate } from "@/types/ausencias"

/**
 * Una fila del catálogo de tipos de ausencia.
 *
 * 🔴 EL BOTÓN DICE "Dar de baja", NO "Eliminar", y la diferencia no es cosmética: el tipo NO
 * se borra. `solicitudes_ausencia.tipo_id` es una FK sin ON DELETE, así que borrarlo fallaría
 * —y si no fallara, se llevaría el historial de ausencias con él. Lo que hace es desactivarlo:
 * sale de los selects y las ausencias viejas siguen mostrando su nombre. Un botón que dijera
 * "Eliminar" prometería algo que no pasa.
 */
export function TipoAusenciaFila({
  tipo, editable, ocupado, onEditar, indentado = false,
}: {
  tipo: TipoAusencia
  editable: boolean
  ocupado: boolean
  onEditar: (cambios: TipoAusenciaUpdate) => void
  /**
   * Es un SUBTIPO: se indenta debajo de su padre (migración 088).
   *
   * 🔴 UN PROP, NO UN COMPONENTE NUEVO NI UN ÁRBOL. La profundidad máxima está garantizada en 2
   * (la guarda vive en `_tipos_jerarquia`), así que un componente de árbol —expandir, colapsar,
   * estado por nodo— resolvería un problema que este modelo no tiene. Con 4 padres y una decena
   * de hijos, todo entra en pantalla sin colapsar nada.
   */
  indentado?: boolean
}) {
  return (
    <li className={`flex flex-wrap items-center gap-x-3 gap-y-2 py-2.5${indentado ? " pl-6" : ""}`}>
      <span className={`font-medium ${tipo.activo ? "" : "text-muted-foreground line-through"}`}>
        {indentado && <span aria-hidden className="mr-1.5 text-muted-foreground">└</span>}
        {tipo.nombre}
      </span>

      {tipo.es_base && <Badge variant="secondary">Base</Badge>}
      {tipo.empresa_id === null && <Badge variant="outline">General</Badge>}
      {!tipo.activo && <Badge variant="outline">Dado de baja</Badge>}

      <label className="ml-auto flex cursor-pointer items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={tipo.cuenta_ausentismo}
          disabled={!editable || ocupado}
          onChange={(e) => onEditar({ cuenta_ausentismo: e.target.checked })}
          className="h-4 w-4 cursor-pointer rounded border border-input accent-primary"
        />
        <span className="text-muted-foreground">Cuenta como ausentismo</span>
      </label>

      {editable && (
        <Button
          variant="ghost"
          size="sm"
          disabled={ocupado || (tipo.es_base && tipo.activo)}
          title={tipo.es_base && tipo.activo
            ? "Los tipos base no se pueden dar de baja"
            : undefined}
          onClick={() => onEditar({ activo: !tipo.activo })}
        >
          {tipo.activo ? "Dar de baja" : "Reactivar"}
        </Button>
      )}
    </li>
  )
}
