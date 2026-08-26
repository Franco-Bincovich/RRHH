"""
Escrituras de la VACANTE en sí: alta, edición y baja.

Extraído de `vacante_service.py`, que estaba en 147/150 y no admitía el endpoint de export.
Molde: `_vacante_candidatos.py` (el satélite hermano, que se llevó las escrituras del
CANDIDATO) y `_empresa_logo.py` — funciones libres que reciben sus colaboradores.

POR QUÉ SALIÓ ESTE BLOQUE: las tres arman su payload de auditoría INLINE, y eso es la mitad de
sus líneas. Son además las tres que mutan la fila de `vacantes`; lo que queda en el service son
lecturas y la delegación a los candidatos. El corte cae en la misma costura que ya había
separado `_vacante_candidatos`.

🔴 EL ORDEN DEL BORRADO ES LOAD-BEARING y por eso viaja completo con `eliminar`: congelar el
nombre de la búsqueda en los candidatos va ANTES de borrar la vacante, porque después la FK
queda en NULL (migración 071) y el texto ya no se puede reconstruir.

⚠️ Vive en `services/`, así que su límite es 150 líneas, como cualquier service. No hereda un
límite más alto por ser un satélite.
"""
from typing import Optional
from uuid import UUID

from schemas.vacante import VacanteCreate, VacanteResponse, VacanteUpdate
from services._vacante_codigo import normalizar
from services._vacante_codigo_choque import asegurar_unico, choque_de_codigo
from utils.errors import AppError
from utils.logger import logger

_ESTADOS = {"nueva", "en_proceso", "con_candidatos", "cerrada"}


def _or_404(vacante: Optional[VacanteResponse]) -> VacanteResponse:
    """Literal ÚNICO del 404 del módulo: "no existe" y "es de otra empresa" son el mismo caso."""
    if not vacante:
        raise AppError("Vacante no encontrada", "VACANTE_NOT_FOUND", 404)
    return vacante


def _guardar_con_codigo(codigo: str, repo, escribir):
    """Ejecuta la escritura traduciendo el choque del índice único a un mensaje que se entiende.

    🔴 EL `try` NO ES REDUNDANTE CON `asegurar_unico`. Aquél consulta antes y sirve para NOMBRAR
    la búsqueda dueña; entre esa consulta y este INSERT/UPDATE otra sesión puede escribir el
    mismo código. La garantía la da el índice `vacantes_codigo_uq`, y sin esta traducción el
    usuario vería un 500 de PostgREST sobre lo que en realidad es un código repetido.

    ⚠️ Relanza el error ORIGINAL si no es el índice: tragarse cualquier fallo de base detrás de
    "código duplicado" mandaría a Capital Humano a cambiar un código que estaba perfecto.
    """
    try:
        return escribir()
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001 — se inspecciona y se relanza si no es lo nuestro
        choque = choque_de_codigo(exc, repo, codigo)
        if choque:
            raise choque from exc
        raise


def crear(repo, audit, data: VacanteCreate, created_by: str) -> VacanteResponse:
    """
    Crea una nueva vacante en estado 'nueva'. empresa_id viene en el body.

    El código lo escribe Capital Humano en TEXTO NATURAL ("Lider de equipo"): se convierte a su
    forma canónica (`LIDER-DE-EQUIPO`) y se verifica que no la tenga otra búsqueda ANTES de
    escribir, para poder decir cuál. 🔴 La unicidad se mide sobre el CANÓNICO, no sobre lo
    tipeado: `Lider de equipo` y `LIDER DE EQUIPO` son el mismo código.

    Args:
        repo: VacanteRepo (o doble de test).
        audit: AuditService (o doble de test).
        data: Datos de la vacante validados por Pydantic (incluye empresa_id y codigo).
        created_by: ID del usuario que realiza la operación (trazabilidad).

    Raises:
        AppError: CODIGO_VACANTE_INVALIDO (422) · CODIGO_VACANTE_DUPLICADO (409).
    """
    data.codigo = normalizar(data.codigo)
    asegurar_unico(repo, data.codigo)
    vacante = _guardar_con_codigo(data.codigo, repo, lambda: repo.save(data))
    audit.registrar(
        usuario_id=created_by, entidad="vacante", registro_id=vacante.id, accion="INSERT",
        evento="alta_vacante", empresa_id=vacante.empresa_id, datos_anteriores=None,
        datos_nuevos={"codigo": vacante.codigo, "titulo": vacante.titulo,
                      "area_id": vacante.area_id, "estado": vacante.estado},
    )
    logger.info("Vacante creada", extra={"vacante_id": vacante.id, "created_by": created_by})
    return vacante


