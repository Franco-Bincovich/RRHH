"use client"

import { AlertTriangle, CheckCircle2, KeyRound, Unlink } from "lucide-react"

import { ApiKeyBlock } from "@/components/features/configuracion/ApiKeyBlock"
import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { useIntegraciones } from "@/components/features/configuracion/useIntegraciones"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

/** Chip "Conectado/Configurada" del encabezado; sale del propio estado de la integración. */
function ChipConectado({ texto }: { texto: string }) {
  return (
    <Badge variant="secondary" className="ml-auto">
      <CheckCircle2 className="mr-1 size-3" />
      {texto}
    </Badge>
  )
}

/** Las tres integraciones por usuario: Google/Gmail, Anthropic y Zernio. */
export function IntegracionesSection() {
  const {
    loading, ocupado, google, anthropic, zernio,
    guardarKey, conectarGoogle, desconectarGoogle,
  } = useIntegraciones()

  return (
    <>
      <ConfigSection
        value="google"
        icon={<span className="text-lg font-bold text-[#4285F4]">G</span>}
        iconClassName="bg-white shadow-sm"
        title="Google / Gmail"
        description="Conectá tu cuenta de Gmail para recibir y procesar emails de candidatos automáticamente"
        badge={google?.connected && <ChipConectado texto="Conectado" />}
      >
        {loading ? (
          <div className="h-9 animate-pulse rounded-md bg-muted" />
        ) : google?.connected ? (
          <div className="space-y-3">
            {/* 🔴 El aviso va ACÁ, en la pantalla donde se conecta, y no en el momento del envío.
                Google no amplía un consentimiento ya otorgado: la cuenta conectada antes del
                scope de envío lee perfecto y no puede mandar nada. Enterarse por un 403 en medio
                de un envío es el peor lugar posible — y encima el mensaje de Google no dice qué
                hacer. Reconectar es un clic (el flujo ya fuerza la pantalla de consentimiento). */}
            {!google.puede_enviar && (
              <p className="flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <span>
                  Esta cuenta está conectada <strong>solo para lectura</strong>. Para que el
                  sistema pueda enviar mails, volvé a conectarla: se te va a pedir el permiso de
                  envío, que antes no existía.
                </span>
              </p>
            )}
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-muted-foreground">{google.email_cuenta}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={desconectarGoogle}
              disabled={ocupado["google-off"]}
            >
              <Unlink className="mr-2 size-4" />
              Desconectar
            </Button>
          </div>
          </div>
        ) : (
          <Button onClick={conectarGoogle} disabled={ocupado.google}>
            <span className="mr-2 font-bold text-[#4285F4]">G</span>
            {ocupado.google ? "Abriendo…" : "Conectar con Google"}
          </Button>
        )}
      </ConfigSection>

      <ConfigSection
        value="anthropic"
        icon={<KeyRound className="size-5 text-orange-500" />}
        iconClassName="bg-orange-50"
        title="Inteligencia Artificial (Anthropic)"
        description="Si tenés tu propia API key de Anthropic podés usarla. Si no, el sistema usa la key compartida."
        badge={anthropic?.connected && <ChipConectado texto="Configurada" />}
      >
        <ApiKeyBlock
          id="api-key"
          etiqueta="API Key"
          placeholder="sk-ant-…"
          conectada={Boolean(anthropic?.connected)}
          guardando={Boolean(ocupado.anthropic)}
          onGuardar={(key) => guardarKey("anthropic", key)}
        />
      </ConfigSection>

      <ConfigSection
        value="zernio"
        icon={<span className="text-sm font-bold text-[#0A66C2]">Z</span>}
        iconClassName="bg-[#0A66C2]/10"
        title="Zernio (LinkedIn)"
        description="Conectá tu cuenta de Zernio para publicar vacantes en LinkedIn y otras redes automáticamente."
        badge={zernio?.connected && <ChipConectado texto="Configurado" />}
      >
        {/* El link va acá y no en la descripción: esa vive dentro del <button> del trigger. */}
        <p className="mb-3 text-sm text-muted-foreground">
          Sacá tu API key desde{" "}
          <a
            href="https://zernio.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2"
          >
            zernio.com
          </a>
          .
        </p>
        <ApiKeyBlock
          id="zernio-key"
          etiqueta="API Key de Zernio"
          placeholder="zrn_…"
          conectada={Boolean(zernio?.connected)}
          guardando={Boolean(ocupado.zernio)}
          onGuardar={(key) => guardarKey("zernio", key)}
        />
      </ConfigSection>
    </>
  )
}
