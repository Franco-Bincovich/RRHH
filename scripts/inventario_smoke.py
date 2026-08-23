#!/usr/bin/env python3
"""
GENERA `docs/INVENTARIO-SMOKE.md`: todo lo que hay que probar, y qué se puede probar solo.

    backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py
    backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py --verificar   # no escribe

🔴 SE GENERA, NO SE ESCRIBE. Un inventario a mano se desactualiza en la primera tanda y después
MIENTE, que es peor que no tenerlo: se lee como cobertura y es una foto vieja. Este repo ya pagó
ese modo de falla cinco veces este mes —`MODELO_DATOS.md` describía 13 tablas que no existían—, y
la respuesta que sí funcionó fue siempre la misma: derivar del código y poner un barrido que
rojee cuando el documento se atrasa. Acá es `backend/tests/test_inventario_smoke.py`.

🔴 READ-ONLY SOBRE EL CÓDIGO. No emite un solo request, no toca la base y no importa nada que
haga IO en import-time salvo montar la app de FastAPI en memoria (que es lo que hace la suite
entera). Corre sin `.env`: usa las mismas credenciales de mentira que `backend/tests/`.

--verificar sale con código 1 si el archivo del repo no coincide con lo que se generaría, para
poder usarlo como gate sin escribir nada.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))

import _inv_render as R                                                       # noqa: E402
import _inv_render_casos as RC                                                # noqa: E402
from _inv_acciones import acciones, sin_pantalla                              # noqa: E402
from _inv_backend import declarados_sin_caller, endpoints                     # noqa: E402
from _inv_casos import casos                                                  # noqa: E402
from _inv_cobertura import veredicto                                          # noqa: E402
from _inv_destructivo import evidencia_baja_logica, verbos_desconocidos       # noqa: E402
from _inv_llamadas import llamadas_por_funcion                                # noqa: E402
from _inv_pantallas import pantallas                                          # noqa: E402

SALIDA = RAIZ / "docs" / "INVENTARIO-SMOKE.md"


def _paths_del_front():
    """(MÉTODO, path normalizado) de toda llamada que el front sabe hacer."""
    return {llamada for llamadas in llamadas_por_funcion().values() for llamada in llamadas}


def _veredictos(eps, ps, acs):
    """Conteo por lista y por veredicto, más el desglose de motivos de los endpoints."""
    from collections import Counter
    por_lista = {
        "endpoints": Counter(veredicto(e.metodo, e.path, e.solo_con_flag).automatizable
                             for e in eps),
        "pantallas": Counter(("no" if p.apagada else "sí") for p in ps),
        "acciones": Counter(a.automatizable for a in acs),
    }
    motivos = Counter((veredicto(e.metodo, e.path, e.solo_con_flag).automatizable,
                       veredicto(e.metodo, e.path, e.solo_con_flag).motivo)
                      for e in eps if veredicto(e.metodo, e.path, e.solo_con_flag).motivo)
    return {k: dict(v) for k, v in por_lista.items()}, motivos.most_common()


def generar() -> str:
    """El documento entero, como string. Ninguna cifra sale de una constante escrita a mano."""
    eps, ps, acs, ks = endpoints(), pantallas(), acciones(), casos()
    sin_caller = declarados_sin_caller()
    conteos, motivos = _veredictos(eps, ps, acs)
    lineas = R.encabezado(date.today().isoformat())
    lineas += R.resumen(eps, ps, acs, ks, conteos, motivos)
    lineas += R.tabla_endpoints(eps, _paths_del_front(), sin_caller, veredicto)
    lineas += R.tabla_pantallas(ps, veredicto)
    lineas += R.tabla_acciones(acs)
    lineas += RC.tabla_casos(ks)
    lineas += RC.bloque_sin_caller(sin_caller)
    lineas += _bloque_salud(acs)
    return "\n".join(lineas).rstrip() + "\n"


def _bloque_salud(acs) -> list:
    """Lo que la generación encontró y nadie pidió. Va EN el documento, no en la consola: un
    hallazgo que sólo aparece en la salida de un script lo lee la sesión que lo corrió y nadie más."""
    huerfanas = sin_pantalla()
    verbos = verbos_desconocidos([(m, p) for a in acs for m, p in a.endpoints])
    rotas = evidencia_baja_logica()
    out = ["## Lo que la generación encontró", "", "| Chequeo | Resultado |", "|---|---|"]
    out.append(f"| acciones cuyo componente no cuelga de ninguna pantalla ni layout | "
               f"{len(huerfanas) or '**0** — ninguna'} |")
    if huerfanas:
        out += [f"| ↳ | `{a.componente}` · `{a.funcion}` |" for a in huerfanas]
    from _inv_destructivo import BAJA_LOGICA
    out.append("| declaraciones de baja lógica que ya no se sostienen contra el código | "
               f"{', '.join(rotas) if rotas else f'**0** — las {len(BAJA_LOGICA)} siguen sanas'} |")
    out.append("| verbos de escritura sin clasificar (caen en «reversible» por default) | "
               f"{', '.join('`' + v + '`' for v in verbos) if verbos else 'ninguno'} |")
    return out + [""]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verificar", action="store_true",
                    help="no escribe: sale con 1 si el archivo del repo quedó atrás")
    ap.add_argument("--salida", type=Path, default=SALIDA)
    args = ap.parse_args()
    texto = generar()
    if args.verificar:
        actual = args.salida.read_text(encoding="utf-8") if args.salida.exists() else ""
        if actual == texto:
            print(f"OK: {args.salida.name} esta al dia.")
            return 0
        print(f"DESACTUALIZADO: {args.salida.name} no coincide con lo que el codigo dice hoy.\n"
              "Regeneralo:  backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py")
        return 1
    args.salida.write_text(texto, encoding="utf-8")
    print(f"escrito: {args.salida}  ({len(texto.splitlines())} lineas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
