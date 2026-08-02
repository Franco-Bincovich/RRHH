"use client"

import { Suspense } from "react"
import { Accordion } from "@base-ui/react/accordion"

import { IntegracionesSection } from "@/components/features/configuracion/IntegracionesSection"
import { OAuthPopupHandler } from "@/components/features/configuracion/OAuthPopupHandler"
import { PerfilSection } from "@/components/features/configuracion/PerfilSection"
import { PlantillasSection } from "@/components/features/configuracion/PlantillasSection"
import { ReglasSections } from "@/components/features/configuracion/ReglasSections"
import { TiposAusenciaSection } from "@/components/features/configuracion/TiposAusenciaSection"
import { PageHeader } from "@/components/layout/PageHeader"
import { useCanRead, useCanWrite } from "@/hooks/useCanWrite"

/**
 * Secciones abiertas al entrar: solo las de identidad, que son las que todo usuario tiene.
 *
 * Las reglas nacen PLEGADAS a propósito. No es una preferencia estética: con ocho bloques
 * abiertos la pantalla que la mayoría viene a usar —cambiar la contraseña— queda debajo de
 * varias pantallas de formularios de reglas que casi nadie toca.
 */
const ABIERTAS = ["password", "perfil"]

/**
 * /configuracion — la ruta NO está gateada (services/permisos.ts la deja fuera de
 * RUTA_SECCION): acá vive el cambio de contraseña, que todo usuario necesita sea cual sea su
 * rol. El gate va POR BLOQUE, y hay DOS criterios distintos porque los bloques no son iguales:
 *
 *  · INTEGRACIONES → se OCULTAN sin permiso de escritura. Atrás no hay nada que leer: son
 *    tres formularios de escritura (dos API keys y un OAuth). Un form deshabilitado con
 *    "••••••••" no informa nada, y uno habilitado que responde 403 al guardar es el bug que
 *    esto vino a cerrar.
 *
 *  · REGLAS y TIPOS DE AUSENCIA → se muestran en SOLO LECTURA sin permiso de escritura. Acá
 *    el valor SÍ es información: saber que la escala es 14/21/28 o que la base son 22 días
 *    hábiles explica de dónde sale cada número de los reportes, y gerencia_lectura tiene
 *    lectura sobre configuración justamente para eso. Ocultarlas dejaría a un rol que puede
 *    leer todos los reportes sin poder saber con qué reglas se calcularon.
 *
 * 🔴 Y LOS TRES GATES SE DECIDEN ACÁ, NO ADENTRO DE CADA COMPONENTE, porque el fetch de los
 * tres vive en HOOKS y los hooks corren aunque el componente devuelva null después. Un `if`
 * adentro dejaría el 403 igual en la red. Sin montar el componente, la llamada no sale nunca.
 * Es la lección de sucesión, escrita en CLAUDE.md: fijate primero dónde vive el fetch.
 */
export default function ConfiguracionPage() {
  const puedeIntegraciones = useCanWrite("integraciones")
  const puedeLeerReglas = useCanRead("configuracion")
  const puedeEditarReglas = useCanWrite("configuracion")

  return (
    <>
      {/* useSearchParams obliga al boundary; sin él `next build` falla al prerenderizar. */}
      <Suspense fallback={null}>
        <OAuthPopupHandler />
      </Suspense>

      <div className="mx-auto max-w-2xl">
        <PageHeader
          title="Configuración"
          description="Reglas de la empresa, cuentas conectadas y tu perfil"
        />

        <Accordion.Root
          defaultValue={ABIERTAS}
          multiple
          className="mt-6 flex flex-col gap-4"
        >
          {puedeLeerReglas && (
            <>
              <ReglasSections editable={puedeEditarReglas} />
              <TiposAusenciaSection editable={puedeEditarReglas} />
              <PlantillasSection editable={puedeEditarReglas} />
            </>
          )}
          {puedeIntegraciones && <IntegracionesSection />}
          <PerfilSection />
        </Accordion.Root>
      </div>
    </>
  )
}
