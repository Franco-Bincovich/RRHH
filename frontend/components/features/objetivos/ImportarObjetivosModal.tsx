"use client"

import { useState } from "react"
import { Loader2, Upload } from "lucide-react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ImportObjetivosPreviewTabla } from "@/components/features/objetivos/ImportObjetivosPreview"
import { ImportObjetivosResultadoDetalle } from "@/components/features/objetivos/ImportObjetivosResultado"
import { confirmarImportObjetivos, previewImportObjetivos } from "@/services/importacionObjetivos"
import { ApiError } from "@/services/api"
import type {
  ImportacionObjetivosPreview, ImportacionObjetivosResultado,
} from "@/types/importacionObjetivos"

/**
 * Import de objetivos por Excel, en dos pasos: subir → previsualizar → confirmar → resultado.
 *
 * Molde: `ImportarNominaCSVModal`. Las dos vistas grandes (el preview y el resultado) viven en
 * componentes propios: acá quedan el estado y las llamadas, que es lo que un modal tiene que
 * tener. Es también lo que las hace testeables — el `Dialog` monta por portal y vitest corre sin
 * jsdom, así que este archivo no se puede afirmar desde un test.
 *
 * 🔴 LOS MENSAJES DE ERROR DEL BACKEND SE MUESTRAN TAL CUAL. Vienen redactados para alguien de
 * RRHH con la planilla abierta ("Faltan columnas obligatorias en el archivo: Responsable",
 * "El archivo trae una columna de objetivo padre y este import no arma jerarquía…"). Un genérico
 * de "Ocurrió un error" tiraría exactamente lo que hace falta para arreglar el archivo.
 */
type Paso = "subir" | "preview" | "resultado"

export function ImportarObjetivosModal(
  { open, empresaId, onClose, onSuccess }: {
    open: boolean; empresaId: string; onClose: () => void; onSuccess: () => void
  },
) {
  const [paso, setPaso] = useState<Paso>("subir")
  const [archivo, setArchivo] = useState<File | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState("")
  const [preview, setPreview] = useState<ImportacionObjetivosPreview | null>(null)
  const [resultado, setResultado] = useState<ImportacionObjetivosResultado | null>(null)

  function cerrar() {
    setPaso("subir"); setArchivo(null); setError("")
    setPreview(null); setResultado(null); setCargando(false)
    onClose()
  }

  async function subir(f: File) {
    setArchivo(f); setError(""); setCargando(true)
    try {
      setPreview(await previewImportObjetivos(f))
      setPaso("preview")
    } catch (e) {
      // 🔴 El archivo se rechazó ENTERO (headers faltantes o columna de padre): no se cargó
      // nada y el usuario se queda en el paso 1 para subir otro. El mensaje es del backend.
      setError(e instanceof ApiError ? e.message : "No se pudo leer el archivo.")
    } finally { setCargando(false) }
  }

  async function confirmar() {
    if (!preview) return
    setCargando(true); setError("")
    try {
      setResultado(await confirmarImportObjetivos(empresaId, preview.filas_validas))
      setPaso("resultado")
      onSuccess()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo importar.")
    } finally { setCargando(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) cerrar() }}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {paso === "subir" && "Importar objetivos desde Excel"}
            {paso === "preview" && "Revisá antes de importar"}
            {paso === "resultado" && "Resultado de la importación"}
          </DialogTitle>
        </DialogHeader>

        {error && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {paso === "subir" && (
          <div className="space-y-3 py-2">
            <label className="flex min-h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border p-6 hover:border-primary/50 hover:bg-muted/30">
              <Upload className="size-8 text-muted-foreground" />
              <span className="text-center text-sm">
                {archivo
                  ? <span className="font-medium text-foreground">{archivo.name}</span>
                  : <><span className="font-medium text-foreground">Elegí el archivo Excel</span>
                      <br /><span className="text-muted-foreground">.xlsx — se lee la primera hoja</span></>}
              </span>
              <input
                type="file" accept=".xlsx" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) void subir(f) }}
              />
            </label>
            <div className="rounded-lg border bg-muted/30 p-3 text-xs">
              <p className="mb-1.5 font-medium text-foreground">Columnas de la planilla:</p>
              <p className="font-mono text-muted-foreground">
                Titulo, Responsable, Prioridad, Fecha entrega, Descripcion, Responsables
              </p>
              <p className="mt-2 text-muted-foreground">
                <strong>Titulo</strong> y <strong>Responsable</strong> son obligatorias. El
                responsable se escribe con su email, su usuario o su nombre y apellido, y tiene que
                ser un usuario activo del sistema. <strong>Responsables</strong> admite varios
                separados por punto y coma.
              </p>
            </div>
          </div>
        )}

        {paso === "preview" && preview && <ImportObjetivosPreviewTabla preview={preview} />}
        {paso === "resultado" && resultado && (
          <ImportObjetivosResultadoDetalle resultado={resultado} />
        )}

        <DialogFooter>
          {paso === "preview" && preview && (
            <>
              <Button variant="outline" onClick={() => { setPaso("subir"); setPreview(null) }}>
                Elegir otro archivo
              </Button>
              <Button onClick={confirmar} disabled={cargando || preview.filas_validas.length === 0}>
                {cargando && <Loader2 className="mr-1.5 size-4 animate-spin" />}
                Importar {preview.filas_validas.length}
              </Button>
            </>
          )}
          {paso !== "preview" && (
            <Button variant={paso === "resultado" ? "default" : "outline"} onClick={cerrar}>
              {paso === "resultado" ? "Listo" : "Cancelar"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