def actualizar(repo, audit, id: UUID, data: VacanteUpdate, empresa_id: Optional[UUID] = None,
               usuario_id: Optional[str] = None) -> VacanteResponse:
    """
    Actualiza los campos de una vacante existente (actualización parcial).

    El código se puede corregir, con la MISMA validación que el alta: se normaliza y se verifica
    que no lo tenga otra búsqueda. `excepto_id` es esta misma vacante — sin él, guardarla sin
    tocarle el código chocaría contra sí misma.

    ⚠️ Cambiar el código NO toca a los candidatos que ya entraron: cuelgan de `vacante_id`. Lo
    que queda desalineado es el AVISO ya publicado — un mail que llegue con el código viejo cae
    en "pendientes" con `vacante_desconocida` y se asigna a mano. La pantalla lo avisa antes de
    guardar cuando la búsqueda ya tiene candidatos.

    Raises:
        AppError: ESTADO_INVALIDO (400) si el estado no está en el enum.
        AppError: VACANTE_NOT_FOUND (404) si el ID no existe o no pertenece a la empresa.
        AppError: CODIGO_VACANTE_INVALIDO (422) · CODIGO_VACANTE_DUPLICADO (409).
    """
    if data.estado and data.estado not in _ESTADOS:
        raise AppError(
            f"Estado inválido. Permitidos: {', '.join(_ESTADOS)}", "ESTADO_INVALIDO", 400
        )
    # Lectura previa para el diff: `update` devuelve la fila YA actualizada, así que sin esto
    # el evento no podría decir de qué valor se venía. El 404 es el mismo de abajo.
    previa = _or_404(repo.find_by_id(str(id), empresa_id))
    if data.codigo is not None:
        data.codigo = normalizar(data.codigo)
        asegurar_unico(repo, data.codigo, excepto_id=previa.id)
    vacante = _or_404(_guardar_con_codigo(
        data.codigo or previa.codigo, repo, lambda: repo.update(str(id), data, empresa_id)))
    tocados = data.model_dump(exclude_none=True)
    audit.registrar(
        usuario_id=usuario_id, entidad="vacante", registro_id=str(id), accion="UPDATE",
        evento="edicion_vacante", empresa_id=vacante.empresa_id,
        datos_anteriores={k: getattr(previa, k, None) for k in tocados},
        datos_nuevos={k: getattr(vacante, k, None) for k in tocados},
    )
    logger.info("Vacante actualizada", extra={"vacante_id": str(id)})
    return vacante


def eliminar(repo, candidato_repo, adjuntos, audit, id: UUID, empresa_id: Optional[UUID] = None,
             rol: Optional[str] = None, usuario_id: Optional[str] = None) -> None:
    """Elimina la vacante. Orden estricto: (1) congela el nombre en sus candidatos (sobreviven
    vía FK SET NULL, migración 071), (2) borra físicamente + soft-delete sus imágenes, (3) borra
    la fila. Raises VACANTE_NOT_FOUND (404)."""
    vac = _or_404(repo.find_by_id(str(id), empresa_id))
    texto = f"{vac.titulo} — {vac.area_nombre}" if vac.area_nombre else vac.titulo
    candidato_repo.congelar_busqueda(str(id), texto, empresa_id)  # ANTES de borrar la vacante
    adjuntos.eliminar_todos_por_entidad("vacante", str(id), empresa_id, rol, usuario_id)
    repo.delete(str(id), empresa_id)
    audit.registrar(
        usuario_id=usuario_id, entidad="vacante", registro_id=str(id), accion="DELETE",
        evento="baja_vacante", empresa_id=vac.empresa_id,
        datos_anteriores={"titulo": vac.titulo}, datos_nuevos=None,
    )
    logger.info("Vacante eliminada", extra={"vacante_id": str(id)})
