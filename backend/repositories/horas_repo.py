"""Repositorio de horas_proyecto. Acceso a Supabase con supabase_admin.

El mapper y sus lookups por lotes viven en `_hora_row.py` (este archivo llegaba a 118/100 al
sumarle la migración 103).

🔴 UNA SOLA TABLA, DOS CAMINOS DE ESCRITURA. `save` acepta los campos de los dos y manda solo
los que recibe: el camino viejo (asignación + proyecto + snapshot) y la carga directa (cliente +
empleado + modalidad + textos). Ninguno de los dos ve los campos del otro en el payload.
"""
from typing import List, Optional, Tuple

from integrations.supabase_client import supabase_admin
from repositories._hora_row import build
from schemas.horas import HoraResponse
from utils.errors import AppError

_T = "horas_proyecto"

# Campos que solo van al INSERT si el caller los trae. `descripcion` y `cargado_por` estaban
# antes con un `if <valor>:` (truthiness); acá el criterio es `is not None` para los nuevos, que
# es lo correcto para textos: `proyecto_texto=""` es un dato que el usuario escribió, no un
# campo ausente. Se dejan los dos viejos con su comportamiento original.
_OPCIONALES = ("asignacion_id", "proyecto_id", "valor_hora_snapshot",
               "cliente_id", "empleado_id", "modalidad", "proyecto_texto", "tarea_texto",
               "idempotencia")


class HorasRepo:
    def find_by_proyecto(self, proyecto_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[HoraResponse], int]:
        """Retorna (página de horas del proyecto, más reciente primero, total real).

        Las cargas directas NO aparecen acá: tienen `proyecto_id` NULL y un `.eq()` nunca matchea
        un NULL. Es el comportamiento buscado — no son horas de ningún proyecto."""
        res = (supabase_admin.table(_T).select("*", count="exact")
               .eq("proyecto_id", proyecto_id).order("fecha", desc=True)
               .range((page - 1) * page_size, page * page_size - 1).execute())
        return build(res.data or []), res.count or 0

    def save(
        self, empresa_id: str, empleado_empresa_id: str, fecha: str, horas: float,
        descripcion: Optional[str] = None, cargado_por: Optional[str] = None, **opcionales,
    ) -> HoraResponse:
        """Inserta un registro. Los campos de cada camino llegan por `opcionales`.

        Obligatorios en los DOS caminos: empresa, empresa del empleado, fecha y horas.
        `valor_hora_snapshot` ya viene congelado por el service (camino viejo)."""
        payload: dict = {
            "empresa_id": empresa_id, "empleado_empresa_id": empleado_empresa_id,
            "fecha": fecha, "horas": horas,
        }
        payload.update({k: v for k, v in opcionales.items()
                        if k in _OPCIONALES and v is not None})
        if descripcion:
            payload["descripcion"] = descripcion
        if cargado_por:
            payload["cargado_por"] = cargado_por
        res = supabase_admin.table(_T).insert(payload).execute()
        if not res.data:
            raise AppError("Error al registrar las horas", "DB_ERROR", 500)
        rows = supabase_admin.table(_T).select("*").eq("id", str(res.data[0]["id"])).execute().data or []
        return build(rows)[0]

    def total_horas_del_dia(self, empleado_id: str, fecha: str) -> float:
        """Suma de las horas ya cargadas por ese empleado ese día. Insumo del tope de 12.

        🔴 CUENTA POR `empleado_id`, o sea solo las cargas directas del link. Las del camino
        viejo tienen `empleado_id` NULL —se llega a la persona por la asignación— así que no
        entran. Brecha REAL y declarada: se acepta porque `horas_proyecto` tiene 0 filas y ese
        camino es de costeo de proyecto, no de la jornada que declara la persona; cerrarlo pide
        resolver sus asignaciones, o sea una query más en el camino caliente.
        🚩 Disparador: que el camino viejo empiece a usarse de verdad.
        """
        filas = (supabase_admin.table(_T).select("horas")
                 .eq("empleado_id", empleado_id).eq("fecha", fecha).execute().data or [])
        return float(sum(float(f["horas"]) for f in filas))

    def buscar_por_idempotencia(self, idempotencia: str) -> Optional[HoraResponse]:
        """La carga ya creada con ese identificador de envío, o None. Sostiene el doble tap."""
        filas = (supabase_admin.table(_T).select("*")
                 .eq("idempotencia", idempotencia).execute().data or [])
        return build(filas)[0] if filas else None

    def find_proyecto_id(self, hora_id: str) -> Optional[str]:
        """Retorna proyecto_id del registro de horas. None si no existe O si no tiene proyecto
        (carga directa): el caller trata los dos casos igual, y es correcto — una carga sin
        proyecto no se alcanza por la ruta /proyectos/{id}/horas."""
        res = supabase_admin.table(_T).select("proyecto_id").eq("id", hora_id).maybe_single().execute()
        if not (res and res.data and res.data.get("proyecto_id")):
            return None
        return str(res.data["proyecto_id"])

    def delete(self, id: str) -> bool:
        return bool(supabase_admin.table(_T).delete().eq("id", id).execute().data)
