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
    # 🔴 OBLIGATORIO desde el 26/8/2026: lo escribe Capital Humano, ya no lo emite la secuencia
    # de la base. Sin default a propósito — una vacante sin código no puede recibir CVs, y un
    # `""` por defecto la crearía muda. La forma y la unicidad las valida
    # `services/_vacante_codigo.py` (y el CHECK + índice único de la mig 122 detrás).
    codigo: str
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
    # Se puede corregir: el caso típico es un typo en el código que ya se pegó en el aviso.
    # ⚠️ Cambiarlo NO mueve ningún candidato —cuelgan de `vacante_id`, no del código— pero deja
    # sin matchear los mails que lleguen con el código viejo. La pantalla lo avisa antes.
    codigo: Optional[str] = None
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
    # 🔴 LO ESCRIBE CAPITAL HUMANO (mig 122). Hasta el 26/8/2026 lo generaba el DEFAULT de la base
    # (`vacantes_codigo_seq`, mig 097) y este comentario decía que no se elegía ni se editaba.
    # El DEFAULT sigue puesto como RED —una fila que entre por afuera de la app nace con código
    # igual— pero el camino normal es el formulario. Lo que NO cambió es el modo de falla que
    # importa: dos vacantes con el mismo código rompen el matcher de CVs para siempre, y por eso
    # la unicidad la sostiene el índice único de la base, no un chequeo de la aplicación.
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


class AvisoPostulacionResponse(BaseModel):
    """Lo que RRHH copia para pegar en el aviso de LinkedIn. Ver `services/_vacante_aviso.py`.

    `casilla` y `texto` son Optional porque puede no haber casilla del sistema designada. En ese
    caso `codigo` sale igual —es de la vacante y no depende de ninguna integración— y la pantalla
    avisa qué falta configurar, en vez de ofrecer un texto con un agujero adentro."""
    codigo: str
    casilla: Optional[str] = None
    texto: Optional[str] = None


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


class VacanteListResponse(BaseModel):
    """Página del listado de vacantes. Contrato del molde de paginación."""
    items: list[VacanteResponse]
    # `total` es el del FILTRO sin paginar (`count="exact"` de la misma query), NO el largo de
    # `items`. Es lo que la barra necesita para saber cuántas páginas hay y lo que el export
    # chequea contra el tope: derivarlo de `items` diría 20 y el archivo saldría incompleto.
    total: int
    page: int = 1
    page_size: int = 0
    total_pages: int = 0
