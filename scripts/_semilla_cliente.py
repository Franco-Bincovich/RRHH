"""
El cliente HTTP y el MANIFIESTO de la semilla de smoke. Acá vive la idempotencia.

🔴 CÓMO SE RESUELVE LA IDEMPOTENCIA — DOS CAPAS, Y LAS DOS HACEN FALTA.

  1. **El manifiesto** (`scripts/.semilla-smoke.json`, fuera de git). Cada fila sembrada deja
     `{recurso, clave, id}`. Una segunda corrida ve la clave y NO vuelve a pedir el alta. Es la
     capa rápida y es además el registro EXACTO de qué borrar después.

  2. **La clave natural**, que es la que salva cuando el manifiesto se perdió (otra máquina,
     otro clon, alguien lo borró). Antes de crear, `obtener_o_crear` BUSCA la fila por su clave
     en el listado real del sistema: el legajo del colaborador, el nombre del perfil, el título
     del objetivo. Si está, la adopta y la anota. **Sin esta capa, un manifiesto perdido
     duplicaría todo el padrón sembrado**, que es exactamente el estado que hace imposible
     limpiar después.

  🔑 Las dos capas convergen en el mismo invariante: **una clave natural = una fila**. Por eso
  las claves viven en `_semilla_padron.py` / `_semilla_catalogo.py` como constantes y no se
  generan al vuelo: un nombre generado con `random` haría que la segunda corrida no reconozca
  nada de la primera.

⚠️ NO TODO RECURSO TIENE CLAVE NATURAL CONSULTABLE. Las recategorizaciones y las asignaciones de
formación se buscan por una tupla compuesta que el listado sí devuelve (empleado + fecha +
motivo, capacitación + persona); la nómina no necesita ninguna porque su endpoint YA es un
upsert sobre `UNIQUE (empleado_id, anio, mes)`. Cada fase declara la suya al llamar.

⚠️ EL RITMO. Todo write pasa por acá y espera `pausa` segundos. El baseline del rate limit son
300/minuto por IP (`utils/rate_limit.py`) y una corrida completa son ~160 requests: sin pausa
entran todos en el mismo minuto y el final de la corrida se come 429s. 0.15 s alcanza y cuesta
menos de medio minuto.
"""
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import httpx

MANIFIESTO = Path(__file__).resolve().parent / ".semilla-smoke.json"
TIMEOUT = 60.0


def consola_utf8() -> None:
    """Pone stdout/stderr en UTF-8. 🔴 En Windows es OBLIGATORIO, no cosmético.

    La consola de la Lenovo es **cp1252** y estos scripts imprimen `→`, `·` y `✅`: sin esto, el
    primer `print` de la primera fase muere con `UnicodeEncodeError` **después** de haber
    sembrado filas, y la corrida se corta a la mitad dejando el manifiesto incompleto. Es la
    misma familia del `⚠️` que carteleaba `pip install` en Windows (`test_requirements_ascii.py`):
    el texto no ASCII no rompe donde se escribe, rompe donde se IMPRIME.
    """
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")


class TokenVencido(Exception):
    """El backend respondió 401. 🔴 CORTA LA CORRIDA ENTERA, no se cuenta como un fallo más.

    Un token de Supabase dura ~1 hora y una corrida completa son ~160 requests. Si vence a la
    mitad, TODO lo que sigue devuelve 401 y sin esto el reporte final saldría con cien "fallos"
    que no son hallazgos sino la misma credencial muerta repetida — enterrando los fallos de
    verdad. Peor: `obtener_o_crear` interpretaría cada 401 como "no se pudo crear" y la fase
    siguiente arrancaría con ids faltantes. Al primer 401 se para y se dice dónde quedó.
    """


class FalloAPI(Exception):
    """Un endpoint respondió algo que no es éxito. Lleva el detalle para el reporte final."""

    def __init__(self, metodo: str, ruta: str, status: int, cuerpo: str) -> None:
        super().__init__(f"{metodo} {ruta} → {status}: {cuerpo[:300]}")
        self.metodo, self.ruta, self.status, self.cuerpo = metodo, ruta, status, cuerpo[:300]


class Manifiesto:
    """El registro de lo sembrado: `{recurso: {clave: id}}`, más los datos que la limpieza pide.

    Se guarda en cada anotación y no al final: si la corrida muere a la mitad, lo escrito hasta
    ahí ya se puede limpiar. Un manifiesto a medias es recuperable; uno que nunca se escribió
    deja filas sin dueño.
    """

    def __init__(self, ruta: Path = MANIFIESTO) -> None:
        self.ruta = ruta
        self.datos: Dict[str, Dict[str, Any]] = (
            json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {})

    def id_de(self, recurso: str, clave: str) -> Optional[str]:
        return (self.datos.get(recurso) or {}).get(clave)

    def anotar(self, recurso: str, clave: str, valor: Any) -> None:
        self.datos.setdefault(recurso, {})[clave] = valor
        self.ruta.write_text(json.dumps(self.datos, indent=2, ensure_ascii=False), encoding="utf-8")


