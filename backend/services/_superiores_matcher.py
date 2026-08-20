"""
NÚCLEO COMPARTIDO del matcheo de superiores: de "APELLIDO, NOMBRE" a `manager_id`.

🔴 EXISTE PARA QUE HAYA UN SOLO MATCHEO, NO DOS. Lo usan dos entradas distintas:
  · el import de nómina (`_nomina_superiores`), sobre las filas del CSV recién escritas;
  · el botón "resolver pendientes" (`superiores_pendientes_service`), sobre lo que quedó
    guardado en `empleado_superior_pendiente`.
Si cada una tuviera su propia resolución, se separarían sin avisar: el import diría "ambiguo" y
el botón "resuelto" sobre los mismos datos, o al revés. Es el patrón que este repo ya pagó caro
con los filtros duplicados front/back — misma regla escrita dos veces diverge, siempre.

## Los criterios (los mismos del import de evaluaciones)
Clave de identidad = `clave_identidad` (trim + colapsa espacios + sin acentos + casefold). Se
IMPORTA de `_evaluacion_import_transforms`, no se copia: son los dos únicos imports del sistema
que cruzan personas por nombre, y dos normalizaciones que se separen darían dos criterios.

  `resuelto`      → exactamente UN empleado con ese apellido+nombre.
  `ambiguo`       → más de uno. NO se elige: queda pendiente para revisión humana.
  `sin_candidato` → ninguno.

🔴 CERO MATCHEO DIFUSO POR SIMILITUD. Un apellido parecido le asignaría el equipo de otra persona
a un mando medio — y desde el 2/8/2026 eso es acceso de LECTURA Y ESCRITURA sobre gente de
cualquier empresa del grupo (ver `services/_alcance_mandos.py`). El costo de no adivinar es un
pendiente que alguien resuelve a mano; el de adivinar mal, una fuga silenciosa.
"""
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from repositories._empleado_lookup_repo import indice_por_nombre
from schemas.empleado import EmpleadoUpdate
from services._empleados_manager import ensure_no_ciclo_manager
from services._evaluacion_import_transforms import clave_identidad
from utils.errors import AppError
from utils.logger import logger


def clave(apellido: Optional[str], nombre: Optional[str]) -> str:
    """La clave de cruce de un superior. Única fuente: los dos callers la usan para anotar."""
    return clave_identidad(apellido or "", nombre or "")


def resolver(anotados: List[dict], repo) -> Tuple[List[str], List[dict]]:
    """Resuelve y escribe los `manager_id` que dan un candidato único.

    Args:
        anotados: dicts con al menos `empleado_id`, `empresa_id` y `clave`. Cualquier otra clave
            (nº de fila, nombre del empleado…) se ARRASTRA sin tocar hasta el pendiente, para que
            cada caller arme su propio reporte sin que este módulo conozca sus schemas.
        repo: EmpleadoRepo (o doble).

    Returns:
        `(ids_resueltos, pendientes)`. Cada pendiente es el anotado original + `motivo`.
    """
    if not anotados:
        return [], []

    indice = _indice()
    resueltos, pendientes = [], []
    for a in anotados:
        candidatos = indice.get(a["clave"], [])
        if not candidatos:
            pendientes.append({**a, "motivo": "no hay ningún colaborador cargado con ese nombre"})
        elif len(candidatos) > 1:
            pendientes.append({**a, "motivo": f"{len(candidatos)} empleados con ese nombre: hay que elegir cuál"})
        else:
            motivo = _escribir(repo, a, candidatos[0])
            (pendientes.append({**a, "motivo": motivo}) if motivo
             else resueltos.append(a["empleado_id"]))
    logger.info("Superiores resueltos", extra={"resueltos": len(resueltos),
                                               "pendientes": len(pendientes)})
    return resueltos, pendientes


def _indice() -> Dict[str, List[str]]:
    """clave de identidad → ids de empleado. UNA query para todo el lote, nunca una por fila.

    Un homónimo produce una lista de más de uno, que es lo que dispara `ambiguo`: el índice NO
    desempata, solo cuenta. Y NO se acota por empresa — el porqué (y el costo) en
    `_empleado_lookup_repo.indice_por_nombre`."""
    indice: Dict[str, List[str]] = {}
    for r in indice_por_nombre():
        indice.setdefault(clave_identidad(r["apellido"], r["nombre"]), []).append(r["id"])
    return indice


def _escribir(repo, a: dict, manager_id: str) -> Optional[str]:
    """Escribe el `manager_id`. Devuelve None si salió bien, o el motivo del pendiente.

    🔴 CHEQUEO DE CICLOS EXPLÍCITO. Este camino NO pasa por `EmpleadoService.update_empleado`
    —que lo haría solo— por dos razones: emitiría un evento de auditoría por empleado (contra la
    regla "un evento por lote", y encima duplicado para las filas que ya emitieron el suyo en la
    primera pasada del import), y revalidaría área y legajo que el import ya validó. Al saltearlo
    hay que traer a mano lo único que sí hace falta: los ciclos. El recorrido es GLOBAL, cruza
    empresas — ver `ensure_no_ciclo_manager`, donde está el bug que eso arregló.
    `ensure_manager_valido` NO hace falta: el candidato salió de la tabla de empleados hace tres
    líneas, así que su existencia no es un supuesto.

    El chequeo va ANTES de cada escritura y consulta la base, así que ve los `manager_id` que
    esta misma pasada acaba de escribir: dos filas que se apuntan mutuamente no pueden colarse.

    Best-effort por fila, como el resto de los colaboradores del import: un fallo puntual queda
    como pendiente con su motivo y no aborta los demás. Los empleados ya están cargados; perder
    un `manager_id` es recuperable con el botón de pendientes, perder el resto del lote no.

    ⚠️ El UPDATE lleva la empresa DEL EMPLEADO (`a["empresa_id"]`), nunca la de un header:
    aplicación directa de Vista vs Acción.
    """
    try:
        ensure_no_ciclo_manager(repo, a["empleado_id"], manager_id)
        repo.update(a["empleado_id"], EmpleadoUpdate(manager_id=UUID(manager_id)),
                    UUID(a["empresa_id"]))
        return None
    except AppError as exc:
        if exc.code == "MANAGER_CICLO":
            return "asignarlo generaría una jerarquía circular"
        return f"no se pudo guardar: {exc.message}"
    except Exception as exc:  # noqa: BLE001 — una fila no tumba la resolución de las demás
        logger.warning("No se pudo asignar el superior", extra={
            "empleado_id": a["empleado_id"], "error": str(exc)})
        return "no se pudo guardar (error inesperado)"
