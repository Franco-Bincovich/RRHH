"use client"

import { HistorialTabla } from "@/components/features/comunicacion/HistorialTabla"
import { useHistorialMails } from "@/components/features/comunicacion/useHistorialMails"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"

/**
 * Pestaña "Historial" de /comunicacion: qué mails salieron, a quién y —si falló— por qué.
 *
 * 🔴 EL DATO EXISTÍA Y NO LO VEÍA NADIE. `mail_enviado` se escribe desde la migración 087 y
 * hasta hoy no tenía endpoint ni pantalla: cuando alguien decía "no me llegó", la única forma de
 * contestar era abrir la base. Eso es lo que esta pestaña cierra.
 *
 * Orquestador: junta el hook con la barra y la tabla, y nada más. La carga vive en
 * `cargarHistorialMails` (testeable sin jsdom) y el render en `HistorialTabla` (testeable con
 * `renderToStaticMarkup`); acá queda solo el cableado, que es lo que la suite no puede ver.
 *
 * ⚠️ No hay export ni paginado, y las dos ausencias son decisiones: ver `services/mails.ts`.
 */
export function HistorialMails() {
  const { campos, items, limite, cargando, error, recargar } = useHistorialMails()

  /*
   * "Hay filtros puestos" ya no es una bandera propia: son los CHIPS, derivados de los mismos
   * campos que dibujan la barra. Es el mismo dato con una ventaja — además de saber SI hay
   * filtros, el vacío puede decir CUÁLES ("No hay mails con estado No entregados").
   */
  const chips = chipsDeCampos(campos)

  return (
    <div>
      {/* `panel`: la forma completa del patrón de filtros (caja propia y los chips de la fila
          inferior). Los dos filtros van a la vista: con dos —y uno es un rango de fechas—
          esconder alguno detrás de "Más filtros" no compra nada. */}
      <FiltersBar campos={campos} panel disabled={cargando} />

      <HistorialTabla
        items={items} cargando={cargando} error={error}
        chips={chips} onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        onReintentar={recargar}
      />

      {/* El aviso de recorte solo cuando el recorte MUERDE. Decirlo siempre lo vuelve ruido y
          se deja de leer justo cuando importa. */}
      {!error && !cargando && limite > 0 && items.length >= limite && (
        <p className="mt-3 text-xs text-muted-foreground">
          Se muestran los {limite} envíos más recientes. Acotá por fecha para ver otros.
        </p>
      )}
    </div>
  )
}
