"use client"

import { Suspense } from "react"
import { Accordion } from "@base-ui/react/accordion"

import { IntegracionesSection } from "@/components/features/configuracion/IntegracionesSection"
import { OAuthPopupHandler } from "@/components/features/configuracion/OAuthPopupHandler"
import { PerfilSection } from "@/components/features/configuracion/PerfilSection"
import { ReglasSections } from "@/components/features/configuracion/ReglasSections"
import { ScreeningSection } from "@/components/features/configuracion/ScreeningSection"
import { TiposAusenciaSection } from "@/components/features/configuracion/TiposAusenciaSection"
import { PageHeader } from "@/components/layout/PageHeader"
import { useCanRead, useCanWrite } from "@/hooks/useCanWrite"
import { useEmpresaConcreta } from "@/hooks/useEmpresaConcreta"

/**
 * 🔴 NINGUNA SECCIÓN ARRANCA DESPLEGADA — cambió el 23/8/2026. Acá había `["password", "perfil"]`
 * con este argumento: *"con ocho bloques abiertos la pantalla que la mayoría viene a usar
 * —cambiar la contraseña— queda debajo de varias pantallas de formularios de reglas"*. El
 * argumento sigue siendo verdadero y por eso lleva a la conclusión contraria: **con las ocho
 * plegadas, los ocho títulos entran en una sola pantalla y "Contraseña" se encuentra de un
 * vistazo**, que es exactamente lo que esa nota quería. Dejarlas abiertas empujaba hacia abajo a
 * las otras seis para ahorrarle un click a dos.
 *
 * Se mantiene el array (vacío) y no se saca el `defaultValue`: el día que una sección tenga que
 * nacer abierta, el lugar donde se decide eso es éste y está a la vista. Un `defaultValue` que
 * desaparece obliga al próximo a averiguar dónde iba.
 */
const ABIERTAS: string[] = []

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
  // 🔴 CUARTO GATE, y se decide acá por lo mismo que los otros tres. Las reglas y el criterio de
  // screening se guardan SOBRE UNA EMPRESA (`require_empresa_id` en el backend), así que en la
  // vista consolidada esos botones no pueden funcionar: hasta el 25/8/2026 se ofrecían
  // habilitados y devolvían 400 después del click. No se OCULTAN como integraciones —el valor
  // se sigue pudiendo leer, y elegir la empresa es algo que el usuario puede hacer— sino que se
  // bloquean con el motivo a la vista. Ver `AccionBloqueada`.
  const { motivo: motivoSinEmpresa } = useEmpresaConcreta()

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
              {/* Las plantillas de mail se fueron a /comunicacion el 7/8/2026: desde ahí ahora
                  se MANDAN mails, y eso es operación, no configuración. */}
              <ReglasSections editable={puedeEditarReglas} motivoBloqueo={motivoSinEmpresa} />
              {/* Tipos de ausencia NO recibe el motivo: crear uno en consolidado crea un tipo
                  GLOBAL, que es el comportamiento declarado del service (`create_tipo`), no un
                  error. Es la única escritura de esta pantalla que sí funciona sin empresa. */}
              <TiposAusenciaSection editable={puedeEditarReglas} />
              {/* Mismo criterio de gate que las otras reglas: en solo lectura sin permiso de
                  escritura. El criterio con el que se preseleccionan CVs es información que
                  explica por qué un candidato quedó marcado como quedó. */}
              <ScreeningSection editable={puedeEditarReglas} motivoBloqueo={motivoSinEmpresa} />
            </>
          )}
          {puedeIntegraciones && <IntegracionesSection />}
          <PerfilSection />
        </Accordion.Root>
      </div>
    </>
  )
}
