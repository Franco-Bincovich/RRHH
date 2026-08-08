"use client"

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react"

import type { ImportacionObjetivosPreview } from "@/types/importacionObjetivos"

/**
 * Paso 2 del modal: qué filas se van a cargar y cuáles NO, con el motivo de cada una.
 *
 * Exportado y separado del `<DialogContent>` que lo envuelve **para poder testearlo**: `Dialog`
 * monta por portal y vitest corre sin jsdom, así que renderizar el modal entero devuelve string
 * vacío y cualquier aserción sobre él pasaría en el aire. Molde: `PlantillaAcciones.tsx`.
 *
 * 🔴 LAS FILAS CON PROBLEMAS SE MUESTRAN SIEMPRE, no detrás de un "ver detalles". Es la mitad
 * de la información: un preview que solo liste lo que va a entrar deja al usuario creyendo que
 * su archivo de 40 filas está entero cuando van a entrar 12. Van ARRIBA de las válidas por lo
 * mismo — es lo que tiene que leer antes de apretar Confirmar.
 */
export function ImportObjetivosPreviewTabla({ preview }: { preview: ImportacionObjetivosPreview }) {
  const validas = preview.filas_validas
  const errores = preview.errores

  return (
    <div className="space-y-3 py-2">
      <div className="flex flex-wrap gap-4 text-sm">
        <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="size-4" />
          {validas.length} {validas.length === 1 ? "objetivo se va a cargar" : "objetivos se van a cargar"}
        </span>
        {errores.length > 0 && (
          <span className="flex items-center gap-1.5 text-destructive">
            <XCircle className="size-4" />
            {errores.length} {errores.length === 1 ? "fila con problemas" : "filas con problemas"}
          </span>
        )}
      </div>

      {preview.total_hojas > 1 && preview.hoja_leida && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          El archivo tiene {preview.total_hojas} hojas y se leyó <strong>{preview.hoja_leida}</strong>,
          que es la primera. Las demás se ignoran.
        </p>
      )}

      {errores.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-destructive/30">
          <p className="border-b border-destructive/30 bg-destructive/5 px-3 py-2 text-xs font-medium text-destructive">
            Estas filas NO se van a cargar. El resto sí: corregilas y volvé a subir el archivo si
            las necesitás.
          </p>
          <table className="w-full text-sm">
            <tbody>
              {errores.map((e) => (
                <tr key={`e-${e.fila}`} className="border-b last:border-0">
                  <td className="w-14 px-3 py-2 text-muted-foreground">{e.fila}</td>
                  <td className="px-3 py-2 font-medium text-foreground">{e.identificador}</td>
                  {/* El motivo viene redactado por el backend para el usuario: se muestra tal cual. */}
                  <td className="px-3 py-2 text-destructive">{e.motivo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {validas.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50 text-xs text-muted-foreground">
                <th className="px-3 py-2 text-left font-medium">Fila</th>
                <th className="px-3 py-2 text-left font-medium">Título</th>
                <th className="px-3 py-2 text-left font-medium">Responsable</th>
                <th className="px-3 py-2 text-left font-medium">Prioridad</th>
                <th className="px-3 py-2 text-left font-medium">Entrega</th>
              </tr>
            </thead>
            <tbody>
              {validas.map((f) => (
                <tr key={`v-${f.fila}`} className="border-b bg-emerald-500/5 last:border-0">
                  <td className="px-3 py-2 text-muted-foreground">{f.fila}</td>
                  <td className="px-3 py-2 font-medium text-foreground">{f.titulo}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {f.responsable_nombre}
                    {f.responsables_ids.length > 0 && ` +${f.responsables_ids.length}`}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{f.prioridad}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {f.fecha_entrega ?? "—"}
                    {f.faltantes.includes("fecha") && (
                      <span className="ml-1 inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                        <AlertTriangle className="size-3" />sin leer
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          Ninguna fila del archivo se puede cargar. Revisá los motivos de arriba.
        </p>
      )}

      <p className="text-xs text-muted-foreground">
        Todos los objetivos se cargan como principales. Si alguno tiene que ser un subobjetivo,
        asignale el objetivo padre desde la pantalla después de importar.
      </p>
    </div>
  )
}
