"""Dependencia FastAPI: parsea el alta de candidato por multipart (campos + CV opcional).

Mantiene el router fino: ensambla CandidatoCreate y lee los bytes del CV una vez.
Devuelve (data, cv_bytes, cv_filename, cv_content_type); el CV es opcional (None si no vino).
"""
from typing import Optional, Tuple

from fastapi import File, Form, UploadFile

from schemas.candidato import CandidatoCreate


async def candidato_form(
    nombre: str = Form(...), apellido: str = Form(...), email: str = Form(...),
    cargo_anterior: Optional[str] = Form(None), empresa_anterior: Optional[str] = Form(None),
    cv: Optional[UploadFile] = File(None),
) -> Tuple[CandidatoCreate, Optional[bytes], Optional[str], Optional[str]]:
    """Ensambla los campos del candidato y lee el CV opcional a bytes."""
    data = CandidatoCreate(
        nombre=nombre, apellido=apellido, email=email,
        cargo_anterior=cargo_anterior, empresa_anterior=empresa_anterior,
    )
    contenido = await cv.read() if cv else None
    return data, contenido, (cv.filename if cv else None), (cv.content_type if cv else None)
