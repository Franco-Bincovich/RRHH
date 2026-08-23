"""
El markdown de `docs/INVENTARIO-SMOKE.md`. Sólo formato: todo lo que afirma sale de los otros
módulos, y ninguna cifra se escribe a mano.

⚠️ EL ORDEN DE LAS COLUMNAS ES UNA DECISIÓN: "¿se puede probar automáticamente?" va SIEMPRE
última y "por qué" inmediatamente después. Un veredicto sin su motivo al lado se lee como un
juicio y no como un dato, y a la tercera lectura alguien lo cambia sin saber qué lo sostenía.
"""
import re
from typing import Dict, List, Set, Tuple

from _inv_casos import Caso

from _inv_acciones import Accion
from _inv_backend import Endpoint
from _inv_pantallas import Pantalla

_ESC = str.maketrans({"|": "\\|"})


def _c(texto: str) -> str:
    """Una celda: sin pipes sueltos y sin saltos, que rompen la tabla."""
    return " ".join(str(texto).split()).translate(_ESC)


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path)


def encabezado(fecha: str) -> List[str]:
    return [
        "# INVENTARIO-SMOKE — todo lo que hay que probar, y qué se puede probar solo",
        "",
        "> **GENERADO DESDE EL CÓDIGO. No editar a mano.**",
        "> Se regenera con `backend\\venv\\Scripts\\python.exe scripts/inventario_smoke.py`,",
        "> y `backend/tests/test_inventario_smoke.py` da ROJO si el archivo quedó atrás.",
        f"> Última generación: **{fecha}**.",
        "",
        "## Por qué existe",
        "",
        "Hay 5.700 tests y 36 barridos estructurales, y **ninguno atraviesa navegador → front →",
        "HTTP → backend → base real**: el backend se prueba contra un doble de Supabase y el",
        "front contra un backend simulado. El pegamento entre las dos mitades no lo mira nadie, y",
        "de ahí salieron el deslogueo de `/vacantes` (once días echando al usuario en cada carga),",
        "los 24 `maybe_single()` que devolvían 500 —con `POST /api/offboarding` inutilizable en",
        "producción sin que nadie lo notara— y los botones cortados en mobile.",
        "",
        "🔴 **El objetivo NO es probar todo: es que nada quede sin listar.** Cada fila dice si se",
        "puede probar automáticamente y, si no, por qué. Una fila que dice «no» con su motivo es",
        "un resultado; una fila que falta es el modo de falla que este repo ya pagó cinco veces.",
        "",
        "### Qué NO afirma este documento",
        "",
        "| No dice | Por qué |",
        "|---|---|",
        "| que la prueba EXISTA | dice si se puede escribir. Lo único que hoy corre de punta a "
        "punta es el smoke de LECTURA (`docs/SMOKE-TEST.md`), acotado a los GET |",
        "| que el resultado sea correcto | un endpoint que responde 200 con números equivocados "
        "figura igual que uno sano |",
        "| el texto de cada botón | ver la nota de alcance de la sección 3 |",
        "",
    ]


def resumen(eps: List[Endpoint], pantallas: List[Pantalla], acciones: List[Accion],
            casos: List[Caso], veredictos: Dict[str, Dict[str, int]],
            motivos: List[Tuple[str, int]]) -> List[str]:
    out = ["## Resumen", "", "| Lista | Filas | Automatizable | Sólo sobre datos sembrados | No |",
           "|---|---:|---:|---:|---:|"]
    for nombre, total, clave in (("Endpoints", len(eps), "endpoints"),
                                 ("Pantallas", len(pantallas), "pantallas"),
                                 ("Acciones de escritura", len(acciones), "acciones")):
        v = veredictos[clave]
        out.append(f"| {nombre} | {total} | {v.get('sí', 0)} | "
                   f"{v.get('sí, sólo sobre datos sembrados', 0)} | {v.get('no', 0)} |")
    out += ["", "### Los endpoints que no salen automatizables a secas", "",
            "⚠️ **`sí, sólo sobre datos sembrados` NO es lo mismo que `no`**: esas filas se "
            "prueban igual, con la semilla. Van juntas acá porque las dos exigen una decisión "
            "antes de escribir la prueba, pero la columna dice cuál es cuál.", "",
            "| ¿Automatizable? | Motivo | Endpoints |", "|---|---|---:|"]
    out += [f"| {v} | {_c(m)} | {n} |" for (v, m), n in motivos]
    out += ["", f"Y {len(casos)} familias de casos declarados (sección 5), que no se descubren "
                "recorriendo la superficie.", ""]
    return out


