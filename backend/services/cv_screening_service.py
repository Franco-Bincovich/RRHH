"""
"Clasificar los CVs pendientes de esta vacante": la corrida completa. Fase 3 de 3 del screening.

    candidatos sin clasificar → por cada uno: prompt → Claude Haiku → validar → persistir

## 🔴 ES UN FILTRO DE DESCARTE, NO UNA DECISIÓN

No rankea, no puntúa, no elige. Un humano revisa siempre, incluido lo que quede en
`no_relevante`. La regla entera y el sesgo hacia `dudoso` viven en `_clasificador_prompt.py`.

## 🔴 NO CORRE EN LA INGESTA — CORRIDA APARTE, CON PRESUPUESTO PROPIO

`cv_ingesta_service` ya tiene 240 s para leer la casilla, bajar adjuntos y subirlos a Storage.
Sumarle N llamadas al modelo la cortaría: son 2-4 s por CV, así que un lote de 20 la pasa del
techo de `vercel.json` **sin reporte y sin decir cuál mitad quedó hecha**. Son dos botones.

El resultado NO es binario: `clasificados`, `sin_texto`, `errores` y `sin_procesar` son cuatro
números distintos y ninguno se deduce de los otros. Ver `ScreeningLoteResponse`.

## 🔴 CONTROL DE COSTOS: TOPE POR CORRIDA, NO EL `check_usage_limit` DE §6.2

`docs/SEGURIDAD-PENTEST.md` §6.2 propone un contador diario por usuario. **Acá no corresponde, y
el motivo no es que sea caro de implementar** (no existe: su `usage_repo` tampoco existe en el
repo). Su modelo de amenaza es la generación libre y repetible por el usuario —un chat, donde
apretar enviar N veces cuesta N—. Este endpoint no es eso:

  · **Está gateado a `Seccion.VACANTES + WRITE`** (hoy solo `admin_rrhh`), no es superficie
    pública ni conversacional.
  · **Es idempotente por construcción**: `find_para_clasificar` pide `clasificacion_ia IS NULL`,
    así que volver a apretar el botón sobre una vacante ya clasificada cuesta CERO llamadas. El
    abuso por repetición —justo lo que el contador diario defiende— ya está cerrado.
  · Lo que sí queda abierto es **una sola corrida sobre una vacante con muchísimos pendientes**.

El control proporcionado a ESE riesgo es un tope por corrida, no un cupo diario: mismo criterio
y mismo molde que `LIMITE_FILAS_EXPORT`. Va acompañado de los topes de entrada y salida que ya
existen (20.000 caracteres de CV en `_cv_texto`, 300 tokens de respuesta en `_cv_clasificador`),
que son los que acotan el costo de CADA llamada.

⚠️ **El tope se AVISA**: si hay más pendientes que el tope, la respuesta trae
`tope_alcanzado=True` y `sin_procesar` con el resto. Un tope silencioso se leería como "ya está
todo clasificado" — la regla de "no silent caps" del repo.
"""
from typing import List, Optional
from uuid import UUID, uuid4

from repositories.candidato_screening_repo import CandidatoScreeningRepo
from repositories.vacante_repo import VacanteRepo
from schemas.screening import CandidatoClasificado, ScreeningLoteResponse
from services._busqueda_prompt import bloque_busqueda
from services._clasificador_prompt import _limpio
from services._presupuesto import Presupuesto
from services._screening_candidato import clasificar_uno
from services.audit_service import AuditService
from services.screening_config_service import ScreeningConfigService
from utils.errors import AppError
from utils.logger import logger

# Por debajo del `maxDuration: 300` de vercel.json, con margen para que la respuesta salga.
# No es settings: subirlo exige revisar el techo de la plataforma. Igual que LIMITE_FILAS_EXPORT.
PRESUPUESTO_SEGUNDOS = 240.0

# Techo de llamadas al modelo por corrida. Ver el encabezado: es el control de costos que
# corresponde acá. Constante de módulo y NO variable de entorno — subirlo es una decisión.
TOPE_POR_CORRIDA = 200


