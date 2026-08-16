"""
Schemas del módulo de candidatos.

🔄 SE LLEVÓ LOS CINCO QUE VIVÍAN EN `vacante.py` (15/8/2026): `CandidatoCreate`,
`CandidatoResponse`, `CandidatoGrupoResponse`, `EtapaUpdate` y `CandidatosPaginaResponse`.
`vacante.py` llegó a 212/200 al sumarle el wrapper paginado, y el corte natural no era por
tamaño: un candidato no es una vacante. Estaban juntos porque el módulo nació así.

⚠️ `CandidatoResponse` y sus derivados se siguen importando desde MUCHOS lugares
(`vacante_service`, `candidato_service`, los routers, `_candidato_row`): la mudanza cambia el
módulo de origen, no los nombres.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AsignarVacanteRequest(BaseModel):
    """A qué búsqueda va un candidato que estaba huérfano."""
    vacante_id: UUID


class CandidatoCreate(BaseModel):
    nombre: str
    apellido: str
    email: str
    cargo_anterior: Optional[str] = None
    empresa_anterior: Optional[str] = None
    cv_url: Optional[str] = None


class CandidatoResponse(BaseModel):
    id: str
    vacante_id: Optional[str] = None  # NULL si su búsqueda fue borrada (migración 071)
    # Columna NOT NULL de `candidatos`, heredada de la vacante al crear. Viaja en el response
    # porque el evento de auditoría de la baja la necesita DEL REGISTRO, no del header: el
    # selector del sidebar es VISTA y en modo consolidado es None.
    empresa_id: Optional[str] = None
    nombre: str
    apellido: str
    email: str
    telefono: Optional[str] = None
    cargo_anterior: Optional[str] = None
    empresa_anterior: Optional[str] = None
    etapa_pipeline: str
    score_ia: Optional[float] = None
    busqueda_congelada: Optional[str] = None  # "Título — Área" congelado al borrar la vacante
    cv_storage_path: Optional[str] = None  # ruta en bucket privado 'cvs'; NULL si no adjuntó CV
    # POR QUÉ el CV no se pudo procesar (mig 099). Texto legible, no un flag: cada motivo pide
    # una acción distinta de RRHH. ⚠️ `cv_texto` NO se expone a propósito — es la entrada del
    # clasificador, puede pesar 20 KB por fila y engordaría todos los listados sin que nadie
    # lo mire en pantalla.
    screening_warning: Optional[str] = None
    # Filtro de descarte del screening (mig 100): relevante | dudoso | no_relevante, o None si
    # todavía no se clasificó. El MOTIVO viaja al lado y es lo que RRHH lee para decidir si
    # revisa igual: sin él la etiqueta sola invita a confiar en ella, que es justo lo contrario
    # de lo que este módulo es. 🔴 Si estas dos líneas faltaran, el `select("*")` traería las
    # columnas y el schema las descartaría EN SILENCIO — el bug que ya pasó tres veces acá.
    clasificacion_ia: Optional[str] = None
    clasificacion_motivo: Optional[str] = None
    # Quién puso la clasificación vigente: modelo | humano (mig 101). NULL = no hay clasificación.
    # Viaja al front porque la pantalla tiene que poder decir "esto lo corrigió alguien": sin eso,
    # el revisor siguiente no sabe si está mirando una salida del modelo o una decisión ya tomada.
    clasificacion_origen: Optional[str] = None
    created_at: datetime


class CandidatoGrupoResponse(CandidatoResponse):
    """Candidato + nombre del grupo resuelto (vivo o congelado) para la sección Candidatos."""

    grupo_nombre: Optional[str] = None  # título vivo de la vacante, o busqueda_congelada
    busqueda_activa: bool = False  # True si la vacante sigue viva; False si fue borrada


class EtapaUpdate(BaseModel):
    etapa: str


class CandidatosPaginaResponse(BaseModel):
    """Página del listado de candidatos + el conteo por búsqueda.

    🔴 `conteo_por_grupo` EXISTE PORQUE LA PANTALLA AGRUPA Y LA PÁGINA CORTA LOS GRUPOS.
    El listado se pagina PLANO (decisión de producto) y el front sigue agrupando por búsqueda
    dentro de la página. Si el encabezado de cada grupo contara los candidatos que tiene a la
    vista, diría "Analista SSR (4)" cuando la búsqueda tiene 40 y sólo 4 entraron en la página —
    un número plausible y falso, que es la clase de bug que esta tanda existe para no repetir.
    Acá viene el total REAL de cada grupo, calculado sobre el conjunto filtrado entero.

    Se calcula con UNA query de dos columnas, no con un count por búsqueda: el porqué está en
    `repositories/_candidato_listado_repo.py`.
    """
    items: list[CandidatoGrupoResponse]
    # Total de FILAS del filtro, sin paginar. No es la suma de `conteo_por_grupo` sólo por
    # casualidad: lo es siempre, y por eso no se deriva uno del otro (dos fuentes que se
    # calculan distinto pueden separarse; una derivada esconde el error de la otra).
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0
    # {nombre del grupo → cuántos candidatos tiene en TODO el filtro}. La clave es el mismo
    # `grupo_nombre` con el que el front agrupa, así que la pantalla no traduce nada.
    conteo_por_grupo: dict[str, int] = {}
