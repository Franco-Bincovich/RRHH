import type { MotivoEgreso } from "@/types/offboarding"

/**
 * Los tres mapas de texto visible del módulo de offboarding, extraídos de
 * `app/(dashboard)/offboarding/page.tsx` (311/150) al sumarle la efectivización de la baja.
 *
 * Viven en un `.ts` de datos y no adentro de `OffboardingCard` porque los consume más de un
 * componente: la tarjeta los usa para el badge, y `EfectivizarBajaButton` usa `MOTIVO_LABEL`
 * para que la confirmación diga "Renuncia de Juan Pérez" en vez de repetir el enum crudo.
 * Importar constantes desde un componente para usarlas en otro es lo que empieza los ciclos.
 */

export const MOTIVO_LABEL: Record<MotivoEgreso, string> = {
  renuncia:      "Renuncia",
  despido:       "Desvinculación",
  acuerdo_mutuo: "Acuerdo mutuo",
  fin_contrato:  "Fin de contrato",
  jubilacion:    "Jubilación",
  fallecimiento: "Fallecimiento",
  otro:          "Otro motivo",
}

export const MOTIVO_VARIANT: Record<MotivoEgreso, "secondary" | "destructive"> = {
  renuncia:      "secondary",
  despido:       "destructive",
  acuerdo_mutuo: "secondary",
  fin_contrato:  "secondary",
  jubilacion:    "secondary",
  fallecimiento: "destructive",
  otro:          "secondary",
}

export const TIPO_ACTIVO_LABEL: Record<string, string> = {
  laptop:           "Laptop de trabajo",
  celular:          "Teléfono corporativo",
  monitor:          "Monitor",
  tarjeta_acceso:   "Tarjeta de acceso",
  licencia_software:"Licencias de software",
  llave:            "Llaves",
  uniforme:         "Uniforme",
  otro:             "Activo corporativo",
}
