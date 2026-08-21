"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import type { Area } from "@/types/area"
import type { Empresa } from "@/types/empresa"
import type { TipoEval } from "@/types/assessment"

import { TIPOS } from "./_camposCampana"

/**
 * Los CINCO campos del alta de campaña. Presentacional y controlado: no fetchea, no valida y no
 * tiene estado propio — todo entra por props y sale por los `set*`.
 *
 * 🔴 Salió de `CampanaModal.tsx` porque ese archivo estaba en 202 líneas contra un límite de 150
 * (deuda ya anotada en CLAUDE.md). El corte deja al modal con lo que decide —abrir, validar,
 * mandar, cerrar— y acá lo que se dibuja, que es la mitad más larga y la que menos cambia.
 *
 * ⚠️ NO HAY VALIDACIÓN EN DOS NIVELES, y no es un olvido: tampoco hay mensajes POR CAMPO. Este
 * formulario tiene un único `error` de texto que sale del submit o del servidor y se muestra
 * abajo. Un banner `<FormErrores cantidad>` arriba diría "Revisá 1 campo" sin poder decir cuál,
 * que es peor que no tenerlo.
 */
export function CampanaFormFields({
  mostrarEmpresa, empresas, empresaId, setEmpresaId,
  nombre, setNombre, tipo, setTipo, areas, areaId, setAreaId,
  posicionObjetivo, setPosicion, error,
}: {
  mostrarEmpresa: boolean
  empresas: Empresa[]
  empresaId: string
  setEmpresaId: (v: string) => void
  nombre: string
  setNombre: (v: string) => void
  tipo: TipoEval
  setTipo: (v: TipoEval) => void
  areas: Area[]
  areaId: string
  setAreaId: (v: string) => void
  posicionObjetivo: string
  setPosicion: (v: string) => void
  error: string | null
}) {
  return (
    <>
      {/* Selector de empresa — solo cuando topbar = "Todas" */}
      {mostrarEmpresa && (
        <div className="space-y-1.5">
          <Label htmlFor="campana-empresa">Empresa</Label>
          <Select
            id="campana-empresa"
            value={empresaId}
            onChange={(e) => setEmpresaId(e.target.value)}
          >
            <option value="">Seleccioná una empresa…</option>
            {empresas.map((e) => (
              <option key={e.id} value={e.id}>{e.nombre}</option>
            ))}
          </Select>
        </div>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="campana-nombre">Nombre</Label>
        <Input
          id="campana-nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej. Assessment Q2 2025"
          autoFocus
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="campana-tipo">Tipo de evaluación</Label>
        <Select
          id="campana-tipo"
          value={tipo}
          onChange={(e) => setTipo(e.target.value as TipoEval)}
        >
          {TIPOS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="campana-area">Área <span className="text-muted-foreground">(opcional)</span></Label>
        <Select
          id="campana-area"
          value={areaId}
          onChange={(e) => setAreaId(e.target.value)}
        >
          <option value="">Sin área específica</option>
          {areas.map((a) => (
            <option key={a.id} value={a.id}>{a.nombre}</option>
          ))}
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="campana-posicion">
          Posición objetivo <span className="text-muted-foreground">(opcional)</span>
        </Label>
        <Input
          id="campana-posicion"
          value={posicionObjetivo}
          onChange={(e) => setPosicion(e.target.value)}
          placeholder="Ej. Tech Lead, Product Manager…"
        />
      </div>

      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </>
  )
}
