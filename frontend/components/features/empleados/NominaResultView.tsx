import { AlertTriangle, CheckCircle2, Link2, Link2Off, PauseCircle, XCircle } from "lucide-react"

import type { ImportacionNominaEmpleadosResult } from "@/types/importacion"

/**
 * Reporte del import de nómina en 3 grupos: OK · con faltantes · no cargados.
 *
 * Si `parcial` viene en true, el archivo no se terminó de procesar. Se muestra como
 * INFORMACIÓN (azul, con instrucción), no como error: lo procesado quedó cargado y el
 * reintento continúa donde quedó. Pintarlo de rojo haría que RRHH crea que perdió el trabajo.
 */
export function NominaResultView({ result }: { result: ImportacionNominaEmpleadosResult }) {
  const { creados, actualizados, con_faltantes, no_cargados } = result
  return (
    <div className="space-y-4 py-2">
      {result.parcial && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 p-3 dark:border-sky-800 dark:bg-sky-950">
          <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-sky-900 dark:text-sky-100">
            <PauseCircle className="size-4 shrink-0" />
            Se procesó una parte del archivo
          </p>
          <p className="text-sm text-sky-900 dark:text-sky-100">
            Llegó hasta la fila {result.ultima_fila_procesada ?? "—"} y quedaron{" "}
            {result.filas_sin_procesar} sin procesar.{" "}
            <strong>Volvé a subir el mismo archivo para continuar</strong>: lo ya cargado no se
            duplica y el import sigue donde quedó.
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
        <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="size-4" />
          {creados} nuevo{creados !== 1 ? "s" : ""}, {actualizados} actualizado{actualizados !== 1 ? "s" : ""}
        </span>
        {con_faltantes.length > 0 && (
          <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
            <AlertTriangle className="size-4" />
            {con_faltantes.length} con faltantes
          </span>
        )}
        {no_cargados.length > 0 && (
          <span className="flex items-center gap-1.5 text-destructive">
            <XCircle className="size-4" />
            {no_cargados.length} no cargado{no_cargados.length !== 1 ? "s" : ""}
          </span>
        )}
        {result.superiores_resueltos > 0 && (
          <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
            <Link2 className="size-4" />
            {result.superiores_resueltos} superior{result.superiores_resueltos !== 1 ? "es" : ""} asignado{result.superiores_resueltos !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {con_faltantes.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950">
          <p className="mb-1.5 text-sm font-medium text-amber-800 dark:text-amber-200">Cargados con faltantes</p>
          <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200" role="list">
            {con_faltantes.map((r, i) => (
              <li key={`f-${r.fila}-${i}`}>Fila {r.fila}: {r.empleado} — cargado, falta {r.faltan.join(", ")}</li>
            ))}
          </ul>
        </div>
      )}

      {result.superiores_pendientes.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950">
          <p className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-amber-800 dark:text-amber-200">
            <Link2Off className="size-4 shrink-0" />
            Sin superior asignado
          </p>
          {/* Estas filas SÍ se cargaron: lo único que falta es el manager_id. Van en ámbar y
              aparte de "No cargados" a propósito — leerlas como filas perdidas haría que RRHH
              vuelva a subir el archivo creyendo que algo falló. */}
          <p className="mb-1.5 text-sm text-amber-800 dark:text-amber-200">
            Los empleados quedaron cargados. Podés dar de alta a los superiores que faltan y
            resolverlos desde el listado, sin volver a subir el archivo.
          </p>
          <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200" role="list">
            {result.superiores_pendientes.map((s, i) => (
              <li key={`s-${s.fila}-${i}`}>Fila {s.fila}: {s.empleado} → {s.superior} — {s.motivo}</li>
            ))}
          </ul>
        </div>
      )}

      {no_cargados.length > 0 && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
          <p className="mb-1.5 text-sm font-medium text-destructive">No cargados</p>
          <ul className="space-y-1 text-sm text-destructive" role="list">
            {no_cargados.map((r, i) => (
              <li key={`n-${r.fila}-${i}`}>Fila {r.fila}: {r.empleado} — {r.motivo}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
