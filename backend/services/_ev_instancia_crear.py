"""
Alta de una instancia de evaluación (extraído para mantener el service ≤150 líneas).

Función libre que recibe los colaboradores (repo, ciclos_repo, plantillas_repo) — mismo molde que
services/_onboarding_iniciar.py, del que además copia el criterio de la barrera. El service la
delega en una línea. La lógica se movió VERBATIM desde EvInstanciasService.create.
"""
from integrations.supabase_client import supabase_admin
from schemas.evaluaciones import InstanciaCreate, InstanciaDetalleResponse
from utils.errors import AppError
from utils.logger import logger


def crear(repo, ciclos_repo, plantillas_repo, data: InstanciaCreate) -> InstanciaDetalleResponse:
    """
    Crea una instancia de evaluación para un empleado en un ciclo.
    Hereda empresa_id del ciclo. Genera filas vacías de ev_resultados.

    🔴 EL EMPLEADO SE BUSCA ACOTADO A LA EMPRESA DEL CICLO, y por eso ya no existe un
    EMPRESA_MISMATCH (422). Antes el lookup por id no acotaba y el desajuste se detectaba DESPUÉS,
    con un status propio: pedir el id de un empleado de otra empresa devolvía 422 mientras que un
    id inventado devolvía 404, y esa diferencia confirmaba que ese empleado existe. Ahora el filtro
    va EN EL WHERE (Forma A), así que "no existe" y "es de otra empresa" son el mismo 404, con el
    mismo code y el mismo mensaje. Es el cierre que la Fase 2 aplicó en 92 endpoints y que acá
    había quedado suelto porque no responde a un id del path sino al cruce de dos entidades.

    ⚠️ La empresa contra la que se valida es la del CICLO, no la del header: la instancia se
    escribe en la empresa del ciclo, así que es la única comparación que significa algo.

    Args:
        repo: EvInstanciasRepo (o doble de test).
        ciclos_repo: EvCiclosRepo (o doble de test).
        plantillas_repo: EvPlantillasRepo (o doble de test).
        data: ciclo, empleado y evaluador opcional.

    Returns:
        InstanciaDetalleResponse con la instancia recién creada y sus resultados vacíos.

    Raises:
        AppError: CICLO_NOT_FOUND (404), CICLO_CERRADO (422),
                  EMPLEADO_NOT_FOUND (404) si no existe o es de otra empresa,
                  PLANTILLA_NOT_FOUND (404), INSTANCIA_DUPLICADA (409), DB_ERROR (500).
    """
    ciclo = ciclos_repo.find_by_id(str(data.ciclo_id))
    if not ciclo:
        raise AppError("Ciclo no encontrado", "CICLO_NOT_FOUND", 404)
    if ciclo.estado == "cerrado":
        raise AppError("No se puede asignar empleados a un ciclo cerrado", "CICLO_CERRADO", 422)
    emp = supabase_admin.table("empleados").select("empresa_id").eq("id", str(data.empleado_id)).eq(
        "empresa_id", str(ciclo.empresa_id)).maybe_single().execute()
    if not (emp and emp.data):  # no existe, o es de otra empresa: indistinguible a propósito
        raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
    plantilla = plantillas_repo.find_by_id(str(ciclo.plantilla_id))
    if not plantilla:
        raise AppError("Plantilla del ciclo no encontrada", "PLANTILLA_NOT_FOUND", 404)
    if repo.exists(str(data.ciclo_id), str(data.empleado_id)):
        raise AppError("Este empleado ya tiene una evaluación en este ciclo", "INSTANCIA_DUPLICADA", 409)
    criterios = [{"id": str(c.id)} for c in plantilla.criterios]
    evaluador_id = str(data.evaluador_id) if data.evaluador_id else None
    instancia = repo.create(str(data.ciclo_id), str(data.empleado_id), evaluador_id, str(ciclo.empresa_id), criterios)
    if not instancia:
        raise AppError("Error al crear la instancia", "DB_ERROR", 500)
    logger.info("Instancia de evaluación creada", extra={
        "empleado_id": str(data.empleado_id), "ciclo_id": str(data.ciclo_id),
    })
    return instancia
