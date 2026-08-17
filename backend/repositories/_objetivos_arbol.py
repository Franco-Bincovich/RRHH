"""
La jerarquía de objetivos del lado del repo: armar el árbol desde la lista plana, contarlo, y
preguntarle a la base si un objetivo tiene hijos.

Las dos primeras son puras; `tiene_hijos` consulta. Viven juntas porque las tres responden a la
misma relación padre-hijo, y separarlas dejaría un archivo de una sola función.

🔴 EL ORDEN NUEVO, Y POR QUÉ EL VIEJO NO SERVÍA. Hasta la jerarquía el listado salía plano por
`fecha_entrega` ascendente: lo primero que vence, arriba. Con subobjetivos ese orden DESARMA el
árbol — un hijo que vence en marzo saldría por encima de un padre que vence en septiembre, y la
pantalla mostraría la tarea suelta antes que el objetivo del que cuelga.

El orden nuevo es: **las RAÍCES por `fecha_entrega` ascendente (nulos al final), y los hijos
inmediatamente debajo de su padre, entre ellos también por `fecha_entrega` ascendente.**

Y no hace falta ordenar acá: la query sigue trayendo TODO por `fecha_entrega` ascendente, y este
agrupado es ESTABLE —recorre las filas en el orden en que vinieron—, así que raíces e hijos
conservan cada uno el orden de la base. El `.order()` se queda donde tiene que estar, en la
query; lo único que cambió es el armado.

🔴 UN HIJO NUNCA DESAPARECE. Si un filtro deja pasar al hijo pero no a su padre (por ejemplo
estado=terminado, con el padre todavía en curso), el hijo se promueve al nivel superior en vez
de perderse. Es la misma invariante que gobierna los exports del repo: el archivo y la pantalla
pueden mostrar de más, nunca de menos y en silencio. La alternativa —descartarlo— haría que un
objetivo terminado no apareciera en ningún lado con ciertos filtros.

🔴 CON EL FILTRO POR `tipo` (migración 119) ESA PROMOCIÓN DEJA DE SER UN CASO BORDE Y PASA A SER
EL CASO NORMAL, así que hay que decirlo entero: **el mismo objetivo cuenta como HIJO en una vista
y como RAÍZ en la otra.**

El escenario no es rebuscado, es el que la feature busca: un OPERATIVO colgado de un ANUAL —el
objetivo del año descompuesto en tareas del trimestre—, que es plausible y por eso el tipo NO se
hereda entre padre e hijo (decisión de producto, ver `schemas/objetivo.ObjetivoCreate`). Filtrando
`tipo=anual` ese hijo no pasa y el padre sale solo; filtrando `tipo=operativo` el que no pasa es
el PADRE, y el hijo se promueve y aparece suelto en el nivel superior.

Es CORRECTO —el hijo es un objetivo operativo y la vista operativa tiene que mostrarlo— pero
tiene una consecuencia que no se ve leyendo el número: `ObjetivoListResponse.total` cuenta RAÍCES,
así que la suma de los totales de las dos vistas puede ser MAYOR que la cantidad de objetivos.
Quien compare "anuales + operativos" contra el total sin filtro va a encontrar una diferencia, y
la diferencia son exactamente los hijos promovidos, no filas duplicadas.
⚠️ El conteo APLANADO (`contar_con_hijos`, el que usa el tope de export) no tiene este problema:
cuenta padres e hijos, así que cada objetivo vale uno en cualquier vista.

La profundidad máxima es 2 (services/_objetivos_jerarquia.py), así que esto no recursiona: un
hijo no puede tener hijos y su lista queda siempre vacía.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from schemas.objetivo import ObjetivoResponse


def armar_arbol(items: List[ObjetivoResponse]) -> List[ObjetivoResponse]:
    """Anida cada hijo bajo su padre y devuelve solo el nivel superior, en el orden recibido."""
    por_id = {o.id: o for o in items}
    raices: List[ObjetivoResponse] = []
    for o in items:
        padre = por_id.get(o.parent_id) if o.parent_id else None
        if padre is None:
            raices.append(o)      # raíz real, o hijo cuyo padre no pasó el filtro
        else:
            padre.hijos.append(o)
    return raices


def contar_con_hijos(raices: List[ObjetivoResponse]) -> int:
    """Total de objetivos del árbol, padres e hijos.

    Lo consume el chequeo de límite del export, que cuenta FILAS DEL ARCHIVO: el export lista
    padres e hijos, así que `len(raices)` diría menos de lo que se va a escribir.
    """
    return sum(1 + len(r.hijos) for r in raices)


def tiene_hijos(objetivo_id: str, empresa_id: Optional[UUID] = None) -> bool:
    """True si el objetivo tiene al menos un subobjetivo.

    Query dirigida (`limit 1`), no un conteo: la pregunta es "¿alguno?", y traer el total
    costaría lo mismo que traer todos. La consume `_objetivos_jerarquia.ensure_no_tiene_hijos`
    para impedir que un padre se cuelgue de otro y sus hijos se vuelvan nietos.
    """
    q = supabase_admin.table("objetivos").select("id").eq("parent_id", objetivo_id)
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    return bool(q.limit(1).execute().data)
