"""
Servicio de configuración de reglas de negocio (migración 085).
Flujo: router → service → repository → DB

🔑 LA RESOLUCIÓN ES COALESCE(fila de mi empresa, fila global), y vive ACÁ.

No está en la query porque son dos tablas distintas con dos criterios distintos: en
parametros_empresa la fila es una sola y gana la de la empresa si existe; en la escala son
VARIAS filas y la empresa que tiene aunque sea un tramo propio usa SOLO los suyos — nunca la
unión con la global, que mezclaría dos escalas y daría tramos que nadie configuró.

⚠️ ESTA SESIÓN SOLO GUARDA Y LEE LOS VALORES. El único que un cálculo consume es
base_dias_habiles (la tasa de ausentismo). La escala, el corte de antigüedad, el primer año,
el vencimiento y el PERÍODO VACACIONAL se persisten y se muestran, y nada los aplica todavía.
En particular NO existe validación que impida cargar una licencia fuera del período
vacacional: falta definir si bloquea o solo avisa. Ver el encabezado de la migración 085.
"""
from typing import Optional
from uuid import UUID

from repositories.configuracion_repo import ConfiguracionRepo
from schemas.configuracion import (
    ConfiguracionResponse, EscalaResponse, EscalaUpdate,
    ParametrosResponse, ParametrosUpdate, TramoEscala,
)
from utils.errors import AppError


class ConfiguracionService:
    def __init__(self, repo: Optional[ConfiguracionRepo] = None) -> None:
        self._repo = repo or ConfiguracionRepo()

    # ── Lectura ───────────────────────────────────────────────────────────────────────────

    def get_parametros(self, empresa_id: Optional[UUID]) -> ParametrosResponse:
        """
        Parámetros vigentes para la empresa: los suyos si tiene fila propia, si no los globales.

        `empresa_id=None` (vista consolidada) no es un error: devuelve directamente la global,
        que es exactamente lo que rige para cualquier empresa que no haya configurado nada.
        """
        propia = self._repo.find_parametros(str(empresa_id)) if empresa_id else None
        if propia:
            return ParametrosResponse(**propia, es_propia=True)
        return ParametrosResponse(**self._global_o_error(), es_propia=False)

    def get_escala(self, empresa_id: Optional[UUID]) -> EscalaResponse:
        """
        Escala vigente. Con al menos un tramo propio se usan SOLO los propios; si no, la global.

        No se unen las dos listas a propósito: una empresa que configuró "0→15 días" y hereda
        además el "0→14" global tendría dos tramos reclamando la misma antigüedad, y cuál gana
        dependería del orden de la query.
        """
        propios = self._repo.find_escala(str(empresa_id)) if empresa_id else []
        if propios:
            return EscalaResponse(tramos=[TramoEscala(**t) for t in propios], es_propia=True)
        globales = self._repo.find_escala(None)
        return EscalaResponse(tramos=[TramoEscala(**t) for t in globales], es_propia=False)

    def get_configuracion(self, empresa_id: Optional[UUID]) -> ConfiguracionResponse:
        """Todo lo que la pantalla necesita, en una sola ida."""
        return ConfiguracionResponse(
            parametros=self.get_parametros(empresa_id),
            escala=self.get_escala(empresa_id),
        )

    def _global_o_error(self) -> dict:
        """
        La fila global la siembra la migración 085. Si falta, la base no está donde el código
        cree: se falla fuerte en vez de inventar defaults en Python, porque unos defaults
        silenciosos harían que la pantalla mostrara valores que NO son los que rigen.
        """
        fila = self._repo.find_parametros(None)
        if not fila:
            raise AppError(
                "No hay configuración global cargada. ¿Se corrió la migración 085?",
                "CONFIG_GLOBAL_FALTANTE", 500,
            )
        return fila

    # ── Escritura ─────────────────────────────────────────────────────────────────────────

    def set_parametros(self, empresa_id: UUID, data: ParametrosUpdate) -> ParametrosResponse:
        """
        Guarda los parámetros de la empresa activa. Si venía heredando la global, este guardado
        CREA su fila propia y a partir de acá deja de seguirla.

        `empresa_id` es obligatorio (el router usa require_empresa_id): en modo consolidado no
        hay a qué empresa escribirle, y elegir la global por descarte cambiaría las reglas de
        TODAS las empresas creyendo estar cambiando las de una.
        """
        guardada = self._repo.upsert_parametros(str(empresa_id), data.model_dump())
        return ParametrosResponse(**{k: guardada[k] for k in data.model_dump()}, es_propia=True)

    def set_escala(self, empresa_id: UUID, data: EscalaUpdate) -> EscalaResponse:
        """
        Reemplaza la escala de la empresa activa.

        Una lista VACÍA es un reset explícito: la empresa deja de tener tramos propios y vuelve
        a heredar la global. Es la contracara de quitar tramos desde la UI hasta no dejar
        ninguno, y el `es_propia=False` de la respuesta lo hace visible en pantalla.

        Raises:
            AppError: ESCALA_TRAMOS_DUPLICADOS (422) si dos tramos comparten antigüedad. El
                índice único de la base también lo rechaza, pero como 500 genérico: acá el
                usuario se entera de cuál es el tramo repetido.
        """
        antiguedades = [t.antiguedad_anios for t in data.tramos]
        if len(antiguedades) != len(set(antiguedades)):
            raise AppError(
                "Hay dos tramos con la misma antigüedad. Cada antigüedad puede aparecer una sola vez.",
                "ESCALA_TRAMOS_DUPLICADOS", 422,
            )
        self._repo.replace_escala(str(empresa_id), [t.model_dump() for t in data.tramos])
        return self.get_escala(empresa_id)
