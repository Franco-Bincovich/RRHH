"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus } from "lucide-react"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"

import { PageHeader } from "@/components/layout/PageHeader"
import { CampanaModal } from "@/components/features/assessment/CampanaModal"
import { CampanasTabla } from "@/components/features/assessment/CampanasTabla"
import { ResultadosTabla } from "@/components/features/assessment/ResultadosTabla"
import { Button } from "@/components/ui/button"
import { fetchCampanas, fetchResultados } from "@/services/assessment"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Campana, Resultado } from "@/types/assessment"

export default function AssessmentPage() {
  const router = useRouter()
  /*
   * 🔴 MÓDULO DESACTIVADO A PROPÓSITO (no es un bug): redirige a /dashboard y no renderiza nada.
   * Para reactivarlo: `useState(true)` acá. El backend además lo gatea con `ASSESSMENT_ENABLED`,
   * que por default está en `false` y hace que el router ni se monte — encender el front solo no
   * alcanza y no expone nada.
   *
   * ⚠️ ES `useState` Y NO UN `const` CON LITERAL, y eso no es estilo: TS colapsa `const x = false`
   * al tipo literal `false`, marca el cuerpo de abajo inalcanzable, pierde el narrowing y
   * `next build` falla. Está escrito igual en /sucesion y en assessment/[id].
   *
   * ⚠️ Y REEMPLAZA A UN `return null` SUELTO con `// eslint-disable-next-line no-unreachable`
   * encima. Aquello dejaba SIETE `useState` y un `useEffect` después de un return incondicional:
   * hooks que no corren nunca, en un orden que cambiaría el día que alguien saque el return.
   * Reactivar así era una línea que rompía las reglas de hooks sin que nadie lo viera venir.
   */
  const [moduloActivo] = useState(false)

  useEffect(() => {
    if (!moduloActivo) router.replace("/dashboard")
  }, [router, moduloActivo])

  if (!moduloActivo) return null

  return <AssessmentContenido />
}

/*
 * El contenido vive en un componente aparte por el mismo motivo que en /sucesion: sus dos cargas
 * se disparan al montar, así que si estuvieran en el cuerpo de arriba la pantalla desactivada
 * pegaría dos llamadas al backend antes de redirigir. Acá directamente no se monta.
 */
function AssessmentContenido() {
  const router = useRouter()
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())
  const [campanas, setCampanas] = useState<Campana[]>([])
  const [resultados, setResultados] = useState<Resultado[]>([])
  const [loadingC, setLoadingC] = useState(true)
  const [loadingR, setLoadingR] = useState(true)
  const [errorC, setErrorC] = useState(false)
  const [errorR, setErrorR] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const mostrarEmpresa = !empresaActivaId

  // Las dos cargas salen del efecto para que cada `ErrorState` pueda volver a disparar SU tab:
  // reintentar campañas no tiene por qué recargar resultados, que quizás llegaron bien. Antes el
  // reintento era una cadena de promesas escrita entera adentro del JSX de cada tab.
  const cargarCampanas = useCallback(() => {
    setLoadingC(true); setErrorC(false)
    fetchCampanas().then(setCampanas).catch(() => setErrorC(true)).finally(() => setLoadingC(false))
  }, [])

  const cargarResultados = useCallback(() => {
    setLoadingR(true); setErrorR(false)
    fetchResultados().then(setResultados).catch(() => setErrorR(true)).finally(() => setLoadingR(false))
  }, [])

  useEffect(() => { cargarCampanas(); cargarResultados() }, [cargarCampanas, cargarResultados])

  const nuevaCampana = (
    <Button className="min-h-11" onClick={() => setModalOpen(true)}>
      <Plus />
      Nueva campaña
    </Button>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assessment Engine"
        /* El conteo sale del largo de la lista y NO de un `total` del backend porque acá no hay
           wrapper paginado: el endpoint devuelve el array entero. Es el único caso en que
           `length` es el total, y está declarado para que no se lea como el bug de siempre. */
        description={
          loadingC
            ? "Campañas de evaluación y resultados del modelo AREAS"
            : `${campanas.length} campaña${campanas.length !== 1 ? "s" : ""} · resultados del modelo AREAS`
        }
        action={nuevaCampana}
      />

      <CampanaModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreated={(c) => setCampanas((prev) => [c, ...prev])}
      />

      <Tabs variant="pill" defaultValue="campanias" className="space-y-6">
        <TabList>
          <Tab value="campanias">Campañas</Tab>
          <Tab value="resultados">Resultados</Tab>
        </TabList>

        <TabPanel value="campanias">
          <CampanasTabla
            campanas={campanas}
            loading={loadingC}
            error={errorC}
            onReintentar={cargarCampanas}
            mostrarEmpresa={mostrarEmpresa}
            accionVacio={nuevaCampana}
          />
        </TabPanel>

        <TabPanel value="resultados">
          <ResultadosTabla
            resultados={resultados}
            loading={loadingR}
            error={errorR}
            onReintentar={cargarResultados}
            mostrarEmpresa={mostrarEmpresa}
            onAbrir={(id) => router.push(`/assessment/${id}`)}
          />
        </TabPanel>
      </Tabs>
    </div>
  )
}
