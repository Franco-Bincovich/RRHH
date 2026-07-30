"""
Enumeración y clasificación de la superficie HTTP, para el smoke test.

Las rutas salen de `app.routes` (introspección de FastAPI), NUNCA de una lista escrita a mano:
un endpoint nuevo queda cubierto solo. Es el mismo criterio que `tests/test_paridad_list_export.py`
y el barrido de límite de export.

🔴 GUARDA CONTRA EL FALSO VERDE: `MINIMO_RUTAS`. Si la enumeración se rompe (un import que falla,
un router que deja de montarse), el barrido devolvería pocas rutas y TODO pasaría en el vacío,
con un reporte en verde que no probó nada.
"""
from typing import Dict, List, NamedTuple, Optional

# Al 29/7/2026 la app monta 199 rutas. El piso es holgado a propósito: tiene que disparar ante
# una enumeración rota, no ante el alta o baja normal de un endpoint.
MINIMO_RUTAS = 150

# 🔴 Las rutas públicas se IMPORTAN de donde viven, no se copian acá. Una lista escrita a mano
# tiene dos modos de falla y los dos ya pasaron en la primera corrida de este script: una ruta
# pública nueva se reporta como "DESPROTEGIDA" (falso positivo ruidoso), y una que dejó de ser
# pública se reporta OK (falso negativo, el peligroso).
from middleware.auth import PUBLIC_ROUTES as PUBLICAS  # noqa: E402,F401

# Prefijos que la plataforma REALMENTE enruta al backend, según `backend/vercel.json`
# (`routes: [/health, /api/(.*)]`). Todo lo demás —`/docs`, `/openapi.json`— existe en la tabla
# de rutas de FastAPI pero en producción devuelve el 404 de Vercel sin llegar a la app.
# No es un agujero de seguridad ni un endpoint caído: es una ruta que no está publicada.
PREFIJOS_PUBLICADOS = ("/health", "/api/")


def esta_publicada(path: str) -> bool:
    """¿La plataforma enruta este path al backend? Ver PREFIJOS_PUBLICADOS."""
    return path.startswith(PREFIJOS_PUBLICADOS)


class Ruta(NamedTuple):
    metodo: str
    path: str

    @property
    def es_get(self) -> bool:
        return self.metodo == "GET"

    @property
    def tiene_param(self) -> bool:
        return "{" in self.path

    @property
    def es_export(self) -> bool:
        return "export" in self.path.lower()

    @property
    def modulo(self) -> str:
        """Segmento que agrupa el endpoint en el reporte: /api/<modulo>/..."""
        partes = [p for p in self.path.split("/") if p and p != "api"]
        return partes[0] if partes else "(raíz)"


def enumerar(app) -> List[Ruta]:
    """Todas las rutas montadas, una por (método, path). Ordenadas para que el reporte sea estable."""
    rutas: List[Ruta] = []
    for r in app.routes:
        for metodo in sorted(getattr(r, "methods", set()) - {"HEAD", "OPTIONS"}):
            rutas.append(Ruta(metodo, r.path))
    return sorted(set(rutas), key=lambda x: (x.path, x.metodo))


def verificar_minimo(rutas: List[Ruta]) -> None:
    """Aborta si la enumeración devolvió menos de lo esperado. Ver la nota del encabezado."""
    if len(rutas) < MINIMO_RUTAS:
        raise SystemExit(
            f"ABORTADO: la enumeración encontró {len(rutas)} rutas y el mínimo es {MINIMO_RUTAS}.\n"
            "Algo se rompió al montar la app; un reporte con esta superficie sería un falso verde."
        )


