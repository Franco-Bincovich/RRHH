"use client"

import { useCallback, useEffect, useState } from "react"
import { CheckCircle2, Clock } from "lucide-react"

import { AvisoIrreversible } from "@/components/features/horasPublico/AvisoIrreversible"
import { CargaForm } from "@/components/features/horasPublico/CargaForm"
import { IdentificacionForm } from "@/components/features/horasPublico/IdentificacionForm"
import { SemanaTabla } from "@/components/features/horasPublico/SemanaTabla"
import {
  AYUDA_IDENTIFICACION, FORM_HORAS_VACIO, FORM_LICENCIA_VACIO, HORAS_ASUMIDAS, bodyHoras,
  bodyLicencia, esSesionMuerta, mensajeDeError, normalizarDni, validarHoras, validarLicencia,
  type Modo,
} from "@/components/features/horasPublico/logica"
import { borrarToken, guardarToken, leerToken } from "@/components/features/horasPublico/sesionHoras"
import {
  cargarHoras, cargarLicencia, fetchClientes, fetchSemana, identificar,
} from "@/services/horasPublico"
import type { ClientePublico, Semana } from "@/types/horasPublico"

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
 */
export default function HorasPublicoPage() {
  const [token, setToken] = useState<string | null>(null)
  const [nombre, setNombre] = useState("")
  const [dni, setDni] = useState("")
  const [modo, setModo] = useState<Modo>("horas")
  const [formHoras, setFormHoras] = useState(FORM_HORAS_VACIO)
  const [formLicencia, setFormLicencia] = useState(FORM_LICENCIA_VACIO)
  const [clientes, setClientes] = useState<ClientePublico[]>([])
  const [semana, setSemana] = useState<Semana | null>(null)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const [error, setError] = useState("")
  const [ok, setOk] = useState("")
  const [enviando, setEnviando] = useState(false)

  const cerrarSesion = useCallback((mensaje: string) => {
    borrarToken(); setToken(null); setNombre(""); setSemana(null); setClientes([])
    setError(mensaje)
  }, [])

  const refrescar = useCallback(async (t: string) => {
    try {
      const [cs, sem] = await Promise.all([fetchClientes(t), fetchSemana(t)])
      setClientes(cs.items); setSemana(sem)
    } catch (e) {
      if (esSesionMuerta(e)) cerrarSesion(mensajeDeError(e))
    }
  }, [cerrarSesion])

  // El token sobrevive al refresh de la página: se relee de sessionStorage al montar. Ver
  // `sesionHoras.ts` para por qué sessionStorage y no las otras dos opciones.
  useEffect(() => {
    const guardado = leerToken()
    if (guardado) { setToken(guardado); void refrescar(guardado) }
  }, [refrescar])

  async function onIdentificar(e: React.FormEvent) {
    e.preventDefault()
    setError(""); setOk(""); setEnviando(true)
    try {
      const r = await identificar(normalizarDni(dni))
      guardarToken(r.token); setToken(r.token); setNombre(r.nombre); setDni("")
      await refrescar(r.token)
    } catch (err) {
      setError(mensajeDeError(err))
    } finally { setEnviando(false) }
  }

  async function onCargar(e: React.FormEvent) {
    e.preventDefault()
    if (!token) return
    const errs = modo === "horas" ? validarHoras(formHoras) : validarLicencia(formLicencia)
    setErrores(errs)
    if (Object.keys(errs).length) return
    setError(""); setOk(""); setEnviando(true)
    try {
      if (modo === "horas") {
        await cargarHoras(bodyHoras(token, formHoras, crypto.randomUUID()))
        setFormHoras(FORM_HORAS_VACIO); setOk("Listo. Cargamos tus horas.")
      } else {
        const r = await cargarLicencia(bodyLicencia(token, formLicencia))
        setFormLicencia(FORM_LICENCIA_VACIO)
        // El backend avisa cuando el empleado no tiene horas de contrato y asumió 8. Ocultarlo
        // sería mostrar un número inventado como si fuera dato.
        setOk(`Listo. Cargamos ${r.dias} día${r.dias !== 1 ? "s" : ""} de licencia`
          + ` (${r.horas_equivalentes} h`
          + `${r.horas_por_dia_estimadas ? `, estimadas en ${HORAS_ASUMIDAS} h por día` : ""}).`)
      }
      await refrescar(token)
    } catch (err) {
      if (esSesionMuerta(err)) cerrarSesion(mensajeDeError(err))
      else setError(mensajeDeError(err))
    } finally { setEnviando(false) }
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-8">
      <header className="mb-6 flex items-center gap-2">
        <Clock className="size-5 text-muted-foreground" />
        <h1 className="text-xl font-semibold text-foreground">Carga de horas</h1>
      </header>

      {error && (
        <div className="mb-4 rounded-lg border border-destructive/40 bg-destructive/10 p-3">
          <p className="text-sm font-medium text-destructive">{error}</p>
          {!token && <p className="mt-1 text-xs text-muted-foreground">{AYUDA_IDENTIFICACION}</p>}
        </div>
      )}
      {ok && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3">
          <CheckCircle2 className="size-4 shrink-0 text-emerald-600" />
          <p className="text-sm text-foreground">{ok}</p>
        </div>
      )}

      {!token ? (
        <IdentificacionForm dni={dni} onDni={setDni} enviando={enviando}
                            onSubmit={onIdentificar} />
      ) : (
        <>
          <p className="mb-4 text-sm text-muted-foreground">
            Hola <span className="font-medium text-foreground">{nombre}</span>.
          </p>
          <AvisoIrreversible />
          <form onSubmit={onCargar} className="mb-6 rounded-lg border bg-card p-4">
            <CargaForm modo={modo} onModo={setModo} horas={formHoras} onHoras={setFormHoras}
                       licencia={formLicencia} onLicencia={setFormLicencia} clientes={clientes}
                       errores={errores} enviando={enviando} hoy={new Date()} />
          </form>
          {semana && <SemanaTabla semana={semana} />}
        </>
      )}
    </main>
  )
}
