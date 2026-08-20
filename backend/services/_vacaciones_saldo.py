"""
Adaptador del núcleo puro para UN empleado — la pantalla de vacaciones.

Traduce filas del repo a `Consumo`, decide QUÉ PERÍODOS entran, y compone
`_vacaciones_cupos.cupos_por_periodo` con `_vacaciones_fifo.saldo`. Ninguna regla de negocio
vive acá: los parámetros están en `config/reglas_vacaciones.py` y la aritmética en los dos
módulos puros. Esto es la COSTURA entre la base y el núcleo, y nada más.

🔴 EL OTRO CONSUMIDOR DEL MISMO NÚCLEO es `services/reportes/_reporte_saldos.py` (R11), que
hace esta misma traducción pero desde dicts crudos y en BATCH para N empleados. Unificar el
cálculo hace que no puedan divergir POR ARITMÉTICA, pero los ADAPTADORES siguen siendo dos y
ahí sí pueden: este usa objetos Pydantic y `derive_estado`, aquel compara fechas contra el
cierre del mes. Esa costura la vigila `tests/test_saldo_service_vs_r11.py`.
"""
from dataclasses import asdict
from datetime import date
from typing import Iterable, List, Optional

from config.reglas_vacaciones import REGLAS, ReglasVacaciones
from schemas.vacaciones import SaldoPeriodoResponse, SaldoVacacionesResponse
from services._vacaciones_cupos import cupos_por_periodo, periodo_de
from services._vacaciones_fifo import Consumo, saldo
from services._vacaciones_utils import derive_estado
from utils.errors import AppError


def _fecha(valor) -> Optional[date]:
    """'YYYY-MM-DD...' → date. Supabase devuelve las fechas como string."""
    return date.fromisoformat(str(valor)[:10]) if valor else None


def consumos_de(solicitudes: Iterable, pendientes: Iterable, hoy: date) -> List[Consumo]:
    """Filas del repo → `Consumo`. Es el ADAPTADOR: el núcleo no sabe de tablas.

    🔴 LAS DOS FUENTES SE TRADUCEN DISTINTO Y NO ES UNA INCONSISTENCIA (está explicado en el
    docstring de `Consumo`): una solicitud consume sus `dias` porque la licencia SE TOMÓ —que
    además se haya liquidado es administrativo y no devuelve días—, y un pendiente consume solo
    `dias_liquidados` porque ahí los días NO se tomaron y lo único que los gasta es que se
    paguen.

    Un pendiente sin liquidar se OMITE, no se manda como `Consumo(dias=0)`. La diferencia no se
    ve en ningún total —sumar 0 no cambia ninguna suma, y por eso el mutation check descubrió
    que sacar esta guarda dejaba la suite en verde— pero sí se ve en la FORMA: un consumo de 0
    días contra un período fuera de la ventana le CREA a ese período una fila con cupo 0, o sea
    un período fantasma en la pantalla del empleado.

    El filtro de `cancelada` y de `tipo` NO está acá: lo hace el repo en el WHERE, que es donde
    corresponde. Repetirlo sería una segunda definición de "qué descuenta".
    """
    out = [Consumo(dias=s.dias, periodo=getattr(s, "periodo", None),
                   tomado=derive_estado(s, hoy).estado == "tomada")
           for s in solicitudes]
    out += [Consumo(dias=p.dias_liquidados, periodo=p.periodo, tomado=True)
            for p in pendientes if p.dias_liquidados]
    return out


