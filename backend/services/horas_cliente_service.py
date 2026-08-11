"""
Vista interna "Horas por cliente" (solo RRHH).
Flujo: router → service → repository → DB

Es una VISTA: la empresa sale del header `X-Empresa-Id` (el selector del sidebar) y `None` es el
consolidado. Lo único que es ACCIÓN acá es la baja, y por eso su evento de auditoría se etiqueta
con la empresa de la ENTIDAD y no con la del header.

🔴 QUÉ SE PUEDE HACER Y QUÉ NO, DESDE ESTA PANTALLA
El mockup dice "ver detalle abre las cargas día por día, con editar o borrar cada una".
**Borrar está; editar NO, a propósito.** `HorasService` declara los registros INMUTABLES por
decisión escrita —tiene `delete` y no tiene `update`, con el motivo en su docstring— y agregar un
update no es sumar una feature: es revocar esa decisión. Lo que haría falta está enumerado en
`_QUE_FALTARIA_PARA_EDITAR`, abajo, para que la decisión se tome mirando el costo real y no de
memoria.

Los KPIs usan el patrón `_safe` del dashboard: si uno falla, los otros salen igual. Acá los
cuatro salen del MISMO recorrido, así que el `_safe` envuelve el bloque entero — un fallo deja
los KPIs en cero y la tabla igual se muestra, que es mejor que un 500 sobre una pantalla que ya
tenía los datos.
"""
from typing import Optional
from uuid import UUID

from repositories import _horas_vista_repo as vista_repo
from schemas.horas_cliente import DetalleEmpleadoResponse, HorasPorClienteResponse
from services._audit_payloads_horas import payload_baja_hora
from services._horas_cliente_agrupacion import agrupar
from services._horas_cliente_export import construir_filas_export
from services._limite_export import verificar_limite_export
from services.audit_service import AuditService
from services.export import Descarga, build_export
from services.reportes._common import periodo_str, rango_mes
from utils.errors import AppError
from utils.logger import logger

_NO_ENCONTRADA = ("Registro de horas no encontrado", "HORA_NOT_FOUND", 404)

# 🔴 LO QUE HARÍA FALTA PARA "EDITAR", si algún día se decide revocar la inmutabilidad. No es una
# lista de tareas: es el costo, para poder decidir con él a la vista.
#   1. Un `update` en el repo Y la revocación explícita del docstring de `HorasService`, que hoy
#      dice lo contrario. Dos fuentes que se contradigan es peor que no tener la feature.
#   2. Re-validar el TOPE DE 12 con la fila vieja EXCLUIDA de la suma del día: editar 4 h a 6 h
#      sobre un día con 12 tiene que comparar 12 - 4 + 6, no 12 + 6. El helper de hoy
#      (`verificar_tope`) no sabe restar nada.
#   3. Re-validar la VENTANA de 30 días, y decidir algo que hoy no está decidido: si RRHH puede
#      editar una carga que ya quedó fuera de la ventana del empleado. Probablemente sí, pero
#      es una regla nueva, no una consecuencia.
#   4. Un payload de auditoría de UPDATE con diff, que por la regla del repo tiene que excluir
#      los derivados de joins (`cliente_nombre`, `empleado_nombre`, `costo`) o registraría
#      cambios que nunca ocurrieron.
#   5. Decidir si se puede cambiar el `empleado_id` de una carga. Si sí, deja de ser una edición
#      y pasa a ser una reimputación entre personas, con lo que eso implica para el tope diario
#      de LAS DOS.
_QUE_FALTARIA_PARA_EDITAR = 5


def _safe(fn, default, seccion: str):
    """Ejecuta fn; si falla, loguea y devuelve default. Molde: `dashboard_service._safe`."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        logger.error("horas_cliente_seccion_fallo", extra={"seccion": seccion, "error": str(exc)})
        return default


class HorasClienteService:
    def __init__(self, repo=None, audit: Optional[AuditService] = None) -> None:
        self._repo = repo or vista_repo
        self._audit = audit or AuditService()

    def _filas(self, mes: int, anio: int):
        """Las filas del período, de TODAS las sociedades. FUENTE ÚNICA del listado y del export.

        Sin `empresa_id`: el total de un cliente no se recorta (L8). Ver `_horas_vista_repo`."""
        desde, hasta = rango_mes(mes, anio)
        return self._repo.find_por_periodo(desde, hasta)

    def get_vista(self, mes: int, anio: int) -> HorasPorClienteResponse:
        """KPIs + clientes colapsables del mes. Con el mes vacío devuelve ceros y [], no un error."""
        filas = self._filas(mes, anio)
        kpis, clientes = _safe(lambda: agrupar(filas),
                               ({"horas_totales": 0.0, "clientes_con_carga": 0,
                                 "empleados_que_cargaron": 0, "registros": 0}, []),
                               "agrupacion")
        return HorasPorClienteResponse(mes=mes, anio=anio, kpis=kpis, clientes=clientes)

    def get_detalle(self, empleado_id: UUID, mes: int, anio: int) -> DetalleEmpleadoResponse:
        """Las cargas día por día de un empleado. Trae el `id` de cada una: la pantalla lo
        necesita para poder borrar."""
        desde, hasta = rango_mes(mes, anio)
        items = self._repo.find_por_empleado(str(empleado_id), desde, hasta)
        return DetalleEmpleadoResponse(
            items=items, total_horas=round(sum(float(h.horas or 0) for h in items), 2))

    def exportar(self, mes: int, anio: int, formato: str = "excel") -> Descarga:
        """Export plano, una fila por carga, con los MISMOS filtros que el listado.

        Lleva columna "Empresa" por fila (`_horas_cliente_export`), así que el reparto por
        sociedad se puede reconstruir desde el archivo."""
        filas = self._filas(mes, anio)
        verificar_limite_export(len(filas))
        datos = {"Horas": construir_filas_export(filas)}
        return build_export(nombre=f"Horas por cliente — {periodo_str(mes, anio)}", datos=datos,
                            filename_base="horas-por-cliente", formato=formato)

    def eliminar(self, hora_id: UUID, usuario_id: Optional[str] = None) -> None:
        """Borra una carga. Es la única corrección que RRHH puede hacer desde acá.

        Lee el PRIOR antes de borrar: sin él no hay qué auditar.

        ⚠️ NO se delega en `HorasService.delete`, que valida por PROYECTO. Una carga del link
        público tiene `proyecto_id` NULL, así que ese camino le daría 404 a TODAS las filas que
        esta pantalla muestra.

        Sin recorte por empresa (L9): se borra por `id`, que es lo único que identifica la fila.
        """
        prior = self._repo.find_by_id(str(hora_id))
        if not prior:
            raise AppError(*_NO_ENCONTRADA)
        if not self._repo.delete(str(hora_id)):
            raise AppError(*_NO_ENCONTRADA)
        # La empresa del evento sale de la ENTIDAD, nunca del header. Ver el payload.
        self._audit.registrar(**payload_baja_hora(prior, usuario_id, str(prior.empresa_id)))
        logger.info("Carga de horas eliminada", extra={"hora_id": str(hora_id)})
