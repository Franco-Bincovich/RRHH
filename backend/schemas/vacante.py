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
    created_at: datetime


class CandidatoGrupoResponse(CandidatoResponse):
    """Candidato + nombre del grupo resuelto (vivo o congelado) para la sección Candidatos."""

    grupo_nombre: Optional[str] = None  # título vivo de la vacante, o busqueda_congelada
    busqueda_activa: bool = False  # True si la vacante sigue viva; False si fue borrada


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
