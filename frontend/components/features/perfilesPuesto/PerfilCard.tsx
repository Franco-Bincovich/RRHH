import { Pencil, RotateCcw, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import type { CamposPerfilResponse, PerfilPuesto } from "@/types/perfilPuesto"

import { etiquetaDe, vocabularioDe } from "./_perfilCampos"

/**
 * Un perfil de puesto, como TARJETA (`docs/SISTEMA-DE-DISENO.md` §5: "cada perfil una tarjeta:
 * nombre del puesto, nivel, modalidad, resumen"). Tarjeta y no fila porque un perfil es algo que
 * **se elige**, no un registro que se compara con el de al lado.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 LOS CUATRO CAMPOS DE §5 Y NINGUNO MÁS. Lo que falta, falta a propósito.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * §7 del sistema de diseño y `schemas/perfil_puesto.py:14-18` dicen lo MISMO y en el mismo
 * orden: un perfil **no tiene competencias, no tiene ubicación y no tiene contador de ocupantes
 * ni de vacantes**. Las tres las inventó un prototipo anterior. No se agregan ni como `0`: un
 * "0 vacantes" en la tarjeta se lee como *"este perfil no tiene búsquedas abiertas"*, que es una
 * afirmación que el sistema no puede hacer — no existe el vínculo que la sostendría.
 *
 * ⚠️ EL CHIP DE "BAJA" NO ES UN QUINTO CAMPO: aparece SOLO cuando el perfil está dado de baja, y
 * sólo se lo puede ver con el filtro "Ver bajas" puesto. Sin él, prender ese filtro sumaría
 * tarjetas indistinguibles de las activas y la pantalla estaría mintiendo sobre qué está vigente.
 *
 * ⚠️ NI `interactive` NI hover: la tarjeta no es un control. No hay pantalla de detalle a la que
 * llevar —el listado ya trae los 12 campos y el resto se lee en el formulario—, y ponerle
 * elevación al apuntar prometería un click que no existe. Los controles son los dos botones.
 */
export function PerfilCard({
  perfil, catalogos, canWrite, onEdit, onBaja, onReactivar,
}: {
  perfil: PerfilPuesto
  /** Para traducir `nivel` y `modalidad` a su etiqueta legible. `null` si `/campos` no cargó. */
  catalogos: CamposPerfilResponse | null
  canWrite: boolean
  onEdit: (p: PerfilPuesto) => void
  onBaja: (p: PerfilPuesto) => void
  onReactivar: (p: PerfilPuesto) => void
}) {
  // Sin catálogo se muestra el valor crudo ("semi_senior") antes que nada: la tarjeta tiene que
  // decir el nivel aunque el endpoint de labels no haya contestado.
  const nivel = catalogos
    ? etiquetaDe(vocabularioDe("nivel", catalogos), perfil.nivel)
    : perfil.nivel ?? ""
  const modalidad = catalogos
    ? etiquetaDe(vocabularioDe("modalidad", catalogos), perfil.modalidad)
    : perfil.modalidad ?? ""

  return (
    <Card padding="sm" interactive className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 text-sm font-semibold break-words text-foreground">
          {perfil.nombre}
        </h3>
        {!perfil.activo && (
          <Badge variant="outline" className="shrink-0 bg-danger-wash text-destructive border-danger-line">
            Baja
          </Badge>
        )}
      </div>

      {/* Nivel y modalidad: los dos atributos que §5 pide para poder ELEGIR de un vistazo. Un
          perfil puede no tener ninguno de los dos cargados —los once campos que no son el nombre
          son opcionales—, y en ese caso la fila de chips no se dibuja en vez de mostrar vacíos. */}
      {(nivel || modalidad) && (
        <div className="flex flex-wrap gap-1.5">
          {nivel && <Badge variant="outline">{nivel}</Badge>}
          {modalidad && <Badge variant="outline">{modalidad}</Badge>}
        </div>
      )}

      {/* El resumen. `line-clamp-3` y no un truncado en JS: cortar el string por cantidad de
          caracteres parte palabras y da distinto según el ancho de la tarjeta. */}
      <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
        {perfil.descripcion || "Sin descripción."}
      </p>

      {canWrite && (
        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          <Button variant="outline" size="sm" onClick={() => onEdit(perfil)}>
            <Pencil className="size-3.5" aria-hidden="true" />
            Editar
          </Button>
          {/* La baja es LÓGICA y reversible: por eso el par de acciones es baja/reactivar y no un
              borrado. Ver el service — un DELETE físico le arrancaría en silencio la trazabilidad
              a toda vacante creada desde este perfil (`ON DELETE SET NULL`). */}
          {perfil.activo ? (
            <Button variant="outline" size="sm" onClick={() => onBaja(perfil)}>
              <Trash2 className="size-3.5" aria-hidden="true" />
              Dar de baja
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={() => onReactivar(perfil)}>
              <RotateCcw className="size-3.5" aria-hidden="true" />
              Reactivar
            </Button>
          )}
        </div>
      )}
    </Card>
  )
}
