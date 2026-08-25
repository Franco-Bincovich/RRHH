"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { UserPlus } from "lucide-react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { ContratarFormFields } from "@/components/features/candidatos/ContratarFormFields"
import {
  validar, sinErrores, type ErroresContratar, type FormContratar,
} from "@/components/features/candidatos/_contratarForm"
import { ApiError } from "@/services/api"
import { contratarCandidato } from "@/services/candidatos"
import { fetchRolesConocidos } from "@/services/empleados"
import type { CandidatoConGrupo } from "@/types/candidato"

/**
 * El puente candidato → empleado: crea el legajo en `preingreso` a partir de la búsqueda.
 *
 * Molde: `EliminarCandidatoButton` (botón autocontenido que avisa al padre por callback). La
 * diferencia es que acá hace falta un modal, porque el acto pide tres datos que no existen en
 * ninguna tabla — el resto del legajo lo deriva el backend del candidato y de su vacante.
 *
 * 🔴 SOLO CON `etapa_pipeline === "oferta"` Y `estado === "activo"`. Las dos, y son ejes
 * distintos: la etapa dice dónde está en el proceso, el estado dice si sigue en carrera. La
 * condición la aplica `CandidatoAcciones`, que es quien decide si esta acción se ofrece; acá
 * queda el acto. El backend revalida las dos igual (`_candidato_contratar_guardas.py:49-72`):
 * esto es UI, no la barrera.
 *
 * 🔴 VALIDA POR CAMPO, Y NO SIEMPRE LO HIZO. Hasta el 24/8/2026 la única guarda era un
 * `disabled` con condiciones de PRESENCIA (`!email.trim() || roles.length === 0`), heredado del
 * molde que copió —`EliminarCandidatoButton`, que es un botón de CONFIRMACIÓN y no un
 * formulario—. Con eso, un email `"a"` habilitaba el botón y creaba el legajo. La validación
 * vive ahora en `_contratarForm.ts`, con la misma forma que el resto de los formularios del
 * repo, y el email usa el validador COMPARTIDO (había tres copias del regex con tres mensajes
 * distintos). Ver el encabezado de `shared/validacionEmail.ts`.
 *
 * 🔴 LOS SEIS ERRORES DEL BACKEND SE MUESTRAN CON SU MENSAJE. Los cuatro de estado y el de fecha vienen
 * redactados con la salida adentro ("Solo se puede contratar a un candidato en etapa 'oferta', y
 * este está en 'entrevista_tecnica'"), y el sexto —el 409 de `email_corporativo` ya usado, que
 * sube desde el alta de empleado— es el único que se puede corregir sin salir del modal. Un
 * genérico obligaría a adivinar cuál de los seis fue, y en el del email además a buscar dónde.
 */
export function ContratarCandidatoButton(
  { candidato, onContratado }: { candidato: CandidatoConGrupo; onContratado: () => void },
) {
  const hoy = new Date().toISOString().slice(0, 10)
  const [open, setOpen] = useState(false)
  // Un objeto y no tres `useState` sueltos: es la misma forma que `validar` y `ContratarFormFields`
  // reciben, así que agregar un campo cuarto se toca en un lugar y no en cinco.
  const [form, setForm] = useState<FormContratar>({ email: "", roles: [], fecha: hoy })
  const [sugerencias, setSugerencias] = useState<string[]>([])
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState("")
  // Los errores por campo aparecen recién al intentar guardar: mostrarlos mientras se tipea
  // pinta de rojo un email que todavía se está escribiendo. Mismo criterio que /empleados.
  const [errores, setErrores] = useState<ErroresContratar>({})

  // El pool de roles ya cargados es el MISMO que usa el alta de empleado, y sale de todas las
  // empresas: el legajo que este puente crea es un empleado más, así que sugerirle un
  // vocabulario propio lo separaría del padrón desde el primer día.
  useEffect(() => {
    if (open && sugerencias.length === 0) {
      fetchRolesConocidos().then(setSugerencias).catch(() => {})
    }
  }, [open, sugerencias.length])

  function cerrar() {
    setOpen(false); setError(""); setGuardando(false); setErrores({})
    setForm({ email: "", roles: [], fecha: hoy })
  }

  async function confirmar() {
    const encontrados = validar(form, hoy)
    setErrores(encontrados)
    if (!sinErrores(encontrados)) return
    setGuardando(true); setError("")
    try {
      await contratarCandidato(candidato.id, {
        email_corporativo: form.email.trim(), roles: form.roles, fecha_ingreso: form.fecha,
      })
      toast.success(`${candidato.nombre} ${candidato.apellido} ya tiene legajo, en preingreso`)
      cerrar()
      onContratado()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo contratar al candidato.")
    } finally {
      setGuardando(false)
    }
  }

  return (
    <>
      <Button className="gap-2" onClick={() => setOpen(true)}>
        <UserPlus className="size-4" /> Contratar
      </Button>

      <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) cerrar() }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Contratar a {candidato.nombre} {candidato.apellido}</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <p className="text-sm text-muted-foreground">
              Se crea el legajo en estado <strong className="text-foreground">preingreso</strong>.
              La persona todavía no cuenta en headcount: el día que entre se confirma el ingreso
              desde su ficha. El resto de los datos salen del candidato y de la búsqueda.
            </p>

            <ContratarFormFields
              form={form} errores={errores} sugerencias={sugerencias} hoy={hoy}
              emailPersonal={candidato.email}
              onCampo={(campo, valor) => setForm((f) => ({ ...f, [campo]: valor }))}
            />

            {error && (
              <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" className="min-h-11" onClick={cerrar} disabled={guardando}>
              Cancelar
            </Button>
            <Button
              className="min-h-11"
              onClick={confirmar}
              /* 🔴 SÓLO se deshabilita mientras GUARDA. Antes también con los campos vacíos, y
                 eso es lo que convertía la validación en un botón muerto: el usuario ve un botón
                 gris y no sabe cuál de los tres campos falta. Ahora el botón se puede apretar
                 siempre y la respuesta es un mensaje POR CAMPO que dice qué corregir — que es lo
                 que pide §3 del sistema de diseño y lo que ya hacía /empleados. */
              disabled={guardando}
            >
              {guardando ? "Creando legajo..." : "Contratar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
