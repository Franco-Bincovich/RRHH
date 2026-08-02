"use client"

/**
 * Los chips de variables disponibles para el contexto elegido.
 *
 * 🔴 SE INSERTAN CON UN CLIC, NO SE ESCRIBEN. El catálogo llega del backend, así que lo que se
 * ofrece acá es EXACTAMENTE lo que el guardado va a aceptar — es la forma de que un typo
 * (`{{nombre_emplado}}`) no llegue nunca a existir. El backend lo rechaza igual con un 422, pero
 * el mejor error es el que no se puede cometer.
 *
 * Si la lista llegara a decenas de variables, esto pide un buscador; con las que hay (entre 3 y
 * 14 según el contexto) los chips son más rápidos que cualquier control con búsqueda.
 */
export function PlantillaVariables({ variables, onInsertar }: {
  variables: string[]
  onInsertar: (v: string) => void
}) {
  return (
    <div className="mt-1 flex flex-wrap gap-1.5">
      {variables.map((v) => (
        <button key={v} type="button" onClick={() => onInsertar(v)}
                className="rounded-md border px-2 py-1 text-xs hover:bg-accent">
          {`{{${v}}}`}
        </button>
      ))}
    </div>
  )
}
