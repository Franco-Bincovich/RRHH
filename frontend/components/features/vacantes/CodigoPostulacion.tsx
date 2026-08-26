"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Check, Copy, Hash, Pencil, TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { fetchAvisoPostulacion } from "@/services/vacantes"
import type { AvisoPostulacion } from "@/types/vacantes"

import { EditarCodigoModal } from "./EditarCodigoModal"

/**
 * El código de la vacante y la frase lista para pegar en el aviso de LinkedIn.
 *
 * 🔴 SE COPIA LA FRASE ENTERA, NO SOLO EL CÓDIGO, y ese es el punto del componente. Si RRHH
 * tiene que armar la instrucción a mano, la va a escribir distinta cada vez ("ref VAC 0001",
 * "poner el código en el asunto") y el candidato va a mandar cualquier cosa: el mail entra, el
 * código no matchea, y el CV termina en "sin asignar" sin que nada haya fallado visiblemente.
 * El botón grande es el de la frase; el del código suelto queda para cuando alguien la necesita
 * dentro de un texto propio.
 *
 * La frase la arma el BACKEND (`services/_vacante_aviso.py`), no esta pantalla: es una sola
 * definición para todos los avisos. Acá solo se muestra y se copia.
 *
 * Sin casilla del sistema designada el backend manda `texto: null` y se muestra el aviso de qué
 * falta configurar, en vez de una frase con un agujero adentro. El código se muestra igual.
 *
 * 🔴 EL CÓDIGO SE CAMBIA DESDE ACÁ, y no desde un "editar vacante" que no existe en el producto:
 * es el único lugar donde el código está a la vista CON su contexto —la frase que se pega en el
 * aviso—, así que corregir un typo y ver cómo queda el texto publicado es un solo movimiento.
 */
interface CodigoPostulacionProps {
  vacanteId: string
  /** Cuántos candidatos tiene la búsqueda: decide si el modal avisa sobre el aviso publicado. */
  candidatos: number
  canWrite: boolean
}

export function CodigoPostulacion({ vacanteId, candidatos, canWrite }: CodigoPostulacionProps) {
  const router = useRouter()
  const [aviso, setAviso] = useState<AvisoPostulacion | null>(null)
  const [loading, setLoading] = useState(true)
  const [copiado, setCopiado] = useState<"codigo" | "texto" | null>(null)
  const [editando, setEditando] = useState(false)

  // `useCallback`: el modal RECARGA el aviso al guardar. La frase la arma el backend con el
  // código nuevo, así que sin recargar la pantalla seguiría mostrando la vieja.
  const cargar = useCallback(() => {
    let vigente = true
    fetchAvisoPostulacion(vacanteId)
      .then((a) => { if (vigente) setAviso(a) })
      .catch(() => { /* el bloque no se muestra; la ficha no depende de esto */ })
      .finally(() => { if (vigente) setLoading(false) })
    return () => { vigente = false }
  }, [vacanteId])

  useEffect(cargar, [cargar])

  async function copiar(valor: string, cual: "codigo" | "texto") {
    try {
      await navigator.clipboard.writeText(valor)
      setCopiado(cual)
      setTimeout(() => setCopiado(null), 2000)
    } catch {
      /* si el navegador bloquea el portapapeles, el valor está a la vista para copiarlo a mano */
    }
  }

  if (loading) return <Skeleton className="mb-8 h-28 w-full rounded-xl" />
  if (!aviso) return null

  return (
    <Card className="mb-8">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Hash className="size-4 text-muted-foreground" />
        <h2 className="text-base font-semibold text-foreground">Código de la búsqueda</h2>
        <code className="rounded-md bg-muted px-2.5 py-1 font-mono text-sm font-semibold text-foreground">
          {aviso.codigo}
        </code>
        <Button
          variant="ghost"
          size="sm"
          className="min-h-10 gap-2"
          onClick={() => copiar(aviso.codigo, "codigo")}
        >
          {copiado === "codigo" ? <Check className="size-4" /> : <Copy className="size-4" />}
          {copiado === "codigo" ? "Copiado" : "Copiar código"}
        </Button>
        {canWrite && (
          <Button
            variant="ghost"
            size="sm"
            className="min-h-10 gap-2"
            onClick={() => setEditando(true)}
          >
            <Pencil className="size-4" />
            Cambiar
          </Button>
        )}
      </div>

      {aviso.texto ? (
        <>
          <p className="mb-2 text-sm text-muted-foreground">
            Pegá esto en el aviso para que las postulaciones se asignen solas a esta búsqueda:
          </p>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <p className="min-w-0 flex-1 rounded-lg border bg-muted/50 px-3 py-2 text-sm text-foreground">
              {aviso.texto}
            </p>
            <Button
              className="min-h-11 shrink-0 gap-2"
              onClick={() => copiar(aviso.texto as string, "texto")}
            >
              {copiado === "texto" ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copiado === "texto" ? "Copiado" : "Copiar para el aviso"}
            </Button>
          </div>
        </>
      ) : (
        <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <p>
            No hay una casilla del sistema designada, así que todavía no se puede armar la
            instrucción del aviso.{" "}
            <button
              className="font-medium underline underline-offset-2"
              onClick={() => router.push("/configuracion")}
            >
              Ir a Configuración
            </button>{" "}
            para designarla.
          </p>
        </div>
      )}

      <EditarCodigoModal
        open={editando}
        vacanteId={vacanteId}
        codigoActual={aviso.codigo}
        candidatos={candidatos}
        onClose={() => setEditando(false)}
        onSaved={() => { setEditando(false); cargar() }}
      />
    </Card>
  )
}
