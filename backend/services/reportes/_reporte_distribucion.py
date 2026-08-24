"""
Reporte de distribución de la plantilla ACTIVA por seniority, modalidad de contratación y turno.
Es un corte transversal (snapshot al momento, sin período). Los valores nulos/vacíos se agrupan
en la categoría visible "Sin especificar" (no se descartan, no rompen) y quedan al final del ranking.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from services._nomina_parsers import VACIOS, normalizar_nombre
from services.reportes._common import _eid

_SIN = "Sin especificar"


def _agrupar(rows: List[dict], campo: str) -> List[dict]:
    """Cuenta por `campo`; los nulos/vacíos caen en 'Sin especificar'. Orden: por total desc,
    con 'Sin especificar' siempre al final.

    🔴 "VACÍO" NO ES SOLO NULL Y '': la lista canónica es `_nomina_parsers.VACIOS` y se IMPORTA,
    no se reescribe acá. El import ya la aplica al ESCRIBIR; esto la aplica al LEER, que es lo
    que cubre las filas cargadas ANTES de que un literal entrara a esa lista. Concreto: los 4
    empleados con `seniority = 'SIN DATOS'` de producción se cargaron cuando ese texto todavía
    no estaba en `VACIOS`, así que ya están en la base y ninguna corrección del import los toca.

    🔴 EL AGRUPAMIENTO ES INSENSIBLE A LA CAJA Y AL ESPACIADO, Y ESO ARREGLA UN CONTEO MAL DADO.
    Antes la clave era el valor CRUDO y el `.upper()` solo decidía si estaba vacío, así que
    `SENIOR` y `senior` salían como DOS categorías. En producción (medido el 23/8/2026) eran 1 y
    5: el reporte partía en dos los 6 seniors de la empresa. La causa es que la columna tiene DOS
    escritores con vocabularios distintos —el formulario escribe minúsculas (`senior`,
    `semi_senior`) y el import de nómina escribe el Excel tal cual, en mayúsculas (`SENIOR`,
    `EXPERT`, `TRAINEE`)—. Dos grafías que solo difieren en la caja son la misma categoría, punto:
    contarlas por separado es un error de aritmética, no una preferencia de formato.

    🔴 QUÉ ETIQUETA SE MUESTRA CUANDO DOS GRAFÍAS SE UNIFICAN: **la más frecuente**, y ante empate
    la menor alfabéticamente. Las dos mitades importan.
      · *La más frecuente* es la que la organización realmente usa (senior 5 vs SENIOR 1), y sale
        del dato: no se inventa texto. Title-case-ar la clave sería inventarlo, y acá rompería:
        `turno` es texto libre con valores como "8 A 17 HS.", que quedarían como "8 A 17 Hs.".
      · *El desempate alfabético* es lo que la hace DETERMINISTA. "la primera que aparezca" habría
        sido lo obvio y está mal: la query no lleva ORDER BY, así que el mismo reporte podría
        decir "SENIOR" un día y "senior" al siguiente sin que cambiara un solo dato.

    ⚠️ ESTO ARREGLA EL CONTEO, NO EL VOCABULARIO, y la diferencia es el punto entero.
    `tipo_contrato` tiene hoy `RELACION DE DEPENDENCIA` (30), `efectivo` (10) y `HONORARIOS` (1):
    **ninguna normalización de caja las junta**, porque no son la misma palabra escrita distinto
    — son vocabularios distintos, y si `efectivo` y `RELACION DE DEPENDENCIA` son la misma
    categoría lo decide RRHH, no este archivo. Cerrar eso pide las tres cosas juntas: una lista
    cerrada para la columna, que el import traduzca a esa lista, y un UPDATE de las filas que ya
    están. Va con el combobox de seniority (bloque N), no acá: mientras el histórico siga en la
    tabla, este agrupamiento tiene que seguir siendo defensivo igual.
    """
    # `normalizar_nombre` es la definición canónica de "la misma cadena" del repo (trim + colapso
    # de espacios + casefold). Se importa en vez de reescribirla: dos definiciones de "mismo
    # texto" que se separen darían dos criterios distintos sobre lo mismo. El nombre habla de
    # nombres por su primer uso (empresas y áreas); la operación es exactamente ésta.
    conteo: dict[str, int] = {}
    grafias: dict[str, dict[str, int]] = {}
    for r in rows:
        valor = r.get(campo)
        crudo = valor.strip() if isinstance(valor, str) else valor
        vacio = not crudo or str(crudo).upper() in VACIOS
        etiqueta = _SIN if vacio else str(crudo)
        clave = _SIN if vacio else normalizar_nombre(etiqueta)
        conteo[clave] = conteo.get(clave, 0) + 1
        grafias.setdefault(clave, {})
        grafias[clave][etiqueta] = grafias[clave].get(etiqueta, 0) + 1

    def _etiqueta(clave: str) -> str:
        """La grafía más usada del grupo; empate → la menor alfabéticamente (determinismo)."""
        return sorted(grafias[clave].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    return sorted(
        [{"categoria": _etiqueta(k), "total": v} for k, v in conteo.items()],
        # El tercer criterio no es decorativo: sin él, dos categorías con el mismo total salen en
        # el orden del dict y el reporte cambia de forma entre corridas sin cambiar de datos.
        key=lambda x: (x["categoria"] == _SIN, -x["total"], x["categoria"]),
    )


def generate_distribucion(empresa_id: Optional[UUID] = None,
                          area_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Distribución de la plantilla activa por seniority / tipo_contrato / turno.
    Filtra por empresa_id y/o area_id (empleados.area_id, directo).

    🔴 `por_modalidad` sale de `tipo_contrato`, NO de la ex `modalidad_contratacion`. Esta
    consulta leía esa otra columna, que ningún camino escribía: el reporte mostraba
    "Sin especificar" para toda la plantilla teniendo el dato en la columna de al lado (el
    import lo escribe en `tipo_contrato` desde la migración 065). La columna duplicada se borró
    en la 084; el porqué completo está ahí. La clave de salida sigue llamándose
    `por_modalidad` porque es lo que el front y el PDF ya consumen."""
    eid = _eid(empresa_id)
    aid = _eid(area_id)
    q = supabase_admin.table("empleados").select("seniority, tipo_contrato, turno").eq("estado", "activo")
    if eid:
        q = q.eq("empresa_id", eid)
    if aid:
        q = q.eq("area_id", aid)
    rows = q.execute().data or []

    return {
        "titulo": "Distribución de plantilla",
        "total_empleados": len(rows),
        "por_seniority": _agrupar(rows, "seniority"),
        "por_modalidad": _agrupar(rows, "tipo_contrato"),
        "por_turno": _agrupar(rows, "turno"),
    }
