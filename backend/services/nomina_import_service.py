"""
Confirmación del import de nómina de COSTOS (Flujo 2): persiste el lote ya revisado.

Existe porque el `confirmar` era el ÚNICO de los tres imports sin capa de service: iba
router → repo directo, con el armado de las filas y el conteo adentro del handler. Meter ahí el
evento de auditoría habría sumado más lógica de negocio a una capa que por convención no la
lleva, y habría dejado `routers/importacion_nomina.py` (70/80) al borde. El service saca líneas
del router en vez de agregárselas: el handler queda recibiendo, delegando y devolviendo, y los
tres imports quedan simétricos.

El PREVIEW de este mismo flujo vive en `nomina_csv_service.parse_nomina_csv` y no se movió: son
las dos mitades del flujo, pero ese archivo está en 120/150 y sumarle esto lo pasaba del límite.

AUDITORÍA: UN evento por lote, nunca fila por fila (regla del repo). El detalle de qué lleva y
qué NO lleva —y por qué— está en `_audit_payloads_import.payload_importacion_costos`.
"""
from typing import List, Optional

from repositories.nomina_import_repo import NominaImportRepo
from schemas.importacion import (
    FilaNominaPreview,
    ImportacionNominaConfirmarRequest,
    ImportacionNominaConfirmarResponse,
)
from services._audit_payloads_import import payload_importacion_costos
from services.audit_service import AuditService
from utils.logger import logger


def _periodos(filas: List[FilaNominaPreview]) -> List[str]:
    """Períodos "AAAA-MM" distintos del lote, ordenados y sin repetir.

    No hay UN período en el lote: cada fila trae el suyo. Lo normal es que un archivo de nómina
    sea de un mes —y entonces la lista tiene un elemento—, pero nada lo impide y el evento no
    puede inventar un período único que el archivo no afirma. Devolver SIEMPRE una lista (nunca
    un string cuando hay uno solo) evita que quien lee el log tenga que manejar dos formas.
    """
    return sorted({f"{f.anio:04d}-{f.mes:02d}" for f in filas})


class NominaImportService:
    def __init__(
        self, repo: Optional[NominaImportRepo] = None, audit: Optional[AuditService] = None,
    ) -> None:
        self._repo = repo or NominaImportRepo()
        self._audit = audit or AuditService()

    def confirmar(
        self, body: ImportacionNominaConfirmarRequest, usuario_id: Optional[str] = None,
    ) -> ImportacionNominaConfirmarResponse:
        """Persiste el lote de nómina (UPSERT por empleado/anio/mes) y audita el import.

        `empresa_id` sale del BODY, no del header: confirmar un import es una ACCIÓN y la
        empresa es un parámetro del formulario, no el selector del sidebar (Vista vs Acción).

        🔴 EL EVENTO SE EMITE SIEMPRE, también con lote vacío o parcial. Es el único registro de
        que alguien importó sueldos: las filas escritas no emiten evento propio (sería uno por
        fila, contra la regla), así que un import sin este evento es un import invisible. Mismo
        criterio que `nomina_empleados_service.importar`, donde está escrito largo.

        ⚠️ La RESPUESTA sigue devolviendo el desglose importados/actualizados derivado del
        `es_actualizacion` que mandó el cliente — es el contrato que consume la pantalla y no
        cambia acá. El EVENTO no lo repite, a propósito: ese flag no es verificable server-side
        (ver el payload). O sea que la pantalla dice más que el log, y el log dice solo lo que
        puede sostener.

        Args:
            body: empresa y filas ya revisadas en el preview.
            usuario_id: operador que confirma, para la trazabilidad del evento.

        Returns:
            Conteo de importados/actualizados. `errores` va vacío: el upsert es una sola query,
            o entra el lote o falla entero — no hay fallo por fila que reportar.
        """
        # 🔴 Los dos ids van con `str()`: son UUID en el schema y este dict se entrega TAL CUAL a
        # PostgREST (`batch_upsert_nomina` no lo vuelve a tocar), donde un objeto UUID no es
        # serializable. Acá no hay `model_dump(mode="json")` que lo cubra — el dict se arma a
        # mano —, así que la conversión tiene que ser explícita.
        empresa_id = str(body.empresa_id)
        filas = [
            {
                "empleado_id": str(f.empleado_id), "anio": f.anio, "mes": f.mes,
                "salario_bruto": f.salario_bruto,
                "cargas_sociales": max(0.0, f.salario_bruto - f.neto),
                "empresa_id": empresa_id,
            }
            for f in body.filas
        ]
        persistidas = self._repo.batch_upsert_nomina(filas)

        # `empresa_id` ya convertido: el payload lo declara `str`. `AuditService.registrar` haría
        # el `str()` igual, pero un UUID crudo acá dependería de esa cortesía de la capa de abajo
        # — y si fallara, el error se lo traga el audit y el evento desaparece sin rastro.
        self._audit.registrar(**payload_importacion_costos(
            empresa_id, _periodos(body.filas), len(body.filas), len(persistidas), usuario_id,
        ))

        importados = sum(1 for f in body.filas if not f.es_actualizacion)
        actualizados = sum(1 for f in body.filas if f.es_actualizacion)
        logger.info(
            "Importación nómina confirmada",
            extra={"importados": importados, "actualizados": actualizados, "errores": 0,
                   "filas_persistidas": len(persistidas)},
        )
        return ImportacionNominaConfirmarResponse(
            importados=importados, actualizados=actualizados, errores=[],
        )
