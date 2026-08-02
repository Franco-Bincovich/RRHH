"""
Las filas que se ESCRIBEN en `onboarding_templates` y `onboarding_tareas`.

Separadas de `_onboarding_templates_row.py` por el mismo motivo que `_empleado_write_repo.py` se
separó de `_empleado_row.py`: leer y escribir no son la misma operación y sus defaults no se
parecen. Acá vive la traducción `titulo` (API) → `nombre` (columna) del lado de la escritura; la
del lado de la lectura está en el mapper `tarea()`.
"""
from typing import Optional
from uuid import UUID


def payload_template(nombre: str, descripcion: Optional[str], empresa_id: UUID,
                     created_by: Optional[str]) -> dict:
    """Fila de `onboarding_templates` a insertar.

    `es_publica` NO va: se deja al default de la columna (true, migración 082). Una plantilla
    nace compartida y se vuelve privada por decisión explícita de su autor desde el detalle.
    """
    return {"nombre": nombre, "descripcion": descripcion, "activo": True,
            "empresa_id": str(empresa_id), "created_by": created_by}


def payload_tarea(template_id: str, empresa_id: str, data: dict) -> dict:
    """Fila de `onboarding_tareas` a insertar. La tarea hereda el empresa_id de su plantilla.

    Traduce `titulo` (API) a `nombre` (columna) y aplica los defaults de las columnas que la
    UI todavía no expone (`responsable_tipo`, `dias_limite`).
    """
    return {
        "template_id": template_id, "empresa_id": str(empresa_id), "nombre": data["titulo"],
        "descripcion": data.get("descripcion"), "semana": data["semana"],
        "orden": data["orden"], "responsable_tipo": data.get("responsable_tipo", "rrhh"),
        "dias_limite": data.get("dias_limite", 1),
    }


def payload_tarea_update(data: dict) -> dict:
    """Campos a actualizar de una tarea, sin los ausentes. Vacío = nada que hacer."""
    campos = {"nombre": data.get("titulo"), "descripcion": data.get("descripcion"),
              "semana": data.get("semana"), "orden": data.get("orden")}
    return {k: v for k, v in campos.items() if v is not None}
