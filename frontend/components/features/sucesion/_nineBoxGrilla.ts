/**
 * La DEFINICIÓN de la grilla 9-box: las nueve celdas con su nombre y su zona, los colores de cada
 * zona y el helper de iniciales. Sin JSX y sin estado.
 *
 * 🔴 SALIÓ DE `NineBox.tsx` PORQUE ESE ARCHIVO SE PASABA DEL LÍMITE DE 150 (estaba en 198 antes
 * de esta tanda, deuda ya anotada en CLAUDE.md, y el comentario de los colores lo llevaba a 204).
 * El corte es por responsabilidad, no por línea: acá está QUÉ es cada casillero —dato que no
 * cambia nunca y que se lee de un vistazo— y allá cómo se dibuja y cómo responde al clic.
 */

// ─── Public types ─────────────────────────────────────────────────────────────

export interface EmpleadoCelda {
  id: string
  nombre: string
  cargo: string
  area: string
  /** 0 = Alto potencial (top), 2 = Bajo potencial (bottom) */
  fila: 0 | 1 | 2
  /** 0 = Bajo desempeño (left), 2 = Alto desempeño (right) */
  columna: 0 | 1 | 2
}

export type Zone = "verde" | "amarillo" | "rojo"

interface Celda {
  fila: 0 | 1 | 2
  columna: 0 | 1 | 2
  nombre: string
  zone: Zone
}

// Ordered row-by-row, left-to-right — matches CSS grid placement order
export const CELDAS: Celda[] = [
  { fila: 0, columna: 0, nombre: "Enigma",        zone: "amarillo" },
  { fila: 0, columna: 1, nombre: "Alto Potencial", zone: "verde"   },
  { fila: 0, columna: 2, nombre: "Estrella",       zone: "verde"   },
  { fila: 1, columna: 0, nombre: "A Desarrollar",  zone: "rojo"    },
  { fila: 1, columna: 1, nombre: "Sólido",         zone: "amarillo"},
  { fila: 1, columna: 2, nombre: "Referente",      zone: "verde"   },
  { fila: 2, columna: 0, nombre: "Riesgo",         zone: "rojo"    },
  { fila: 2, columna: 1, nombre: "Consistente",    zone: "rojo"    },
  { fila: 2, columna: 2, nombre: "Efectivo",       zone: "amarillo"},
]

/*
 * Las tres zonas del 9-box, con la paleta SEMÁNTICA del sistema y no con la escala cruda de
 * Tailwind. Cada par (wash de fondo + line de borde + color fuerte de texto) es uno de los que
 * `app/contrasteTokens.test.ts` mide en los dos temas; los `emerald-50/amber-50/rose-50` que
 * había acá quedaban fuera de ese barrido y de cualquier ajuste posterior de la paleta.
 *
 * ⚠️ Y las variantes `dark:` desaparecen porque no hacen falta: los tokens YA cambian de valor
 * con el tema. Escribir el par dos veces era la forma de que el modo oscuro se olvidara.
 */
export const ZONE_BG: Record<Zone, string> = {
  verde:    "bg-success-wash border-success-line",
  amarillo: "bg-warning-wash border-warning-line",
  rojo:     "bg-danger-wash border-danger-line",
}

export const ZONE_TEXT: Record<Zone, string> = {
  verde:    "text-success",
  amarillo: "text-warning",
  rojo:     "text-destructive",
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function initials(nombre: string): string {
  return nombre
    .split(" ")
    .slice(0, 2)
    .map((p) => p[0] ?? "")
    .join("")
    .toUpperCase()
}
