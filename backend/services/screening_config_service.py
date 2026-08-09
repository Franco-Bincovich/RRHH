"""
El criterio configurable del clasificador de CVs (migración 100).
Flujo: router → service → repository → DB

🔑 La resolución es COALESCE(fila de mi empresa, fila global) y vive ACÁ, igual que en
`configuracion_service`: la fila es una sola y gana la de la empresa si existe.

## 🔴 LO QUE ESTE MÓDULO **NO** DEJA CONFIGURAR, Y POR QUÉ

Configurable: las tres definiciones y unas notas adicionales. Nada más.

NO configurable, y por diseño: la separación system/user, el sanitizado del CV, las tres
categorías, la validación de la salida, la declaración de que el CV son datos y nunca
instrucciones, y el sesgo **ante la duda, dudoso**. Todo eso es estructura fija en
`_clasificador_prompt.py` y los textos de acá se INSERTAN dentro, como dato.

El sesgo hacia `dudoso` es el que más tienta a exponer y el que más caro sale: los falsos
negativos de un filtro de CVs son invisibles por construcción —nadie se entera del buen
candidato que se descartó—, así que la primera empresa que quisiera "menos ruido" lo aflojaría
sin ver lo que pierde. Es un filtro de descarte, no una decisión: un humano revisa siempre.
"""
from typing import Optional
from uuid import UUID

from repositories.parametros_screening_repo import ParametrosScreeningRepo
from schemas.screening import ScreeningCriterioResponse, ScreeningCriterioUpdate
from utils.errors import AppError


class ScreeningConfigService:
    def __init__(self, repo: Optional[ParametrosScreeningRepo] = None) -> None:
        self._repo = repo or ParametrosScreeningRepo()

    def get_criterio(self, empresa_id: Optional[UUID]) -> ScreeningCriterioResponse:
        """
        Criterio vigente: el de la empresa si tiene fila propia, si no el global.

        `empresa_id=None` (vista consolidada) no es un error: devuelve el global, que es lo que
        rige para cualquier empresa que no haya configurado nada.
        """
        propia = self._repo.find(str(empresa_id)) if empresa_id else None
        if propia:
            return ScreeningCriterioResponse(**propia, es_propia=True)
        return ScreeningCriterioResponse(**self._global_o_error(), es_propia=False)

    def set_criterio(self, empresa_id: UUID,
                     data: ScreeningCriterioUpdate) -> ScreeningCriterioResponse:
        """
        Guarda el criterio de la empresa activa. Si venía heredando el global, este guardado CREA
        su fila propia y a partir de acá deja de seguirlo.

        `empresa_id` es obligatorio (el router usa require_empresa_id): en modo consolidado no
        hay a qué empresa escribirle, y elegir la global por descarte cambiaría el criterio de
        TODAS las empresas creyendo estar cambiando el de una.
        """
        guardada = self._repo.upsert(str(empresa_id), data.model_dump())
        campos = {k: guardada[k] for k in data.model_dump()}
        return ScreeningCriterioResponse(**campos, es_propia=True)

    def restaurar_defaults(self, empresa_id: UUID) -> ScreeningCriterioResponse:
        """
        Vuelve a heredar el criterio global: borra la fila propia de la empresa.

        No copia los textos globales a la fila de la empresa — ver `borrar_propia` en el repo:
        copiarlos dejaría `es_propia=True` sobre una foto congelada de los defaults de hoy, y la
        pantalla diría "criterio propio" sobre un texto que nadie escribió.
        """
        self._repo.borrar_propia(str(empresa_id))
        return self.get_criterio(empresa_id)

    def _global_o_error(self) -> dict:
        """
        La fila global la siembra la migración 100. Si falta, la base no está donde el código
        cree: se falla fuerte en vez de inventar defaults en Python, porque unos defaults
        silenciosos harían que la pantalla mostrara —y el clasificador usara— un criterio que NO
        es el que rige.
        """
        fila = self._repo.find(None)
        if not fila:
            raise AppError(
                "No hay criterio de screening global cargado. ¿Se corrió la migración 100?",
                "SCREENING_CONFIG_FALTANTE", 500,
            )
        return fila
