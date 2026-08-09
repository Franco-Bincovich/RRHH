"""Schemas propios del módulo de candidatos (los compartidos con vacantes viven en vacante.py)."""
from uuid import UUID

from pydantic import BaseModel


class AsignarVacanteRequest(BaseModel):
    """A qué búsqueda va un candidato que estaba huérfano."""
    vacante_id: UUID
