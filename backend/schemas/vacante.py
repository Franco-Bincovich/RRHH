"""
Schemas Pydantic para el módulo de vacantes y candidatos.
VacanteCreate → VacanteUpdate → VacanteResponse
CandidatoCreate → CandidatoResponse
"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class VacanteCreate(BaseModel):
    empresa_id: UUID  # empresa de la vacante — viaja en el body, no en el header
    titulo: str
    area_id: UUID
    descripcion: Optional[str] = None
    requisitos: Optional[str] = None  # texto libre (JSONB→TEXT, migración 070)
    tipo_contrato: str  # efectivo | plazo_fijo | contratado | pasantia
    # Campos de publicación (todos opcionales — la vacante puede crearse sin ellos).
    copy_publicacion: Optional[str] = None  # texto del post para redes (≠ descripcion interna)
    hashtags: Optional[str] = None  # texto libre, ej. "#BusquedaLaboral #MarDelPlata"
    email_contacto: Optional[str] = None  # email donde reciben CVs (columna existente, 034)
    ubicacion: Optional[str] = None  # ej. "Mar del Plata"
    modalidad: Optional[str] = None  # enum existente: presencial | remoto | hibrido (CHECK en DB)
    jornada: Optional[str] = None  # texto libre, ej. "Part time 6hs", "Full time"
    # Información del puesto (texto libre, insumo para el matching de CVs con IA).
    # Se cargan desde la sección del detalle vía update; en Create van opcionales.
    funciones: Optional[str] = None
    formacion: Optional[str] = None
    experiencia: Optional[str] = None
    conocimientos_tecnicos: Optional[str] = None


class VacanteUpdate(BaseModel):
    titulo: Optional[str] = None
    area_id: Optional[UUID] = None
    descripcion: Optional[str] = None
    requisitos: Optional[str] = None
    tipo_contrato: Optional[str] = None
    estado: Optional[str] = None
    copy_publicacion: Optional[str] = None
    hashtags: Optional[str] = None
    email_contacto: Optional[str] = None
    ubicacion: Optional[str] = None
    modalidad: Optional[str] = None  # presencial | remoto | hibrido (CHECK en DB)
    jornada: Optional[str] = None
    funciones: Optional[str] = None
    formacion: Optional[str] = None
    experiencia: Optional[str] = None
    conocimientos_tecnicos: Optional[str] = None


class VacanteResponse(BaseModel):
    id: str
    # 🔴 NO ESTÁ EN VacanteCreate NI EN VacanteUpdate, Y ES A PROPÓSITO: lo genera el DEFAULT de
    # la base (secuencia `vacantes_codigo_seq`, migración 097). RRHH no lo elige ni lo edita, y
    # el backend tampoco lo calcula — si lo hiciera, dos altas simultáneas podrían emitir el
    # mismo, que es el único modo de falla que rompe el matcher de CVs para siempre.
    # Es NOT NULL en la base, así que acá va sin default: una vacante sin código sería una que
    # no puede recibir postulaciones, y prefiero que eso explote al mapear y no en silencio.
    codigo: str
    empresa_id: Optional[str] = None
    empresa_nombre: Optional[str] = None
    titulo: str
    area_id: str
    area_nombre: Optional[str] = None
    descripcion: Optional[str] = None
    requisitos: Optional[str] = None
    tipo_contrato: Optional[str] = None
    estado: str
    fecha_apertura: Optional[date] = None
    created_at: datetime
    linkedin_post_id: Optional[str] = None
    linkedin_url: Optional[str] = None
    email_contacto: Optional[str] = None
    copy_publicacion: Optional[str] = None
    hashtags: Optional[str] = None
    ubicacion: Optional[str] = None
    modalidad: Optional[str] = None
    jornada: Optional[str] = None
    funciones: Optional[str] = None
    formacion: Optional[str] = None
    experiencia: Optional[str] = None
    conocimientos_tecnicos: Optional[str] = None


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


class AvisoPostulacionResponse(BaseModel):
    """Lo que RRHH copia para pegar en el aviso de LinkedIn. Ver `services/_vacante_aviso.py`.

    `casilla` y `texto` son Optional porque puede no haber casilla del sistema designada. En ese
    caso `codigo` sale igual —es de la vacante y no depende de ninguna integración— y la pantalla
    avisa qué falta configurar, en vez de ofrecer un texto con un agujero adentro."""
    codigo: str
    casilla: Optional[str] = None
    texto: Optional[str] = None


class EtapaUpdate(BaseModel):
    etapa: str


class PublicarLinkedinRequest(BaseModel):
    email_contacto: str


class PublicarLinkedinResponse(BaseModel):
    post_id: str
    url: str
    publicado_en: datetime


class EmailCandidatoResponse(BaseModel):
    email_id: str
    remitente: str
    asunto: str
    fecha: str
    cuerpo_preview: str


class CandidatoDesdeEmailRequest(BaseModel):
    email_id: str
