"""
Proyección de columnas legibles para el export de offboardings activos.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`empleado_id` y `empresa_id`). Los headers del Excel son las keys de cada dict.

🔴 `activos` Y `accesos` SE CUENTAN, NO SE VUELCAN. Las dos son listas de objetos anidados y el
motor de export renderiza escalares: volcarlas dejaría el `repr` de Python dentro de una celda.
Lo que sirve en una planilla —y lo que la pantalla muestra como barra de progreso— es cuántos
de cuántos se devolvieron: "3 de 7". Por eso van tres columnas (devueltos, total y el % que ya
viene calculado) en vez de una lista ilegible.

Se conservan las tres y ninguna reemplaza a las otras: "0 de 0" y "0 de 7" dan los dos 0% de
progreso y significan cosas distintas —uno es un proceso sin activos asignados y el otro es un
proceso donde no se devolvió nada—. Con el porcentaje solo, no se distinguen.

⚠️ `notas_entrevista` queda AFUERA a propósito: es texto libre que escribe RRHH sobre por qué
se fue una persona. Es exactamente el campo que no se quiere en un archivo que se manda por
mail; el flag de si la entrevista se hizo sí sale, porque eso es seguimiento del proceso.
"""
from typing import List

from schemas.offboarding import OffboardingResponse

_MOTIVO_LABEL = {
    "renuncia": "Renuncia",
    "despido": "Desvinculación",
    "acuerdo_mutuo": "Acuerdo mutuo",
    "fin_contrato": "Fin de contrato",
    "jubilacion": "Jubilación",
    "fallecimiento": "Fallecimiento",
    "otro": "Otro motivo",
}


def _motivo(valor) -> str:
    """Traduce el motivo al texto de la pantalla (MOTIVO_LABEL del front). Cae al valor crudo
    si aparece uno nuevo: mejor un archivo que dice `motivo_futuro` que uno que dice ''."""
    return _MOTIVO_LABEL.get(valor, valor or "")


def _fecha(v) -> str:
    """`fecha_inicio` llega como str ISO desde el repo, no como date: se corta el día.
    '' si viene vacía — nunca la cadena "None"."""
    if not v:
        return ""
    partes = str(v)[:10].split("-")
    return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else str(v)


def construir_filas_export(items: List[OffboardingResponse]) -> List[dict]:
    """Proyecta los offboardings a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Empresa": o.empresa_nombre,
            "Colaborador": o.empleado_nombre,
            "Motivo": _motivo(o.motivo),
            "Estado": o.estado,
            "Inicio": _fecha(o.fecha_inicio),
            "Activos devueltos": sum(1 for a in o.activos if a.devuelto),
            "Activos totales": len(o.activos),
            "Progreso": f"{o.progreso}%",
            "Accesos revocados": sum(1 for a in o.accesos if a.revocado),
            "Accesos totales": len(o.accesos),
            "Entrevista de salida": "Sí" if o.entrevista_salida else "No",
        }
        for o in items
    ]
