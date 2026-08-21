"use client"

import { useState } from "react"
import { CheckCircle2, Clock } from "lucide-react"

import { AvisoError } from "@/components/ui/AvisoError"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { AvisoIrreversible } from "@/components/features/horasPublico/AvisoIrreversible"
import { CargaForm } from "@/components/features/horasPublico/CargaForm"
import { IdentificacionForm } from "@/components/features/horasPublico/IdentificacionForm"
import { SemanaTabla } from "@/components/features/horasPublico/SemanaTabla"
import { useSesionHoras } from "@/components/features/horasPublico/useSesionHoras"
import {
  AYUDA_IDENTIFICACION, FORM_HORAS_VACIO, FORM_LICENCIA_VACIO, HORAS_ASUMIDAS, bodyHoras,
  bodyLicencia, esSesionMuerta, mensajeDeError, normalizarDni, validarHoras, validarLicencia,
  type Modo,
} from "@/components/features/horasPublico/logica"
import { cargarHoras, cargarLicencia, identificar } from "@/services/horasPublico"

/**
 * Carga de horas — PANTALLA PÚBLICA. La usa un empleado SIN cuenta en el sistema.
 *
 * 🔴 VIVE FUERA DE `(dashboard)` A PROPÓSITO: sin sidebar, sin selector de empresa y sin
 * AuthGuard. Molde: `app/evaluacion/[token]`, la pantalla pública de assessment. Meterla bajo
 * `(dashboard)` la haría redirigir a `/login` a alguien que nunca va a tener usuario.
 *
 * 🔴 CUANDO LA SESIÓN MUERE (401 `SESION_INVALIDA`), se vuelve al paso del DNI y se muestra el
 * mensaje del backend. Dejar el formulario en pantalla sería dejar a la persona completándolo
 * para que cada envío falle. Se distingue por el CODE y no por el status: el rechazo del DNI
 * también es 401, y confundirlos borraría una sesión sana por un dígito mal tipeado.
 *
 * ⚠️ EL MÓDULO ESTÁ APAGADO por `HORAS_PUBLICO_ENABLED=false` en el backend: el router no se monta
 * y las rutas salen de `PUBLIC_ROUTES`. Esta pantalla se mantiene igual, pero hoy no responde
 * nadie del otro lado. El flag no se toca desde acá.
 */
export default function HorasPublicoPage() {
  const s = useSesionHoras()
  const [dni, setDni] = useState("")
  const [modo, setModo] = useState<Modo>("horas")
  const [formHoras, setFormHoras] = useState(FORM_HORAS_VACIO)
  const [formLicencia, setFormLicencia] = useState(FORM_LICENCIA_VACIO)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [ok, setOk] = useState("")
  const [enviando, setEnviando] = useState(false)

  async function onIdentificar(e: React.FormEvent) {
    e.preventDefault()
    s.setError(""); setOk(""); setEnviando(true)
    try {
      const r = await identificar(normalizarDni(dni))
      setDni("")
      await s.abrir(r.token, r.nombre)
    } catch (err) {
      s.setError(mensajeDeError(err))
    } finally { setEnviando(false) }
  }

  async function onCargar(e: React.FormEvent) {
    e.preventDefault()
    if (!s.token) return
    const errs = modo === "horas" ? validarHoras(formHoras) : validarLicencia(formLicencia)
    setErrores(errs)
    if (Object.keys(errs).length) return
    s.setError(""); setOk(""); setEnviando(true)
    try {
      if (modo === "horas") {
        await cargarHoras(bodyHoras(s.token, formHoras, crypto.randomUUID()))
        setFormHoras(FORM_HORAS_VACIO); setOk("Listo. Cargamos tus horas.")
      } else {
        const r = await cargarLicencia(bodyLicencia(s.token, formLicencia))
        setFormLicencia(FORM_LICENCIA_VACIO)
        // El backend avisa cuando el empleado no tiene horas de contrato y asumió 8. Ocultarlo
        // sería mostrar un número inventado como si fuera dato.
        setOk(`Listo. Cargamos ${r.dias} día${r.dias !== 1 ? "s" : ""} de licencia`
          + ` (${r.horas_equivalentes} h`
          + `${r.horas_por_dia_estimadas ? `, estimadas en ${HORAS_ASUMIDAS} h por día` : ""}).`)
      }
      await s.refrescar(s.token)
    } catch (err) {
      if (esSesionMuerta(err)) s.cerrar(mensajeDeError(err))
      else s.setError(mensajeDeError(err))
    } finally { setEnviando(false) }
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-8">
      <header className="mb-6 flex items-center gap-2">
        <Clock className="size-5 text-muted-foreground" aria-hidden="true" />
        <h1 className="text-xl font-semibold text-foreground">Carga de horas</h1>
      </header>

      {s.error && (
        <div className="mb-4">
          {/* La ayuda fija va SÓLO en el paso del DNI: es el rechazo único del backend, que no
              distingue "no existe" de "tu empresa no tiene clientes". Ver `AYUDA_IDENTIFICACION`. */}
          <AvisoError ayuda={!s.token ? AYUDA_IDENTIFICACION : undefined}>{s.error}</AvisoError>
        </div>
      )}
      {ok && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-success-line bg-success-wash p-3">
          {/* Los pares `--success-*` de la paleta y no `emerald-500/10`, que era lo que había:
              esos pares están medidos en los dos temas por `app/contrasteTokens.test.ts` y un
              emerald hardcodeado no lo ve nadie. En oscuro el emerald quedaba casi ilegible. */}
          <CheckCircle2 className="size-4 shrink-0 text-success" aria-hidden="true" />
          <p className="text-sm text-foreground">{ok}</p>
        </div>
      )}

      {s.cargando ? (
        // El esqueleto tiene la forma de lo que viene (§3): el formulario y la tabla de la semana.
        <div className="space-y-4">
          <Skeleton shimmer className="h-64 w-full rounded-lg" />
          <Skeleton shimmer className="h-40 w-full rounded-lg" />
        </div>
      ) : s.errorCarga && s.token ? (
        <ErrorState
          description="No pudimos traer tus datos. Puede ser tu conexión."
          action={() => void s.refrescar(s.token!)}
        />
      ) : !s.token ? (
        <IdentificacionForm dni={dni} onDni={setDni} enviando={enviando} onSubmit={onIdentificar} />
      ) : (
        <>
          <p className="mb-4 text-sm text-muted-foreground">
            Hola <span className="font-medium text-foreground">{s.nombre}</span>.
          </p>
          <AvisoIrreversible />
          <form onSubmit={onCargar} className="mb-6 rounded-lg border bg-card p-4">
            {/* 🔴 Cambiar de modo LIMPIA los errores: los dos formularios validan campos
                distintos, así que dejarlos dejaría el banner contando errores de campos que ya
                no están en pantalla — "Revisá 3 campos" sobre un formulario sin un solo borde
                rojo, que es peor que no tener banner. */}
            <CargaForm modo={modo} onModo={(m) => { setModo(m); setErrores({}) }}
                       horas={formHoras} onHoras={setFormHoras}
                       licencia={formLicencia} onLicencia={setFormLicencia} clientes={s.clientes}
                       errores={errores} enviando={enviando} hoy={new Date()} />
          </form>
          {s.semana && <SemanaTabla semana={s.semana} />}
        </>
      )}
    </main>
  )
}
