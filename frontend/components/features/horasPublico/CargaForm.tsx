"use client"

import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import { CamposHoras, CamposLicencia } from "@/components/features/horasPublico/CamposCarga"
import {
  puedeEnviar, ventanaFechas,
  type FormHoras, type FormLicencia, type Modo,
} from "@/components/features/horasPublico/logica"
import type { ClientePublico } from "@/types/horasPublico"

interface Props {
  modo: Modo
  onModo: (m: Modo) => void
  horas: FormHoras
  onHoras: (f: FormHoras) => void
  licencia: FormLicencia
  onLicencia: (f: FormLicencia) => void
  clientes: ClientePublico[]
  errores: Record<string, string>
  enviando: boolean
  hoy: Date
}

/**
 * El formulario. Horas o licencia, nunca los dos.
 *
 * 🔴 AL ELEGIR LICENCIA, LOS CAMPOS DE HORAS NO SE DESHABILITAN: **NO SE RENDERIZAN**.
 * Dos motivos, y el segundo es el que decide:
 *   1. Un `disabled` sobre el Button/Input de shadcn no se puede afirmar en un test — el markup
 *      trae la clase `disabled:` SIEMPRE, con y sin la prop, así que `not.toContain("disabled")`
 *      es una aserción que no puede fallar nunca.
 *   2. Los dos endpoints del backend reciben bodies DISJUNTOS: el de licencia ni siquiera acepta
 *      `horas` ni `cliente_id`. Un campo gris en pantalla sugeriría que existe pero está
 *      bloqueado; la verdad es que en ese modo no existe.
 *
 * El botón de enviar SÍ usa `disabled` mientras faltan obligatorios — ahí es correcto: el campo
 * existe, la acción todavía no. Lo que un test puede afirmar de eso es `puedeEnviar()`, que es
 * la función pura que lo decide.
 *
 * 🔴 LA VALIDACIÓN ES EN DOS NIVELES (§3): el banner con la CUENTA arriba de los campos y el
 * mensaje que dice QUÉ CORREGIR en cada uno. Acá el banner se gana su lugar: en modo horas hay
 * cuatro obligatorios que en un teléfono se apilan en una columna, así que el último campo y el
 * botón quedan lejos del primer borde rojo.
 *
 * ⚠️ El banner va DEBAJO del selector de modo, no arriba de todo: el modo no es un campo que se
 * pueda "corregir" —siempre tiene un valor— y contarlo entre los errores no tendría sentido. La
 * página LIMPIA `errores` al cambiar de modo, y eso es lo que impide que el banner diga "Revisá 3
 * campos" sobre el formulario de licencia con los errores que habían quedado del de horas.
 */
export function CargaForm(p: Props) {
  const { min, max } = ventanaFechas(p.hoy)
  const err = (k: string) =>
    p.errores[k] ? <p className="text-xs text-destructive" role="alert">{p.errores[k]}</p> : null

  return (
    <div className="space-y-4">
      <div className="flex gap-2" role="radiogroup" aria-label="Qué querés cargar">
        {(["horas", "licencia"] as Modo[]).map((m) => (
          <Button key={m} type="button" variant={p.modo === m ? "default" : "outline"}
                  className="min-h-11 flex-1" aria-pressed={p.modo === m}
                  onClick={() => p.onModo(m)}>
            {m === "horas" ? "Horas trabajadas" : "Licencia"}
          </Button>
        ))}
      </div>

      <FormErrores cantidad={Object.values(p.errores).filter(Boolean).length} />

      {p.modo === "horas" ? (
        <CamposHoras form={p.horas} onForm={p.onHoras} clientes={p.clientes}
                     err={err} min={min} max={max} />
      ) : (
        <CamposLicencia form={p.licencia} onForm={p.onLicencia} err={err} min={min} max={max} />
      )}

      <Button type="submit" className="min-h-11 w-full"
              disabled={p.enviando || !puedeEnviar(p.modo, p.horas, p.licencia)}>
        {p.enviando ? "Enviando..." : "Enviar"}
      </Button>
    </div>
  )
}
