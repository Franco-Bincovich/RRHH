"""
BARRIDO ESTRUCTURAL nº 52 — **el nombre de la plataforma se escribe en UN solo lugar por lado.**

🔴 PARA QUÉ (bloque N9, 25/8/2026). El nombre va a cambiar y todavía no está confirmado. Estaba
escrito literal en OCHO archivos —seis del front (título del navegador, sidebar, login, pie de la
evaluación pública y tres textos del panel de IA) y dos del backend (el título de la API y el
metadato `author` de todo PDF exportado)—, así que cambiarlo era un buscar-y-reemplazar sobre un
literal corto en un repo que además lo menciona en decenas de COMENTARIOS y en datos de prueba.
Esa es la operación en la que se cambia de más o de menos y nadie se entera hasta que un usuario
lo ve en pantalla.

Centralizarlo no alcanza sin esto: el próximo texto que nombre la plataforma vuelve a escribirlo
literal en el próximo PR, y el "un solo lugar" deja de ser cierto sin que nada avise. Es la misma
forma que `barridoSelect` (nadie escribe un `<select>` fuera del primitivo) y `barridoTarjetas`.

🔑 SE BARREN LAS DOS PUNTAS DESDE ACÁ, en un solo test, porque **la regla es una sola**. Partirlo
en un test de Python y uno de vitest daría dos listas de excepciones que se separan. El molde de
un test del backend que lee el árbol del front es `test_legajo_ficha_export.py`.

⚠️ SÓLO CUENTA EL TEXTO QUE LLEGA A PANTALLA. Los comentarios y docstrings se enmascaran antes de
buscar, y no por comodidad: este repo documenta sus decisiones EN PROSA y varios archivos explican
justamente por qué el nombre no está escrito ahí. Un barrido por texto plano marcaría esas
explicaciones y empujaría a borrarlas, que es el peor resultado posible.
"""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
FRONT = RAIZ / "frontend"

# 🔴 EL LITERAL ES EL NOMBRE DE HOY, Y CAMBIA CON ÉL. El 27/8/2026 pasó de «HR Karstec» a
# «Core RH» (definido por Capital Humano). Este renglón es el TERCERO y último que hay que tocar
# para renombrar la plataforma —los otros dos son los defaults de `DUENOS`—, y es la prueba de
# que la centralización del bloque N9 funcionó: el renombre fueron tres líneas, no un
# buscar-y-reemplazar sobre las decenas de comentarios que nombran la marca.
#
# ⚠️ NO se guarda además el nombre VIEJO, y no es un olvido. El barrido pregunta "¿alguien
# escribe el nombre de la plataforma literal en vez de usar la constante?", y esa pregunta es
# sobre el nombre VIGENTE: un literal «HR Karstec» que hubiera quedado en pantalla habría rojeado
# ANTES de este cambio, con el barrido en verde como estaba. Guardar los dos nombres para siempre
# convertiría esta constante en una lista histórica que nadie poda.
LITERAL = "Core RH"

# Los DOS lugares donde el literal vive a propósito: el default de cada lado.
DUENOS = {
    "backend/config/settings.py": "el default de `settings.marca`.",
    "frontend/lib/marca.ts": "el default de `MARCA`, el espejo del front.",
}

# Archivos que nombran la plataforma en pantalla y NO pasan por la constante, con su razón.
# Vacío: si mañana aparece uno, se declara acá con el porqué o se cablea. Una excepción sin razón
# es la que nadie revisa.
EXCEPCIONES: dict = {}

# 🔴 LAS MIGRACIONES NO SE BARREN, Y NO ES UN AGUJERO. Son historia: la 027 sembró un template de
# onboarding llamado "Template Estándar Karstec" y la 035 datos de demo con correos @karstec.com.
# Reescribir una migración ya corrida no cambia una sola fila de producción —ya se ejecutó— y sí
# rompe cualquier reconstrucción desde cero que se compare contra el histórico.
_EXCLUIR = ("node_modules", ".next", "__pycache__", "venv", ".venv", "migrations", "docs",
            "migracionAWS", "scripts", ".git")