class CvScreeningService:
    def __init__(self, vacante_repo=None, screening_repo=None, config=None, audit=None,
                 cliente=None) -> None:
        self._vacantes = vacante_repo or VacanteRepo()
        self._repo = screening_repo or CandidatoScreeningRepo()
        self._config = config or ScreeningConfigService()
        self._audit = audit or AuditService()
        self._cliente = cliente

    def clasificar_pendientes(self, vacante_id: str, empresa_id: Optional[UUID],
                              usuario_id: Optional[str] = None,
                              presupuesto: Optional[float] = None) -> ScreeningLoteResponse:
        """Clasifica los candidatos de la vacante que todavía no tienen clasificación.

        🔴 Barrera de empresa ANTES que cualquier otro chequeo: una vacante de otra empresa da
        404, el mismo que una inexistente. Si el orden se invirtiera, un "no hay pendientes"
        sobre un id ajeno confirmaría que la vacante existe.

        Raises:
            AppError: VACANTE_NOT_FOUND (404) si no existe o es de otra empresa.
        """
        vacante = self._vacantes.find_by_id(vacante_id, empresa_id)
        if not vacante:
            raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)

        # 🔴 Vista vs Acción: la empresa con la que se escribe y se audita sale de la VACANTE,
        # no del header. En modo consolidado el header es None y auditar con él dejaría el evento
        # fuera del filtro por empresa de /auditoria.
        empresa = str(vacante.empresa_id) if vacante.empresa_id else None

        # 🔴 Una búsqueda con solo título se SALTEA entera en vez de clasificarse igual: el
        # porqué, y por qué el chequeo es por vacante y no por candidato, está en el encabezado
        # de `_busqueda_prompt`. 🚨 Va DESPUÉS de la barrera de empresa, nunca antes: un 422
        # sobre una vacante ajena confirmaría que existe.
        busqueda = bloque_busqueda(vacante, _limpio)
        if busqueda.sin_contenido:
            raise AppError(
                "La búsqueda no tiene contenido cargado: completá al menos uno de Funciones, "
                "Requisitos, Formación, Experiencia o Conocimientos técnicos antes de "
                "clasificar. Con solo el título el sistema no tiene contra qué comparar los CVs.",
                "VACANTE_SIN_CONTENIDO", 422)
        if busqueda.truncado:
            logger.warning("La búsqueda excede el tope del prompt y se truncó",
                           extra={"vacante_id": vacante_id})

        criterio = self._config.get_criterio(vacante.empresa_id)

        pendientes = self._repo.find_para_clasificar(vacante_id, empresa)
        tope_alcanzado = len(pendientes) > TOPE_POR_CORRIDA
        tanda, excedente = pendientes[:TOPE_POR_CORRIDA], max(0, len(pendientes) - TOPE_POR_CORRIDA)

        reloj = Presupuesto(PRESUPUESTO_SEGUNDOS if presupuesto is None else presupuesto)
        detalle = [clasificar_uno(fila, vacante, criterio, empresa, repo=self._repo,
                                  cliente=self._cliente) for fila in reloj.con_margen(tanda)]
        return self._resumen(detalle, reloj, excedente, tope_alcanzado, vacante_id, empresa,
                             usuario_id, busqueda.truncado)

    def _resumen(self, detalle: List[CandidatoClasificado], reloj: Presupuesto, excedente: int,
                 tope: bool, vacante_id: str, empresa: Optional[str],
                 usuario_id: Optional[str], busqueda_truncada: bool) -> ScreeningLoteResponse:
        clasificados = sum(1 for d in detalle if d.clasificacion)
        errores = sum(1 for d in detalle if d.error)
        respuesta = ScreeningLoteResponse(
            clasificados=clasificados, errores=errores,
            sin_texto=len(detalle) - clasificados - errores,
            # Los cortados por presupuesto MÁS los que no entraron en el tope. Los dos son
            # reintentables: el botón vuelve a tomarlos porque siguen en NULL.
            sin_procesar=reloj.sin_procesar + excedente,
            parcial=reloj.parcial, tope_alcanzado=tope, segundos=reloj.transcurridos(),
            busqueda_truncada=busqueda_truncada, detalle=detalle)
        # UN evento por lote, nunca uno por CV: una corrida es UNA acción de RRHH. Regla propia
        # del repo. `registro_id` es un uuid4 de EVENTO — la corrida no persiste fila con id.
        self._audit.registrar(
            usuario_id=usuario_id, entidad="candidato", registro_id=str(uuid4()),
            accion="UPDATE", evento="screening_cv", empresa_id=empresa, datos_anteriores=None,
            datos_nuevos={"vacante_id": vacante_id, "clasificados": clasificados,
                          "sin_texto": respuesta.sin_texto, "errores": errores,
                          "sin_procesar": respuesta.sin_procesar, "parcial": reloj.parcial,
                          "tope_alcanzado": tope})
        logger.info("Screening de CVs terminado",
                    extra={"vacante_id": vacante_id, "clasificados": clasificados,
                           "errores": errores})
        return respuesta
