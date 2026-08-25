"""
Import de objetivos por Excel: preview → confirmar.

El PREVIEW vive en `objetivos_import_preview.py` (salió por límite de líneas, igual que las dos
mitades del Flujo 2). Molde: el Flujo 2 (nómina de COSTOS), el único import del repo con preview. La forma del
reporte de filas con problemas viene del Flujo 1 (nómina de empleados), que es el más maduro en
eso: cada fila cae en un grupo y **el lote no aborta por una fila**.

🔴 EL RESPONSABLE SE RESUELVE CONTRA `users`, NO CONTRA `empleados`. Este es el tablero de tareas
del equipo de RRHH, no de los 31 empleados — decisión de producto cerrada, y es la razón por la
que la migración de `responsable_id` a empleados se canceló. Una fila cuyo responsable no existe
o está inactivo **no se carga y se reporta**: nunca se carga con un responsable nulo, entre otras
cosas porque `objetivos.responsable_id` es NOT NULL y el insert fallaría igual, pero con un 500
en vez de un renglón en el reporte.

🔴 QUÉ DEL MODELO NUEVO SOPORTA: responsables múltiples SÍ, jerarquía NO (todo nace como raíz), y
un archivo con columna de padre se RECHAZA ENTERO en vez de ignorarla. El porqué de las dos
cosas está en `_objetivos_import_transforms`.

AUDITORÍA: UN evento por lote, en el confirmar. Ver `_audit_payloads_objetivos_import`.
"""
from typing import List, Optional
from uuid import UUID

from schemas.importacion_objetivos import (
    FilaObjetivoError, FilaObjetivoPreview, ImportacionObjetivosConfirmarRequest,
    ImportacionObjetivosConfirmarResponse, ImportacionObjetivosPreviewResponse,
)
from schemas.objetivo import ObjetivoCreate
from services._audit_payloads_objetivos_import import payload_importacion_objetivos
from services.audit_service import AuditService
from services.objetivos_import_preview import preview as _preview
from services.objetivo_service import ObjetivoService
from utils.errors import AppError
from utils.logger import logger


