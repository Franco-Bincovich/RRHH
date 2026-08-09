"""
La corrección manual de una clasificación. Flujo: router → service → repository.

## 🔴 POR QUÉ ESTE MÓDULO EXISTE

El clasificador se presenta —en su docstring, en la migración 100 y en la pantalla— como un
FILTRO DE DESCARTE en el que "un humano revisa siempre, incluido lo que el agente marque
no_relevante". Hasta esta tanda el humano podía **mirar y no corregir**: el único write de
`clasificacion_ia` era el clasificador, y `find_para_clasificar` pide `clasificacion_ia IS NULL`,
así que ni siquiera volver a apretar el botón cambiaba un veredicto equivocado. La promesa estaba
escrita en tres lugares y no se cumplía en ninguno.

## 🔴 LA CORRECCIÓN GANA, Y GANA PARA SIEMPRE

Una vez corregida, la fila tiene `clasificacion_ia` con valor, así que **`find_para_clasificar` ya
no la toma**: ninguna corrida posterior la pisa. Eso NO es un efecto lateral afortunado del filtro
`IS NULL` — es la garantía que hace que corregir valga la pena, y por eso hay un test que la fija.
Si algún día ese filtro cambia, el test avisa antes de que el modelo empiece a sobrescribir
decisiones humanas en silencio.

## 🔴 DOS REGISTROS DE QUE FUE UN HUMANO, Y NINGUNO SOBRA

  · **`clasificacion_origen = 'humano'`**, en el mismo UPDATE que la clasificación. Es lo que
    permite preguntar "¿cuántos de los no_relevante los puso el modelo?" con un filtro sobre
    `candidatos`, sin tocar el log.
  · **Un evento `correccion_clasificacion`**, INDIVIDUAL (no por lote como el resto del módulo:
    esto es una acción humana sobre un dato sensible, y su unidad natural es el candidato). Lleva
    en `datos_anteriores` **el veredicto que el modelo había puesto** — que la corrección PISA y
    que la columna sola no conserva. Es el único lugar donde queda el par (dijo el modelo, dijo
    el humano), que es lo que se necesita para medir en qué dirección se equivoca el filtro.

El porqué de tener los dos está escrito entero en el encabezado de la migración 101.
"""
from typing import Optional
from uuid import UUID

from repositories.candidato_repo import CandidatoRepo
from repositories.candidato_screening_repo import CandidatoScreeningRepo
from schemas.screening import ClasificacionUpdate
from schemas.vacante import CandidatoResponse
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger


class ScreeningCorreccionService:
    def __init__(self, candidato_repo=None, screening_repo=None, audit=None) -> None:
        self._candidatos = candidato_repo or CandidatoRepo()
        self._repo = screening_repo or CandidatoScreeningRepo()
        self._audit = audit or AuditService()

    def corregir(self, candidato_id: str, data: ClasificacionUpdate,
                 empresa_id: Optional[UUID] = None,
                 usuario_id: Optional[str] = None) -> CandidatoResponse:
        """Fija a mano la clasificación de un candidato y la marca como humana.

        🔴 La barrera de empresa va PRIMERO y sale por el 404 canónico: un candidato de otra
        empresa responde igual que uno inexistente. Cualquier otro código —o un 403— confirmaría
        que el recurso ajeno existe.

        Raises:
            AppError: CANDIDATO_NOT_FOUND (404) si no existe o es de otra empresa.
        """
        previo = self._candidatos.find_by_id(candidato_id, empresa_id)
        if not previo:
            raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)

        # 🔴 Vista vs Acción: la empresa con la que se escribe y se audita sale del CANDIDATO,
        # no del header. En modo consolidado el header es None y el candidato sí tiene empresa.
        empresa = previo.empresa_id
        self._repo.set_correccion(candidato_id, data.clasificacion, data.motivo, empresa)

        self._audit.registrar(
            usuario_id=usuario_id, entidad="candidato", registro_id=candidato_id,
            accion="UPDATE", evento="correccion_clasificacion", empresa_id=empresa,
            # Acá vive el veredicto del modelo, que el UPDATE de arriba acaba de pisar. Sin
            # esto, medir "en qué se equivoca el filtro" sería imposible: la fila ya no lo tiene.
            datos_anteriores={"clasificacion_ia": previo.clasificacion_ia,
                              "clasificacion_motivo": previo.clasificacion_motivo,
                              "clasificacion_origen": previo.clasificacion_origen},
            datos_nuevos={"clasificacion_ia": data.clasificacion,
                          "clasificacion_motivo": data.motivo,
                          "clasificacion_origen": "humano"})
        logger.info("Clasificación corregida a mano",
                    extra={"candidato_id": candidato_id, "de": previo.clasificacion_ia,
                           "a": data.clasificacion})

        corregido = self._candidatos.find_by_id(candidato_id, empresa_id)
        if not corregido:  # pragma: no cover — la fila existía dos líneas arriba
            raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
        return corregido
