"use client"

import { useState } from "react"
import { Loader2 } from "lucide-react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ImportFormacionPreviewTabla } from "@/components/features/capacitaciones/ImportFormacionPreview"
import { ImportFormacionSubir } from "@/components/features/capacitaciones/ImportFormacionSubir"
import { ImportFormacionResultadoDetalle } from "@/components/features/capacitaciones/ImportFormacionResultado"
import { confirmarFormacion, previewFormacion } from "@/services/importacionFormacion"
import { ApiError } from "@/services/api"
import type {
  ImportacionFormacionPreview, ImportacionFormacionResultado,
} from "@/types/importacionFormacion"

/**
 * Import de formación por Excel, en dos pasos: subir → previsualizar → confirmar → resultado.
 *
 * Molde: `ImportarObjetivosModal`. Las dos vistas grandes (el preview y el resultado) viven en
 * componentes propios: acá quedan el estado y las llamadas, que es lo que un modal tiene que
 * tener. Es también lo que las hace testeables — el `Dialog` monta por portal y vitest corre sin
 * jsdom, así que este archivo no se puede afirmar desde un test.
 *
 * 🔴 LA EMPRESA VIAJA YA EN EL PREVIEW, a diferencia del import de objetivos. Acá cambia EL
 * RESULTADO de la previsualización: contra qué padrón se matchean los colaboradores y contra qué
 * catálogo se decide qué cursos hay que crear. Con la empresa solo en el confirmar, el usuario
 * aprobaría un preview calculado contra una empresa y escrito contra otra.
 *
 * 🔴 LOS MENSAJES DE ERROR DEL BACKEND SE MUESTRAN TAL CUAL. Vienen redactados para alguien de
 * RRHH con la planilla abierta ("Faltan columnas obligatorias en el archivo: ..."). Un genérico
 * de "Ocurrió un error" tiraría exactamente lo que hace falta para arreglar el archivo.
 */
type Paso = "subir" | "preview" | "resultado"

export function ImportarFormacionModal(
  { open, empresaId, onClose, onSuccess }: {
    open: boolean; empresaId: string; onClose: () => void; onSuccess: () => void
  },
) {
  const [paso, setPaso] = useState<Paso>("subir")
  const [archivo, setArchivo] = useState<File | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState("")
  const [preview, setPreview] = useState<ImportacionFormacionPreview | null>(null)
  const [resultado, setResultado] = useState<ImportacionFormacionResultado | null>(null)

  function cerrar() {
    setPaso("subir"); setArchivo(null); setError("")
    setPreview(null); setResultado(null); setCargando(false)
    onClose()
  }

  async function subir(f: File) {
    setArchivo(f); setError(""); setCargando(true)
    try {
      setPreview(await previewFormacion(f, empresaId))
      setPaso("preview")
    } catch (e) {
      // 🔴 El archivo se rechazó ENTERO (headers faltantes, hoja ilegible): no se cargó nada y
      // el usuario se queda en el paso 1 para subir otro. El mensaje es del backend.
      setError(e instanceof ApiError ? e.message : "No se pudo leer el archivo.")
    } finally { setCargando(false) }
  }

  async function confirmar() {
    if (!preview) return
    setCargando(true); setError("")
    try {
      setResultado(await confirmarFormacion(preview.filas_validas, empresaId))
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
            {paso === "subir" && "Importar formación desde Excel"}
            {paso === "preview" && "Revisá antes de importar"}
            {paso === "resultado" && "Resultado de la importación"}
          </DialogTitle>
        </DialogHeader>

        {error && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {paso === "subir" && <ImportFormacionSubir archivo={archivo} onArchivo={(f) => void subir(f)} />}

        {paso === "preview" && preview && <ImportFormacionPreviewTabla preview={preview} />}
        {paso === "resultado" && resultado && (
          <ImportFormacionResultadoDetalle resultado={resultado} />
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
