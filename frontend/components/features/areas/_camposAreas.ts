import type { FiltroCampo } from "@/components/ui/FiltersBar"

/**
 * Armado del array de <FiltersBar> para /areas. Aparte de la página por lo mismo que en el resto
 * del bloque: **es lo único que un test puede ejercitar sin DOM**, así que los chips se prueban
 * contra el cableado real y no contra campos inventados.
 *
 * 🔴 ACÁ HAY UN SOLO FILTRO Y NINGUNO ES AVANZADO. La regla del patrón ("un 'Más filtros' para el
 * resto") existe para que una fila de siete controles no tape la tabla; con uno, esconderlo atrás
 * de un botón deja la pantalla sin ningún control a la vista.
 *
 * 🔴 SE LLAMA "NOMBRE" Y NO "BUSCAR", y es una decisión del texto del VACÍO, no del control. El
 * chip usa la etiqueta del campo para armar la frase (`textoVacio`), así que con "Buscar" la
 * pantalla vacía diría *"No hay áreas con buscar Sistemas"*, que no es español. Con "Nombre" dice
 * *"No hay áreas con nombre Sistemas"*. El placeholder sigue diciendo "Buscar por nombre...", así
 * que el control se sigue leyendo como lo que es.
 *
 * ⚠️ NO HAY UN SELECT DE EMPRESA ACÁ, aunque el backend acepte `empresa_id` como Query. La empresa
 * de esta pantalla la manda el **selector del sidebar** (`getEmpresaActivaId()` en `useAreas`), y
 * es el único módulo donde ese valor viaja como query param en vez de header. Agregar un select
 * propio sería una segunda fuente para el mismo dato: dos controles de empresa en la misma
 * pantalla, uno de los cuales el usuario no ve. Está reportado como filtro sin control propio.
 *
 * Sin estado ni efectos: recibe el valor y su setter. El reset a página 1 lo hace `setSearch` de
 * `useAreas` (invariante 4 del bloque B), así que el chip lo hereda gratis al llamar al MISMO
 * `onChange` del control.
 */
export interface ArgsCamposAreas {
  search: string
  setSearch: (v: string) => void
}

export function construirCampos(a: ArgsCamposAreas): FiltroCampo[] {
  return [
    { tipo: "search" as const, label: "Nombre", value: a.search,
      placeholder: "Buscar por nombre...", onChange: a.setSearch },
  ]
}
