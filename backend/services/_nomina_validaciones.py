"""
Guardas previas a la escritura de una fila del import de nómina: obligatorios, resolución de
empresa/área y dedup INTRA-ARCHIVO por DNI y por legajo.

Extraído de `nomina_empleados_service.py`, que llegó a 145 contra un límite de 150 y no admitía
la pieza de superiores (`_nomina_superiores.py`) sin pasarse. La lógica se movió VERBATIM: mismos
mensajes de `ValueError`, mismo orden de chequeos, mismas claves de dedup.

Molde: `_vacaciones_write.crear(...)` — función libre que recibe los colaboradores por parámetro,
en vez de una clase con estado propio como `_nomina_proyectos`/`_nomina_cesiones`. Acá la forma no
es estética: los tests del import construyen el service con `__new__` y le setean `_catalogos`,
`_seen_dni` y `_seen_legajo` a mano (`test_nomina_fix_chico.py`, `test_nomina_presupuesto.py`), así
que mudar ese estado a un objeto nuevo rompería dos archivos de test sin ninguna ganancia.

🔴 EL DEDUP ES CONTRA EL ARCHIVO, NO CONTRA LA BASE — y es la razón de que estos dos sets existan.
`ensure_legajo_unico` (y el dedup por DNI del repo) validan contra lo YA PERSISTIDO: dos filas del
MISMO CSV con el mismo DNI o legajo pasan las dos, porque ninguna está en la base todavía, y la
segunda revienta en el INSERT con el error crudo de `empleados_legajo_empresa_key`, que llega al
usuario como texto de Postgres en vez de un motivo legible. Estos sets convierten ese caso en un
"no cargado" con explicación.
"""
from typing import Set, Tuple

from services import _nomina_empleados_transforms as tx


def validar_y_resolver(f: dict, catalogos, seen_dni: Set[tuple],
                       seen_legajo: Set[tuple]) -> Tuple[str, str]:
    """Valida la fila ya parseada y devuelve `(empresa_id, area_id)` resueltos.

    Los tres motivos de rechazo salen por `ValueError` con el texto listo para el reporte: el
    caller (`_procesar_fila`) no los distingue, los pasa tal cual a `lote.registrar_fallo`.

    ⚠️ MUTA `seen_dni`/`seen_legajo`: la fila que pasa queda anotada, para que la siguiente con la
    misma clave se rechace. Es el efecto buscado —los sets son el estado del lote, no una copia—,
    y por eso llegan por parámetro en vez de crearse acá adentro.

    El orden importa: los obligatorios PRIMERO, porque `empresa_id`/`area_id` se resuelven contra
    `f["_empresa"]`/`f["_area"]`, que son dos de los campos que ese chequeo exige.

    Args:
        f: fila ya parseada por `tx.parsear_fila`.
        catalogos: `NominaCatalogos` con el cache de empresa/área primado.
        seen_dni: claves `(empresa_id, dni)` ya vistas EN ESTE ARCHIVO.
        seen_legajo: claves `(empresa_id, legajo)` ya vistas EN ESTE ARCHIVO.

    Returns:
        `(empresa_id, area_id)` como str.

    Raises:
        ValueError: falta un obligatorio, o el DNI/legajo ya apareció en una fila previa.
    """
    faltan_oblig = tx.obligatorios_faltantes(f)
    if faltan_oblig:
        raise ValueError(f"falta {', '.join(faltan_oblig)}")

    empresa_id = catalogos.empresa_id(f["_empresa"])
    area_id = catalogos.area_id(empresa_id, f["_area"])

    clave = (empresa_id, f["dni"])
    if clave in seen_dni:
        raise ValueError("DNI duplicado dentro del archivo (fila previa ya procesada)")
    seen_dni.add(clave)

    if f["legajo"]:
        clave_legajo = (empresa_id, f["legajo"])
        if clave_legajo in seen_legajo:
            raise ValueError("Legajo duplicado dentro del archivo (fila previa ya procesada)")
        seen_legajo.add(clave_legajo)

    return empresa_id, area_id
