import { Field, Section } from "@/components/features/empleados/ficha/_primitives"
import type { Empleado } from "@/types/empleado"
import { domicilioLegible, mostrarCrudo } from "@/components/features/empleados/ficha/_domicilio"

/**
 * Bloque estático de la ficha: información personal + laboral (espejo del formulario).
 * Presentación pura a partir del empleado ya cargado. Los documentos adjuntos viven en
 * AdjuntosSection (sección propia, autoabastecida).
 * Mantiene el fallback de roles roles[0] ?? cargo hasta la limpieza S6.
 */
export function DatosEmpleadoSection({ empleado }: { empleado: Empleado }) {
  const horasContrato = empleado.horas_contrato != null ? String(empleado.horas_contrato) : null
  // null = nadie lo declaró, que NO es lo mismo que "No". La celda vacía dice justamente eso.
  const siNo = (v: boolean | null) => (v == null ? null : v ? "Sí" : "No")
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
        <Field label="Equipo" value={empleado.equipo} />
        <Field label="Turno" value={empleado.turno} />
        <Field label="Horas de contrato" value={horasContrato} />
        <Field label="Seniority" value={empleado.seniority} />
        <Field label="Categoría" value={empleado.categoria} />
        <Field label="Fecha de ingreso" value={empleado.fecha_ingreso} />
        {/* 🔴 LA FECHA QUE DECIDE EL CUPO DE VACACIONES, y hasta hoy no se mostraba en NINGÚN
            lado (bloque N6). Cuando está cargada reemplaza a la de ingreso para calcular la
            antigüedad —una cesión, un pase entre sociedades del grupo—, así que es la única
            explicación posible de un cupo que no coincide con la fecha de ingreso de al lado.
            Va JUSTO DEBAJO para que la diferencia se lea sin buscarla. */}
        <Field label="Fecha de ingreso reconocida" value={empleado.fecha_ingreso_reconocida} />
        <Field label="Modalidad de trabajo" value={empleado.modalidad_trabajo} />
        <Field label="Tipo de contrato" value={empleado.tipo_contrato} />
        {/* El ESTADO ya no vive acá: es parte de la identidad de la persona, no de sus datos
            laborales, y el patrón de ficha lo pone como chip en la barra de arriba (§3). Tenerlo
            en los dos lados obligaba a mirar cuál de las dos versiones era la verdadera. */}
        <Field label="Líder" value={empleado.es_lider ? "Sí" : "No"} />
        {/* El texto CRUDO que declaró la nómina. Sale además del booleano de arriba porque
            cuando no se pudo mapear a Sí/No ("GERENTE DE ÁREA"), `es_lider` quedó sin escribir
            y este campo es lo único que dice qué llegó realmente en el archivo. */}
        <Field label="Liderazgo (declarado)" value={empleado.liderazgo} />
        <Field label="Product owner" value={siNo(empleado.product_owner)} />
        <Field label="Co-sourcing" value={siNo(empleado.co_sourcing)} />
      </Section>

      {/* 🔴 SECCIÓN PROPIA, Y NO DOS CAMPOS MÁS EN "INFORMACIÓN LABORAL". Son los dos ejes del
          9-box de sucesión y hoy dicen "medio" para TODA la plantilla: ése es el DEFAULT de la
          columna y su único escritor (el assessment) está apagado. Mezclados entre el turno y el
          tipo de contrato se leerían como una calificación que Capital Humano puso; con título
          propio queda claro de qué mapa salen. El subtítulo lo dice de frente. */}
      <Section title="Mapa de talento (9-box)">
        <Field label="Potencial" value={empleado.potencial} />
        <Field label="Desempeño" value={empleado.desempeno} />
      </Section>
    </>
  )
}
