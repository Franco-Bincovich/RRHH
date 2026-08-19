"""
Matcheo del "Colaborador" del Excel de Formación contra el padrón de la empresa, y la detección
de pares de nombres sospechosamente parecidos.

Molde: `ResolutorIdentidad` de evaluaciones — MISMA normalización (se importa `normalizar_campo`
en vez de reescribirla: dos normalizaciones que diverjan harían que el mismo nombre matchee en
un import y no en el otro) y el mismo principio: **NADA de fuzzy para ASIGNAR** — un apellido
parecido le colgaría la formación a la persona equivocada. Las diferencias con evaluaciones, y
por qué esto no lo reusa directamente:
  · el Excel no separa apellido de nombre: trae UNA celda, y el archivo real mezcla los DOS
    órdenes ("Alarcon Valentina" arriba, "Agustin Romero" abajo). El índice indexa cada empleado
    por los dos órdenes y el matcheo prueba la celda tal cual.
  · no hay señal de superior para desempatar: dos empleados con el mismo nombre → ambiguo →
    nombre_libre con aviso. Nunca se elige uno al azar.

El fuzzy SÍ existe pero SOLO PARA AVISAR (`pares_parecidos`): reporta pares de nombres crudos
distintos que probablemente sean la misma persona — el caso real del archivo es
"Pesce Morela"/"Morella Pesce": invertida Y con una letra distinta, así que si una matchea y la
otra no, la misma persona queda una vez vinculada y una vez suelta. El import no decide: RRHH
decide con los dos nombres a la vista.
"""
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from services._evaluacion_import_transforms import normalizar_campo

# Umbral del aviso de parecidos: distancia de edición sobre la forma canónica (tokens
# ordenados). 2 cubre una letra doble o un typo sin disparar sobre apellidos cortos distintos;
# el piso de largo evita comparar "gomez" contra "gome" como si fuera señal.
_DISTANCIA_MAXIMA = 2
_LARGO_MINIMO = 8


class IndiceEmpleados:
    """Padrón indexado por nombre normalizado EN LOS DOS ÓRDENES."""

    def __init__(self, empleados: List[dict]) -> None:
        """`empleados`: filas con id, nombre y apellido (lo que da `empleados_por_empresa`)."""
        self._por_clave: Dict[str, set] = {}
        self._visible: Dict[str, str] = {}
        for e in empleados:
            eid = str(e["id"])
            self._visible[eid] = f"{e['nombre']} {e['apellido']}"
            for clave in (normalizar_campo(f"{e['apellido']} {e['nombre']}"),
                          normalizar_campo(f"{e['nombre']} {e['apellido']}")):
                self._por_clave.setdefault(clave, set()).add(eid)

    def resolver(self, crudo: str) -> Tuple[Optional[str], Optional[str]]:
        """(empleado_id, None) si matchea UNO solo; (None, motivo) si no.

        El ambiguo NO elige: dos homónimos en el padrón hacen que la celda vaya a nombre_libre
        con su aviso, igual que el estado 'ambiguo' de evaluaciones (ahí lo desempata el
        superior; acá no hay señal con qué)."""
        ids = self._por_clave.get(normalizar_campo(crudo), set())
        if len(ids) == 1:
            return next(iter(ids)), None
        if not ids:
            return None, "sin candidato en el padrón"
        return None, "más de un empleado con ese nombre"

    def nombre_visible(self, empleado_id: str) -> Optional[str]:
        return self._visible.get(str(empleado_id))


def _canonica(crudo: str) -> str:
    """Forma insensible al ORDEN: tokens normalizados y ordenados. "Matias Cattaneo" y
    "Cattaneo Matias" colapsan a la misma; una letra de diferencia queda a distancia 1."""
    return " ".join(sorted(normalizar_campo(crudo).split()))


def _distancia(a: str, b: str) -> int:
    """Levenshtein clásico por filas. Los nombres canónicos miden <40 chars: O(n·m) es nada."""
    if a == b:
        return 0
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def pares_parecidos(nombres: List[str], resueltos: Dict[str, Optional[str]]) -> List[Tuple[str, str, str]]:
    """Pares de nombres CRUDOS distintos que probablemente sean la misma persona.

    `resueltos`: nombre crudo → empleado_id (o None). Un par donde LOS DOS resolvieron al MISMO
    empleado no se reporta — el matcheo por los dos órdenes ya los unificó y no hay nada que
    decidir. Todo lo demás con forma canónica igual o a distancia ≤ 2 sale con su motivo,
    aunque no se pueda decidir: decide RRHH.
    """
    avisos: List[Tuple[str, str, str]] = []
    for a, b in combinations(sorted(set(nombres)), 2):
        ra, rb = resueltos.get(a), resueltos.get(b)
        if ra is not None and ra == rb:
            continue
        ca, cb = _canonica(a), _canonica(b)
        if ca == cb:
            avisos.append((a, b, "mismo nombre con el orden o la caja cambiados"))
        elif min(len(ca), len(cb)) >= _LARGO_MINIMO and _distancia(ca, cb) <= _DISTANCIA_MAXIMA:
            avisos.append((a, b, "difieren en una o dos letras: probable typo de la misma persona"))
    return avisos
