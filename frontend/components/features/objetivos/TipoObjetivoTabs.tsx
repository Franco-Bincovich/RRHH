"use client"

import { Tab, TabList, Tabs } from "@/components/ui/tabs"
import type { OpcionVista } from "@/components/features/objetivos/_catalogosObjetivos"
import type { TipoObjetivo } from "@/types/objetivo"

/**
 * El selector de VISTA de /objetivos: anual, operativo, o las dos.
 *
 * 🔴 "VISTA" SIGNIFICA DOS COSAS EN ESTE MÓDULO Y NO SON LA MISMA — leer antes de tocar nada.
 *   · ACÁ, vista = a cuál de los dos conjuntos pertenece el objetivo (`objetivos.tipo`, migración
 *     119). Es un dato de la fila: la anual es la que Capital Humano le presenta al directorio.
 *     **El recorte lo hace el BACKEND** (`?tipo=`), como cualquier otro filtro del bloque B.
 *   · En `ObjetivosVistas.tsx`, "vista" = Tablero o Lista, o sea CÓMO se dibuja lo que llegó.
 *     Ese eje no toca la red.
 * Se combinan: la vista anual mirada como tablero, la operativa como lista.
 *
 * 🔴 EL FILTRO ES SERVER-SIDE Y NO PUEDE NO SERLO. Filtrar por `tipo` en el cliente sobre `items`
 * sería mentir dos veces: el contador del encabezado sale de `total`, que el backend calcula
 * sobre el filtro entero, y el EXPORT lo arma el backend, así que el Excel saldría con las dos
 * vistas mientras la pantalla muestra una. Es la invariante 1 del bloque B, con el agravante de
 * que este listado devuelve un ÁRBOL: recortar en el cliente dejaría hijos sin padre o al revés.
 * El endpoint ya acepta `tipo` en el listado Y en el export; lo fija `filtros-export.test.ts`.
 *
 * 🔴 LAS ETIQUETAS LAS TRAE EL BACKEND (`GET /api/objetivos/campos`), no se escriben acá. Los dos
 * `value` son el literal del CHECK de la migración 119 y del `Literal` de Pydantic; una copia
 * local que derive ofrecería un valor que el backend rechaza con 422. "Todas" sí es nuestro: no
 * es un tipo, es la AUSENCIA del filtro — mandar `tipo=""` daría 422 y `tipo=todas` daría cero.
 *
 * ⚠️ EL DEFAULT ES "Todas", y es la opción conservadora: hoy el tablero muestra todo, así que
 * arrancar en una de las dos vistas ESCONDERÍA objetivos que hasta ahora se veían, sin que nadie
 * lo pidiera. Cambiarlo es una decisión de producto de una línea, en `useFiltrosObjetivos`.
 *
 * Presentacional y controlado: sin estado, sin fetch. El catálogo lo pide `_catalogosObjetivos`.
 */
export function TipoObjetivoTabs(
  { vistas, valor, onCambio }: {
    vistas: OpcionVista[]
    valor: TipoObjetivo | ""
    onCambio: (v: TipoObjetivo | "") => void
  },
) {
  // Sin catálogo no hay selector. Dibujar sólo "Todas" sería una barra de una sola solapa que no
  // elige nada, y el listado sin `tipo` ya muestra exactamente eso.
  if (vistas.length === 0) return null

  return (
    <Tabs value={valor} onValueChange={(v) => onCambio(v as TipoObjetivo | "")}>
      <TabList className="mb-4" aria-label="Vista de objetivos">
        <Tab value="">Todas</Tab>
        {vistas.map((v) => <Tab key={v.value} value={v.value}>{v.label}</Tab>)}
      </TabList>
    </Tabs>
  )
}