def periodos_a_calcular(ingreso: date, corte: date, consumos: List[Consumo],
                        reglas: ReglasVacaciones = REGLAS) -> List[int]:
    """Qué períodos entran en el desglose: la ventana vigente, estirada hacia atrás hasta el
    consumo declarado más viejo, y recortada por el ingreso.

    🚩 ESTA ES LA ÚNICA FUNCIÓN DE TODA LA TANDA QUE ES RECONSTRUCCIÓN Y NO RECUPERACIÓN.
    Su cuerpo nunca llegó a disco: los archivos que sobrevivieron la LLAMAN (R11 y el saldo)
    pero ninguno la contiene. La forma se dedujo de tres evidencias, y se escribe acá para que
    el día que se revise no haya que deducirla de nuevo:
      1. `consumos` es un PARÁMETRO. Si la ventana fuera "todo desde el ingreso", los consumos
         serían redundantes: todo período declarado ya estaría adentro. Que se pasen significa
         que la ventana es acotada y que ellos la estiran.
      2. El front recibe filas con `vencido: true` y las filtra al renderizar
         (`SaldoResumen.test.tsx`), así que el backend SÍ manda períodos vencidos — la ventana
         no puede ser solo la vigente.
      3. `test_saldo_service_vs_r11` llama "ventana de acumulación (hoy−4 … hoy)" a los
         períodos que quería tocar, que es exactamente `anios_acumulacion` hacia atrás.

    POR QUÉ NO "TODO DESDE EL INGRESO", que era la otra opción seria: con `solicitudes_vacaciones`
    en 0 filas (producción, verificado el 3/8/2026), a alguien con 15 años de antigüedad le
    saldrían ~11 períodos vencidos enteros sin gozar y un cartel de "vencieron 200 días". Ese
    número no describiría a la persona: describiría que RRHH todavía no cargó el histórico. Un
    saldo que alarma por un dato faltante se deja de mirar, y ahí se pierde también el aviso
    real. Con esta ventana, un período vencido aparece porque HAY un consumo que lo nombra —o
    sea porque existe el dato— y no por su ausencia.

    ⚠️ CONSECUENCIA QUE HAY QUE CONOCER: los días de un período vencido sobre el que nunca se
    cargó ningún movimiento NO se reportan como perdidos. Es deliberado y es el precio del
    párrafo anterior. Si RRHH decide que quiere ver la pérdida histórica completa, se cambia
    `desde` por `periodo_de(ingreso)` acá y nada más — el resto del cálculo no se entera.
    """
    hasta = periodo_de(corte)
    declarados = [c.periodo for c in consumos if c.periodo is not None]
    desde = max(min(hasta - reglas.anios_acumulacion, *declarados) if declarados
                else hasta - reglas.anios_acumulacion, periodo_de(ingreso))
    return list(range(desde, hasta + 1))


def calcular_saldo(repo, empleado_id, empresa_id=None, pendientes_repo=None) -> SaldoVacacionesResponse:
    """Saldo de vacaciones de un empleado, por período y con vencimiento.

    `empresa_id` acota TODAS las consultas (None = consolidado). El caller ya validó el empleado
    con `ensure_empleado_visible`; propagarlo igual mantiene el filtro donde se leen los datos,
    para que la consulta no dependa de que el gate de arriba exista.

    `pendientes_repo` es opcional y su ausencia significa "sin pendientes", no "error": los
    pendientes son una fuente ADICIONAL de consumo (migración 083) y un caller que no la pase
    obtiene un saldo sin ellos en vez de una excepción.

    Raises:
        AppError: EMPLEADO_NOT_FOUND (404) si no existe o es de otra empresa — el MISMO 404
            para los dos casos, sin oráculo de existencia.
        AppError: EMPLEADO_SIN_FECHA_INGRESO (422), que levanta el núcleo. Ver `fecha_antiguedad`.
    """
    datos = repo.find_datos_para_saldo(str(empleado_id), empresa_id)
    if datos is None:
        raise AppError("Colaborador no encontrado", "EMPLEADO_NOT_FOUND", 404)
    hoy = date.today()
    ingreso = _fecha(datos.get("fecha_ingreso"))
    pendientes = pendientes_repo.find_by_empleado(str(empleado_id), empresa_id) if pendientes_repo else []
    consumos = consumos_de(repo.find_vacaciones_empleado(str(empleado_id), empresa_id), pendientes, hoy)
    # El `if ingreso else []` espeja EXACTAMENTE a R11 (_reporte_saldos._fila_saldo): si acá se
    # decidiera distinto, los dos adaptadores volverían a divergir en el borde. El 422 lo levanta
    # el núcleo, que es quien sabe por qué la fecha hace falta.
    cupos = cupos_por_periodo(ingreso, _fecha(datos.get("fecha_ingreso_reconocida")),
                              datos.get("dias_vacaciones_asignados"),
                              periodos_a_calcular(ingreso, hoy, consumos) if ingreso else [])
    s = saldo(cupos, consumos, hoy)
    return SaldoVacacionesResponse(
        empleado_id=str(empleado_id), asignados=s.asignados, gozados=s.gozados,
        pedidos=s.pedidos, disponibles=s.disponibles, vencidos=s.vencidos,
        por_periodo=[SaldoPeriodoResponse(**asdict(f)) for f in s.por_periodo],
    )
