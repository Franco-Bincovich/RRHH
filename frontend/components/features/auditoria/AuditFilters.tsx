import { ENTIDAD_LABEL, EVENTO_LABEL } from "@/components/features/auditoria/auditLabels"
import type { AuditoriaFiltros } from "@/services/auditoria"
import type { UsuarioOption } from "@/services/usuarios"
import { Select } from "@/components/ui/select"

interface AuditFiltersProps {
  filtros: AuditoriaFiltros
  onChange: (filtros: AuditoriaFiltros) => void
  usuarios: UsuarioOption[]
}

/*
 * Los `<input>` de la barra (fecha y búsqueda). **La altura es la MISMA fórmula que la del
 * `size="sm"` de `components/ui/select.tsx`, y tiene que seguir siéndolo:** 44px de área táctil
 * abajo de `md`, y los 30px que `docs/SISTEMA-DE-DISENO.md` §3 fija para la barra de filtros de
 * `md` para arriba.
 *
 * 🔴 POR QUÉ ESTÁ ESCRITO ACÁ Y NO SALE DE UN PRIMITIVO. Al migrar los `<select>` a `<Select>`
 * (19/8/2026) los selectores tomaron esa altura y estos inputs se quedaron en `min-h-11`, así que
 * la barra quedó con controles de 30px al lado de controles de 44px — visiblemente peor que antes
 * de unificar nada. Igualarlos acá es el arreglo mínimo; el correcto es que estos inputs pasen a
 * `components/ui/input.tsx` con la misma variante de tamaño, y eso es una tanda de patrones.
 * ⚠️ Mientras tanto: si cambia la altura del `size="sm"` del select, cambia también acá. Son dos
 * lugares con un solo valor, y el que se olvide vuelve a partir la barra.
 */
const FIELD_CLASS =
  "h-11 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground md:h-[30px] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

/** Barra de filtros de auditoría. Cada control tiene label visible (doc UX). */
export function AuditFilters({ filtros, onChange, usuarios }: AuditFiltersProps) {
  function set(campo: keyof AuditoriaFiltros, valor: string) {
    onChange({ ...filtros, [campo]: valor || undefined })
  }

  return (
    <div className="mb-4 flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Sección
        <Select size="sm" className="w-auto" value={filtros.entidad ?? ""} onChange={(e) => set("entidad", e.target.value)}>
          <option value="">Todas</option>
          {Object.entries(ENTIDAD_LABEL).map(([v, label]) => (
            <option key={v} value={v}>{label}</option>
          ))}
        </Select>
      </label>

      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Evento
        <Select size="sm" className="w-auto" value={filtros.evento ?? ""} onChange={(e) => set("evento", e.target.value)}>
          <option value="">Todos</option>
          {Object.entries(EVENTO_LABEL).map(([v, label]) => (
            <option key={v} value={v}>{label}</option>
          ))}
        </Select>
      </label>

      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Usuario
        <Select size="sm" className="w-auto" value={filtros.usuario_id ?? ""} onChange={(e) => set("usuario_id", e.target.value)}>
          <option value="">Todos</option>
          {usuarios.map((u) => (
            <option key={u.id} value={u.id}>{u.nombre} {u.apellido}</option>
          ))}
        </Select>
      </label>

      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Desde
        <input type="date" className={FIELD_CLASS} value={filtros.fecha_desde ?? ""} onChange={(e) => set("fecha_desde", e.target.value)} />
      </label>

      <label className="flex flex-col gap-1 text-xs text-muted-foreground">
        Hasta
        <input type="date" className={FIELD_CLASS} value={filtros.fecha_hasta ?? ""} onChange={(e) => set("fecha_hasta", e.target.value)} />
      </label>
    </div>
  )
}
