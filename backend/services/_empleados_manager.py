"""
Las dos validaciones del SUPERIOR INMEDIATO (`manager_id`): que exista, y que no cierre un ciclo.

Extraídas VERBATIM de `_empleados_utils.py`, que llegó a 164 contra un límite de 150 al
documentarse la excepción de superior cruzado entre empresas (2/8/2026). No cambió una línea de
código ni un mensaje: solo la casa.

El corte es por unidad de sentido, no por cantidad de líneas. En `_empleados_utils` quedan las
validaciones que miran UN campo contra su catálogo (legajo, área) más el literal canónico del
404. Acá viven las dos que miran el GRAFO de jefaturas, que es lo que las hace distintas: no
preguntan "¿este valor es válido?" sino "¿esta arista se puede agregar al organigrama?".

🔴 LAS DOS SON LA EXCEPCIÓN A LA BARRERA DE EMPRESA DE LA FASE 2, y por eso conviene que estén
juntas: ninguna acota por `empresa_id`, las dos a propósito, y las dos tienen escrito el porqué
en su docstring. Leerlos antes de "restaurar" nada. El resto de la excepción vive en
`services/_alcance_mandos.py`.
"""
from typing import Optional

from repositories.empleado_repo import EmpleadoRepo
from utils.errors import AppError


def ensure_manager_valido(repo: EmpleadoRepo, manager_id) -> None:
    """Lanza MANAGER_NOT_FOUND (404) si `manager_id` no es un empleado EXISTENTE.

    🔴 VALIDA EXISTENCIA, **NO** PERTENENCIA A UNA EMPRESA — y es deliberado. NO le agregues el
    `empresa_id` de vuelta "para restaurar la barrera de Fase 2".

    UN EMPLEADO PUEDE TENER SUPERIOR DE OTRA EMPRESA DEL GRUPO (decisión de producto, 2/8/2026).
    Para `mandos_medios` el `manager_id` REEMPLAZA al filtro de empresa: sus subordinados son
    suyos sin importar de qué empresa sean, en LECTURA y en ESCRITURA. El vínculo de jefatura es
    más fuerte que la frontera societaria, porque describe quién responde ante quién — que es
    exactamente la pregunta que el ownership contesta.

    ⚠️ Hasta el 2/8/2026 esta función validaba contra la empresa, y su docstring daba como MOTIVO
    justamente lo que ahora se permite: *"el ownership de mandos_medios se resuelve por manager_id,
    y un superior de otra empresa haría que ids_subordinados cruce la frontera"*. Eso no era un
    efecto colateral, era el objetivo — y hoy es la feature. Se deja escrito para que la próxima
    sesión no lo revierta de buena fe leyendo la regla general.

    POR QUÉ SIGUE SIENDO SEGURO (los tres ejes que NO se aflojaron):
      1. El eje de empresa sigue rigiendo para admin_rrhh y gerencia_lectura, y para todas las
         secciones que no son VACACIONES/AUSENCIAS. Ver `services/_ownership_filter.empresa_efectiva`.
      2. Para `mandos_medios` el ownership NUNCA devuelve "sin restricción" (ver la invariante en
         `_ownership_filter`): siempre es una lista concreta de ids o el vacío fail-closed. Aflojar
         la empresa no puede degenerar en "ve todo".
      3. El 404 no cambia: sigue siendo indistinguible del de "no existe", así que no aparece un
         oráculo nuevo. Lo único que se ensancha es que un UUID de empleado de otra empresa deja de
         ser rechazado — y para llegar ahí hay que adivinar un UUID v4.

    POR QUÉ NO SE BORRA LA FUNCIÓN: sigue impidiendo que se escriba un `manager_id` que no
    corresponde a ningún empleado. La FK `empleados_manager_id_fkey` ya lo garantiza a nivel base,
    pero fallaría con un error crudo de Postgres en vez de un AppError legible.

    El guard de nulo vive acá (no en los call sites): manager_id None = "sin superior", caso
    válido que no valida nada.

    Args:
        repo: EmpleadoRepo (o doble de test).
        manager_id: superior candidato (UUID o str). None = no hay nada que validar.

    Raises:
        AppError: MANAGER_NOT_FOUND (404) si el superior no existe.
    """
    if manager_id is None:
        return
    if not repo.find_by_id(str(manager_id), None):  # None = búsqueda global, a propósito (ver arriba)
        raise AppError("Superior no encontrado", "MANAGER_NOT_FOUND", 404)


def ensure_no_ciclo_manager(repo: EmpleadoRepo, empleado_id, manager_id,
                            max_saltos: int = 50) -> None:
    """Lanza MANAGER_CICLO (400) si asignar `manager_id` como superior de `empleado_id` crea una
    jerarquía circular. Sube por la cadena de managers del candidato (find_by_id); si en algún
    salto se llega al propio empleado, hay ciclo — incluye la auto-referencia (manager == empleado).
    `max_saltos` es la red contra datos ya corruptos: si la cadena no termina, se asume ciclo.

    🔴 EL RECORRIDO ES GLOBAL, SIN ACOTAR POR EMPRESA — y esto ARREGLA UN BUG, no lo introduce.

    Hasta el 2/8/2026 el caller le pasaba el `empresa_id` del request y cada salto consultaba
    `find_by_id(actual, empresa_id)`. Con una cadena que cruza empresas, el primer salto fuera de
    la empresa devolvía `None` y la función caía por la rama `nodo is None` → **retornaba "no hay
    ciclo"**. O sea que un ciclo A(empresa 1) → B(empresa 2) → A **no se detectaba**, y un ciclo
    entre empresas cuelga `ids_subordinados` exactamente igual que uno interno.

    Bajo la regla vieja una cadena cruzada era dato CORRUPTO y acotar el recorrido tenía sentido
    (el docstring anterior lo decía: "evita que una cadena cruzada altere el veredicto"). Con la
    decisión de superior cruzado (ver `ensure_manager_valido`) esa cadena es dato LEGÍTIMO, así que
    acotarla es justamente lo que deja pasar el ciclo. `max_saltos` gana importancia: el grafo
    global es más grande que el de una empresa, y sigue siendo el corte duro.

    Args:
        repo: EmpleadoRepo (o doble de test).
        empleado_id: empleado al que se le quiere asignar el superior.
        manager_id: superior candidato. None = no hay nada que validar.
        max_saltos: tope de saltos antes de asumir ciclo (red contra datos ya corruptos).

    Raises:
        AppError: MANAGER_CICLO (400) si la asignación cierra un circuito.
    """
    if manager_id is None:
        return
    emp = str(empleado_id)
    actual: Optional[str] = str(manager_id)
    for _ in range(max_saltos):
        if actual == emp:
            raise AppError("El superior asignado genera una jerarquía circular", "MANAGER_CICLO", 400)
        nodo = repo.find_by_id(actual, None)  # None = global: un ciclo cruzado también es ciclo
        if nodo is None or nodo.manager_id is None:
            return
        actual = str(nodo.manager_id)
    raise AppError("El superior asignado genera una jerarquía circular", "MANAGER_CICLO", 400)
