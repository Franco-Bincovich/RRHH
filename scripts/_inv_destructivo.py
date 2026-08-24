"""
QUÉ DEJA EL SISTEMA CAMBIADO SIN VUELTA. Es la pregunta que decide si un tester puede apretar un
botón en producción, y vive aparte de `_inv_cobertura` a propósito: son dos preguntas distintas
sobre la misma fila —«¿se puede probar solo?» y «¿se puede deshacer?»— y sólo la segunda depende
de lo que el service hace con la fila. Mezclarlas obligaba a leer 220 líneas para cambiar un verbo.

🔴 EL DEFAULT ES «REVERSIBLE», Y POR ESO LA LISTA DE VERBOS IMPORTA. Un POST o un PUT que nadie
clasificó sale del inventario como reversible: si en realidad no lo es, el documento lo dice mal
EN SILENCIO, que es el único error que esta columna no se puede permitir. `verbos_desconocidos`
existe para que ese silencio tenga nombre.
"""
import re
from functools import lru_cache
from typing import Dict, List, Set, Tuple

from _inv_backend import BACKEND, _crudo
from _inv_baja_logica import sospechosas_de_baja_logica  # noqa: F401 — reexport


# Verbos finales de path que marcan un ACTO IRREVERSIBLE. Se indexa por el ÚLTIMO SEGMENTO y no
# por el path completo a propósito: el verbo es estable y el path no. Un `POST .../efectivizar`
# nuevo sobre otro recurso clasifica solo; un path nuevo con un verbo desconocido cae en el
# default (reversible) y el barrido de `_inv_acciones` obliga a mirarlo.
IRREVERSIBLES: Dict[str, str] = {
    "activar": "convierte un preingreso en activo; no hay endpoint que lo devuelva a preingreso",
    "contratar": "crea el legajo del candidato; no hay des-contratar",
    "efectivizar": "escribe estado='baja' y fecha_egreso en el legajo",
    "confirmar": "persiste el lote entero del import; en evaluaciones BORRA el período anterior "
                 "por CASCADE antes de escribir el nuevo",
    "eliminar": "baja en LOTE: borra varias filas de una y cada una arrastra sus hijas por "
                "CASCADE, así que un clic de más no se deshace fila por fila",
    "submit": "cierra la evaluación del token; el link queda consumido",
    "enviar": "sale un mail real a un buzón real; no se puede desenviar",
    "publicar-linkedin": "publica afuera del sistema",
    # ⚠️ NO dice "llama a Claude", que es lo que decía y era falso para 13 de los 14 tipos: sólo
    # `tipo="adhoc"` le pega a Anthropic, y está oculto del catálogo. Lo irreversible es otra
    # cosa y sigue siendo cierto: el reporte queda en el historial y no hay endpoint que lo
    # borre. Ver `_inv_cobertura._llama_a_claude`.
    "generar": "deja el reporte en el historial y no hay endpoint que lo borre",
    "revisar": "lee la casilla de Gmail y crea candidatos a partir de lo que encuentre",
}

# DELETEs que NO destruyen: la baja es LÓGICA y la fila se recupera con un update.
# 🔴 Es la ÚNICA parte del inventario declarada a mano, porque no hay señal mecánica confiable:
# el `activo=False` vive dentro del service, a dos saltos del handler, y rastrearlo por AST daba
# CERO detecciones sobre los casos reales (probado antes de escribir esto). Cada entrada
# lleva su evidencia, y el barrido verifica que la ruta siga existiendo Y que el archivo citado
# siga diciendo lo que dice.
#
# ⚠️ `/api/capacitaciones/{id}` NO ESTÁ ACÁ, y estuvo: su service dice "soft-delete si tiene
# asignaciones; hard-delete si no" (`capacitacion_service.py:86`). O sea que sobre una formación
# recién sembrada —que por definición no tiene asignaciones— **borra de verdad**, que es justo el
# caso del smoke. Una baja lógica CONDICIONAL no es una baja lógica: declararla acá haría que el
# inventario diga "reversible" precisamente en el escenario en que no lo es. Las condicionales
# se declaran en `BAJA_CONDICIONAL`, abajo.
#
# 🔴 ESTA LISTA ESTUVO CORTA Y NADIE PODÍA VERLO. Declaraba 3 y el smoke de escritura del
# 23/8/2026 encontró **2 más** borrando de verdad: `adjuntos` (`estado='eliminado'`) y `users`
# (`activo=false` + ban en Auth) salían marcados «🔴 borra la fila» y no borraban la fila. El
# barrido de entonces sólo verificaba que las 3 declaradas siguieran sanas, así que por
# construcción no podía ver las que faltaban. Ahora `sospechosas_de_baja_logica()` las descubre
# y `test_inventario_smoke.py` exige que cada una esté en UNA de las dos listas.
BAJA_LOGICA: Dict[str, Tuple[str, str]] = {
    "/api/clientes/{}": ("services/cliente_service.py", "LA BAJA ES LÓGICA"),
    "/api/perfiles-puesto/{}": ("services/perfil_puesto_service.py", "LA BAJA ES LÓGICA"),
    "/api/adjuntos/{}": ("services/adjunto_service.py", "Soft delete (estado='eliminado')"),
    "/api/usuarios/{}": ("services/usuario_service.py", "baja BLANDA y REVERSIBLE"),
    "/api/areas/{}": ("services/area_service.py", "soft delete"),
}



