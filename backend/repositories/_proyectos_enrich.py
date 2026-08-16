"""
Enriquecimiento de proyectos: nombre de la empresa dueña y resumen de costeo (costo
acumulado, presupuesto restante, % consumido). Todo con lookups batch — una query por
dimensión, sin N+1 (mismo patrón que _evaluacion_lotes_enrich / audit_repo). Aislado de
proyectos_repo para no pasar su límite de líneas. Un helper más a portar a asyncpg junto
con su repo.
"""
from integrations.supabase_client import supabase_admin
from schemas.proyectos import CosteoResumen, ProyectoResponse


def _costo_de(r: dict) -> float:
    """horas × valor_hora_snapshot de UNA fila. Sin snapshot → 0.0.

    🔑 ES LA UNICA DEFINICION DEL COSTO DE UNA CARGA, y por eso la usan las DOS agregaciones de
    abajo. Con una copia en cada una, el costeo del proyecto y el total de la pantalla de horas
    podrian empezar a decir numeros distintos sobre las mismas filas.

    ⚠️ El `is None` no es defensivo de mas: desde la migración 103 `valor_hora_snapshot` es
    NULLABLE (las cargas del link público no tienen con qué costearse). Hoy no llegan acá porque
    van con `proyecto_id` NULL, pero un `float(None)` revienta y el guard cuesta una línea.
    Suman 0 porque para un TOTAL "no costeable" aporta cero — lo que NO se puede hacer es
    imprimir ese 0 como "$ 0", que diría que costaron nada (ver types/proyecto.ts::Hora).
    """
    vh = r.get("valor_hora_snapshot")
    return float(r["horas"]) * float(vh) if vh is not None else 0.0


def batch_costos(proyecto_ids: list[str]) -> dict[str, float]:
    """SUM(horas × valor_hora_snapshot) por proyecto en una sola query.
    {} con la lista vacía — ahí no dispara ninguna query."""
    if not proyecto_ids:
        return {}
    rows = (supabase_admin.table("horas_proyecto")
            .select("proyecto_id, horas, valor_hora_snapshot")
            .in_("proyecto_id", proyecto_ids).execute().data or [])
    costos: dict[str, float] = {}
    for r in rows:
        pid = r["proyecto_id"]
        costos[pid] = costos.get(pid, 0.0) + _costo_de(r)
    return costos


def totales_de_proyecto(proyecto_id: str) -> tuple[float, float]:
    """(horas, costo) de TODAS las cargas del proyecto — NO de una página.

    🔴 EXISTE PORQUE UN TOTAL NO SE PUEDE CALCULAR SOBRE LA PAGINA. La pantalla de horas paginaba
    y sumaba con un `.reduce()` sobre las 20 filas visibles: con 400 cargas decía "9 h". Un total
    que cambia al pasar de página no es un total, y el usuario no tiene cómo notar que está mal.
    Por eso lo calcula el backend sobre el conjunto entero y viaja en la misma respuesta.

    ⚠️ NO PAGINA A PROPOSITO: trae las filas del proyecto para sumarlas. Es aceptable porque el
    universo es UN proyecto (no la tabla), y es lo mismo que ya hace `batch_costos` para el
    costeo del listado. Si `horas_proyecto` creciera, esto pide un agregado en la base (RPC), no
    volver a sumar en la pantalla.
    """
    rows = (supabase_admin.table("horas_proyecto")
            .select("horas, valor_hora_snapshot")
            .eq("proyecto_id", proyecto_id).execute().data or [])
    return (round(sum(float(r["horas"]) for r in rows), 2),
            round(sum(_costo_de(r) for r in rows), 2))


def enriquecer(rows: list[dict], costo_map: dict[str, float]) -> list[ProyectoResponse]:
    """Mapea filas crudas de proyectos a ProyectoResponse con empresa_nombre y costeo.
    [] si no hay filas — ahí no dispara la query de empresas."""
    if not rows:
        return []
    emp_ids = list({r["empresa_id"] for r in rows})
    empresa_map = {
        e["id"]: e["nombre"]
        for e in (supabase_admin.table("empresas").select("id, nombre")
                  .in_("id", emp_ids).execute().data or [])
    }
    result = []
    for r in rows:
        costo = round(costo_map.get(r["id"], 0.0), 2)
        ppto = float(r.get("presupuesto") or 0)
        restante = round(ppto - costo, 2)
        pct = round(costo / ppto * 100, 1) if ppto > 0 else None
        result.append(ProyectoResponse.model_validate({
            **r,
            "empresa_nombre": empresa_map.get(r["empresa_id"]),
            "costeo": CosteoResumen(
                costo_acumulado=costo,
                presupuesto_restante=restante,
                pct_consumido=pct,
            ),
        }))
    return result
