"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Plus } from "lucide-react"
import { Tab, TabList, TabPanel, Tabs } from "@/components/ui/tabs"

import { PageHeader } from "@/components/layout/PageHeader"
import { CampanaModal } from "@/components/features/assessment/CampanaModal"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { fetchCampanas, fetchResultados } from "@/services/assessment"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Campana, Resultado } from "@/types/assessment"

// ─── Helpers ─────────────────────────────────────────────────────────────────

const TIPO_LABEL: Record<string, string> = {
  completo:   "Completo",
  conductual: "Conductual",
  cognitivo:  "Cognitivo",
}

const ESTADO_VARIANT: Record<string, "default" | "secondary"> = {
  activa:   "default",
  cerrada:  "secondary",
  borrador: "secondary",
  archivada: "secondary",
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

// ─── Skeleton rows ────────────────────────────────────────────────────────────

function TableSkeleton({ cols, rows = 4 }: { cols: number; rows?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AssessmentPage() {
  const router = useRouter()

  // HIDDEN — módulo desactivado temporalmente; redirige sin renderizar el resto
  useEffect(() => { router.replace("/dashboard") }, [router])
  return null

  // eslint-disable-next-line no-unreachable
  const [empresaActivaId] = useState<string | null>(() => getEmpresaActivaId())

  const [campanas, setCampanas]   = useState<Campana[]>([])
  const [resultados, setResultados] = useState<Resultado[]>([])
  const [loadingC, setLoadingC]   = useState(true)
  const [loadingR, setLoadingR]   = useState(true)
  const [errorC, setErrorC]       = useState(false)
  const [errorR, setErrorR]       = useState(false)
  const [modalOpen, setModalOpen] = useState(false)

  const mostrarEmpresa = !empresaActivaId

  useEffect(() => {
    fetchCampanas()
      .then(setCampanas)
      .catch(() => setErrorC(true))
      .finally(() => setLoadingC(false))
    fetchResultados()
      .then(setResultados)
      .catch(() => setErrorR(true))
      .finally(() => setLoadingR(false))
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assessment Engine"
        description="Campañas de evaluación y resultados del modelo AREAS"
        action={
          <Button className="min-h-11" onClick={() => setModalOpen(true)}>
            <Plus />
            Nueva campaña
          </Button>
        }
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

        {/* ── Tab 1: Campañas ───────────────────────────────────────────── */}
        <TabPanel value="campanias">
          {errorC ? (
            <ErrorState action={() => { setErrorC(false); setLoadingC(true); fetchCampanas().then(setCampanas).catch(() => setErrorC(true)).finally(() => setLoadingC(false)) }} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  {mostrarEmpresa && <TableHead>Empresa</TableHead>}
                  <TableHead>Tipo</TableHead>
                  <TableHead>Creada</TableHead>
                  <TableHead className="text-right">Links</TableHead>
                  <TableHead className="text-right">Completados</TableHead>
                  <TableHead>Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingC ? (
                  <TableSkeleton cols={mostrarEmpresa ? 7 : 6} />
                ) : campanas.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={mostrarEmpresa ? 7 : 6}>
                      <EmptyState icon={<Plus />} title="Sin campañas" description="Creá la primera campaña de assessment." />
                    </TableCell>
                  </TableRow>
                ) : campanas.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-medium">{c.nombre}</TableCell>
                    {mostrarEmpresa && (
                      <TableCell className="text-muted-foreground">{c.empresa_nombre ?? "—"}</TableCell>
                    )}
                    <TableCell className="text-muted-foreground">{TIPO_LABEL[c.tipo] ?? c.tipo}</TableCell>
                    <TableCell className="text-muted-foreground">{fmtDate(c.created_at)}</TableCell>
                    <TableCell className="text-right text-muted-foreground">{c.links_enviados}</TableCell>
                    <TableCell className="text-right">
                      <span className={c.completados === c.links_enviados && c.links_enviados > 0 ? "text-emerald-600 dark:text-emerald-400 font-medium" : ""}>
                        {c.completados}
                      </span>
                      <span className="text-muted-foreground">/{c.links_enviados}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={ESTADO_VARIANT[c.estado] ?? "secondary"} className="capitalize">
                        {c.estado}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabPanel>

        {/* ── Tab 2: Resultados ─────────────────────────────────────────── */}
        <TabPanel value="resultados">
          {errorR ? (
            <ErrorState action={() => { setErrorR(false); setLoadingR(true); fetchResultados().then(setResultados).catch(() => setErrorR(true)).finally(() => setLoadingR(false)) }} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Evaluado</TableHead>
                  {mostrarEmpresa && <TableHead>Empresa</TableHead>}
                  <TableHead>Tipo</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Perfil dominante</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loadingR ? (
                  <TableSkeleton cols={mostrarEmpresa ? 6 : 5} />
                ) : resultados.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={mostrarEmpresa ? 6 : 5}>
                      <EmptyState icon={<Plus />} title="Sin resultados" description="Todavía no hay evaluaciones completadas." />
                    </TableCell>
                  </TableRow>
                ) : resultados.map((r) => (
                  <TableRow
                    key={r.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/assessment/${r.id}`)}
                  >
                    <TableCell className="font-medium">{r.evaluado_nombre}</TableCell>
                    {mostrarEmpresa && (
                      <TableCell className="text-muted-foreground">{r.empresa_nombre ?? "—"}</TableCell>
                    )}
                    <TableCell className="text-muted-foreground">{TIPO_LABEL[r.tipo] ?? r.tipo}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {r.fecha_completado ? fmtDate(r.fecha_completado) : "—"}
                    </TableCell>
                    <TableCell>
                      {r.perfil_dominante ? <Badge variant="outline">{r.perfil_dominante}</Badge> : "—"}
                    </TableCell>
                    <TableCell className="text-right font-semibold">
                      {r.score_general ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabPanel>
      </Tabs>
    </div>
  )
}
