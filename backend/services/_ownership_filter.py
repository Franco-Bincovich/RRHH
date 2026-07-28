"""
Resolvers de filtrado de listados por ownership (base → + área → + proyecto → + empleado puntual).

Fuente ÚNICA compartida por vacaciones, ausencias y (Fase 2) el resto de los módulos
con datos de empleados — para no duplicar la intersección. La lógica vive acá; el
repo recibe una sola lista (o None).

Contrato de la CAPA BASE (services/ownership.ids_empleados_visibles):
    None  → sin restricción (admin/gerencia): ve todo.
    []    → no ve ningún empleado (fail-closed).
    [ids] → ve exactamente esos.

⚠️ Contrato de la CAPA DE FILTRO (las funciones de este módulo) = (empleado_ids, vacio).
El `None` significa DOS cosas OPUESTAS según `vacio` — mirarlo solo abre datos ajenos:
    (None,  False) → sin restricción: el caller NO filtra por empleado, ve todo.
    (None,  True)  → VACÍO / fail-closed: el caller NO debe consultar la tabla.
    ([ids], False) → restringir EXACTO a esos empleados.

⚠️ ASIMETRÍA DELIBERADA entre `area_id` y `proyecto_ids` — no la "uniformes".
El área se resuelve ACÁ ADENTRO (con `repo.ids_empleados_por_area`); el proyecto llega YA
RESUELTO desde `repositories/_scope_filtros.empleados_de_proyecto`. Se ve inconsistente y
hay un motivo: este módulo es de la Fase 2 y su contrato de tupla es donde un error abre
datos ajenos. Sumar el proyecto como conjunto ya resuelto es ADITIVO — no toca el camino de
ownership de las 13 superficies de vacaciones/ausencias. Mover la resolución de área afuera
"por simetría" sí lo tocaría, y no compra nada: el eje seguiría intersecándose igual.
"""
from typing import List, Optional, Tuple

from services.ownership import ids_empleados_visibles


def resolver_filtro_empleados(
    user_id: str, rol: str, empresa_id, area_id, repo, proyecto_ids=None,
) -> Tuple[Optional[List[str]], bool]:
    """
    Ownership ∩ área ∩ proyecto. Retorna (empleado_ids, vacio) — contrato de la tupla en el
    docstring del módulo (⚠️ el `None` depende de `vacio`).

    Traduce el `[]` del base a (None, True): el fail-closed pasa a viajar en `vacio`,
    NO en la lista. INTERSECCIÓN de todos los ejes presentes, nunca unión: un empleado
    entra solo si está en TODOS los conjuntos que se pidieron.

    🔴 FAIL-CLOSED POR CADA EJE. Si CUALQUIERA de los tres queda vacío, el resultado es
    (None, True) = vacío — nunca "sin filtro". Es el punto exacto donde un bug abre datos
    ajenos: un `None` devuelto como "sin restricción" en vez de como "nada" haría que un
    mando sin subordinados, o un área sin miembros, vean TODO.

    Args:
        user_id: UUID (str) del usuario logueado.
        rol: Rol canónico (ver ROLES_VALIDOS en utils.permisos).
        empresa_id: empresa activa (None = consolidado) para acotar la resolución de área.
        area_id: filtro de área opcional (None = sin filtro de área).
        repo: EmpleadoOwnershipRepo (o doble) con find_by_user_id, ids_subordinados
              e ids_empleados_por_area.
        proyecto_ids: empleados del proyecto, YA RESUELTOS por el caller (None = sin filtro
              de proyecto). Ver la nota de asimetría en el docstring del módulo.
    """
    visibles = ids_empleados_visibles(user_id, rol, repo)  # None | [] | [ids]
    if visibles == []:
        return None, True                                  # mando sin subordinados → nada
    conjuntos: List[List[str]] = []                        # los ejes que SÍ restringen
    if visibles is not None:
        conjuntos.append(visibles)
    if area_id:
        area_ids = repo.ids_empleados_por_area(empresa_id, area_id)
        if not area_ids:
            return None, True                              # área sin miembros → nada
        conjuntos.append(area_ids)
    if proyecto_ids is not None:
        if not proyecto_ids:
            return None, True                              # proyecto sin asignados → nada
        conjuntos.append(list(proyecto_ids))
    if not conjuntos:
        return None, False                                 # admin/gerencia sin filtros: ve todo
    # Se recorre el primer conjunto y se filtra contra los demás: preserva SU orden, que es
    # el que el repo recibe en el .in_(). Un set().intersection() sería más corto y devolvería
    # los ids en orden arbitrario.
    resto = [set(c) for c in conjuntos[1:]]
    inter = [i for i in conjuntos[0] if all(i in s for s in resto)]
    return (inter, False) if inter else (None, True)


def resolver_empleado_ids(
    user_id: str, rol: str, empresa_id, area_id, empleado_id, repo, proyecto_ids=None,
) -> Tuple[Optional[List[str]], bool]:
    """
    Ownership ∩ área ∩ proyecto ∩ empleado puntual (superset de resolver_filtro_empleados).

    Retorna (empleado_ids, vacio) con el MISMO contrato de la tupla (ver módulo). Con
    empleado_id=None es IDÉNTICO a resolver_filtro_empleados. Si se provee, acota a ese
    único empleado SOLO si cae dentro del alcance de ownership.

    ⚠️ Un empleado_id FUERA del alcance del mando devuelve (None, True) = VACÍO
    (fail-closed), NO el empleado filtrado. Es intencional (un mando no ve ni gestiona
    ajenos); no lo "corrijas" pensando que es un bug.
    """
    empleado_ids, vacio = resolver_filtro_empleados(user_id, rol, empresa_id, area_id, repo, proyecto_ids)
    if empleado_id and not vacio:
        eid = str(empleado_id)
        if empleado_ids is None or eid in empleado_ids:
            empleado_ids = [eid]              # dentro del alcance → acotar a ese empleado
        else:
            empleado_ids, vacio = None, True  # fuera del alcance del mando → vacío
    return empleado_ids, vacio
