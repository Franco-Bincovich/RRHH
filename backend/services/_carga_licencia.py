"""
Carga de una LICENCIA desde el link público. Va a `solicitudes_ausencia`, no a una tabla nueva.

Función libre que recibe los colaboradores — mismo molde que `_ausencias_write.crear`, del que
esto es el hermano público. **NO se reusa `_ausencias_write.crear`**, y el motivo importa: esa
función exige un `created_by` que es el OPERADOR y lo usa para el chequeo de ownership y para el
`usuario_id` de la auditoría. Acá no hay operador: el sujeto ES el empleado, no tiene cuenta
(`empleados.user_id` está 0/31) y el ownership no aplica —nadie está actuando sobre un tercero—.
Forzar ese camino habría pedido inventar un usuario del sistema.

── LAS TRES DECISIONES DE PRODUCTO QUE ESTE ARCHIVO FIJA ──────────────────────

1. 🔴 EL TIPO ES "Licencia", SEMBRADO CON UUID FIJO (migración 107).
   Los cuatro tipos que ya existían —Enfermedad, Personal, Otro, Injustificada— son MOTIVOS, y un
   motivo es una calificación que hace RRHH mirando la documentación. Lo que la persona carga
   desde el link no es un motivo: es el hecho de que ese día no trabajó. Se referencia por ID y
   NO por nombre porque `tipos_ausencia.nombre` lo edita RRHH desde la pantalla de configuración:
   buscar por texto rompería la carga pública el día que alguien lo renombre.
   `cuenta_ausentismo` va en TRUE (la licencia computa para el ausentismo) y vive en el tipo.

2. 🔴 `justificada = False`, SIEMPRE. Un empleado NO puede justificarse a sí mismo: `justificada`
   es el juicio que RRHH emite sobre el hecho, no una declaración del interesado. Ponerlo en True
   le daría a cualquiera con un DNI la autoridad de dar por justificada su propia ausencia, que
   es exactamente la que este flujo no tiene.
   ⚠️ CONSECUENCIA QUE HAY QUE SABER, no un efecto colateral escondido: hasta que RRHH lo revise,
   estas licencias aparecen en la franja "injustificado" de `_reporte_ausentismo`. El valor no
   significa "injustificada para siempre" sino "todavía no revisada" — y no hay un tercer estado
   donde ponerlo, porque la columna es booleana. Es el precio de no dejar que se autojustifiquen.

3. 🔴 SIN `horas_contrato` SE ASUMEN 8, Y SE AVISA. La columna está en 0/31, así que "no dejar
   cargar" dejaría la feature inservible para el padrón ENTERO desde el día uno. Se asume 8 —el
   valor de 30 de los 31 turnos reales— y la respuesta viaja con `horas_por_dia_estimadas=True`
   para que la pantalla lo diga en vez de afirmar un número inventado como si fuera dato.
   No se deriva de `empleados.turno`: ver `identificacion_repo.horas_contrato`.

── EL DOBLE TAP ───────────────────────────────────────────────────────────────
🟢 Ya está cerrado EN LA BASE y verificado contra el catálogo vivo: la migración 089 SÍ está
corrida, así que existe `uq_ausencia_empleado_rango_tipo (empleado_id, fecha_desde, fecha_hasta,
tipo_id)`. Dos envíos idénticos no pueden crear dos licencias. Acá solo se traduce ese choque a
un mensaje legible en vez de dejar salir el error crudo de la constraint.
"""
from datetime import date

from schemas.horas_publico import CargaLicenciaRequest, CargaLicenciaResponse
from services._carga_reglas import verificar_ventana
from utils.errors import AppError
from utils.logger import logger

# Espejo del id sembrado en `migrations/107_tipo_ausencia_licencia.sql`. Fijo a propósito: ver la
# decisión 1 del encabezado. Hay un test que compara este literal contra el de la migración.
TIPO_LICENCIA_ID = "9f3b7c2a-1d4e-4a6b-8c5d-0e1f2a3b4c5d"

# Jornada asumida cuando `empleados.horas_contrato` está vacío. Ver la decisión 3.
HORAS_POR_DIA_POR_DEFECTO = 8


def crear(ausencias_repo, datos_repo, empleado_id: str, empresa_id: str,
          data: CargaLicenciaRequest, hoy: date) -> CargaLicenciaResponse:
    """Registra la licencia. `empleado_id`/`empresa_id` vienen de la SESIÓN, nunca del body.

    Raises:
        AppError: FECHA_FUTURA / FECHA_MUY_VIEJA / RANGO_INVALIDO (422), LICENCIA_DUPLICADA (409).
    """
    if data.fecha_hasta < data.fecha_desde:
        raise AppError("La fecha de fin no puede ser anterior a la de inicio.",
                       "RANGO_INVALIDO", 422)
    # La ventana se valida en los DOS extremos: `desde` para que no sea más vieja que el límite,
    # `hasta` para que no caiga en el futuro. Validar uno solo dejaría pasar un rango que empieza
    # ayer y termina el año que viene.
    verificar_ventana(data.fecha_desde, hoy)
    verificar_ventana(data.fecha_hasta, hoy)

    dias = (data.fecha_hasta - data.fecha_desde).days + 1
    horas_dia = datos_repo.horas_contrato(empleado_id)
    estimadas = horas_dia is None
    horas_dia = horas_dia if horas_dia else HORAS_POR_DIA_POR_DEFECTO

    try:
        row = ausencias_repo.save(
            empleado_id, empresa_id, TIPO_LICENCIA_ID,
            data.fecha_desde, data.fecha_hasta, dias,
            False,                      # justificada — ver la decisión 2
            data.observaciones,
        )
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 — el choque de uq_ausencia_empleado_rango_tipo
        logger.warning("Licencia duplicada rechazada por la base",
                       extra={"empleado_id": empleado_id, "error": str(exc)})
        raise AppError("Ya cargaste una licencia para esas fechas.", "LICENCIA_DUPLICADA", 409)

    if estimadas:
        logger.info("Licencia con jornada estimada: el colaborador no tiene horas_contrato",
                    extra={"empleado_id": empleado_id})
    return CargaLicenciaResponse(
        id=row.id, fecha_desde=data.fecha_desde, fecha_hasta=data.fecha_hasta, dias=dias,
        horas_equivalentes=float(dias * horas_dia), horas_por_dia_estimadas=estimadas,
    )
