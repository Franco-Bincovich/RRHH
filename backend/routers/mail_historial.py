"""
Router del historial de mails enviados.

🔴 ARCHIVO PROPIO Y NO UN ENDPOINT MÁS EN `routers/plantillas.py`: aquel está en 77/80 líneas y
sumarle esto lo pasaba del límite. La alternativa era partir plantillas, que no tiene nada que
ver con esta tanda. El prefijo es `/api/mails` (montado en main.py), no `/api/plantillas/...`:
el historial es de MAILS, y una plantilla puede haberse borrado sin que sus envíos desaparezcan.

🔒 Gate: `Seccion.CONFIGURACION`, el MISMO que plantillas y envío. La sección de permisos no
cambió al mudar la pantalla a /comunicacion — crear una `Seccion` nueva habría tocado el espejo
manual `permisos.py` ↔ `permisos.ts` para obtener exactamente el mismo resultado (admin escribe,
gerencia lee, mandos_medios no entra), porque `puede()` es genérica y no distingue secciones.

⚠️ Solo READ, y no existe export: `mail_enviado` guarda datos personales y el cuerpo entero de
cada mail. El porqué está en `services/mail_historial_service.py`.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from schemas.plantillas import MailHistorialResponse
from services.mail_historial_service import LIMITE_DEFAULT, MailHistorialService
from utils.empresa import get_empresa_id
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.CONFIGURACION

_READ = Depends(require_permission(SECCION, Accion.READ))


@router.get("", response_model=MailHistorialResponse, dependencies=[_READ])
async def listar(request: Request,
                 estado: Optional[str] = Query(None),
                 fecha_desde: Optional[str] = Query(None),
                 fecha_hasta: Optional[str] = Query(None),
                 limite: int = Query(LIMITE_DEFAULT, ge=1, le=200)) -> MailHistorialResponse:
    """Últimos mails enviados, del más reciente al más viejo.

    `get_empresa_id` (Optional) y no `require_empresa_id`: esto es una VISTA, y en consolidado
    la respuesta correcta es "los de todas las empresas". Es el opuesto del envío, que es una
    ACCIÓN y exige empresa concreta — mirar = el sidebar manda, hacer = el parámetro manda.
    """
    return MailHistorialService().listar(
        empresa_id=get_empresa_id(request), estado=estado,
        desde=fecha_desde, hasta=fecha_hasta, limite=limite)
