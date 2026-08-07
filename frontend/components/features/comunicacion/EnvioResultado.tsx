"use client"

import type { EnvioResponse } from "@/types/plantillas"

export const TITULO_COMPLETO = "Listo, salieron todos"
export const TITULO_INCOMPLETO = "El envío no salió completo"

function plural(n: number, singular: string, plural_: string): string {
  return `${n} ${n === 1 ? singular : plural_}`
}

/**
 * El resumen de un envío, en castellano y sin jerga.
 *
 * 🔴 UN "ENVIADO" A SECAS SERÍA MENTIRA. El backend manda de a uno con presupuesto de tiempo y
 * devuelve CINCO números, no un ok: un lote de 50 puede terminar con 30 enviados, 5 omitidos, 2
 * fallidos y 13 sin siquiera intentar. Con un toast de éxito, RRHH se quedaría creyendo que el
 * comunicado llegó a los 50 — y la única forma de enterarse sería que alguien reclame.
 *
 * Por eso el título distingue los dos desenlaces (`TITULO_COMPLETO` / `TITULO_INCOMPLETO`) y
 * cada número aparece solo cuando es distinto de cero: una lista fija de cinco renglones con
 * ceros se vuelve ruido y deja de leerse justo cuando uno de ellos importa.
 *
 * ⚠️ `omitidos` NO se cuenta como problema, y es la línea más fácil de escribir mal: son los que
 * YA habían recibido este mail hoy. Es la idempotencia del backend, que es lo que hace que
 * reintentar un lote cortado continúe en vez de mandarle dos veces a los mismos.
 */
export function EnvioResultado({ res }: { res: EnvioResponse }) {
  const incompleto = res.parcial || res.fallidos.length > 0

  return (
    <div className="space-y-3 text-sm">
      <p className={incompleto ? "font-medium text-amber-700 dark:text-amber-500" : "font-medium text-emerald-700 dark:text-emerald-500"}>
        {incompleto ? TITULO_INCOMPLETO : TITULO_COMPLETO}
      </p>

      <ul className="space-y-1.5 text-foreground">
        <li>Se {res.enviados === 1 ? "envió" : "enviaron"} {plural(res.enviados, "mail", "mails")}.</li>

        {res.omitidos > 0 && (
          <li className="text-muted-foreground">
            A {plural(res.omitidos, "persona", "personas")} ya se le había mandado este mail hoy,
            así que no se le volvió a enviar.
          </li>
        )}

        {res.fallidos.length > 0 && (
          <li className="text-amber-700 dark:text-amber-500">
            {plural(res.fallidos.length, "mail no se pudo enviar", "mails no se pudieron enviar")}:
            <ul className="mt-1 space-y-0.5 pl-4 text-xs">
              {res.fallidos.map((f, i) => (
                <li key={`${f.destinatario}-${i}`}>{f.destinatario} — {f.motivo}</li>
              ))}
            </ul>
          </li>
        )}

        {res.parcial && (
          <li className="text-amber-700 dark:text-amber-500">
            Quedaron {plural(res.sin_procesar, "persona", "personas")} sin procesar porque el
            envío se pasó del tiempo disponible. Volvé a abrir esta ventana y mandá el mismo
            grupo: sigue donde quedó y a nadie le llega el mail dos veces.
          </li>
        )}
      </ul>

      {res.segundos !== null && (
        <p className="text-xs text-muted-foreground">Tardó {res.segundos} segundos.</p>
      )}
    </div>
  )
}
