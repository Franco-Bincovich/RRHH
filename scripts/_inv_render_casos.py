"""
El markdown de la sección 5 (los casos declarados) y del bloque de endpoints sin caller.

Vive aparte de `_inv_render` por la misma frontera que separa las listas del documento: arriba
van las TRES LISTAS DERIVADAS —endpoints, pantallas, acciones—, que se descubren recorriendo el
código; acá van las AFIRMACIONES, que no se descubren recorriendo nada y por eso llevan su origen
escrito al lado. Son dos maneras distintas de saber que algo hay que probarlo.
"""
from typing import Dict, List, Tuple

from _inv_casos import BUGS_DEL_RECORRIDO, Caso, brechas_de_diseno, decisiones_visuales
from _inv_render import _c


def tabla_casos(casos: List[Caso]) -> List[str]:
    verificadas, no_verif = decisiones_visuales()
    brechas = brechas_de_diseno()
    out = [
        "## 5 — Los casos que ya sabemos que hay que probar", "",
        "No salen de recorrer la superficie: son **afirmaciones sobre el comportamiento**, y si "
        "no están escritas no están. Los conteos se miden contra el código.", "",
        "| Familia | Qué probar | Origen | Casos | ¿Automatizable? | Reserva |",
        "|---|---|---|---:|---|---|",
    ]
    for c in casos:
        out.append(f"| **{_c(c.familia)}** | {_c(c.que_probar)} | {_c(c.origen)} | {c.cuantos} | "
                   f"{c.automatizable} | {_c(c.motivo)} |")
    out += ["", "### Los cuatro bugs abiertos del recorrido", "",
            "| Bug | Dónde mirar |", "|---|---|"]
    out += [f"| {_c(q)} | {_c(d)} |" for q, d in BUGS_DEL_RECORRIDO]
    out += ["", "### Sistema de diseño §2 y §3, punto por punto", "",
            f"**{len(verificadas)}** decisiones las verifica `decisionesVisuales.test.ts` por "
            "clase CSS contra el primitivo donde viven, con su cita del documento. Se listan "
            "acá para que el recorrido manual no las repita.", "",
            "| § | Decisión | La cubre un barrido |", "|---|---|---|"]
    out += [f"| {s} | {_c(q)} | sí |" for s, q in verificadas]
    out += [f"| {s} | {_c(q)} | **no — declarada no verificable desde el código** |"
            for s, q in no_verif]
    out += ["", "#### 🔴 Las dos que NO están construidas", "",
            "Medidas contra el código en esta corrida. Las dos son **invisibles para el barrido "
            "de decisiones visuales**, y por el mismo motivo estructural: ese barrido verifica "
            "que una clase esté donde la decisión dice, y prohíbe el vidrio fuera de donde §2 lo "
            "permite. Ninguna de sus dos preguntas puede ver una decisión que **no se construyó "
            "en ningún lado**.", "",
            "| Qué falta | Evidencia | Qué dice §2 |", "|---|---|---|"]
    out += [f"| **{_c(q)}** | {_c(e)} | «{_c(cita)}» |" for q, e, cita in brechas]
    return out + [""]


def bloque_sin_caller(sin_caller: Dict[Tuple[str, str], str]) -> List[str]:
    out = ["## Endpoints declarados sin caller en el front", "",
           "Importados de `backend/tests/test_callers_huerfanos.py`, no copiados: ese barrido ya "
           "los mantiene vivos en las dos direcciones (una excepción que consigue caller da rojo, "
           "una que apunta a una ruta borrada también).", "",
           "| Endpoint | Razón / disparador de salida |", "|---|---|"]
    for (m, p), razon in sorted(sin_caller.items(), key=lambda x: x[0][1]):
        out.append(f"| `{m} {p}` | {_c(razon)} |")
    return out + [""]