class Cliente:
    """httpx + token + `X-Empresa-Id` + pausa. Cuenta los fallos en vez de abortar la corrida.

    🔴 UN FALLO NO CORTA LA SIEMBRA. Sembrar por la API es el primer uso real de varios caminos
    de escritura, así que un 400/422/500 es un HALLAZGO: se anota con su cuerpo y se sigue con
    la fase siguiente. Abortar dejaría el resto sin probar y el reporte con un solo dato.
    """

    def __init__(self, base: str, token: str, pausa: float = 0.15) -> None:
        self.http = httpx.Client(base_url=base.rstrip("/"), timeout=TIMEOUT, follow_redirects=True)
        self.token, self.pausa = token, pausa
        self.fallos: list = []
        self.manifiesto = Manifiesto()

    def cerrar(self) -> None:
        self.http.close()

    def pedir(self, metodo: str, ruta: str, *, empresa: Optional[str] = None,
              json_body: Any = None, **kwargs) -> Any:
        """Un request. Devuelve el JSON del cuerpo; ante status de error levanta `FalloAPI`."""
        cabeceras = {"Authorization": f"Bearer {self.token}"}
        if empresa:
            cabeceras["X-Empresa-Id"] = empresa
        res = self.http.request(metodo, ruta, headers=cabeceras, json=json_body, **kwargs)
        if metodo != "GET":
            time.sleep(self.pausa)
        if res.status_code == 401:
            raise TokenVencido(f"{metodo} {ruta} → 401 · {res.text[:160]}")
        if res.status_code >= 400:
            raise FalloAPI(metodo, ruta, res.status_code, res.text)
        return res.json() if res.content and res.status_code != 204 else None

    def get(self, ruta: str, **kwargs) -> Any:
        return self.pedir("GET", ruta, **kwargs)

    def anotar_fallo(self, fase: str, detalle: str, exc: Exception) -> None:
        """Registra un fallo para el reporte final y lo imprime en el acto."""
        if isinstance(exc, FalloAPI):
            self.fallos.append(dict(fase=fase, detalle=detalle, metodo=exc.metodo, ruta=exc.ruta,
                                    status=exc.status, cuerpo=exc.cuerpo))
            print(f"    ✗ {detalle}: {exc.metodo} {exc.ruta} → {exc.status} · {exc.cuerpo[:160]}")
        else:
            self.fallos.append(dict(fase=fase, detalle=detalle, metodo="-", ruta="-",
                                    status=0, cuerpo=repr(exc)[:300]))
            print(f"    ✗ {detalle}: {exc!r}")

    def obtener_o_crear(self, recurso: str, clave: str, crear: Callable[[], Any],
                        buscar: Optional[Callable[[], Optional[str]]] = None) -> Optional[str]:
        """El corazón de la idempotencia. Devuelve el id, sin duplicar nunca.

        Orden: manifiesto → clave natural en el sistema → alta. Las tres puntas anotan el mismo
        `(recurso, clave)`, así que la corrida siguiente entra por la primera.
        """
        anotado = self.manifiesto.id_de(recurso, clave)
        if anotado:
            return anotado
        if buscar is not None:
            try:
                existente = buscar()
            except FalloAPI as exc:
                self.anotar_fallo(recurso, f"buscar {clave}", exc)
                existente = None
            if existente:
                self.manifiesto.anotar(recurso, clave, existente)
                return existente
        try:
            nuevo = crear()
        except TokenVencido:
            raise                             # el 401 SÍ corta: ver `TokenVencido`
        except Exception as exc:  # noqa: BLE001 — un fallo no corta la siembra (ver el docstring)
            self.anotar_fallo(recurso, f"crear {clave}", exc)
            return None
        if nuevo:
            self.manifiesto.anotar(recurso, clave, nuevo)
        return nuevo

    def hito(self, recurso: str, clave: str, accion: Callable[[], Any]) -> bool:
        """Un paso que NO crea una fila propia pero que tampoco debe repetirse (efectivizar una
        baja, resolver un evento, mover un candidato de etapa). El manifiesto guarda que ya
        ocurrió; sin esto, la segunda corrida choca contra la guarda de estado del backend y
        ensucia el reporte con 409 que no son hallazgos.
        """
        if self.manifiesto.id_de(recurso, clave):
            return True
        try:
            accion()
        except TokenVencido:
            raise
        except Exception as exc:  # noqa: BLE001
            self.anotar_fallo(recurso, clave, exc)
            return False
        self.manifiesto.anotar(recurso, clave, "hecho")
        return True


def login(base: str, usuario: str, password: str) -> str:
    """Token de un `admin_rrhh` por `POST /api/auth/login`. El JWT lo firma Supabase (ES256) y el
    middleware lo valida contra el JWKS público: no se puede fabricar a mano."""
    with httpx.Client(base_url=base.rstrip("/"), timeout=TIMEOUT) as cli:
        res = cli.post("/api/auth/login", json={"username": usuario, "password": password})
        if res.status_code >= 400:
            raise SystemExit(f"ABORTADO: el login devolvió {res.status_code} · {res.text[:200]}")
        return res.json()["access_token"]
