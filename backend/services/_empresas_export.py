"""
Proyección de columnas legibles para el export de empresas.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría el `id`).
Los headers del Excel son las keys de cada dict. No toca el motor de export.

🔴 ESTE ES EL ÚNICO EXPORT DEL REPO QUE HOY SE PUEDE VERIFICAR MIRANDO EL ARCHIVO: producción
tiene 2 empresas, así que alguien puede abrir el Excel y decir "esto está bien" o "esto está
mal". Los demás salen vacíos o con una fila. Por eso las columnas no son las cuatro de la
tabla de la pantalla (Nombre · CUIT · Email · Estado) sino la ficha completa de la empresa
—razón social, domicilio y teléfono incluidos—: es la planilla que alguien de RRHH usa para
un trámite, y que le falte el CUIT o la razón social la vuelve inútil justo cuando sirve.

Queda afuera `logo_url`: es la URL pública de una imagen. En una celda no se puede mirar y no
se puede usar, y alarga la fila lo suficiente como para tapar lo que sí importa.
"""
from typing import List

from schemas.empresa import EmpresaResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[EmpresaResponse]) -> List[dict]:
    """Proyecta las empresas a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": e.nombre,
            "Razón social": e.razon_social,
            "CUIT": e.cuit,
            "Dirección": e.direccion,
            "Teléfono": e.telefono,
            "Email": e.email,
            # "Activa"/"Inactiva" y no True/False: es el mismo texto que muestra el badge de la
            # pantalla, y un booleano crudo en Excel sale como VERDADERO/FALSO según el idioma
            # de quien lo abre.
            "Estado": "Activa" if e.activa else "Inactiva",
            "Alta": _fecha(e.created_at),
        }
        for e in items
    ]
