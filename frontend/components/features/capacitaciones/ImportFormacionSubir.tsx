"use client"

import { Upload } from "lucide-react"

/**
 * Paso 1 del modal: el dropzone y la ayuda de qué tiene que traer la planilla.
 *
 * Está aparte de `ImportarFormacionModal` —donde el molde de objetivos lo tiene inline— porque
 * aquel llegó a 151/150 con este bloque adentro. El corte cae bien igual: esto no toca la API ni
 * el estado del flujo, solo emite el archivo elegido, y es lo único del paso 1 que se puede
 * afirmar desde un test sin montar el `Dialog` (que va por portal y en vitest sin jsdom
 * renderiza vacío).
 *
 * 🔴 LA AYUDA DE COLUMNAS NO ES DECORATIVA. El error caro de este import no es un archivo mal
 * formado —eso el backend lo rechaza entero y con mensaje— sino no saber que los cursos que no
 * existen SE CREAN y que las personas fuera del padrón entran igual. Las dos cosas cambian lo
 * que RRHH revisa en el preview, así que se dicen antes de subir, no después.
 */
export function ImportFormacionSubir(
  { archivo, onArchivo }: { archivo: File | null; onArchivo: (f: File) => void },
) {
  return (
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
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onArchivo(f) }}
        />
      </label>
      <div className="rounded-lg border bg-muted/30 p-3 text-xs">
        <p className="mb-1.5 font-medium text-foreground">Columnas de la planilla:</p>
        <p className="font-mono text-muted-foreground">
          Colaborador, Capacitación, Tipo, Entidad, Modalidad, Duración, Estado
        </p>
        <p className="mt-2 text-muted-foreground">
          Los cursos que no estén en el catálogo <strong>se crean</strong>. Los colaboradores que
          no estén en el padrón de esta empresa se cargan igual, con su nombre tal cual vino — el
          preview los lista aparte.
        </p>
      </div>
    </div>
  )
}
