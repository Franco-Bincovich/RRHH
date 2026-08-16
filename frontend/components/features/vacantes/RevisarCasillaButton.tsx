"use client"

import { useState } from "react"
import { Inbox, TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ApiError } from "@/services/api"
import { revisarCasilla } from "@/services/vacantes"
import type { IngestaResultado } from "@/types/vacantesIngesta"

/**
 * "Revisar casilla": lee la casilla del sistema, matchea cada mail por el código del asunto y
 * crea los candidatos con su CV.
 *
 * 🔴 VA EN EL LISTADO Y NO EN LA FICHA DE UNA VACANTE. La corrida es sobre la CASILLA entera y
 * cada mail elige su búsqueda por el código: una sola pasada puede tocar varias vacantes, incluso
 * de empresas distintas. Colgarlo de una vacante habría obligado a elegir una antes de saber
 * cuáles hacen falta.
 *
 * 🔴 REEMPLAZA a "Emails recibidos" de la ficha. No conviven: aquel listaba con `format=metadata`
 * —que ni siquiera trae los adjuntos— y decidía qué era una postulación por palabras clave, un
 * filtro que descarta en silencio mails que sí traen el código.
 *
 * ⚠️ `ya_existian` se muestra SIEMPRE que sea > 0, aunque no se haya creado nada: un reintento
 * que dijera solo "0 candidatos nuevos" parecería no haber hecho nada, cuando lo que confirmó es
 * que la casilla ya estaba procesada entera.
 */
const MOTIVO: Record<string, string> = {
  sin_codigo: "Sin código en el asunto",
  codigo_ambiguo: "Más de un código en el asunto",
  vacante_desconocida: "El código no corresponde a ninguna búsqueda",
  sin_adjuntos: "No trae archivos adjuntos",
  sin_cv_valido: "Trae adjuntos, pero ninguno es un CV",
  error: "No se pudo procesar",
}

export function RevisarCasillaButton() {
  const [cargando, setCargando] = useState(false)
  const [resultado, setResultado] = useState<IngestaResultado | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function revisar() {
    setCargando(true)
    setError(null)
    try {
      setResultado(await revisarCasilla())
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error
        ? err.message : "No se pudo revisar la casilla.")
    } finally {
      setCargando(false)
    }
  }

  const abierto = resultado !== null || error !== null

  return (
    <>
      <Button variant="outline" className="min-h-11 gap-2" onClick={revisar} disabled={cargando}>
        <Inbox className="size-4" />
        {cargando ? "Revisando…" : "Revisar casilla"}
      </Button>

      <Dialog open={abierto} onOpenChange={(v) => { if (!v) { setResultado(null); setError(null) } }}>
        <DialogContent className="max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Revisión de la casilla</DialogTitle>
            <DialogDescription>
              {error
                ? "No se pudo completar la revisión."
                : `Se leyeron ${resultado?.mails_leidos ?? 0} mails con adjuntos.`}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
              {error}
            </p>
          )}

          {resultado && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-4 text-sm">
                <span className="font-medium text-foreground">
                  {resultado.candidatos_creados} candidato{resultado.candidatos_creados !== 1 ? "s" : ""} nuevo{resultado.candidatos_creados !== 1 ? "s" : ""}
                </span>
                {resultado.ya_existian > 0 && (
                  <span className="text-muted-foreground">
                    {resultado.ya_existian} ya estaba{resultado.ya_existian !== 1 ? "n" : ""} cargado{resultado.ya_existian !== 1 ? "s" : ""}
                  </span>
                )}
              </div>

              {resultado.parcial && (
                <p className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                  <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                  Quedaron {resultado.sin_procesar} mails sin procesar por tiempo. Volvé a apretar
                  el botón: los que ya entraron no se duplican.
                </p>
              )}

              {resultado.pendientes.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-foreground">
                    {resultado.pendientes.length} mail{resultado.pendientes.length !== 1 ? "s" : ""} para revisar a mano
                  </h3>
                  <div className="space-y-2">
                    {resultado.pendientes.map((m) => (
                      <div key={m.message_id} className="rounded-lg border bg-card p-3">
                        <p className="truncate text-sm font-medium text-foreground">{m.remitente || "(sin remitente)"}</p>
                        <p className="truncate text-sm text-muted-foreground">{m.asunto || "(sin asunto)"}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {MOTIVO[m.motivo ?? ""] ?? m.motivo}
                          {m.descartados.length > 0 && ` · adjuntos descartados: ${m.descartados.join(", ")}`}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button onClick={() => { setResultado(null); setError(null) }}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
