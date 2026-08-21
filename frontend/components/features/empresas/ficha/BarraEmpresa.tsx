import type { ReactNode } from "react"

import { Badge } from "@/components/ui/badge"
import { FichaIdentidad, iniciales } from "@/components/ui/FichaIdentidad"
import type { Empresa } from "@/types/empresa"

import { ESTADO_ESTILO } from "../_grillaEmpresas"
import { datosClaveEmpresa } from "./_datosClaveEmpresa"

/**
 * La barra de identidad de la ficha de una EMPRESA.
 *
 * 🔴 EL CHIP REUSA `ESTADO_ESTILO` DEL LISTADO, que ya existe y ya está testeado. La ficha tenía
 * el suyo escrito inline —`variant={empresa.activa ? "default" : "secondary"}`—, o sea que una
 * empresa activa se pintaba con `bg-primary`: el relleno de marca al lado del botón "Editar", que
 * es el otro relleno de marca de la barra. Además decía distinto que la misma empresa en el
 * listado, donde ya era un par semántico.
 *
 * ⚠️ El monograma sale del nombre de fantasía y NO del logo, aunque la empresa tenga uno cargado:
 * el logo es una imagen remota y el círculo es la primera cosa que se pinta. Un logo que tarda o
 * que falla dejaría el encabezado con un hueco; las iniciales están siempre.
 */
export function BarraEmpresa({ empresa, acciones }: { empresa: Empresa; acciones?: ReactNode }) {
  return (
    <FichaIdentidad
      volverA="/empresas"
      volverLabel="Empresas"
      actual={empresa.nombre}
      monograma={iniciales(empresa.nombre)}
      titulo={empresa.nombre}
      subtitulo={empresa.razon_social || "Sin razón social cargada"}
      chip={
        <Badge variant="outline" className={empresa.activa ? ESTADO_ESTILO.activa : ESTADO_ESTILO.inactiva}>
          {empresa.activa ? "Activa" : "Inactiva"}
        </Badge>
      }
      datos={datosClaveEmpresa(empresa)}
      acciones={acciones}
    />
  )
}
