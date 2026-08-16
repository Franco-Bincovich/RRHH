"""
Proyección de columnas legibles para el export de candidatos.

Mismo molde que los otros exports: no vuelca `model_dump()` crudo (que incluiría `id`,
`vacante_id` y `empresa_id`). Los headers del Excel son las keys de cada dict.

Las columnas salen de lo que la pantalla MUESTRA (`CandidatoRow` + `CandidatoDetailPanel`), no de
lo que parezca razonable: con la tabla en 0 filas nadie va a poder abrir el archivo y corregirlo.

⚠️ `cv_storage_path` queda AFUERA. Es una ruta de un bucket privado: en el Excel no sirve para
nada —no se puede abrir sin firmar la URL— y en cambio expone la organización interna del
storage. Quien necesita el CV lo baja desde la ficha, que sí firma la URL.
"""
from typing import List

from schemas.candidato import CandidatoGrupoResponse


def _fecha(v) -> str:
    """Formatea date/datetime a dd/mm/aaaa (descarta hora); '' si es None."""
    return v.strftime("%d/%m/%Y") if v else ""


def construir_filas_export(items: List[CandidatoGrupoResponse]) -> List[dict]:
    """Proyecta los candidatos a columnas legibles (sin UUIDs crudos)."""
    return [
        {
            "Búsqueda": c.grupo_nombre,
            # La vacante pudo haberse borrado (migración 071): el candidato sobrevive con el
            # título congelado. La columna dice cuál de los dos casos es, porque cambia qué se
            # puede hacer con ese candidato.
            "Búsqueda activa": "Sí" if c.busqueda_activa else "No",
            "Nombre": c.nombre,
            "Apellido": c.apellido,
            "Email": c.email,
            "Teléfono": c.telefono,
            "Cargo anterior": c.cargo_anterior,
            "Empresa anterior": c.empresa_anterior,
            "Etapa": c.etapa_pipeline,
            "Score IA": c.score_ia,
            # Las DOS columnas, no solo la etiqueta: el archivo es lo que RRHH mira fuera del
            # sistema, y una etiqueta sin su motivo es exactamente la lectura que este módulo no
            # quiere provocar. "Sin clasificar" explícito, no vacío: vacío se lee como error.
            "Clasificación": c.clasificacion_ia or "Sin clasificar",
            "Motivo": c.clasificacion_motivo,
            # La columna que separa lo que dijo el modelo de lo que decidió una persona. Sin
            # ella, un archivo que mezcla las dos no sirve para evaluar si el filtro funciona.
            "Clasificado por": {"modelo": "Sistema", "humano": "Revisión manual"}.get(
                c.clasificacion_origen or "", ""),
            "Cargado": _fecha(c.created_at),
        }
        for c in items
    ]
