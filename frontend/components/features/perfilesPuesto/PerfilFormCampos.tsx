import { NotaInfo } from "@/components/ui/NotaInfo"
import type { CamposPerfilResponse } from "@/types/perfilPuesto"

import { PerfilCampoControl } from "./PerfilCampoControl"
import { indiceNotaRequisitos, vocabularioDe } from "./_perfilCampos"
import type { ErroresPerfil } from "./guardarPerfil"

/**
 * El CUERPO del formulario de perfil de puesto.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 SE CONSTRUYE RECORRIENDO `catalogos.campos`, NO CON UNA LISTA ESCRITA ACÁ.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Los 12 campos, su orden, su label, su texto de ayuda y los tres vocabularios cerrados los
 * sirve `GET /api/perfiles-puesto/campos`. Este archivo no nombra ni uno solo de los campos: si
 * alguien agrega un campo en el backend, la pantalla lo muestra sin tocar el front, y si alguien
 * reordena el bloque, el formulario se reordena con él.
 *
 * Y no es sólo comodidad: los `value` de los vocabularios son TAMBIÉN los `Literal` con los que
 * valida Pydantic, así que una copia acá que derivara ofrecería en un select un valor que el
 * backend rechaza con 422 — el error aparecería recién al guardar.
 *
 * ⚠️ ESTÁ SEPARADO DE `PerfilModal` A PROPÓSITO, y es lo que hace que todo esto sea verificable:
 * el modal monta por PORTAL, y con vitest sin jsdom `renderToStaticMarkup` de un `Dialog`
 * devuelve `""`. Un test del modal pasaría con el formulario entero borrado. Este componente, en
 * cambio, es markup plano y se renderiza a string sin nada alrededor.
 */
export function PerfilFormCampos({
  catalogos, valores, errores, onChange,
}: {
  catalogos: CamposPerfilResponse
  valores: Record<string, string>
  errores: ErroresPerfil
  onChange: (campo: string, valor: string) => void
}) {
  const iNota = indiceNotaRequisitos(catalogos.campos)

  return (
    <div className="space-y-5">
      {catalogos.campos.map((campo, i) => (
        <div key={campo.campo} className="space-y-5">
          {i === iNota && <NotaRequisitos texto={catalogos.nota_requisitos} />}
          <PerfilCampoControl
            campo={campo}
            opciones={vocabularioDe(campo.campo, catalogos)}
            valor={valores[campo.campo] ?? ""}
            error={campo.campo === "nombre" ? errores.nombre : undefined}
            onChange={(v) => onChange(campo.campo, v)}
          />
        </div>
      ))}
    </div>
  )
}

/**
 * La nota que explica por qué el bloque "Requisitos" del aviso está partido en cuatro campos.
 *
 * 🔴 VA ARRIBA DEL BLOQUE Y NO EN UN TOOLTIP — lo declara el backend y acá se respeta. Un tooltip
 * se lee después de haber escrito; para entonces el bloque entero ya está pegado en un solo campo
 * y los otros tres quedaron vacíos, que es justo lo que esta nota existe para evitar. El texto
 * tampoco se escribe acá: viene en `nota_requisitos`, del mismo endpoint que los labels.
 *
 * ⚠️ NEUTRA, NO ÁMBAR. El ámbar del sistema de diseño es del aviso de IMPACTO —"esto va a pasar
 * cuando aprietes Guardar"— y esto no es eso: es una instrucción de cómo llenar los campos que
 * siguen. Pintarla de ámbar gastaría la señal que la pantalla usa para las consecuencias reales.
 */
function NotaRequisitos({ texto }: { texto: string }) {
  return <NotaInfo>{texto}</NotaInfo>
}
