"use client"

import { CheckCircle2, XCircle } from "lucide-react"

import type { ImportacionObjetivosResultado } from "@/types/importacionObjetivos"

/**
 * Paso 3 del modal: qué se cargó y qué no.
 *
 * Exportado y separado del modal para poder testearlo sin jsdom (el `Dialog` monta por portal).
 *
 * 🔴 EL RESULTADO NO ES BINARIO, Y ESTE COMPONENTE EXISTE PARA NO MENTIR SOBRE ESO. El lote no
 * aborta por una fila con problemas: se cargan las válidas y se reportan las otras, así que
 * `importados > 0` y `errores.length > 0` conviven. Un cartel de "Importación completada" a
 * secas sobre un lote de 40 filas donde entraron 12 es exactamente la clase de mentira que este
 * repo ya pagó en otros lados — el usuario cierra el modal creyendo que terminó.
 *
 * Por eso hay TRES estados y no dos:
 *   · nada cargado  → error, y se dice que no entró nada.
 *   · todo cargado  → éxito limpio.
 *   · parcial       → éxito ATENUADO, con el conteo de las dos cosas y el detalle de las que no.
 */
export function ImportObjetivosResultadoDetalle(
  { resultado }: { resultado: ImportacionObjetivosResultado },
) {
  const { importados, errores } = resultado
  const fallidas = errores.length
  const parcial = importados > 0 && fallidas > 0
  const nadaCargado = importados === 0

  return (
    <div className="space-y-3 py-2">
      <div
        className={[
          "flex items-start gap-3 rounded-lg border p-3",
          nadaCargado
            ? "border-destructive/30 bg-destructive/5"
            : parcial
              ? "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950"
              : "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950",
        ].join(" ")}
      >
        {nadaCargado ? (
          <XCircle className="mt-0.5 size-5 shrink-0 text-destructive" />
        ) : (
          <CheckCircle2
            className={`mt-0.5 size-5 shrink-0 ${parcial ? "text-amber-600 dark:text-amber-400" : "text-emerald-600 dark:text-emerald-400"}`}
          />
        )}
        <div className="text-sm">
          {nadaCargado ? (
            <p className="font-medium text-destructive">
              No se cargó ningún objetivo. {fallidas > 0 && `Las ${fallidas} filas del archivo tienen problemas.`}
            </p>
          ) : parcial ? (
            <>
              <p className="font-medium text-foreground">
                Se cargaron {importados} de {importados + fallidas} objetivos.
              </p>
              <p className="text-muted-foreground">
                Las otras {fallidas} quedaron sin cargar. El detalle está abajo: corregilas en el
                archivo y volvé a importarlo — las que ya entraron se van a duplicar si las dejás.
              </p>
            </>
          ) : (
            <p className="font-medium text-foreground">
              Se cargaron los {importados} objetivos del archivo.
            </p>
          )}
        </div>
      </div>

      {fallidas > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <p className="border-b bg-muted/50 px-3 py-2 text-xs font-medium text-muted-foreground">
            Filas que no se cargaron
          </p>
          <table className="w-full text-sm">
            <tbody>
              {errores.map((e) => (
                <tr key={`r-${e.fila}`} className="border-b last:border-0">
                  <td className="w-14 px-3 py-2 text-muted-foreground">{e.fila}</td>
                  <td className="px-3 py-2 font-medium text-foreground">{e.identificador}</td>
                  <td className="px-3 py-2 text-destructive">{e.motivo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