# ── Resolución de ids para los endpoints de detalle ──────────────────────────────────────
#
# Un endpoint de detalle (`/api/empleados/{id}`) es de los que NUNCA se prueban, y es donde
# viven los embeds de PostgREST que el fake de la suite no puede desmentir. Para pegarles hace
# falta un id REAL, que sale del listado correspondiente.
#
# Excepciones: rutas cuyo listado no se deduce quitando el último segmento.
_LISTADO_EXPLICITO: Dict[str, str] = {
    "/api/onboarding/templates/{template_id}": "/api/onboarding/templates",
    "/api/evaluaciones/resultados/lotes/{lote_id}": "/api/evaluaciones/resultados/lotes",
    "/api/proyectos/{proyecto_id}/asignaciones": "/api/proyectos",
    "/api/proyectos/{proyecto_id}/horas": "/api/proyectos",
    "/api/empleados/{empleado_id}/cesiones": "/api/empleados",
}


def listado_de(path: str) -> Optional[str]:
    """Endpoint de listado del que sacar un id para `path`. None si no se puede deducir.

    Regla general: cortar en el primer `{param}`. `/api/empleados/{id}/cesiones` → `/api/empleados`.
    Devolver None es un resultado LEGÍTIMO: el endpoint se reporta NO PROBADO con el motivo, que
    es más honesto que inventar un id y contar el 404 como éxito.
    """
    if path in _LISTADO_EXPLICITO:
        return _LISTADO_EXPLICITO[path]
    if "{" not in path:
        return None
    base = path.split("/{")[0]
    return base or None


def extraer_id(payload) -> Optional[str]:
    """Primer id utilizable de una respuesta de listado. None si no hay filas.

    Contempla las dos formas del repo: `{items: [...]}` (paginado) y `[...]` (lista pelada).
    """
    filas = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(filas, list) or not filas:
        return None
    primera = filas[0]
    if not isinstance(primera, dict):
        return None
    for clave in ("id", "empleado_id", "lote_id", "template_id"):
        if primera.get(clave):
            return str(primera[clave])
    return None


# ── Cruce "vacío normal" vs "vacío roto" ─────────────────────────────────────────────────
#
# 🔴 Un 200 con lista vacía tiene DOS causas indistinguibles desde afuera: no hay datos, o la
# query está rota. Es exactamente el modo en que los 6 reportes rotos convivieron con una suite
# en verde. Este mapa dice de qué tabla depende cada listado, y con `--conteos` el veredicto pasa
# de "no sé" a un hecho: vacío + tabla con filas = ROTO.
#
# Un endpoint sin entrada acá se reporta SOSPECHOSO cuando sale vacío, nunca OK.
TABLA_DE: Dict[str, str] = {
    "/api/empleados": "empleados",
    "/api/empresas": "empresas",
    "/api/areas": "areas",
    "/api/proyectos": "proyectos",
    "/api/vacantes": "vacantes",
    "/api/candidatos": "candidatos",
    "/api/vacaciones": "solicitudes_vacaciones",
    "/api/ausencias": "solicitudes_ausencia",
    "/api/ausencias/tipos": "tipos_ausencia",
    "/api/capacitaciones": "capacitaciones",
    "/api/capacitaciones/asignaciones": "empleado_capacitacion",
    "/api/inventario/items": "inventario_items",
    "/api/inventario/asignaciones": "inventario_asignaciones",
    "/api/objetivos": "objetivos",
    "/api/onboarding/templates": "onboarding_templates",
    "/api/onboarding": "onboarding_instancias",
    "/api/offboarding": "offboarding_instancias",
    "/api/evaluaciones/resultados/lotes": "evaluacion_lotes",
    "/api/evaluaciones/instancias": "ev_instancias",
    "/api/evaluaciones/plantillas": "ev_plantillas",
    "/api/evaluaciones/ciclos": "ev_ciclos",
    "/api/auditoria": "auditoria",
    "/api/usuarios": "users",
    "/api/periodos": "periodos_cerrados",
    "/api/sucesion": "sucesion_posiciones",
    "/api/integraciones": "usuario_integraciones",
    "/api/reportes/historial": "reportes_generados",
    "/api/proyectos/{proyecto_id}/horas": "horas_proyecto",
}


def sustituir_param(path: str, valor: str) -> str:
    """Reemplaza el PRIMER `{param}` del path por un valor concreto."""
    import re

    return re.sub(r"\{[^}]+\}", valor, path, count=1)
