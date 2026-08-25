"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { NotaInfo } from "@/components/ui/NotaInfo"
import { Pagination } from "@/components/ui/Pagination"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { PerfilesGrid } from "@/components/features/perfilesPuesto/PerfilesGrid"
import { PerfilModal } from "@/components/features/perfilesPuesto/PerfilModal"
import { cargarCampos, cargarPerfiles } from "@/components/features/perfilesPuesto/cargarPerfiles"
import { useAccionesPerfil } from "@/components/features/perfilesPuesto/useAccionesPerfil"
import { useFiltrosPerfiles } from "@/components/features/perfilesPuesto/useFiltrosPerfiles"
import {
  AVISO_CATALOGO_GLOBAL, AVISO_SIN_PUENTE_VACANTE,
} from "@/components/features/perfilesPuesto/_avisos"
import { exportarPerfiles } from "@/services/perfilesPuesto"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { CamposPerfilResponse, PerfilPuesto } from "@/types/perfilPuesto"

// 12 y no 20: son tarjetas de tres columnas, así que 12 llena exactamente cuatro filas y 20
// dejaría una última fila coja. El backend topea `page_size` en 100.
const PAGE_SIZE_INICIAL = 12

/**
 * El catálogo de PERFILES DE PUESTO: las plantillas con las que se arma un aviso de búsqueda.
 * ORQUESTADOR — el estado y la navegación; las tarjetas, el formulario y la carga viven en
 * `components/features/perfilesPuesto/`.
 *
 * 🔴 ES UNA PANTALLA DE TARJETAS, NO UNA TABLA (`docs/SISTEMA-DE-DISENO.md` §5): un perfil es
 * algo que **se elige**, no un registro que se compara con el de al lado.
 *
 * 🔴 Y ES EL ÚNICO LISTADO DEL SISTEMA QUE EL SELECTOR DE EMPRESA DEL SIDEBAR NO ACOTA. Ninguna
 * de las 7 rutas de perfiles lee `X-Empresa-Id`. Como es lo contrario a lo que hace el resto del
 * producto, la pantalla lo DICE (`AVISO_CATALOGO_GLOBAL`) en vez de dejar que alguien lo deduzca
 * al chocar con el 409 de nombre duplicado.
 */
export default function PerfilesPuestoPage() {
  const canWrite = useCanWrite()
  const [perfiles, setPerfiles] = useState<PerfilPuesto[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [catalogos, setCatalogos] = useState<CamposPerfilResponse | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [modalOpen, setModalOpen] = useState(false)
  const [editando, setEditando] = useState<PerfilPuesto | undefined>(undefined)

  const { filtros, campos } = useFiltrosPerfiles(() => setPage(1))
  const chips = chipsDeCampos(campos)

  const load = useCallback(
    () => cargarPerfiles(filtros, page, pageSize, { setPerfiles, setTotal, setLoading, setError }),
    [filtros, page],
  )
  useEffect(() => { void load() }, [load])
  // Los labels del formulario se piden UNA vez y no por apertura del modal: son estáticos del
  // backend. Su falla no rompe la pantalla — ver `cargarCampos`.
  useEffect(() => { void cargarCampos().then(setCatalogos) }, [])

  // Las dos escrituras que no pasan por el formulario (baja y reactivación) viven aparte;
  // el porqué del corte está en el encabezado del hook.
  const { aBaja, setABaja, bajando, confirmarBaja, reactivar } = useAccionesPerfil(load)

  function abrirAlta() { setEditando(undefined); setModalOpen(true) }

  return (
    <div>
      <PageHeader
        title="Perfiles de puesto"
        // El conteo real se mantiene durante la recarga: `total` no se limpia, así que la
        // pantalla no salta a "Cargando..." y vuelve cada vez que se refiltra.
        description={`${total} ${total === 1 ? "perfil" : "perfiles"} · ${AVISO_CATALOGO_GLOBAL}`}
        action={
          <div className="flex items-center gap-2">
            {/* Los MISMOS filtros que el listado: el archivo no puede traer filas que la
                pantalla no muestre. Sin header de empresa — el catálogo es global. */}
            <ExportMenu onExport={(formato) => exportarPerfiles(formato, filtros)} />
            {canWrite && catalogos && (
              <Button className="min-h-11" onClick={abrirAlta}>
                <Plus />
                Nuevo perfil
              </Button>
            )}
          </div>
        }
      />

      {/* 🔴 EL AVISO VA ARRIBA Y SIEMPRE, no adentro del vacío solamente: con 0 filas el vacío es
          toda la pantalla, pero con 20 perfiles cargados el aviso sigue siendo la información que
          evita que alguien busque el selector de perfil en la vacante y no lo encuentre. */}
      <NotaInfo className="mb-4">{AVISO_SIN_PUENTE_VACANTE}</NotaInfo>

      <FiltersBar campos={campos} disabled={loading} />

      <PerfilesGrid
        perfiles={perfiles}
        catalogos={catalogos}
        loading={loading}
        error={error}
        canWrite={canWrite}
        chips={chips}
        onRetry={load}
        onEdit={(p) => { setEditando(p); setModalOpen(true) }}
        onBaja={setABaja}
        onReactivar={reactivar}
        accionVacio={canWrite && catalogos ? (
          <Button className="min-h-11" onClick={abrirAlta}><Plus />Cargar el primero</Button>
        ) : undefined}
      />

      {!loading && !error && perfiles.length > 0 && (
        <Pagination
          page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage}
        />
      )}

      {/* El modal solo se monta con los catálogos cargados: sin labels, sin ayudas y sin
          vocabularios no sería un formulario a medias sino uno que guarda mal. */}
      {catalogos && (
        <PerfilModal
          open={modalOpen}
          catalogos={catalogos}
          perfil={editando}
          onClose={() => setModalOpen(false)}
          onSuccess={() => { setModalOpen(false); void load() }}
        />
      )}

      <ConfirmDialog
        open={Boolean(aBaja)}
        onClose={() => setABaja(null)}
        onConfirm={confirmarBaja}
        loading={bajando}
        title="Dar de baja el perfil"
        description={`"${aBaja?.nombre}" deja de aparecer en el catálogo. Es una baja lógica: las vacantes creadas desde él no se tocan, y podés reactivarlo cuando quieras.`}
        confirmLabel="Dar de baja"
      />
    </div>
  )
}
