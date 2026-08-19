"""
La Fecha Baja del CSV de nómina: la guarda de estado (A3.3) y el tramo post-escritura de la
fila. Salió de `nomina_empleados_service.py`, que estaba en 149/150 y la guarda no entraba.

🔴 LA DECISIÓN (A3.3, 19/8/2026): una fila con Fecha Baja sobre un empleado en `preingreso` se
SALTEA ENTERA y se REPORTA — no se da de baja, y tampoco se actualiza el resto de la fila. El
CSV es el sistema de nómina describiendo gente que TRABAJA; un preingreso es alguien que ese
sistema todavía no conoce. Una fila que dice "esta persona se fue" sobre alguien que nunca entró
es un ERROR DE DATOS, no una instrucción — y la política del repo es que el import no come filas
en silencio. Darla de baja además saltearía las guardas de `_offboarding_efectivizar`, incluida
la que existe para que quien nunca entró no figure como baja del mes.

🔴 LA GUARDA CORRE ANTES DE CUALQUIER ESCRITURA. Si corriera después del update (donde vivía la
baja), la fila quedaría "actualizada pero no dada de baja": un estado a medias que el reporte no
sabe contar y que convierte el rechazo en una edición parcial silenciosa.

⚠️ Un empleado NUEVO con Fecha Baja NO pasa por la guarda, a propósito: nace y se da de baja en
el acto. Es el import histórico de bajas de siempre (gente que el sistema nunca conoció y ya se
fue), y ahí no hay estado previo que proteger.
"""
from uuid import UUID

from utils.estados_empleado import ESTADO_PREINGRESO


def rechazar_baja_de_preingreso(existente, fecha_baja) -> None:
    """Lanza ValueError —el motivo que el reporte de filas no procesadas muestra— si la fila
    trae Fecha Baja sobre un empleado en preingreso. Ver el encabezado."""
    if fecha_baja and existente is not None and existente.estado == ESTADO_PREINGRESO:
        raise ValueError(
            "la fila trae Fecha Baja pero el empleado está en preingreso: alguien que nunca "
            "ingresó no puede figurar como baja. La fila no se procesó — corregí el archivo o "
            "activá el ingreso primero.")


def aplicar_vinculos(emp_repo, proyectos, cesiones, superiores, f: dict, fila: int,
                     empleado_id: str, empresa_id: str) -> None:
    """El tramo post-escritura de una fila, movido TAL CUAL del service (comentarios incluidos)."""
    if f["fecha_baja"]:
        emp_repo.dar_de_baja(empleado_id, f["fecha_baja"], UUID(empresa_id))
    # Gerencia → proyecto (crear/reusar) + asignar el empleado (no si está de baja).
    # empresa_id del empleado: es la que acabamos de escribir, no hace falta consultarla.
    proyectos.resolver_y_asignar(
        empresa_id, f["gerencia"], empleado_id, f["roles"][0], bool(f["fecha_baja"]),
        empresa_id)
    # Fecha Ingreso Reconocida → cesión (idempotente por fecha, best-effort).
    cesiones.crear_si_falta(empleado_id, empresa_id, f["fecha_ingreso_reconocida"])
    # Superior: se ANOTA acá y se resuelve DESPUÉS del loop — el jefe puede estar en una fila
    # posterior. Anotarlo desde acá es lo que garantiza que solo se resuelvan las filas que
    # de verdad se escribieron, aun si el presupuesto corta el archivo. Ver `_nomina_superiores`.
    superiores.registrar(fila, empleado_id, empresa_id, f)
