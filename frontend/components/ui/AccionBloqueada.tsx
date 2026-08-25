import type { ReactNode } from "react"

import { NotaInfo } from "@/components/ui/NotaInfo"

/**
 * Una acción que HOY no se puede hacer, con el motivo A LA VISTA en vez de un error después del
 * click.
 *
 * ═══════════════════════════════════════════════════════════════════════════════════
 * 🔴 ESTO INVIERTE UNA DECISIÓN QUE ESTABA ESCRITA EN EL CÓDIGO, Y HAY QUE LEER POR QUÉ.
 * ═══════════════════════════════════════════════════════════════════════════════════
 * `ProximosIngresosTable` decía, en mayúsculas: *"EL BOTÓN NO SE DESHABILITA POR FECHA. Se podría
 * y sería peor: un botón muerto no dice por qué lo está"*. El argumento era correcto **contra un
 * `disabled` pelado**, que es lo único que existía. Lo que lo resuelve no es dejar el botón
 * habilitado —eso convierte cada intento en un viaje al servidor para recibir un error que se
 * podía anticipar— sino deshabilitarlo **con el motivo escrito al lado**, que es lo que este
 * componente obliga a hacer: `motivo` no es opcional cuando hay bloqueo.
 *
 * El costo del botón habilitado, medido en el smoke del 25/8/2026: en `/proximos-ingresos` las
 * SEIS filas tenían fecha futura y las seis daban 400. O sea que el 100% de los botones que la
 * pantalla ofrecía no podía funcionar, y para enterarse había que apretarlos uno por uno.
 *
 * 🔑 EL MOTIVO ES TEXTO VISIBLE, NO UN TOOLTIP. Un `title` no existe en touch —y el bloque 9 de
 * esta misma tanda es justamente sobre mobile— ni es alcanzable por teclado sin foco. Se pone
 * ADEMÁS como `title` para el que pasa el mouse por encima del botón, pero nunca en lugar del
 * texto.
 *
 * ⚠️ QUÉ **NO** ES ESTO. No es un gate de permisos: eso oculta el botón (`useCanWrite`), porque
 * un rol que no puede escribir no gana nada viendo una acción que nunca va a poder hacer. Acá el
 * usuario SÍ puede hacer la acción — le falta una condición que él mismo puede cambiar (elegir
 * la empresa, esperar a la fecha, corregir el legajo). Por eso se muestra y se explica.
 *
 * ⚠️ TAMPOCO ES SEGURIDAD. El backend rechaza igual; esto evita ofrecer lo que no funciona.
 */
export function AccionBloqueada({
  motivo,
  children,
  className,
}: {
  /** El motivo por el que la acción no se puede hacer, o `null` si sí se puede. */
  motivo: string | null
  /** Recibe `true` cuando hay motivo: el caller decide qué control deshabilitar. */
  children: (bloqueada: boolean) => ReactNode
  className?: string
}) {
  return (
    <div className={className}>
      {/*
       * `title` en un wrapper y no en el botón: un `<button disabled>` no dispara eventos de
       * mouse en varios navegadores, así que su propio `title` no llega a mostrarse nunca.
       */}
      <div title={motivo ?? undefined}>{children(Boolean(motivo))}</div>
      {motivo && <NotaInfo className="mt-2">{motivo}</NotaInfo>}
    </div>
  )
}