# Bajas lógicas CONDICIONALES: soft si la fila tiene historial, hard si no. NO entran en
# `BAJA_LOGICA` (ver arriba) pero tampoco son un descubrimiento nuevo cada vez que alguien
# corre el barrido: se declaran acá, con la misma evidencia, para que el chequeo de completitud
# las dé por clasificadas y siga marcando lo que de verdad no está declarado.
BAJA_CONDICIONAL: Dict[str, Tuple[str, str]] = {
    "/api/capacitaciones/{}": ("services/capacitacion_service.py", "hard-delete si no"),
    "/api/inventario/items/{}": ("services/inventario_items_service.py", "hard-delete si no"),
    "/api/onboarding/templates/{}": ("services/onboarding_templates_service.py",
                                     "Soft delete si tiene instancias"),
}

def _clave(path: str) -> str:
    """🔴 EL PATH SE NORMALIZA ANTES DE BUSCARLO, y sin esto la tabla MIENTE en las tres filas
    que más importan. Este módulo recibe paths de los DOS lados: del backend llegan con el nombre
    del parámetro (`/api/areas/{id}`) y del front, ya normalizados (`/api/areas/{}`). Con las
    claves sin normalizar, `deleteArea` en la sección 3 salía marcado «borra la fila» siendo una
    baja lógica declarada tres archivos más arriba — el inventario contradiciendo su propia
    declaración, en la columna que decide si el tester puede apretar el botón."""
    return re.sub(r"\{[^}]*\}", "{}", path)


def es_destructivo(metodo: str, path: str) -> Tuple[bool, str]:
    """(¿deja el sistema cambiado sin vuelta desde la UI?, por qué)."""
    verbo = path.rstrip("/").split("/")[-1]
    if verbo in IRREVERSIBLES:
        return True, IRREVERSIBLES[verbo]
    if metodo == "DELETE":
        clave = _clave(path)
        if clave in BAJA_LOGICA:
            return False, f"baja LÓGICA (activo=False) — evidencia: {BAJA_LOGICA[clave][0]}"
        return True, "borra la fila"
    return False, "un update posterior lo revierte"



@lru_cache(maxsize=1)
def evidencia_baja_logica() -> List[str]:
    """Las declaraciones de `BAJA_LOGICA` que YA NO se sostienen contra el código. Vacío = sanas."""
    rotas: List[str] = []
    todas, _, _ = _crudo()
    paths = {_clave(p) for _m, p in todas}
    for path, (archivo, marca) in BAJA_LOGICA.items():
        if path not in paths:
            rotas.append(f"{path}: la ruta ya no existe")
            continue
        fuente = BACKEND / archivo
        if not fuente.exists() or marca not in fuente.read_text(encoding="utf-8", errors="ignore"):
            rotas.append(f"{path}: {archivo} ya no dice «{marca}»")
    return rotas


def verbos_desconocidos(paths: List[Tuple[str, str]]) -> List[str]:
    """Verbos de ACCIÓN sobre un recurso que no están clasificados en `IRREVERSIBLES`.

    No es un error: es la lista de lo que hay que MIRAR. Un `POST .../archivar` nuevo cae en el
    default (reversible), y si resulta que no lo es, el inventario lo estaría diciendo mal **en
    silencio** — que es el único modo de falla que esta columna no puede permitirse.

    🔴 UN ALTA NO ES UN VERBO. `POST /api/clientes` termina en el NOMBRE DEL RECURSO, no en una
    acción: crear en una colección siempre es reversible (se borra) y no hay nada que clasificar.
    Sin ese descarte la lista daba **63 entradas**, casi todas nombres de tabla, y una lista de 63
    que nadie mira es peor que no tenerla — es la forma en que este repo ya perdió dos veces una
    lista de excepciones. Se descartan por MEDICIÓN, no por diccionario: un segmento que además
    es el primero de alguna ruta (`/api/clientes/...`) es un recurso, no un verbo.
    """
    recursos = {p.split("/")[2] for _m, p in paths if len(p.split("/")) > 2}
    recursos |= {p.split("/")[2] for _m, p in _crudo()[0] if len(p.split("/")) > 2}
    out: Set[str] = set()
    for metodo, path in paths:
        if metodo == "GET":
            continue
        seg = [s for s in path.split("/") if s]
        verbo = seg[-1]
        if verbo.startswith("{") or verbo in IRREVERSIBLES or verbo in recursos:
            continue
        # 🔴 SI HAY UN GET EN EL MISMO PATH, EL ÚLTIMO SEGMENTO ES UN SUSTANTIVO, NO UN VERBO.
        # `POST /api/onboarding/templates` crea en una colección que se lee con `GET` en ese
        # mismo path: es un alta, y un alta se deshace con su DELETE. `POST .../contratar` no
        # tiene GET hermano porque no hay nada que leer ahí — es un ACTO. Es la señal que separa
        # los dos casos sin diccionario, y baja la lista de 42 a lo que de verdad hay que mirar.
        if len(seg) >= 3 and re.fullmatch(r"[a-z][a-z-]*", verbo) and path not in _con_get():
            out.add(verbo)
    return sorted(out)


@lru_cache(maxsize=1)
def _con_get() -> Set[str]:
    """Paths que además responden un GET. Ver la nota de `verbos_desconocidos`."""
    return {p for m, p in _crudo()[0] if m == "GET"}
