import { Badge } from "@/components/ui/badge"
import { Field, Section } from "@/components/features/empleados/ficha/_primitives"
import type { Empleado } from "@/types/empleado"
import { domicilioLegible, mostrarCrudo } from "@/components/features/empleados/ficha/_domicilio"

// 🔑 EL TIPO SE ATA A `Empleado["estado"]` A PROPÓSITO, y ahí está todo el valor de este mapa.
// Antes era un `as const` suelto: sus claves no tenían ninguna relación declarada con la unión
// de estados, así que cuando la unión se ensanchó (migración 120: `preingreso` y `suspendido`)
// TypeScript sí lo cazó — y ese rojo es la feature, no la molestia. La alternativa que se
// descartó, `Record<string, ...>`, hace compilar cualquier cosa: es lo que tiene el mapa
// hermano de `EmpleadosTable.tsx:22`, y por eso ÉL no rompió al ensancharse la unión. No es una
// virtud suya: es que dejó de mirar, y un typo en una clave ahí no lo caza nadie.
//
// ⚠️ `Partial` Y NO `Record` COMPLETO: `suspendido` cae DELIBERADAMENTE al `?? "outline"` de
// abajo, no es una entrada olvidada. Es un valor muerto —está en el CHECK pero ningún camino
// del backend lo escribe, ver `utils/estados_empleado.py`— y darle una variante propia sería
// decidir cómo se ve algo que nadie produce. El día que algo lo escriba, se le elige una acá.
//
// 🔴 `preingreso` NO comparte variante con `activo`: alguien que todavía no entró tiene que
// verse DISTINTO en la ficha. Es el punto entero de la feature — si se vieran igual, la
// pantalla afirmaría que esa persona ya está trabajando.
const ESTADO_VARIANTS: Partial<
  Record<Empleado["estado"], "default" | "destructive" | "secondary">
> = {
  activo: "default",
  baja: "destructive",
  licencia: "secondary",
  preingreso: "secondary",
}

/**
 * Bloque estático de la ficha: información personal + laboral (espejo del formulario).
 * Presentación pura a partir del empleado ya cargado. Los documentos adjuntos viven en
 * AdjuntosSection (sección propia, autoabastecida).
 * Mantiene el fallback de roles roles[0] ?? cargo hasta la limpieza S6.
 */
export function DatosEmpleadoSection({ empleado }: { empleado: Empleado }) {
  const horasContrato = empleado.horas_contrato != null ? String(empleado.horas_contrato) : null
  const roles = (empleado.roles ?? []).join(", ") || empleado.cargo

  return (
    <>
      <Section title="Información personal">
        <Field label="Tipo de documento" value={empleado.tipo_documento} />
        <Field label="Documento" value={empleado.dni} />
        <Field label="CUIT/CUIL" value={empleado.cuil} />
        <Field label="N° de legajo" value={empleado.legajo} />
        <Field label="Sexo" value={empleado.sexo} />
        <Field label="Fecha de nacimiento" value={empleado.fecha_nacimiento} />
        <Field label="Teléfono" value={empleado.telefono} />
        <Field label="Teléfono alternativo" value={empleado.telefono_alternativo} />
        <Field label="Email" value={empleado.email_corporativo} />
        <Field label="Email alternativo" value={empleado.email_personal} />
        <Field label="Domicilio" value={domicilioLegible(empleado)} />
        {mostrarCrudo(empleado) && (
          <Field label="Domicilio (sin desglosar)" value={empleado.domicilio} />
        )}
        <Field label="Estudios" value={empleado.estudios} />
      </Section>

      <Section title="Información laboral">
        <Field label="Empresa" value={empleado.empresa_nombre} />
        <Field label="Área" value={empleado.area_nombre} />
        <Field label="Superior inmediato" value={empleado.manager_nombre} />
        <Field label="Rol" value={roles} />
        <Field label="Ubicación" value={empleado.ubicacion} />
        <Field label="Turno" value={empleado.turno} />
        <Field label="Horas de contrato" value={horasContrato} />
        <Field label="Organismo" value={empleado.organismo} />
        <Field label="Gerencia" value={empleado.gerencia} />
        <Field label="Sector" value={empleado.sector} />
        <Field label="Seniority" value={empleado.seniority} />
        <Field label="Perfil" value={empleado.perfil} />
        <Field label="Categoría" value={empleado.categoria} />
        <Field label="Fecha de ingreso" value={empleado.fecha_ingreso} />
        <Field label="Modalidad de trabajo" value={empleado.modalidad_trabajo} />
        <Field label="Tipo de contrato" value={empleado.tipo_contrato} />
        <Field label="Líder" value={empleado.es_lider ? "Sí" : "No"} />
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Estado
          </dt>
          <dd className="mt-1">
            <Badge variant={ESTADO_VARIANTS[empleado.estado] ?? "outline"}>
              {empleado.estado}
            </Badge>
          </dd>
        </div>
      </Section>
    </>
  )
}
