"""
Repositorio del link público de identificación por DNI. Acceso con supabase_admin.

🔴 ESTE REPO LO CONSULTA UNA RUTA SIN AUTENTICACIÓN. Los tres métodos están escritos para
devolver LO MÍNIMO, no lo cómodo:

  · `buscar_por_dni` NO usa el SELECT de `_empleado_row` —el que usa el resto del sistema—
    porque ese trae resueltos por join el área, el manager y el nombre de la empresa. Traer eso
    para descartarlo es cargar en memoria de un handler público exactamente los datos que la
    respuesta no puede mostrar. Se piden cuatro columnas y nada más.
  · NO acota por empresa, a propósito: la ruta pública no tiene `X-Empresa-Id` (no hay sesión) y
    el dni es lo único que llega. Por eso puede devolver 0, 1 o N filas — ver el service.
"""
from typing import List, Optional

from integrations.supabase_client import supabase_admin
from utils.logger import logger

_EMPLEADOS = "empleados"
_CLIENTES = "clientes"
_INTENTOS = "intentos_identificacion"


def buscar_por_dni(dni: str) -> List[dict]:
    """Empleados con ese DNI en CUALQUIER empresa. Lista, no fila: `empleados` tiene
    UNIQUE (empresa_id, dni) y NO unique global, así que el mismo dni puede estar en dos
    sociedades del grupo. Devolver `maybe_single()` acá reventaría con 2 filas."""
    res = (supabase_admin.table(_EMPLEADOS)
           .select("id, nombre, estado, empresa_id")
           .eq("dni", dni).execute())
    return res.data or []


def hay_clientes_activos(empresa_id: str) -> bool:
    """¿La empresa tiene al menos un cliente activo? Sin clientes no hay nada que cargar, así
    que identificarse no sirve de nada — y ese caso sale por el MISMO rechazo que los demás.

    `limit(1)`: la pregunta es de existencia, no de cantidad."""
    res = (supabase_admin.table(_CLIENTES).select("id")
           .eq("empresa_id", empresa_id).eq("activo", True).limit(1).execute())
    return bool(res.data)


def horas_contrato(empleado_id: str) -> Optional[int]:
    """Horas de jornada del empleado, o None si el dato no está cargado.

    ⚠️ NO intenta derivarlo de `empleados.turno`, que es donde el dato REALMENTE vive hoy
    ("8 A 17 HS.", "8 A 14 HS.", 31/31 poblado) mientras `horas_contrato` está en 0/31. Parsear
    ese texto no es aritmética: "8 A 17" son NUEVE horas de reloj que valen OCHO de trabajo, y esa
    conversión es una convención que nadie definió. Inventarla acá metería un número inventado en
    el cálculo de una licencia. El caller asume 8 y lo marca como estimado; el arreglo de fondo es
    poblar la columna. Ver `services/_carga_licencia.py`.
    """
    res = (supabase_admin.table(_EMPLEADOS).select("horas_contrato")
           .eq("id", empleado_id).maybe_single().execute())
    return res.data.get("horas_contrato") if (res and res.data) else None


def registrar_intento(dni: str, resultado: str, empleado_id: Optional[str],
                      empresa_id: Optional[str], ip: Optional[str],
                      user_agent: Optional[str]) -> None:
    """Deja constancia del intento. NUNCA propaga.

    🔴 SE TRAGA TODO ERROR, igual que `AuditService.registrar`, y por el mismo motivo: el log es
    secundario a la operación. Pero acá hay una razón extra y más fuerte — si un fallo del INSERT
    se propagara, el tiempo de respuesta cambiaría según el resultado del intento, y eso
    reintroduciría por la ventana el oráculo de timing que el service cierra por la puerta.

    ⚠️ El `user_agent` se trunca: es un header que controla el cliente y sin techo es un vector
    para inflar la tabla. 512 alcanza para cualquier UA real.
    """
    try:
        supabase_admin.table(_INTENTOS).insert({
            "dni": dni, "resultado": resultado, "empleado_id": empleado_id,
            "empresa_id": empresa_id, "ip": ip,
            "user_agent": (user_agent or "")[:512] or None,
        }).execute()
    except Exception as exc:  # noqa: BLE001 — ver el docstring
        logger.warning("No se pudo registrar el intento de identificación",
                       extra={"resultado": resultado, "error": str(exc)})
