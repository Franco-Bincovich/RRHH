import { ENTIDAD_LABEL, EVENTO_LABEL } from "@/components/features/auditoria/auditLabels"
import type { FiltroCampo, RangoFechas } from "@/components/ui/FiltersBar"
import type { UsuarioOption } from "@/services/usuarios"

/**
 * Armado del array de <FiltersBar> para /auditoria. **Reemplaza a `AuditFilters.tsx`**, que era la
 * barra de filtros propia más rica del repo: cinco controles con label visible, escritos a mano.
 *
 * 🔴 QUÉ SE GANÓ AL MIGRARLA, además de los chips. `AuditFilters` cargaba una constante
 * `FIELD_CLASS` **byte-idéntica a la fórmula de altura del `size="sm"` de `select.tsx`**, con un
 * comentario que decía —textualmente— que eran "dos lugares con un solo valor, y el que se olvide
 * vuelve a partir la barra". Ese comentario describía una deuda que este archivo **elimina**: los
 * cinco controles pasan a salir del mismo primitivo (`FiltrosCampo`), así que ya no hay dos
 * lugares. El archivo entero se borró.
 *
 * ⚠️ LO ÚNICO QUE CAMBIA DE FORMA: "Desde" y "Hasta" eran DOS campos `date` independientes y ahora
 * son UN `daterange`. Emiten el mismo par `fecha_desde`/`fecha_hasta` al backend —no se pierde
 * ningún filtro— pero producen **un solo chip** ("Período: 01/03/2026 – 31/03/2026") en vez de dos.
 * Es lo que ya hacen vacaciones y ausencias, y lo que hace que el contador de "filtros activos"
 * cuente un período como un filtro y no como dos.
 *
 * 🔴 QUÉ QUEDA DETRÁS DE "MÁS FILTROS" Y POR QUÉ SÓLO USUARIO. La pregunta diaria de un log de
 * auditoría es **qué pasó y cuándo** —"¿qué se tocó en vacaciones este mes?"—, así que Sección,
 * Evento y Período quedan a la vista. **Usuario** es el recorte a UNA persona: es una
 * investigación puntual ("¿qué borró Fulano?"), el mismo criterio con el que Colaborador quedó
 * avanzado en ausencias y vacaciones. Sigue a un click y, si viene puesto, el panel arranca
 * abierto y además lo delata su chip.
 *
 * ⚠️ `registro_id` NO tiene control en esta barra —ni lo tenía antes—, aunque el backend lo acepta
 * en el listado Y en el export. Es el filtro "todo lo que le pasó a ESTE registro", y hoy no hay
 * forma de ponerlo desde la UI: está reportado como filtro server-side sin control propio, no
 * cableado. El día que se cablee, el lugar natural es un link desde la ficha de cada entidad.
 *
 * Sin estado ni efectos: recibe valores y setters, devuelve la descripción de los controles. El
 * reset de página lo dispara `onFiltroChange` en cada onChange (invariante 4 del bloque B).
 */
export const ENTIDAD_OPCIONES = Object.entries(ENTIDAD_LABEL).map(([value, label]) => ({ value, label }))
export const EVENTO_OPCIONES = Object.entries(EVENTO_LABEL).map(([value, label]) => ({ value, label }))

export interface ArgsCamposAuditoria {
  entidad: string
  setEntidad: (v: string) => void
  evento: string
  setEvento: (v: string) => void
  usuarioId: string
  setUsuarioId: (v: string) => void
  usuarios: UsuarioOption[]
  rango: RangoFechas
  setRango: (v: RangoFechas) => void
  onFiltroChange: () => void
}

export function construirCampos(a: ArgsCamposAuditoria): FiltroCampo[] {
  return [
    { tipo: "select" as const, label: "Sección", value: a.entidad, opcionTodos: "Todas las secciones",
      onChange: (v: string) => { a.setEntidad(v); a.onFiltroChange() }, opciones: ENTIDAD_OPCIONES },
    { tipo: "select" as const, label: "Evento", value: a.evento, opcionTodos: "Todos los eventos",
      onChange: (v: string) => { a.setEvento(v); a.onFiltroChange() }, opciones: EVENTO_OPCIONES },
    { tipo: "daterange" as const, label: "Período", value: a.rango,
      onChange: (v: RangoFechas) => { a.setRango(v); a.onFiltroChange() } },
    ...((a.usuarios.length > 0) || a.usuarioId ? [{ tipo: "select" as const, label: "Usuario", value: a.usuarioId, opcionTodos: "Todos los usuarios", avanzado: true,
      onChange: (v: string) => { a.setUsuarioId(v); a.onFiltroChange() },
      opciones: a.usuarios.map((u) => ({ value: u.id, label: `${u.nombre} ${u.apellido}` })) }] : []),
  ]
}