def _sin_prosa(texto: str, sufijo: str) -> str:
    """El archivo sin comentarios ni docstrings: lo que queda es lo que puede llegar a pantalla."""
    if sufijo == ".py":
        texto = re.sub(r'"""(?:.|\n)*?"""', "", texto)
        texto = re.sub(r"'''(?:.|\n)*?'''", "", texto)
        return re.sub(r"#[^\n]*", "", texto)
    texto = re.sub(r"\{/\*(?:.|\n)*?\*/\}", "", texto)
    texto = re.sub(r"/\*(?:.|\n)*?\*/", "", texto)
    return re.sub(r"//[^\n]*", "", texto)


def _candidatos():
    """Todo archivo de código de las dos puntas, salvo los excluidos y los de test."""
    for raiz, sufijos in ((BACKEND, (".py",)), (FRONT, (".ts", ".tsx"))):
        for f in raiz.rglob("*"):
            if f.suffix not in sufijos or not f.is_file():
                continue
            rel = f.relative_to(RAIZ).as_posix()
            if any(p in rel.split("/") for p in _EXCLUIR):
                continue
            # Los tests describen la app, no la muestran: uno puede nombrar la marca legítimamente
            # (este archivo, sin ir más lejos) y marcarlo sería marcarse a sí mismo.
            if "test" in f.name.lower():
                continue
            yield rel, f


ARCHIVOS = sorted(_candidatos())
CON_LITERAL = sorted(
    rel for rel, f in ARCHIVOS if LITERAL in _sin_prosa(f.read_text(encoding="utf-8"), f.suffix)
)


def test_hay_algo_que_barrer():
    """Guarda de mínimo: si el recorrido se rompe, todo lo de abajo pasaría sobre cero archivos."""
    assert len(ARCHIVOS) >= 400, f"solo se barrieron {len(ARCHIVOS)} archivos"


def test_los_dos_duenos_del_literal_siguen_teniendolo():
    """La contracara. Sin esto, borrar los dos defaults dejaría el barrido en verde sobre nada —
    y el nombre desaparecería de la app entera."""
    for archivo, razon in DUENOS.items():
        assert archivo in CON_LITERAL, f"{archivo} dejó de tener el literal: {razon}"


@pytest.mark.parametrize("archivo", CON_LITERAL)
def test_nadie_mas_escribe_el_nombre_de_la_plataforma(archivo: str):
    if archivo in DUENOS:
        pytest.skip(DUENOS[archivo])
    if archivo in EXCEPCIONES:
        pytest.skip(EXCEPCIONES[archivo])
    assert False, (
        f"{archivo} escribe «{LITERAL}» literal. Usá `settings.marca` (backend) o `MARCA` de "
        f"`@/lib/marca` (front), o declaralo en EXCEPCIONES con su razón."
    )


def test_los_dos_defaults_dicen_lo_MISMO():
    """🔴 SON DOS CONSTANTES Y NO UNA, porque son dos procesos distintos: el front no puede leer
    `Settings` de Python y el backend no importa TypeScript. Lo que sí se puede exigir es que el
    default coincida — si no, la pantalla y el PDF que descarga esa misma pantalla dirían nombres
    distintos, que es peor que no haber centralizado nada."""
    py = (BACKEND / "config" / "settings.py").read_text(encoding="utf-8")
    ts = (FRONT / "lib" / "marca.ts").read_text(encoding="utf-8")
    en_py = re.search(r'marca:\s*str\s*=\s*"([^"]+)"', py)
    en_ts = re.search(r'MARCA\s*=\s*process\.env\.\w+\s*\|\|\s*"([^"]+)"', ts)
    assert en_py and en_ts, "no se pudo leer alguno de los dos defaults (¿cambió la forma?)"
    assert en_py.group(1) == en_ts.group(1), (
        f"backend dice «{en_py.group(1)}» y front dice «{en_ts.group(1)}»"
    )
