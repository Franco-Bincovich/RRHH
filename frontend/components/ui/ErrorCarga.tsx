"use client"

/**
 * "No se pudo cargar esto" + Reintentar, EN LÍNEA, para usar adentro de un panel o un modal.
 *
 * 🔴 NO ES UN DUPLICADO DE `ErrorState`, ES OTRO TAMAÑO. Aquel ocupa `py-16` con un ícono de
 * 56px y está pensado para reemplazar una pantalla entera; metido en la lista de un modal
 * empuja los botones fuera de la vista y hace scrollear justo cuando el usuario necesita el
 * botón de reintentar. Éste ocupa una caja de tres líneas y reemplaza solo el bloque que falló.
 *
 * 🔴 POR QUÉ EXISTE: un `.catch` que pinta una lista vacía dice "no hay datos" cuando lo que
 * hubo fue un error, y eso manda al usuario a buscar el problema donde no está. Ese fue el
 * modo de falla que dejó dos modales mostrando "no hay empleados" con la base llena durante
 * meses (ver `MAX_PAGE_SIZE` en services/api.ts). Un estado de error con salida es lo que
 * convierte un fallo mudo en algo que el usuario puede reportar o resolver solo.
 *
 * ⚠️ `components/features/usuarios/EmpleadoLiderSelect.tsx:36-48` tiene este mismo bloque escrito
 * a mano, de antes. Es candidato a migrar acá; no se tocó en esta tanda por estar fuera del bug.
 */
export function ErrorCarga({ mensaje, onReintentar }: {
  mensaje: string
  onReintentar: () => void
}) {
  return (
    <div className="rounded-md border border-destructive/40 p-3 text-sm">
      <span className="text-destructive">{mensaje}</span>{" "}
      <button type="button" className="underline hover:text-primary" onClick={onReintentar}>
        Reintentar
      </button>
    </div>
  )
}
