"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/layout/PageHeader"
import { ObjetivoModal } from "@/components/features/objetivos/ObjetivoModal"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { ObjetivosVistas } from "@/components/features/objetivos/ObjetivosVistas"
import type { Vista } from "@/components/features/objetivos/ObjetivosVistas"
import { TipoObjetivoTabs } from "@/components/features/objetivos/TipoObjetivoTabs"
import { useFiltrosObjetivos } from "@/components/features/objetivos/useFiltrosObjetivos"
import { NuevoObjetivoBoton, ObjetivosAcciones } from "@/components/features/objetivos/ObjetivosAcciones"
import { ImportarObjetivosModal } from "@/components/features/objetivos/ImportarObjetivosModal"
import { cambiarEstadoObjetivo, deleteObjetivo, fetchObjetivos } from "@/services/objetivos"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { EstadoObjetivo, Objetivo } from "@/types/objetivo"

/**
 * Orquestador de /objetivos: abre y cierra diálogos y tiene los datos. El estado de FILTROS —los
 * cinco valores, los catálogos que los alimentan y el objeto que viaja al listado y al export—
 * vive en `useFiltrosObjetivos`, que salió de acá cuando este archivo llegó a 147/150 y no
 * admitía el filtro de vista.
 *
 * LOS DOS EJES DE LA PANTALLA, que se leen igual y no son lo mismo (ver `TipoObjetivoTabs`):
 *   · VISTA (anual / operativo) — un dato de la fila; el recorte lo hace el BACKEND.
 *   · TABLERO / LISTA — cómo se dibuja lo que llegó; no toca la red.
 */
export default function ObjetivosPage() {
  const canWrite = useCanWrite()
  const f = useFiltrosObjetivos()
  const [vista, setVista]           = useState<Vista>("tablero")
  const [objetivos, setObjetivos]   = useState<Objetivo[]>([])
  /**
   * 🔴 EL TOTAL LO DICE EL BACKEND, SIEMPRE — nunca `objetivos.length`.
   *
   * Hoy los dos números coinciden porque este listado es el único del sistema que no pagina
   * (`objetivo_repo.find_all` trae el árbol entero). El día que pagine —y el wrapper ya tiene la
   * forma final para eso— `items` pasa a ser una página y `length` diría "20" sobre 400 sin
   * dejar de compilar. Es el bug que `HorasTab` ya pagó una vez: mostraba "9 h" con 400 cargadas
   * porque sumaba con `.reduce()` sobre la página en lugar de leer el total.
   *
   * ⚠️ CUENTA RAÍCES, no objetivos: los subobjetivos viajan anidados en `hijos`, así que
   * `total` NO es la cantidad de filas del tablero ni siquiera hoy. El contador dice "objetivos
   * principales" por eso. El conteo aplanado es otra cosa y solo lo usa el tope de export.
   */
  const [total, setTotal]           = useState(0)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(false)
  const [modalOpen, setModalOpen]   = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [editing, setEditing]       = useState<Objetivo | null>(null)
  const [moviendo, setMoviendo]     = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // El objeto de filtros viaja ENTERO: cambiar la vista dispara el mismo camino que cambiar el
  // estado o la prioridad, y por eso no hay ninguna rama especial para el filtro nuevo.
  const filtros = f.filtros
  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const data = await fetchObjetivos(filtros)
      setObjetivos(data.items)
      setTotal(data.total)
    } catch { setError(true) }
    finally { setLoading(false) }
  }, [filtros.empresaIdOverride, filtros.estado, filtros.prioridad, filtros.responsableId, filtros.tipo])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function handleMover(id: string, estado: EstadoObjetivo) {
    setMoviendo(id)
    try { await cambiarEstadoObjetivo(id, { estado }); await load() }
    catch { toast.error("No se pudo mover el objetivo. Intentá de nuevo.") } finally { setMoviendo(null) }
  }

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteObjetivo(id); await load() }
    catch { toast.error("No se pudo eliminar el objetivo. Intentá de nuevo.") } finally { setDeletingId(null) }
  }

  const chips = chipsDeCampos(f.campos)
  const nuevoBtn = <NuevoObjetivoBoton onClick={() => { setEditing(null); setModalOpen(true) }} />

  return (
    <div>
      <PageHeader
        title="Objetivos"
        description={
          total === 0
            ? "Tablero de tareas del equipo de Capital Humano"
            : `${total} ${total === 1 ? "objetivo principal" : "objetivos principales"} · tablero del equipo de Capital Humano`
        }
        action={
          <ObjetivosAcciones
            canWrite={canWrite}
            filtros={filtros}
            sinEmpresa={!f.empresaDestino}
            onImportar={() => setImportOpen(true)}
            nuevoBtn={nuevoBtn}
          />
        }
      />

      {/* La VISTA va arriba de todo y fuera del panel de filtros: no es un recorte más sobre el
          mismo conjunto, es a cuál de los dos conjuntos se está mirando. */}
      <TipoObjetivoTabs vistas={f.vistas} valor={f.tipoFiltro} onCambio={f.setTipoFiltro} />

      {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los
          chips de la fila inferior).

          🔴 LA BARRA VA SOLA Y A TODO EL ANCHO, como en /empleados, que es la pantalla piloto
          del patrón. Antes compartía una fila con las acciones y eso rompía dos cosas a la vez:
          las acciones del encabezado vivían abajo del encabezado en vez de adentro (o sea que
          /objetivos era la única pantalla donde "Nuevo" no estaba donde está en las otras 20), y
          el `flex-1` con `min-w` metía el panel en una columna propia, con lo cual su caja
          arrancaba corrida y `TipoObjetivoTabs` —que sí va a todo el ancho— quedaba 13px a la
          izquierda del panel. Alinear no era mover las tabs: era sacar la columna. */}
      <FiltersBar campos={f.campos} panel disabled={loading} />

      <ObjetivosVistas
        vista={vista} onVista={setVista} loading={loading} error={error} onReintentar={load}
        objetivos={objetivos} total={total} mostrarEmpresa={f.mostrarEmpresa} canWrite={canWrite}
        onMover={handleMover} moviendo={moviendo} deletingId={deletingId}
        onEdit={(o) => { setEditing(o); setModalOpen(true) }} onDelete={handleDelete}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? nuevoBtn : undefined}
      />

      <ImportarObjetivosModal
        open={importOpen} empresaId={f.empresaDestino}
        onClose={() => setImportOpen(false)}
        onSuccess={() => { void load() }}
      />

      <ObjetivoModal open={modalOpen} onClose={() => { setModalOpen(false); setEditing(null) }}
        onSuccess={() => { setModalOpen(false); setEditing(null); load() }} editing={editing} />
    </div>
  )
}
