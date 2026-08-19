"use client"

import { AlertTriangle, BookPlus, UserX, Users } from "lucide-react"

import type { ImportacionFormacionPreview } from "@/types/importacionFormacion"

/**
 * Los tres grupos del preview de formación que NO son filas del Excel, sino CONSECUENCIAS del
 * lote: qué nombres se parecen entre sí, qué cursos se van a crear y quién no está en el padrón.
 *
 * Separado de `ImportFormacionPreview` (que llegó a 182/150) por ese eje y no por largo: aquel
 * muestra filas del archivo —las que entran y las que se rechazan— y esto muestra qué va a pasar
 * con el catálogo y con las personas. Los dos son testeables sin jsdom por la misma razón: el
 * `Dialog` monta por portal y renderizar el modal entero devuelve string vacío.
 *
 * 🔴 LOS PARES PARECIDOS VAN PRIMERO Y SON LO ÚNICO QUE EXIGE ACCIÓN ANTES DE IMPORTAR. El
 * sistema NO los unifica —decide RRHH— y esa decisión se toma EN EL EXCEL, no acá: importar
 * "Pérez, Juan" y "Juan Perez" como vienen deja dos historiales de formación separados, y nadie
 * se entera hasta que alguien busca el legajo y ve la mitad de los cursos.
 */
export function ImportFormacionAvisos({ preview }: { preview: ImportacionFormacionPreview }) {
  const { capacitaciones_a_crear, sin_match, pares_parecidos } = preview

  return (
    <>
      {pares_parecidos.length > 0 && (
        <div className="rounded-lg border border-amber-300 dark:border-amber-800">
          <p className="flex items-center gap-1.5 border-b border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            <Users className="size-3.5" />
            Estos nombres se parecen entre sí. Si son la misma persona, unificalos EN EL EXCEL y
            volvé a subirlo: importados así quedan como dos historiales separados.
          </p>
          <ul className="divide-y divide-border text-sm" role="list">
            {pares_parecidos.map((p, i) => (
              <li key={`p-${i}`} className="flex flex-wrap items-baseline gap-x-2 px-3 py-2">
                <span className="font-medium text-foreground">{p.nombre_a}</span>
                <span className="text-muted-foreground">↔</span>
                <span className="font-medium text-foreground">{p.nombre_b}</span>
                <span className="text-xs text-muted-foreground">— {p.motivo}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {capacitaciones_a_crear.length > 0 && (
        <div className="rounded-lg border">
          {/* Un import que crea entidades sin decirlo es cómo se llena un catálogo de duplicados
              con typos: "Excel Avanzado" y "Excel avanzado " conviviendo para siempre. */}
          <p className="flex items-center gap-1.5 border-b bg-muted/50 px-3 py-2 text-xs font-medium text-foreground">
            <BookPlus className="size-3.5" />
            Se van a crear {capacitaciones_a_crear.length} cursos nuevos en el catálogo
          </p>
          <ul className="divide-y divide-border text-sm" role="list">
            {capacitaciones_a_crear.map((c) => (
              <li key={c.nombre} className="px-3 py-2">
                <span className="font-medium text-foreground">{c.nombre}</span>
                {c.duracion_horas != null && (
                  <span className="ml-2 text-xs text-muted-foreground">{c.duracion_horas} hs</span>
                )}
                {c.modalidad && <span className="ml-2 text-xs text-muted-foreground">{c.modalidad}</span>}
                {c.avisos.map((a, i) => (
                  <span key={i} className="ml-2 inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                    <AlertTriangle className="size-3" />{a}
                  </span>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sin_match.length > 0 && (
        <div className="rounded-lg border">
          <p className="flex items-center gap-1.5 border-b bg-muted/50 px-3 py-2 text-xs font-medium text-foreground">
            <UserX className="size-3.5" />
            {sin_match.length} personas no están en el padrón de esta empresa
          </p>
          {/* Se cargan IGUAL, como nombre suelto: por eso esta caja es neutra y no destructiva.
              No matchear NO es un error — la formación queda registrada y el vínculo con el
              legajo se puede hacer después. Meterlo entre las filas rechazadas haría que RRHH
              corrija un archivo que no tiene nada malo. */}
          <p className="px-3 pt-2 text-xs text-muted-foreground">
            Su formación se carga igual, con el nombre tal cual vino. Se puede vincular al legajo
            más adelante.
          </p>
          <p className="px-3 py-2 text-sm text-foreground">{sin_match.join(" · ")}</p>
        </div>
      )}
    </>
  )
}
