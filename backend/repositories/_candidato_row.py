"""
La traducción de una fila de `candidatos` a schema.

Extraído de `candidato_repo.py`, que estaba en 95 contra un límite de 100 y no admitía ni la
columna de idempotencia del import por mail ni el método para asignarle una vacante a un
candidato suelto. Molde: `_inventario_items_row.py`, `_objetivo_row.py` — el mapper aparte para
que no pueda divergir entre los SEIS métodos que lo usan (`find_candidatos`,
`find_all_candidatos`, `find_by_id`, `save_candidato`, `update_etapa_candidato` y el retorno de
las escrituras).

El movimiento fue VERBATIM: el cuerpo, sus comentarios y el nombre son idénticos a los que
estaban embebidos en `candidato_repo.py`.

⚠️ Vive en `repositories/`, así que su límite es 100 líneas, como cualquier repositorio. No
hereda un límite más alto por ser un satélite.

🔴 Acá NO hay constante de SELECT porque `candidatos` se lee con `select("*")` y sin embeds: no
tiene joins que resolver. Si alguna vez se le agrega uno, la constante va en este archivo —
`tests/test_selects_repos.py` la resuelve a través del import, igual que hace con `_vacante_row`
y `_empleado_row`.
"""
from schemas.candidato import CandidatoResponse


def _crow(r: dict) -> CandidatoResponse:
    vid = r.get("vacante_id")
    emp = r.get("empresa_id")
    return CandidatoResponse(
        id=str(r["id"]), vacante_id=str(vid) if vid else None,
        # El `select("*")` ya la traía; el mapper la descartaba. La necesita el evento de
        # auditoría de la baja (empresa DEL REGISTRO, no del header).
        empresa_id=str(emp) if emp else None,
        nombre=r["nombre"], apellido=r["apellido"], email=r["email"],
        telefono=r.get("telefono"),
        cargo_anterior=r.get("cargo_anterior"), empresa_anterior=r.get("empresa_anterior"),
        etapa_pipeline=r.get("etapa", "postulado"),
        # El estado de la POSTULACIÓN (activo | descartado | contratado | en_espera), que es
        # otro eje que la etapa: ver el comentario de `CandidatoResponse.estado`. Faltaba esta
        # línea y era exactamente el bug del comentario de abajo, ocurriendo dos campos más
        # arriba: la columna es NOT NULL, el `select("*")` la traía en TODAS las filas, y se
        # perdía sin que nada fallara.
        # El default del `.get` espeja el DEFAULT de la base y sigue el idioma de `etapa`. No
        # cubre ninguna fila real —la columna es NOT NULL, así que siempre viene—: existe para
        # los dicts armados a mano en los tests, que son anteriores a esta columna.
        estado=r.get("estado", "activo"),
        score_ia=r.get("score_ia"),
        busqueda_congelada=r.get("busqueda_congelada"),
        cv_storage_path=r.get("cv_storage_path"),
        # Si esta línea faltara, el `select("*")` traería la columna y el schema la descartaría
        # EN SILENCIO — el bug que ya pasó tres veces en este repo. Hay un test que lo fija.
        screening_warning=r.get("screening_warning"),
        clasificacion_ia=r.get("clasificacion_ia"),
        clasificacion_motivo=r.get("clasificacion_motivo"),
        clasificacion_origen=r.get("clasificacion_origen"),
        created_at=r["created_at"],
    )