class ObjetivosImportService:
    def __init__(self, objetivos: Optional[ObjetivoService] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._objetivos = objetivos or ObjetivoService()
        self._audit = audit or AuditService()

    def preview(self, data: bytes) -> ImportacionObjetivosPreviewResponse:
        """Lee el Excel y clasifica cada fila. Ver services/objetivos_import_preview.preview."""
        return _preview(data)

    def confirmar(self, body: ImportacionObjetivosConfirmarRequest,
                  usuario_id: Optional[str] = None,
                  archivo: str = "objetivos.xlsx") -> ImportacionObjetivosConfirmarResponse:
        """Crea los objetivos del lote y emite UN evento de auditoría.

        🔴 VA POR `ObjetivoService.create`, no por el repo: así el import hereda TODAS las
        validaciones del alta manual —título, prioridad, y sobre todo que el responsable siga
        siendo un user activo—. El preview resolvió para MOSTRAR; el body viajó por la red y el
        cliente lo pudo alterar, así que la autorización se rehace acá. Es el mismo criterio por
        el que `payload_importacion_costos` no confía en el `es_actualizacion` del body.

        🔴 EL EVENTO SE EMITE SIEMPRE, también con lote vacío o con todas las filas fallidas: es
        el ÚNICO registro de que alguien importó objetivos (el alta no emite evento propio, sería
        uno por fila). Mismo criterio que los otros dos imports.

        🔴 LA FILA DUPLICADA SE REPORTA CON UN MENSAJE LEGIBLE, Y ESO SALE DE IR POR `create`.
        Desde la 111 el índice único hace rebotar el segundo INSERT, así que resubir la misma
        planilla ya no duplicaba — pero el motivo que veía RRHH era el texto crudo de Postgres
        (`duplicate key value violates unique constraint "ux_objetivo_responsable_titulo"`),
        porque la `APIError` caía en el `except Exception` de abajo. Ahora `ObjetivoService.create`
        la traduce con `duplicado_a_409` ANTES de que llegue acá, así que entra por la rama de
        `AppError` y el `motivo` es el que nombra las tres salidas (título, periodicidad, vista).
        No hay una línea especial para el duplicado en este archivo, y no la tiene que haber:
        **es la misma traducción que ve el alta manual**, heredada por pasar por el service.
        ⚠️ El `except Exception` de abajo sigue ahí y sigue volcando `str(exc)`. Es correcto —un
        error inesperado tiene que dejar rastro para quien administra el import— pero significa
        que cualquier OTRO fallo de base sí muestra texto crudo. Sabido y acotado a ese caso.
        """
        creados: List[str] = []
        errores: List[FilaObjetivoError] = []
        for f in body.filas:
            try:
                row = self._objetivos.create(self._a_create(f, body.empresa_id), usuario_id or "system")
                creados.append(row.id)
            except AppError as exc:
                errores.append(FilaObjetivoError(fila=f.fila, identificador=f.titulo,
                                                 motivo=exc.message))
            except Exception as exc:  # noqa: BLE001 — el lote no aborta por una fila
                errores.append(FilaObjetivoError(fila=f.fila, identificador=f.titulo,
                                                 motivo=str(exc)))

        # `str()` explícito: el payload declara `empresa_id: str`. `AuditService.registrar` lo
        # convertiría igual, pero apoyarse en eso es frágil acá — si fallara, el audit se traga
        # la excepción por diseño y el evento del lote desaparece sin dejar rastro.
        self._audit.registrar(**payload_importacion_objetivos(
            str(body.empresa_id), archivo, len(body.filas), len(creados), len(errores),
            usuario_id, creados))
        logger.info("Import objetivos confirmado", extra={
            "archivo": archivo, "enviadas": len(body.filas), "creados": len(creados),
            "errores": len(errores)})
        return ImportacionObjetivosConfirmarResponse(importados=len(creados), errores=errores)

    @staticmethod
    def _a_create(f: FilaObjetivoPreview, empresa_id: UUID) -> ObjetivoCreate:
        """Fila del preview → payload de alta. `parent_id` NO se setea: ver el encabezado.

        🔴 ACÁ LA CONVERSIÓN SE SACÓ, NO SE AGREGÓ, y es al revés de lo que uno espera al tipar
        ids: estas dos líneas hacían `UUID(empresa_id)` y `UUID(f.responsable_id)` sobre strings.
        Ahora los dos campos YA son UUID en el schema, y `UUID(objeto_uuid)` no es idempotente:
        levanta TypeError. O sea que tipar el schema sin tocar esto rompería el confirmar entero.
        Es el mismo rastreo que en el otro import descubrió que faltaba un `str()`; el resultado
        fue el opuesto, y por eso hay que SEGUIR el camino en vez de aplicar una regla fija.

        ⚠️ `responsables_ids` sigue siendo `List[str]` en el schema, así que su `UUID(u)` se
        queda. No es inconsistencia por descuido: ese campo no entró en el inventario de esta
        sesión (ver el comentario en el schema).

        🔴 LOS TRES DE LA 119 SE PASAN EXPLÍCITOS, aunque omitirlos daría CASI lo mismo. Casi:
        `ObjetivoCreate.tipo` tiene el mismo default (`operativo`), así que para un archivo sin la
        columna el resultado es idéntico — pero para uno CON la columna, omitirlos acá haría que
        el `Tipo` que el usuario escribió en su planilla se descartara en silencio y todo naciera
        operativo. El preview lo mostraría bien y la base guardaría otra cosa: el peor modo de
        falla de un import, porque la pantalla confirma lo que no pasó.
        `list(...)` en las áreas para no compartir la lista del schema con el payload de alta.
        """
        return ObjetivoCreate(
            empresa_id=empresa_id, responsable_id=f.responsable_id,
            titulo=f.titulo, descripcion=f.descripcion, prioridad=f.prioridad,
            fecha_entrega=f.fecha_entrega,  # type: ignore[arg-type]
            responsables=[UUID(u) for u in f.responsables_ids],
            tipo=f.tipo, periodicidad=f.periodicidad,
            areas_involucradas=list(f.areas_involucradas),
        )
