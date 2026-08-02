"""
🔴 LAS DOS INVARIANTES DEL PUNTO ÚNICO DE SALIDA — tests ESTRUCTURALES, no de una feature.

Como los tres barridos que ya existen en el repo (paridad list↔export, límite de export,
nav↔permisos), estos barren la superficie ENTERA por introspección, así que **cualquier módulo o
proveedor que se agregue queda cubierto sin tocar este archivo**. Y los dos llevan guarda de
mínimo contra el falso verde: si el barrido dejara de encontrar archivos, pasaría sin comparar
nada — que es el modo de falla del caso #5 de "un test solo prueba lo que el fake puede
desmentir".

  1. **Nadie importa `_gmail` fuera de `services/mailer/`.** Un caller que lo importara directo
     se saltearía el log, la auditoría y la resolución de la casilla remitente, y el punto único
     dejaría de serlo SIN QUE NADA FALLE. Es el modo de erosión típico: no rompe, solo deja de
     cumplirse.
  2. **El log y la auditoría viven en `engine.py`, no en el proveedor.** Si vivieran en
     `_gmail.py`, el próximo proveedor —SES en la migración a AWS— nacería sin log. Es
     exactamente lo que pasó con los exports antes de `verificar_limite_export`.

⚠️ Se lee el CÓDIGO FUENTE (`inspect.getsource` / lectura de archivos) y no se falsean módulos:
un fake no puede desmentir "quién importa a quién". Es el mismo mecanismo que usa
`test_limite_export.py` para verificar que `verificar_limite_export` se INVOQUE y no solo se
importe.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

import inspect
from pathlib import Path

import services.mailer as paquete
from services.mailer import engine

_RAIZ = Path(__file__).resolve().parent.parent
_MAILER = _RAIZ / "services" / "mailer"

def _modulos_proveedor() -> set:
    """Los módulos que IMPLEMENTAN un proveedor, derivados del dict de despacho real.

    🔴 Derivarlos y no listarlos a mano es lo que hace que el PRÓXIMO proveedor —SES el día del
    cutover a AWS— quede cubierto sin tocar este archivo. Una lista escrita acá se
    desincronizaría del dict y el barrido dejaría de mirar justo lo nuevo.

    ⚠️ La invariante es sobre los PROVEEDORES, no sobre todo lo que empieza con guión bajo.
    `_render`, `_variables` y `_markdown` SÍ los importan los services (para validar variables al
    guardar y para previsualizar), y está bien: son funciones puras, sin red y sin efectos, y no
    hay nada que saltearse al llamarlas. Lo que no se puede saltear es el ENVÍO, porque ahí es
    donde viven el log, la auditoría y la resolución de la casilla remitente.
    """
    return {fn.__module__.rsplit(".", 1)[-1] for fn in engine._PROVEEDORES.values()}


def _fuentes_del_repo():
    """Todos los .py del backend salvo el propio paquete mailer, los tests y el venv."""
    for ruta in _RAIZ.rglob("*.py"):
        partes = set(ruta.parts)
        if partes & {"venv", ".venv", "__pycache__", "tests", "migracionAWS"}:
            continue
        if _MAILER in ruta.parents:
            continue
        yield ruta


# ── INVARIANTE 1: nadie importa los internos del paquete ──────────────────────

def test_nadie_fuera_del_paquete_importa_un_proveedor() -> None:
    """Un import directo del proveedor saltearía log, auditoría y remitente — SIN fallar. Ese es
    el modo de erosión: no rompe nada, simplemente deja de cumplirse."""
    archivos = list(_fuentes_del_repo())
    assert len(archivos) >= 150, "el barrido no encontró el repo: sin esto pasaría sin comparar nada"
    proveedores = _modulos_proveedor()
    assert proveedores, "no se detectó ningún módulo proveedor: el barrido quedaría vacuo"

    infractores = []
    for ruta in archivos:
        texto = ruta.read_text(encoding="utf-8")
        for interno in proveedores:
            if f"services.mailer.{interno}" in texto or f"from services.mailer import {interno}" in texto:
                infractores.append(f"{ruta.relative_to(_RAIZ)} → {interno}")
    assert not infractores, (
        "Estos módulos importan un proveedor de services/mailer directo y se saltean el punto "
        "único (log, auditoría y casilla remitente): " + ", ".join(infractores))


def test_solo_el_engine_invoca_al_proveedor() -> None:
    """El contrapeso del anterior, dentro del paquete: el despacho vive en `engine`, así que
    ningún otro módulo del paquete debe llamar al proveedor por su cuenta."""
    proveedores = _modulos_proveedor()
    otros = [p for p in _MAILER.glob("*.py") if p.stem not in ({"engine", "__init__"} | proveedores)]
    assert len(otros) >= 2, "el barrido interno quedó vacuo"
    for ruta in otros:
        texto = ruta.read_text(encoding="utf-8")
        assert not any(f"import {p}" in texto for p in proveedores), \
            f"{ruta.name} invoca al proveedor sin pasar por el engine"


def test_el_contrato_del_paquete_expone_solo_la_puerta() -> None:
    """`__all__` ES el contrato. Si crece, alguien abrió una segunda puerta."""
    assert paquete.__all__ == ["enviar_mail"]
    assert hasattr(paquete, "enviar_mail")


# ── INVARIANTE 2: el log y la auditoría viven en el engine ────────────────────

class TestElLogViveEnElEngine:
    def test_el_engine_registra_el_envio(self) -> None:
        """Importarlo no alcanza: se verifica que se INVOQUE en el cuerpo, igual que hace
        `test_limite_export` con `verificar_limite_export`."""
        fuente = inspect.getsource(engine)
        assert "_registrar(" in fuente and "MailEnviadoRepo" in fuente

    def test_el_engine_registra_TAMBIEN_los_fallos(self) -> None:
        """🔴 Sin la fila del fallo, "no me llegó" queda sin respuesta justo cuando hace falta.
        Para que falle: sacar el `_registrar` de la rama `except`."""
        fuente = inspect.getsource(engine)
        assert '"estado": "fallido"' in fuente

    def test_ningun_proveedor_registra_por_su_cuenta(self) -> None:
        """El barrido que hace que el PRÓXIMO proveedor quede cubierto sin tocar este archivo.

        Si un proveedor loguea lo suyo, el log deja de ser una propiedad del punto único y pasa a
        ser una costumbre que cada autor puede olvidar."""
        proveedores = [p for p in _MAILER.glob("_*.py") if p.stem not in ("_markdown", "_render", "_variables")]
        assert len(proveedores) >= 1, "no se encontró ningún proveedor: el barrido quedaría vacuo"
        for ruta in proveedores:
            texto = ruta.read_text(encoding="utf-8")
            assert "MailEnviadoRepo" not in texto, f"{ruta.name} registra por su cuenta"
            assert "AuditService" not in texto, f"{ruta.name} audita por su cuenta"

    def test_todo_proveedor_esta_en_el_dict_de_despacho(self) -> None:
        """Un archivo de proveedor que nadie despacha es código muerto que aparenta cobertura."""
        assert len(engine._PROVEEDORES) >= 1
        for nombre, fn in engine._PROVEEDORES.items():
            assert callable(fn), f"la entrada '{nombre}' no es invocable"


# ── Resend: que no vuelva ─────────────────────────────────────────────────────

def test_resend_no_quedo_en_ninguna_parte() -> None:
    """`resend_api_key` era obligatoria sin default y nadie la importaba: lo único que podía
    hacer era tumbar el arranque entero. Este test impide que vuelva de un merge distraído."""
    archivos = list(_fuentes_del_repo())
    assert len(archivos) >= 150
    culpables = [str(r.relative_to(_RAIZ)) for r in archivos
                 if "resend_api_key: str" in r.read_text(encoding="utf-8")]
    assert not culpables, f"volvió la env var de Resend en: {culpables}"
