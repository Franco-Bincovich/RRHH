"use client"

import Link from "next/link"
import { Accordion } from "@base-ui/react/accordion"
import { CalendarClock, UserPlus } from "lucide-react"

import { ConfigSection } from "@/components/features/configuracion/ConfigSection"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AlertaAtencion } from "@/services/dashboard"

/**
 * Panel "Requiere tu atención": lo accionable sobre PERSONAS y FECHAS — quién entra, a quién se
 * le termina el período de prueba, qué evento de agenda está en su ventana de aviso.
 *
 * 🔴 NO REEMPLAZA A `AlertasPanel`, Y NO ES UNA DUPLICACIÓN. Se midió: la intersección entre lo
 * que devuelve `/api/dashboard/atencion` y lo que devuelve `/api/dashboard` es CERO. Este panel
 * trae tres tipos (`ingreso_proximo`, `fin_periodo_prueba`, `evento_manual`); aquel trae los
 * cinco bloqueos de módulo (tablas vacías que dejan una sección inutilizable), los campos vacíos
 * del padrón y dos derivadas de KPIs. Son dos preguntas distintas: acá "qué tengo que hacer con
 * gente esta semana", allá "qué le falta al sistema para funcionar". Por eso conviven, este va
 * ARRIBA (es lo accionable sobre personas) y los títulos dicen cuál es cuál.
 *
 * Presentacional puro, molde `AlertasPanel`: sin estado, sin fetch, sin ordenar. El orden lo
 * decide el backend (por fecha del hecho, lo urgente arriba, las sin fecha al final) y el
 * destino de cada alerta también — acá NO se arma ninguna ruta.
 *
 * 🔴 EL BOTÓN DE RESOLVER SOLO APARECE EN LAS MANUALES, y no es una decisión de esta pantalla:
 * una calculada no tiene fila ni estado, se deriva al leer y desaparece cuando desaparece su
 * causa. "Resolverla" exigiría persistir ese resuelto en algún lado, y la misma causa la
 * volvería a levantar mañana — una alerta zombi que reaparece ya resuelta. El backend rechaza el
 * intento con ALERTA_NO_RESOLUBLE (409); mostrar el botón sería ofrecer un error.
 *
 * 🔑 El contador es `alertas.length` y sale de los datos que ya llegaron: acá `length` ES el
 * total, porque este endpoint no pagina ni recorta — devuelve todo lo que está en ventana.
 */
export function AtencionPanel(
  { alertas, canResolver, resolviendo, onResolver }: {
    alertas: AlertaAtencion[]
    /** Permiso de EVENTOS + WRITE, que es lo que el backend exige para resolver. */
    canResolver: boolean
    /** `evento_id` en curso, para deshabilitar solo esa fila. */
    resolviendo: string | null
    onResolver: (eventoId: string) => void
  },
) {
  return (
    <Accordion.Root defaultValue={["atencion"]}>
      <ConfigSection
        value="atencion"
        title="Requiere tu atención"
        badge={<Badge variant="secondary">{alertas.length}</Badge>}
      >
        {alertas.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Nada pendiente esta semana: sin ingresos próximos, sin períodos de prueba por vencer y
            sin eventos de agenda en ventana.
          </p>
        ) : (
          <ul className="divide-y divide-border" role="list">
            {alertas.map((a, i) => (
              <li key={a.evento_id ?? `${a.tipo}-${i}`} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                {/* El ícono distingue las dos clases de un vistazo, antes de leer el texto:
                    persona (lo que el sistema dedujo del padrón) vs. agenda (lo que alguien
                    cargó a mano). Es el pedido de "que se note cuál es cuál". */}
                {a.origen === "manual"
                  ? <CalendarClock className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  : <UserPlus className="mt-0.5 size-4 shrink-0 text-muted-foreground" />}

                <div className="min-w-0 flex-1">
                  {a.href ? (
                    <Link href={a.href} className="text-sm text-foreground hover:underline">
                      {a.mensaje}
                    </Link>
                  ) : (
                    <p className="text-sm text-foreground">{a.mensaje}</p>
                  )}
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {a.fecha ?? "Sin fecha"}
                    {/* El autor va SOLO en las manuales, y es la otra mitad del "que se note
                        cuál es cuál": una alerta que alguien escribió tiene a quién preguntarle;
                        una calculada, no. */}
                    {a.origen === "manual" && a.creado_por_nombre && ` · lo cargó ${a.creado_por_nombre}`}
                  </p>
                </div>

                {a.origen === "manual" && a.evento_id && canResolver ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0"
                    disabled={resolviendo === a.evento_id}
                    onClick={() => onResolver(a.evento_id as string)}
                  >
                    {resolviendo === a.evento_id ? "..." : "Resolver"}
                  </Button>
                ) : (
                  <Badge variant="outline" className="shrink-0">
                    {a.origen === "manual" ? "Agenda" : "Automática"}
                  </Badge>
                )}
              </li>
            ))}
          </ul>
        )}
      </ConfigSection>
    </Accordion.Root>
  )
}
