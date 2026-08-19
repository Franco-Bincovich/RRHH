"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { UserPlus } from "lucide-react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { RolesInput } from "@/components/ui/RolesInput"
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
 * 🔴 LOS SEIS ERRORES SE MUESTRAN CON SU MENSAJE. Los cuatro de estado y el de fecha vienen
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
  const [email, setEmail] = useState("")
  const [roles, setRoles] = useState<string[]>([])
  const [fecha, setFecha] = useState(hoy)
  const [sugerencias, setSugerencias] = useState<string[]>([])
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState("")

  // El pool de roles ya cargados es el MISMO que usa el alta de empleado, y sale de todas las
  // empresas: el legajo que este puente crea es un empleado más, así que sugerirle un
  // vocabulario propio lo separaría del padrón desde el primer día.
  useEffect(() => {
    if (open && sugerencias.length === 0) {
      fetchRolesConocidos().then(setSugerencias).catch(() => {})
    }
  }, [open, sugerencias.length])

  function cerrar() {
    setOpen(false); setError(""); setGuardando(false)
    setEmail(""); setRoles([]); setFecha(hoy)
  }

  async function confirmar() {
    setGuardando(true); setError("")
    try {
      await contratarCandidato(candidato.id, {
        email_corporativo: email.trim(), roles, fecha_ingreso: fecha,
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
        <DialogContent className="max-h-[90vh] max-w-md overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Contratar a {candidato.nombre} {candidato.apellido}</DialogTitle>
          </DialogHeader>

          <div className="flex flex-col gap-4 py-2">
            <p className="text-sm text-muted-foreground">
              Se crea el legajo en estado <strong className="text-foreground">preingreso</strong>.
              La persona todavía no cuenta en headcount: el día que entre se confirma el ingreso
              desde su ficha. El resto de los datos salen del candidato y de la búsqueda.
            </p>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-foreground">Email corporativo</span>
              <Input
                type="email" value={email} placeholder="nombre@empresa.com"
                onChange={(e) => setEmail(e.target.value)}
              />
              {/* Se aclara porque el error natural es pegar el mail con el que se postuló: la
                  columna es única en TODO el sistema y ese valor queda quemado para siempre. */}
              <span className="text-xs text-muted-foreground">
                No es el personal ({candidato.email}), que queda igual en la ficha.
              </span>
            </label>

            <RolesInput
              value={roles} onChange={setRoles} suggestions={sugerencias}
              label="Rol en el legajo" required
            />

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-foreground">Fecha de ingreso acordada</span>
              {/* `min` = hoy: el backend exige una fecha hacia adelante y rechaza el pasado con
                  FECHA_INGRESO_PASADA. Es la UI evitando el viaje, no la validación. */}
              <Input type="date" value={fecha} min={hoy}
                onChange={(e) => setFecha(e.target.value)} />
            </label>

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
              disabled={guardando || !email.trim() || roles.length === 0 || !fecha}
            >
              {guardando ? "Creando legajo..." : "Contratar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
