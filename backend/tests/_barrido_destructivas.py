"""
Motor del barrido de auditoría de escrituras DESTRUCTIVAS. HELPER, no test (molde:
`_barrido_auditoria.py`, del que reusa el grafo de llamadas entero).
El test que lo consume es `test_auditoria_destructivas.py`.

🔴 POR QUÉ HACE FALTA UN SEGUNDO BARRIDO DE AUDITORÍA Y NO ALCANZA CON `test_auditoria_coherente`.
Aquél toma como ALCANCE **los archivos que YA emiten al menos un evento** y le exige a cada uno
cubrir todas sus escrituras. Es una regla con fuente de verdad —si un módulo audita el alta y no
la edición, eso es olvido— pero tiene un punto ciego exacto: **un módulo que no emite NINGÚN
evento queda afuera por construcción, y ese es justamente el peor caso.**

No es hipotético. `/objetivos` estuvo así hasta el 24/8/2026: borrado FÍSICO desde la UI, con
CASCADE sobre los subobjetivos, y cero eventos. Un objetivo real de Karstec desapareció entre el
17/8 y el 24/8 y no se puede saber quién ni cuándo. El módulo ni siquiera figuraba como agujero:
tenía UN evento —el del import de Excel— pero lo emitía `objetivos_import_service.py`, otro
archivo, así que el CRUD seguía sin entrar al alcance y el barrido seguía en verde.
(El encabezado de `services/_audit_payloads_objetivos_import.py` ya lo había anticipado por
escrito, meses antes. Estaba dicho y no había nada que lo hiciera fallar.)

═══════════════════════════════════════════════════════════════════════════════════════════
EL EJE, Y POR QUÉ ESTE Y NO "TODA ESCRITURA AUDITA"
═══════════════════════════════════════════════════════════════════════════════════════════
`test_auditoria_coherente` explica por qué la regla amplia no sirve: no existe una fuente de
verdad de qué entidades deben auditarse —es una definición de producto que nadie tomó— y con la
regla amplia **60 escrituras** quedarían en un limbo cuya lista de excepciones diría "no sé", que
es basura que nadie limpia y que tapa el próximo caso.

Este barrido no la contradice: le cambia el eje a uno que **sí tiene fuente de verdad en el
código**, y es el que el incidente demostró que importa.

    Un DELETE FÍSICO es irreversible. Después no hay fila que mirar.

Esa es la diferencia dura, y no una preferencia: una baja LÓGICA (`activo=False`, lo que hacen
`clientes`, `areas` y `capacitaciones`) deja el registro y su historia; un `DELETE` de PostgREST
no deja nada, y si la FK es `ON DELETE CASCADE` se lleva además filas que nadie nombró. Para esas
escrituras el evento de auditoría **no es trazabilidad: es el único registro que va a existir**.

Medido al escribirlo (24/8/2026): **12 métodos de repo** hacen un delete físico y **28 sitios**
de `services/` los invocan. De esos 28, 10 ya auditaban y 18 no — o sea que la lista de
declaraciones es un inventario real y acotado, no un "no sé" de 60 entradas. Ese fue el criterio
para elegir este eje: se midió ANTES de escribir el test.

⚠️ HEREDA EL LÍMITE CONOCIDO DE SU HERMANO, y hay que leerlo igual: la cobertura se resuelve por
el grafo de llamadas, así que **un ancestro que audita OTRA cosa da la escritura por cubierta**.
Es generoso en la dirección peligrosa (sub-reporta). Cerrarlo pide que el payload declare la
tabla que toca, cosa que hoy no hace. Este barrido cubre la omisión TOTAL, que es la que se cobró
el objetivo de Karstec.
"""
import ast
from functools import lru_cache
from pathlib import Path
from typing import List, Set, Tuple

from tests._barrido_auditoria import _arboles, _cubierto, _funciones

_BACKEND = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def metodos_destructivos() -> Set[str]:
    """Nombres de métodos de `repositories/` que ejecutan un DELETE FÍSICO.

    🔑 SE INDEXA POR NOMBRE DE MÉTODO, no por `Clase.metodo`, y es a propósito. Los write paths
    extraídos por límite de líneas reciben el repo como PARÁMETRO SIN ANOTAR (`repo.delete(...)`),
    así que su clase no se puede resolver — `_barrido_auditoria` lo declara como límite y reporta
    `<param>.metodo` en vez de adivinar. Indexar por nombre es lo que hace que esos sitios entren
    igual. El costo es que un método llamado `delete` en un repo NO destructivo también entraría;
    hoy los 12 nombres son todos de borrado real, y si algún día uno colisiona, la declaración con
    su razón es el lugar donde se dice.

    ⚠️ `.delete()` es el verbo de PostgREST. Un `update({"activo": False})` NO cae acá, y eso es
    exactamente el punto: la baja lógica deja la fila.
    """
    out: Set[str] = set()
    for arch, arbol in _arboles().items():
        if not arch.startswith("repositories/"):
            continue
        for node in ast.walk(arbol):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == "delete" for n in ast.walk(node)):
                out.add(node.name)
    return out


@lru_cache(maxsize=1)
def call_sites() -> List[Tuple[str, str, str, bool]]:
    """`(archivo, qual, repo.metodo, cubierto)` de cada sitio de `services/` que borra físico."""
    destructivos = metodos_destructivos()
    out = []
    for clave, f in sorted(_funciones().items()):
        if not f.archivo.startswith("services/"):
            continue
        for esc in sorted(f.escrituras):
            if esc.split(".", 1)[1] in destructivos:
                out.append((f.archivo, f.qual, esc, _cubierto(clave)))
    return out


def sin_auditar() -> List[Tuple[str, str, str]]:
    """Los que borran físico y NO emiten ningún evento, ni ellos ni ningún ancestro."""
    return [(a, q, e) for a, q, e, ok in call_sites() if not ok]
