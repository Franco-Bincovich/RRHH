import type { FiltroCampo } from "@/components/ui/filtrosTipos"
import type { Area } from "@/types/area"

/**
 * El único filtro del mapa 9-box: el área. Función pura, sin JSX y sin estado — la página conserva
 * el `useState` y acá se arma la descripción del control, que es lo que `FiltersBar` renderiza y
 * lo que `chipsDeCampos` convierte en chip.
 *
 * 🔑 EL PUNTO DE PASARLO POR ACÁ NO ES LA BARRA, ES EL CHIP: la etiqueta del chip sale de las
 * MISMAS `opciones` que llenan el selector, así que no puede decir un uuid ni un nombre viejo.
 * Antes el `<Select>` estaba escrito a mano en la tab y el vacío decía "esta área" — sin nombrar
 * cuál—, que es justo la frase que el patrón viene a sacar (§3).
 *
 * ⚠️ ESTE FILTRO ES CLIENT-SIDE Y ESO ACÁ ES CORRECTO. La invariante 1 del bloque B —"si el filtro
 * afecta al export, va server-side"— no aplica: **el mapa no exporta y no pagina**.
 * `GET /api/sucesion/mapa-talento` devuelve el padrón entero con potencial y desempeño cargados, y
 * la tab lo reparte en nueve casilleros; recortar por área en el backend no cambiaría ni el total
 * ni una fila de un archivo que nadie descarga.
 *
 * ⚠️ Y el nombre del área va SOLO, sin sufijo de empresa (`etiquetaArea`): esa función necesita la
 * lista de empresas y esta pantalla no la carga. Con el sidebar en consolidado dos áreas homónimas
 * de dos sociedades se leerían igual — límite conocido, no un olvido. El día que se encienda el
 * módulo, cargar empresas y pasar por `etiquetaArea` es el cambio de una línea.
 */
export function construirCamposSucesion({
  areas, area, setArea,
}: {
  areas: Area[]
  area: string
  setArea: (v: string) => void
}): FiltroCampo[] {
  return [
    {
      tipo: "select",
      label: "Área",
      value: area,
      onChange: setArea,
      opciones: areas.map((a) => ({ value: a.id, label: a.nombre })),
      opcionTodos: "Todas las áreas",
    },
  ]
}
