"""
🔴 LA ÚNICA EXCEPCIÓN A LA BARRERA DE EMPRESA DE LA FASE 2. Leer entero antes de copiar nada.

En todo el resto del sistema rige la regla de la Fase 2: toda consulta filtra por empresa, y un
recurso de otra empresa da el mismo 404 que uno inexistente. Acá vive la ÚNICA excepción, y está
concentrada en un módulo propio justamente para que se lea como lo que es —una excepción con
nombre y motivo— y no como un patrón que el próximo módulo pueda copiar sin entender por qué.

## La decisión (producto, 2/8/2026)

UN EMPLEADO PUEDE TENER SUPERIOR DE OTRA EMPRESA DEL GRUPO. Para `mandos_medios`, el `manager_id`
REEMPLAZA al filtro de empresa: sus subordinados son suyos sin importar de qué empresa sean, en
LECTURA y en ESCRITURA.

**Qué la justifica:** el `manager_id` es un vínculo MÁS FUERTE que la empresa. La empresa dice de
qué sociedad cobra alguien; el `manager_id` dice quién responde ante quién — que es exactamente la
pregunta que el ownership contesta. Un mando que no puede ver las vacaciones de alguien que le
reporta no puede hacer su trabajo, y qué sociedad factura a esa persona no cambia el hecho de que
le reporta. Por eso acá la empresa cede, y solo acá.

## Cómo funciona (y por qué NO toca `_ownership_filter.py`)

La intersección empresa ∩ ownership NO ocurre dentro de `_ownership_filter`: ocurre en el WHERE del
repo, como DOS PREDICADOS INDEPENDIENTES —`.eq("empresa_id", …)` y `.in_("empleado_id", ids)`—. Y el
conjunto de ownership YA ES CIEGO A LA EMPRESA: `EmpleadoOwnershipRepo.ids_subordinados` es un
`.eq("manager_id", …)` pelado, sin `empresa_id`. O sea que para obtener la semántica pedida no hay
que cambiar cómo se calcula el ownership: alcanza con NO mandarle el `empresa_id` al repo.

Por eso `_ownership_filter.py` —el archivo más delicado del repo, del que dependen 13 endpoints— y
su contrato de la tupla `(ids, vacio)` quedan intactos.

## 🔴 LA INVARIANTE DE LA QUE DEPENDE TODO ESTO

> Para `rol == "mandos_medios"`, el ownership NUNCA puede resolver a "sin restricción"
> (`empleado_ids is None` con `vacio=False`).

Hasta el 2/8/2026, si eso pasaba, el `.eq("empresa_id")` del repo igual acotaba al mando a su
empresa: un bug feo pero CONTENIDO. Al sacar ese `.eq`, `(None, False)` deja de significar "veo
toda mi empresa" y pasa a significar **"veo la tabla entera de todas las empresas"**.

Hoy la invariante se cumple por construcción (`ownership.ids_empleados_visibles` devuelve `None`
solo en la rama de admin/gerencia; para `mandos_medios` siempre devuelve una lista, como mínimo
`[su_propio_id]`, y `_ownership_filter` mete esa lista en `conjuntos`, lo que vuelve inalcanzable
su `return None, False`). Pero eso es una propiedad de DOS archivos que este módulo no controla.

Por eso `alcance_listado` NO se limita a documentarla: **la verifica y falla cerrado**. Y por eso
los dos pasos —soltar la empresa y chequear la invariante— viven en la MISMA función: no se puede
obtener el `empresa_id` aflojado sin pasar por el chequeo. Es la parte "por construcción" que un
test solo no puede dar.

## Lo que esta excepción NO afloja

  1. **Los demás roles.** `admin_rrhh` y `gerencia_lectura` siguen recibiendo el `empresa_id` del
     header tal cual. `empresa_efectiva` es la identidad para ellos.
  2. **Las demás secciones.** `mandos_medios` solo llega a VACACIONES y AUSENCIAS
     (`utils.permisos.MANDOS_MEDIOS_SECCIONES`); en el resto el gate de permisos lo frena con 403
     antes de cualquier consulta. ⚠️ Si algún día se agrega una sección a ese frozenset, hay que
     revisar si compone ownership: los REPORTES, por ejemplo, NO lo hacen (cero `ownership` en
     `services/reportes/`), así que ahí soltar la empresa devolvería datos org-wide.
  3. **El ownership mismo.** Sigue siendo la restricción; de hecho pasa a ser la ÚNICA. Un
     `manager_id` mal escrito ya no tiene una segunda red detrás, que es el motivo por el que el
     import resuelve superiores de forma conservadora (sin fuzzy, lo ambiguo queda pendiente).
"""
from typing import List, Optional, Tuple

