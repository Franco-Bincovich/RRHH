"""
Helper del import de nómina: crea/reusa un proyecto por cada valor de Gerencia y asigna
al empleado. Reusa ProyectosService y AsignacionesService (nada de inserts directos).

- Proyecto por gerencia: dedup por nombre normalizado dentro de la empresa (trim+case),
  cacheado + primado desde los proyectos existentes → idempotente al reimportar.
- Asignación: UNIQUE(proyecto_id, empleado_id) en DB → si ya existe, el service tira
  ASIGNACION_DUPLICADA y acá se traga (idempotente). Empleado en baja: no se asigna.
- Best-effort: un fallo de proyecto/asignación NO rompe la carga del empleado (ya creado);
  se loguea y sigue. Gerencia vacía/"NO APLICA" llega como None (limpiada en el parser) → no hace nada.
"""
from typing import Optional
from uuid import UUID

from schemas.proyectos import AsignacionCreate, ProyectoCreate
from services._nomina_parsers import normalizar_nombre
from services.asignaciones_service import AsignacionPrecargada, AsignacionesService
from services.proyectos_service import ProyectosService
from utils.errors import AppError
from utils.logger import logger


class NominaProyectos:
    def __init__(self) -> None:
        self._proyectos = ProyectosService()
        self._asignaciones = AsignacionesService()
        self._cache: dict[tuple, str] = {}      # (empresa_id, nombre_norm) -> proyecto_id
        self._primadas: set[str] = set()

    def resolver_y_asignar(
        self, empresa_id: str, gerencia: Optional[str], empleado_id: str, rol: str, es_baja: bool,
        empleado_empresa_id: Optional[str] = None,
    ) -> None:
        """Crea/reusa el proyecto de la gerencia y asigna al empleado (si no está de baja).
        Gerencia None (vacía/"NO APLICA") → no hace nada. Best-effort: nunca propaga.

        `empleado_empresa_id` es la empresa del empleado que el import ACABA de crear/actualizar.
        Con ese dato la asignación no necesita las 3 queries de validación (ver
        AsignacionPrecargada). None → se resuelven contra la base, como antes."""
        if not gerencia:
            return
        try:
            proyecto_id = self._proyecto_id(empresa_id, gerencia)
            if not es_baja:
                self._asignar(proyecto_id, empleado_id, rol, empresa_id, empleado_empresa_id)
        except Exception as exc:  # noqa: BLE001 — no romper la carga del empleado ya creado
            logger.warning("No se pudo crear/asignar el proyecto de gerencia", extra={
                "gerencia": gerencia, "empleado_id": empleado_id, "error": str(exc)})

    def _proyecto_id(self, empresa_id: str, nombre: str) -> str:
        """Crea o reusa el proyecto por (empresa, nombre normalizado). Guarda nombre original."""
        clave = (empresa_id, normalizar_nombre(nombre))
        if empresa_id not in self._primadas:
            for p in self._proyectos.get_all(UUID(empresa_id)).items:
                self._cache.setdefault((empresa_id, normalizar_nombre(p.nombre)), str(p.id))
            self._primadas.add(empresa_id)
        if clave not in self._cache:
            creado = self._proyectos.create(ProyectoCreate(empresa_id=UUID(empresa_id), nombre=nombre.strip()))
            self._cache[clave] = str(creado.id)
        return self._cache[clave]

    def _asignar(self, proyecto_id: str, empleado_id: str, rol: str, empresa_id: str,
                 empleado_empresa_id: Optional[str] = None) -> None:
        """Asigna el empleado al proyecto. Si ya está asignado (reimport), es idempotente.

        El proyecto sale de `_proyecto_id`, cuyo cache se primó con `get_all(empresa_id)` o se
        llenó creándolo con `ProyectoCreate(empresa_id=...)`: en los dos casos es de esa empresa,
        así que `proyecto_existe_en_empresa=True` no es un supuesto, es lo que acabamos de hacer.
        El estado es 'activo' porque este camino no corre para bajas (lo corta `resolver_y_asignar`)."""
        precargado = (AsignacionPrecargada(True, empleado_empresa_id, "activo")
                      if empleado_empresa_id else None)
        try:
            self._asignaciones.asignar(
                UUID(proyecto_id),
                AsignacionCreate(empleado_id=UUID(empleado_id), rol=rol),
                UUID(empresa_id),
                precargado=precargado,
            )
        except AppError as exc:
            if exc.code != "ASIGNACION_DUPLICADA":
                raise  # otros errores los captura resolver_y_asignar (warning, sin romper la fila)
