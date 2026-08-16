"""
El bloque de EVALUADOS de `evaluacion_repo`: alta en lote, el listado (completo y paginado) y los
sectores que pueblan el filtro.

SALIÓ DE `evaluacion_repo.py`, que estaba en 94/100 y llegó a 152 al sumarle la paginación con
filtros en el WHERE. El corte es por ENTIDAD: ese repo atiende tres —lotes, evaluados y
resultados— y evaluados es la única que crece, porque es la única con pantalla y filtros.

🔴 DOS LECTORES CON CONTRATOS OPUESTOS, Y ES A PROPÓSITO:
  · `find_evaluados` trae el lote ENTERO — lo usan las MÉTRICAS y la ficha, que agregan sobre
    todo (promedios por competencia, brecha de autopercepción, corte por sector). Paginarlo
    habría dejado las métricas calculadas sobre 25 de 1.005, sin error y sin aviso.
  · `find_evaluados_pagina` trae una página con los filtros en el WHERE — es la pantalla.
Los dos comparten `_del_lote()`: con dos queries separadas podrían mirar conjuntos distintos del
mismo lote sin que nada fallara.
"""
from typing import List, Optional, Tuple

from integrations.supabase_client import supabase_admin
from repositories._evaluacion_insert import insert_completo
from schemas.evaluacion_resultados import EvaluadoResponse

TABLE = "evaluacion_evaluados"


def _del_lote(lote_id: str, columnas: str = "*", contar: bool = False):
    """La query base de los evaluados de un lote. UNA definición para los cuatro lectores."""
    tabla = supabase_admin.table(TABLE)
    q = tabla.select(columnas, count="exact") if contar else tabla.select(columnas)
    return q.eq("lote_id", lote_id)


def crear_evaluados(filas: List[dict]) -> List[EvaluadoResponse]:
    """Inserta N evaluados (bulk). [] si no hay; DB_ERROR si el insert no devuelve todas."""
    data = insert_completo(TABLE, filas, "Error al guardar los evaluados del lote")
    return [EvaluadoResponse.model_validate(r) for r in data]

def find_evaluados(lote_id: str) -> List[EvaluadoResponse]:
    """TODOS los evaluados de un lote, ordenados por apellido y nombre. Sin paginar.

    🔴 NO PAGINA A PROPÓSITO: la usan las MÉTRICAS y la ficha individual, que agregan sobre
    el lote entero (promedios por competencia, brecha de autopercepción, corte por sector).
    Paginarla habría dejado las métricas calculadas sobre 25 de 1.005 evaluados, sin error.
    El listado de pantalla usa `find_evaluados_pagina`.
    """
    res = (_del_lote(lote_id).order("apellido_evaluado").order("nombre_evaluado")
           .execute())
    return [EvaluadoResponse.model_validate(r) for r in (res.data or [])] if res else []

def find_evaluados_pagina(lote_id: str, page: int = 1, page_size: int = 20,
                          sector: Optional[str] = None, perfil: Optional[str] = None,
                          con_nota: Optional[str] = None,
                          empleado_ids: Optional[List[str]] = None,
                          ) -> Tuple[List[EvaluadoResponse], int]:
    """Una página de evaluados del lote + el total real del filtro.

    🔴 LOS TRES FILTROS VAN EN EL WHERE. Hasta el 15/8/2026 el panel los aplicaba sobre el
    array ya traído: con ~30 filas era tolerable, pero a 1.005 por lote significa que filtrar
    por sector no encuentra a nadie que esté fuera de la página que se está mirando.

    `empleado_ids` = los del proyecto, ya resueltos por el service (None = sin filtro).
    `.order("id")` desempata: dos personas del mismo lote pueden llamarse igual —el CSV trae
    sólo apellido y nombre, sin DNI ni legajo (es la limitación conocida del matcheo)— así que
    el homónimo es un caso REAL acá, no un borde teórico.
    """
    q = _del_lote(lote_id, contar=True)
    if sector:
        q = q.eq("sector", sector)
    if perfil:
        q = q.eq("perfil", perfil)
    if con_nota == "si":
        q = q.not_.is_("nota_final", "null")
    elif con_nota == "no":
        q = q.is_("nota_final", "null")
    if empleado_ids is not None:
        # ⚠️ UN EVALUADO CON `empleado_id` NULL QUEDA EXCLUIDO ACÁ, Y ES LA DEFINICIÓN, NO UN BUG.
        # El estado "sin_candidato" es válido —el CSV trae sólo apellido y nombre, y no matcheó
        # a nadie—, pero sin empleado NO se lo puede atribuir a ningún proyecto. Misma regla que
        # "un proyecto sin asignados no aparece bajo ninguna área". La UI lo expone con el flag
        # `asignado`, así que el usuario ve por qué desapareció de la lista.
        # `.in_([])` deja a todos afuera: un proyecto sin gente filtra a NADIE, no a todos.
        # (Este párrafo venía del `_pasa` del service, que se borró al mudar los filtros al
        #  WHERE: la regla sobrevive donde ahora se aplica.)
        q = q.in_("empleado_id", empleado_ids)
    res = (q.order("apellido_evaluado").order("nombre_evaluado").order("id")
           .range((page - 1) * page_size, page * page_size - 1).execute())
    return ([EvaluadoResponse.model_validate(r) for r in (res.data or [])] if res else [],
            (res.count or 0) if res else 0)

def sectores_del_lote(lote_id: str) -> List[str]:
    """Los sectores distintos del lote, para poblar el filtro.

    🔑 UNA query de UNA columna sobre el lote entero, no derivados de la página: si las
    opciones salieran de lo que se está viendo, el desplegable ofrecería sólo los sectores
    de la página 1 y filtrar por cualquier otro sería imposible. Mismo patrón que
    `_area_row.counts_by_area`.
    """
    res = _del_lote(lote_id, columnas="sector").execute()
    return sorted({r["sector"] for r in (res.data or []) if r.get("sector")}) if res else []
