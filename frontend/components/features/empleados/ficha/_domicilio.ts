import type { Empleado } from "@/types/empleado"

/**
 * Arma el domicilio estructurado en una línea legible: "Calle 123, Piso 4 B, Localidad, CP,
 * Provincia". Devuelve null si no hay ningún campo cargado.
 *
 * Las partes vacías se descartan en vez de dejar comas colgando: un domicilio con solo
 * localidad y provincia tiene que leerse "Bell Ville, Córdoba", no ", , Bell Ville, , Córdoba".
 *
 * Calle y número van juntos porque así se escribe una dirección; el resto va separado por comas.
 */
export function domicilioLegible(e: Empleado): string | null {
  const calleNumero = [e.domicilio_calle, e.domicilio_numero].filter(Boolean).join(" ")
  const partes = [
    calleNumero,
    e.domicilio_piso_depto,
    e.domicilio_localidad,
    e.domicilio_cp,
    e.domicilio_provincia,
  ].filter((x) => x && String(x).trim())
  return partes.length ? partes.join(", ") : null
}

/**
 * ¿Hay que mostrar el `domicilio` viejo de texto libre?
 *
 * Solo si tiene valor Y los estructurados están vacíos: sirve como referencia para que alguien
 * lo copie a los campos nuevos. Una vez completados, mostrar los dos sería ruido —y peor, dos
 * direcciones que pueden no coincidir sin que nadie sepa cuál rige—.
 */
export function mostrarCrudo(e: Empleado): boolean {
  return Boolean(e.domicilio?.trim()) && domicilioLegible(e) === null
}
