"use client"

import { useEffect, useState } from "react"

import { fetchAreas } from "@/services/areas"
import { fetchEmpresas } from "@/services/empresas"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"

// Carga UNA sola vez las empresas y TODAS las áreas para el armado manual de reportes.
// Cada Area trae empresa_id, así que las tarjetas filtran client-side por la empresa elegida en
// el form — sin N fetches por card. La empresa/área del form NO se leen del selector del sidebar.
export function useReportesFormData() {
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let activo = true
    Promise.all([fetchEmpresas(), fetchAreas()])
      .then(([emp, ar]) => {
        if (!activo) return
        setEmpresas(emp.items)
        setAreas(ar)
      })
      .catch(() => {
        if (activo) {
          setEmpresas([])
          setAreas([])
        }
      })
      .finally(() => {
        if (activo) setLoading(false)
      })
    return () => {
      activo = false
    }
  }, [])

  return { empresas, areas, loading }
}