from services._ownership_filter import resolver_empleado_ids
from utils.logger import logger

# Comparación literal, mismo patrón que `utils.permisos.puede()` y `services.ownership`: un rol
# nuevo que no sea exactamente este string no entra a la excepción (default seguro).
ROL_MANDOS_MEDIOS = "mandos_medios"


def empresa_efectiva(empresa_id, rol: Optional[str]):
    """La empresa que gobierna esta operación: `None` para `mandos_medios`, el header para el resto.

    `None` ya significa "sin filtro de empresa" en todos los repos (es la vista consolidada,
    semántica de `get_empresa_id`), así que devolverlo saca el `.eq("empresa_id")` de la query sin
    tocar una sola línea de repositorio.

    Se usa en los caminos POR FILA (`find_by_id`, `ensure_empleado_visible`, los write paths), donde
    la invariante de `alcance_listado` no aplica: ahí el ownership entra por
    `ownership.puede_gestionar_empleado`, que para `mandos_medios` nunca devuelve True
    incondicionalmente (su `return True` está detrás de `visibles is None`, la rama de
    admin/gerencia). Así que soltar la empresa deja el ownership como única barrera, y esa barrera
    es fail-closed por construcción.

    Args:
        empresa_id: la empresa activa del request (`get_empresa_id`). None = consolidado.
        rol: rol canónico del usuario. Desconocido/None → NO entra a la excepción.

    Returns:
        None si el rol es `mandos_medios`; `empresa_id` sin tocar en cualquier otro caso.
    """
    return None if rol == ROL_MANDOS_MEDIOS else empresa_id


def alcance_listado(user_id: str, rol: Optional[str], empresa_id, area_id, empleado_id,
                    ownership_repo, proyecto_ids=None,
                    ) -> Tuple[Optional[object], Optional[List[str]], bool]:
    """Resuelve de una sola vez los DOS ejes de un listado: `(empresa, empleado_ids, vacio)`.

    Existe como una sola función —en vez de llamar a `empresa_efectiva` y a `resolver_empleado_ids`
    por separado en cada service— porque el chequeo de la invariante tiene que ser INSALTEABLE. Ver
    el encabezado del módulo: soltar la empresa sin verificar que el ownership restringe de verdad
    es el único camino por el que este cambio devolvería datos de todas las empresas.

    `empleado_ids`/`vacio` conservan EXACTAMENTE el contrato de la tupla de `_ownership_filter`
    (⚠️ el `None` significa dos cosas opuestas según `vacio`) — esta función no lo reinterpreta,
    solo puede convertir un caso en el fail-closed `(None, True)`, nunca al revés.

    Args:
        user_id: UUID (str) del usuario logueado.
        rol: rol canónico (ver ROLES_VALIDOS en utils.permisos).
        empresa_id: empresa activa del request, ANTES de aplicar la excepción.
        area_id: filtro de área opcional.
        empleado_id: filtro de empleado puntual opcional.
        ownership_repo: EmpleadoOwnershipRepo (o doble).
        proyecto_ids: empleados del proyecto ya resueltos por el caller (None = sin filtro).

    Returns:
        `(empresa, empleado_ids, vacio)`. `empresa` es lo que hay que pasarle al repo.
    """
    empresa = empresa_efectiva(empresa_id, rol)
    empleado_ids, vacio = resolver_empleado_ids(
        user_id, rol, empresa, area_id, empleado_id, ownership_repo, proyecto_ids)

    # 🔴 EL CHEQUEO DE LA INVARIANTE. Si el ownership de un mando resolviera a "sin restricción",
    # con la empresa ya soltada la consulta traería la tabla entera de TODAS las empresas. No puede
    # pasar hoy (ver el encabezado), y si algún día pasara es un bug de otro archivo, no un caso a
    # contemplar: se corta acá, vacío. Un listado de más es un incidente; uno de menos, un reclamo.
    if rol == ROL_MANDOS_MEDIOS and not vacio and empleado_ids is None:
        logger.error(
            "Ownership de mandos_medios resolvió a 'sin restricción' — invariante rota, se corta vacío",
            extra={"user_id": user_id, "area_id": str(area_id) if area_id else None})
        return empresa, None, True

    return empresa, empleado_ids, vacio
