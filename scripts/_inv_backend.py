"""
LA SUPERFICIE HTTP, POR INTROSPECCIÓN DE `app.routes`. Nunca una lista escrita a mano, nunca un
grep: un endpoint nuevo entra al inventario solo.

🔴 EL GATE DE PERMISOS SE LEE DEL CLOSURE, NO DEL TEXTO DEL ROUTER. `require_permission(seccion,
accion)` devuelve una función que captura los dos valores; FastAPI la guarda en
`route.dependant.dependencies`, así que los valores REALES están ahí. Un grep de
`Depends(require_permission(...))` sobre el archivo del router se pierde los gates que vienen del
`APIRouter(dependencies=[...])` —que en este repo son varios routers enteros— y no sabe distinguir
un gate comentado de uno vivo. Medido: 265 rutas, 246 con gate estático, 19 sin él.

🔴 SE ENCIENDEN TODOS LOS FLAGS ANTES DE ENUMERAR. Con la config por default,
`horas_publico_enabled` y `assessment_enabled` están en False y sus routers NO SE MONTAN: el
link público de horas (5 rutas) y assessment (7) desaparecerían del inventario. Un módulo
apagado no está exento de figurar — está escondido, que es lo contrario de lo que este documento
busca. Es la misma corrección que ya se le hizo a `tests/_barrido_callers.rutas_backend`, y por
eso se lee genérica: se enciende TODO campo de `Settings` que termine en `_enabled`, sin nombrar
ningún flag. El que se agregue mañana entra solo.

⚠️ `escribe` SE DERIVA DEL MÉTODO, con UNA corrección: los `/preview` de los tres imports son
POST y NO PERSISTEN NADA (parsean el archivo y devuelven qué haría el confirmar). Contarlos como
escrituras haría que el inventario declare destructivo un endpoint que se puede llamar cien veces
sin consecuencia. No hay más excepciones: el resto de los POST/PUT/PATCH/DELETE escriben.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"

_ENV_TEST = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}

# 🔴 Guarda contra el falso verde. Si la enumeración se rompe (un import que falla, un router que
# deja de montarse), el inventario saldría corto y en verde sobre nada. Holgado a propósito:
# tiene que morder una ROTURA, no el alta o baja normal de un endpoint. Medido: 265 el 23/8/2026.
MINIMO_RUTAS = 200


class Endpoint(NamedTuple):
    metodo: str
    path: str
    seccion: Optional[str]
    accion: Optional[str]
    escribe: bool
    publica: bool          # declarada en PUBLIC_ROUTES: entra sin token
    dinamica: bool         # el permiso lo resuelve el service, no un Depends
    solo_con_flag: bool    # no se monta con la config por default

    @property
    def gate(self) -> str:
        if self.seccion:
            return f"{self.seccion} · {self.accion}"
        if self.publica:
            return "público (sin auth)"
        if self.dinamica:
            return "dinámico (lo resuelve el service)"
        return "solo auth"

    @property
    def modulo(self) -> str:
        partes = [p for p in self.path.split("/") if p and p != "api"]
        return partes[0] if partes else "(raíz)"


def _preparar() -> None:
    for k, v in _ENV_TEST.items():
        os.environ.setdefault(k, v)
    import sys
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


def _gates(route) -> List[Tuple[str, str]]:
    """(sección, acción) de cada `require_permission` que protege la ruta. Ver el encabezado."""
    out: List[Tuple[str, str]] = []
    for dep in route.dependant.dependencies:
        call = dep.call
        if not getattr(call, "__qualname__", "").startswith("require_permission"):
            continue
        celdas = [c.cell_contents for c in (call.__closure__ or ())]
        sec = next((x.value for x in celdas if type(x).__name__ == "Seccion"), None)
        acc = next((x.value for x in celdas if type(x).__name__ == "Accion"), None)
        if sec:
            out.append((sec, acc or "read"))
    return out


def _rutas_de(app) -> Dict[Tuple[str, str], object]:
    from fastapi.routing import APIRoute
    out: Dict[Tuple[str, str], object] = {}
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        for m in r.methods - {"HEAD", "OPTIONS"}:
            out[(m, r.path)] = r
    return out


@lru_cache(maxsize=1)
def _crudo() -> Tuple[Dict[Tuple[str, str], object], Set[Tuple[str, str]], Set[str]]:
    """(rutas con todos los flags encendidos, rutas que SOLO existen con flag, públicas)."""
    _preparar()
    from fastapi import FastAPI

    from config.settings import settings
    from main import app as app_real
    from middleware.auth import _is_public
    from registro_routers import registrar

    flags = [n for n in type(settings).model_fields if n.endswith("_enabled")]
    previos = {n: getattr(settings, n) for n in flags}
    apagada = FastAPI()
    registrar(apagada)
    con_default = set(_rutas_de(apagada)) | set(_rutas_de(app_real))
    try:
        for n in flags:
            setattr(settings, n, True)
        encendida = FastAPI()
        registrar(encendida)
        todas = {**_rutas_de(encendida), **_rutas_de(app_real)}
        publicas = {p for _m, p in todas if _is_public(p)}
    finally:
        for n, v in previos.items():
            setattr(settings, n, v)
    return todas, set(todas) - con_default, publicas


@lru_cache(maxsize=1)
def _gatea_dinamico() -> Set[str]:
    """Routers cuyo permiso lo decide el SERVICE con `puede(rol, ...)`, no un `Depends`.

    🔴 Mirar sólo el archivo del router no alcanza y daría CERO: `routers/adjuntos.py` no nombra
    `puede()` en ninguna línea — le pasa el `rol` a `AdjuntoService`, que resuelve la sección a
    partir de la ENTIDAD del adjunto (un adjunto de vacante gatea con VACANTES, uno de empleado
    con EMPLEADOS). Se sigue el import hasta el service y se busca ahí. Sin esto, las 5 rutas de
    adjuntos figurarían como "solo auth", o sea SIN control de sección, que es falso.
    """
    import re
    out: Set[str] = set()
    for p in (BACKEND / "routers").glob("*.py"):
        fuentes = [p.read_text(encoding="utf-8", errors="ignore")]
        for m in re.finditer(r"from\s+services\.([\w.]+)\s+import", fuentes[0]):
            hijo = BACKEND / "services" / (m.group(1).replace(".", "/") + ".py")
            if hijo.exists():
                fuentes.append(hijo.read_text(encoding="utf-8", errors="ignore"))
        if any("puede(rol" in f for f in fuentes):
            out.add(p.stem)
    return out


@lru_cache(maxsize=1)
def endpoints() -> List[Endpoint]:
    """Toda la superficie HTTP, ordenada y estable. Aborta si la enumeración se rompió."""
    todas, con_flag, publicas = _crudo()
    dinamicos = _gatea_dinamico()
    out: List[Endpoint] = []
    for (metodo, path), route in todas.items():
        gates = _gates(route)
        modulo = getattr(route.endpoint, "__module__", "").rsplit(".", 1)[-1]
        # Sin `Depends(require_permission)`: o es pública, o el permiso lo decide el service
        # con `puede(rol, ...)` — que es como gatea `adjuntos`, cuyo permiso depende de la
        # ENTIDAD del adjunto y no se puede saber en la firma de la ruta.
        dinamica = not gates and modulo in dinamicos
        out.append(Endpoint(
            metodo=metodo, path=path,
            seccion=gates[0][0] if gates else None,
            accion=gates[0][1] if gates else None,
            escribe=metodo != "GET" and not path.endswith("/preview"),
            publica=path in publicas,
            dinamica=dinamica,
            solo_con_flag=(metodo, path) in con_flag,
        ))
    if len(out) < MINIMO_RUTAS:
        raise SystemExit(
            f"ABORTADO: la enumeración encontró {len(out)} rutas y el mínimo es {MINIMO_RUTAS}. "
            "Algo se rompió al montar la app; un inventario con esta superficie sería un falso verde.")
    return sorted(out, key=lambda e: (e.path, e.metodo))


@lru_cache(maxsize=1)
def declarados_sin_caller() -> Dict[Tuple[str, str], str]:
    """(MÉTODO, path) -> razón/disparador, IMPORTADO de `tests/test_callers_huerfanos.py`.

    🔴 Se importa, no se copia. Es la lista que el barrido de callers huérfanos ya mantiene viva
    en las dos direcciones (una excepción que consigue caller da rojo, una que apunta a una ruta
    borrada también). Una segunda copia acá se separaría de esa y el inventario marcaría como
    "declarado sin caller" algo que hace tres tandas tiene pantalla.
    """
    _preparar()
    from tests.test_callers_huerfanos import _ENDPOINTS_SIN_FRONT
    return dict(_ENDPOINTS_SIN_FRONT)