def tabla_endpoints(eps: List[Endpoint], del_front: Set[Tuple[str, str]],
                    sin_caller: Dict[Tuple[str, str], str],
                    veredicto) -> List[str]:
    out = [
        "## 1 — Endpoints", "",
        f"Los **{len(eps)}** que monta la app, por introspección de `app.routes` **con todos los "
        "flags encendidos**: un módulo apagado no queda exento de figurar. El gate sale del "
        "closure de `require_permission`, no de un grep del router.", "",
        "La columna **Caller** cruza contra los literales de path del front. `—declarado` "
        "significa que `tests/test_callers_huerfanos.py` ya lo tiene declarado sin caller **con "
        "su razón o su disparador de salida**, que se transcribe en la última sección.", "",
        "| # | Método | Path | Gate | Escribe | Caller | ¿Automatizable? | Por qué no |",
        "|---:|---|---|---|:-:|---|---|---|",
    ]
    for i, e in enumerate(eps, 1):
        v = veredicto(e.metodo, e.path, e.solo_con_flag)
        clave = (e.metodo, _norm(e.path))
        if clave in del_front:
            caller = "sí"
        elif (e.metodo, e.path) in sin_caller:
            caller = "**—declarado**"
        else:
            caller = "**— NO**"
        flag = " 🚩flag" if e.solo_con_flag else ""
        out.append(f"| {i} | {e.metodo} | `{e.path}`{flag} | {_c(e.gate)} | "
                   f"{'✍️' if e.escribe else '👁️'} | {caller} | {v.automatizable} | "
                   f"{_c(v.motivo)} |")
    return out + [""]


def tabla_pantallas(ps: List[Pantalla], veredicto) -> List[str]:
    out = [
        "## 2 — Pantallas", "",
        f"Las **{len(ps)}** rutas de `app/`. ⚠️ **La columna GET dice qué endpoints ALCANZA la "
        "pantalla por su grafo de imports, no qué dispara exactamente al montar**: adentro caen "
        "también los fetch de un modal que quizás no se abra. Es un superconjunto a propósito — "
        "un endpoint de más se prueba y se tacha, uno de menos no se descubre nunca.", "",
        "**Roles** sale de `RUTA_SECCION` (el mapa del AuthGuard) resuelto con "
        "`utils.permisos.puede`, que es la fuente canónica: reimplementarlo acá sería un tercer "
        "espejo de un modelo que ya tiene dos y ningún test que los compare.", "",
        "| Ruta | Sección | Roles que la ven | GET | Export | Escrituras | Filtra | Pagina | "
        "Apagada | ¿Automatizable? |",
        "|---|---|---|---:|---:|---:|:-:|:-:|---|---|",
    ]
    for p in ps:
        v = veredicto("GET", "/api/", False, p.apagada)
        roles = "todos" if len(p.roles) == 3 else ", ".join(x.replace("_", " ") for x in p.roles)
        out.append(
            f"| `{p.ruta}` | {p.seccion or '—'} | {_c(roles)} | {len(p.lecturas)} | "
            f"{len(p.exports)} | {len(p.escrituras)} | {'sí' if p.filtra else '—'} | "
            f"{'sí' if p.pagina else '—'} | {_c(p.apagada or '—')} | "
            f"{v.automatizable if p.apagada else 'sí'} |")
    return out + [""]


def tabla_acciones(acs: List[Accion]) -> List[str]:
    out = [
        "## 3 — Acciones de escritura", "",
        f"**{len(acs)}** filas. 🔴 **La unidad es «el componente que importa una función de "
        "escritura y la invoca», no «el botón»**, y la diferencia importa al leer la lista:",
        "",
        "| Se cuenta | Qué pasa |",
        "|---|---|",
        "| dos botones que llaman a la MISMA función en el mismo componente | **una** fila "
        "(sub-cuenta — es el único lado por el que esta lista se queda corta) |",
        "| un componente que llama a dos funciones distintas | **dos** filas |",
        "| `onSubmit`, `onChange` de un toggle y `onClick` | indistinguibles: los tres son "
        "«el componente llama a la función» |",
        "",
        "**Lo que NO se puede derivar del código estático:** el TEXTO del botón (vive en el JSX, "
        "muchas veces armado con un ternario sobre el estado), si el control está VISIBLE (casi "
        "todos cuelgan de `useCanWrite()`, pero también hay condiciones de estado) y si la "
        "acción es idempotente (eso es del backend). La columna dice el COMPONENTE, que es lo "
        "que un tester puede abrir y buscar.",
        "",
        "**Roles** = los de la pantalla **intersecados con `write`**: `gerencia_lectura` lee "
        "todas las pantallas, así que sin esa intersección la tabla diría que ve el botón de "
        "borrar — y el backend le contesta 403.",
        "",
        "| Pantalla | Componente | Función | Endpoint | Roles | Destructivo | ¿Automatizable? | "
        "Por qué |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in sorted(acs, key=lambda x: (x.rutas[:1], x.componente, x.funcion)):
        eps = "<br>".join(f"`{m} {p}`" for m, p in a.endpoints)
        roles = "todos" if len(a.roles) == 3 else ", ".join(x.replace("_", " ") for x in a.roles)
        out.append(
            f"| {_c(', '.join(a.rutas))} | `{a.componente}` | `{a.funcion}` | {eps} | "
            f"{_c(roles)} | {'🔴 ' + _c(a.razon) if a.destructivo else 'reversible'} | "
            f"{a.automatizable} | {_c(a.motivo)} |")
    return out + [""]
