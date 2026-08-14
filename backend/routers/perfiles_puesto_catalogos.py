"""
Router de catálogos de perfiles de puesto — labels, ayudas y vocabularios del formulario.

Separado de `perfiles_puesto.py` para no superar su límite de 80 líneas, y el corte no es
arbitrario: es el mismo que ya existe entre `empleados.py` y `empleados_catalogos.py`. Comparte
el prefijo `/api/perfiles-puesto` y **se registra ANTES** que el router del CRUD, para que la
ruta estática `/campos` matchee antes que el `/{id}` de allá. Si se registrara después, FastAPI
resuelve por orden de declaración y `/campos` entraría como el path param `id: UUID` → 422.
"""
from fastapi import APIRouter, Depends

from schemas._perfil_puesto_campos import (
    CAMPOS, MODALIDADES, NIVELES, NOTA_REQUISITOS, TIPOS_CONTRATO,
)
from utils.permisos import Accion, Seccion, require_permission

router = APIRouter()
SECCION = Seccion.PERFILES_PUESTO


@router.get("/campos", dependencies=[Depends(require_permission(SECCION, Accion.READ))])
async def campos_perfil() -> dict:
    """Labels, textos de ayuda y vocabularios del formulario, para que el front no los duplique.

    Existe por el mismo motivo que `GET /api/empleados/catalogos/provincias`: los tres
    vocabularios cerrados son TAMBIÉN los `Literal` con los que valida
    `schemas/perfil_puesto.py`, así que una copia en el front que derive ofrecería en un select
    un valor que el backend rechaza con 422.

    🔴 `nota_requisitos` NO es decorativa. Sin ella el formulario deja que el bloque "Requisitos"
    del aviso real se pegue entero en un solo campo y los otros tres queden vacíos, que es el
    modo de falla que este módulo tiene documentado. Va ARRIBA del bloque, no en un tooltip: un
    tooltip se lee después de haber escrito. Ver `schemas/_perfil_puesto_campos`.

    Returns:
        `campos` en el ORDEN en que se llenan, `nota_requisitos`, y los tres vocabularios
        cerrados con su etiqueta legible.
    """
    return {"campos": CAMPOS, "nota_requisitos": NOTA_REQUISITOS,
            "modalidades": MODALIDADES, "tipos_contrato": TIPOS_CONTRATO, "niveles": NIVELES}
