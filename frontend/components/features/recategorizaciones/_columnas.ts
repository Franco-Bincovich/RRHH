import type { Columna } from "@/components/ui/grillaTabla"

/**
 * La grilla de la planilla de recategorizaciones.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 LA COLUMNA DE IMPACTO NO EXISTE SIN PERMISO DE COSTOS. No se renderiza vacía: no se
 * renderiza.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Es la misma decisión que ya tomó el export (`_recategorizaciones_export.py`), y por el mismo
 * motivo: **una columna presente y vacía se lee como "no había monto"**, que es una afirmación
 * distinta de "no lo podés ver". La diferencia importa porque `impacto_salarial` vuelve en `null`
 * en los dos casos —el backend no los distingue a propósito, un campo que dijera "oculto"
 * confirmaría que hay un monto cargado— así que la pantalla NO tiene forma de saber cuál de los
 * dos es. Sacar la columna entera es lo único honesto que puede hacer.
 *
 * ⚠️ El listado NO se gatea con COSTOS: el historial de rol y seniority le sirve a cualquiera que
 * vea el legajo, y es el 90% del valor del módulo. Lo que se gatea es la columna.
 *
 * 🔴 NO HAY COLUMNA DE ESTADO NI DE APROBACIÓN. §7: no existe flujo de aprobación, esto es
 * registro puro. Una columna "Estado" que dijera "Registrada" para todas las filas insinuaría que
 * hay otros estados posibles.
 */
export function columnas(mostrarImpacto: boolean): Columna[] {
  return [
    { clave: "fecha", label: "Fecha efectiva", ancho: "w-[11%]" },
    { clave: "colaborador", label: "Colaborador", ancho: "w-[16%]" },
    // La más ancha: lleva hasta tres pares "de → a". Es la columna que contesta la pregunta.
    { clave: "cambios", label: "Qué cambió", ancho: "" },
    { clave: "motivo", label: "Motivo", ancho: "w-[20%]" },
    ...(mostrarImpacto ? [{ clave: "impacto", label: "Impacto", ancho: "w-[10%]" }] : []),
    { clave: "registrado", label: "Registrado por", ancho: "w-[13%]" },
    // Acciones: solo editar. NO hay borrar — el backend no publica DELETE (rompería la cadena
    // de valores anteriores) y la corrección es editar. Ver `services/recategorizaciones.ts`.
    { clave: "acciones", label: "", ancho: "w-[48px]" },
  ]
}
