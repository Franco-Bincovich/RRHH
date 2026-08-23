"""
LOS CASOS QUE YA SABEMOS QUE HAY QUE PROBAR. No salen de recorrer la superficie: salen de bugs
que ya pasaron, de contratos que el repo declara por escrito y de lo que un barrido existente
declaró que NO puede verificar.

🔴 POR QUÉ TIENEN FILA PROPIA Y NO SON UNA NOTA AL PIE. Las tres listas de arriba enumeran lo que
EXISTE (endpoints, pantallas, botones). Estos casos son AFIRMACIONES SOBRE EL COMPORTAMIENTO —
"un id ajeno da 404 y no 403", "el fondo tiene manchas de color"— y no hay superficie que
recorrer para descubrirlos: si no están escritos, no están. El bug de los 24 `maybe_single()`
vivió meses exactamente así: cada endpoint estaba en su lugar, respondía, tenía tests verdes, y
la afirmación "un id inexistente da 404" no la sostenía nadie desde afuera.

⚠️ LAS FAMILIAS SE CUENTAN, NO SE ENUMERAN FILA POR FILA. "un id inexistente en cada endpoint que
recibe uno" son 118 pruebas y listarlas una por una haría el documento ilegible sin agregar
información: el conjunto se deriva de la lista de endpoints, que ya está arriba. Lo que se
declara es la REGLA y el CONTEO, y el conteo se mide contra el código.
"""
import re
from functools import lru_cache
from typing import Dict, List, NamedTuple, Tuple

from _inv_backend import BACKEND, endpoints
from _inv_front import FRONT, RAIZ, sin_comentarios


class Caso(NamedTuple):
    familia: str
    que_probar: str
    origen: str
    cuantos: int
    automatizable: str
    motivo: str


# 🔴 Los 8 endpoints que la Fase 2 marcó NO APLICA para la barrera de empresa, con su razón.
# Se declaran acá porque la razón es de PRODUCTO y no se lee del código: que `empresas/{id}`
# no valide empresa no es un descuido, es que la empresa ES el recurso. Citado de CLAUDE.md,
# sección "Patrón de barrera de empresa". El barrido verifica que las rutas sigan existiendo.
SIN_BARRERA: Dict[Tuple[str, str], str] = {
    ("DELETE", "/api/usuarios/{user_id}"): "los usuarios no cuelgan de una empresa",
    ("GET", "/api/empresas/{id}"): "la empresa ES el recurso",
    ("PUT", "/api/empresas/{id}"): "la empresa ES el recurso",
    ("PATCH", "/api/empresas/{id}/activa"): "la empresa ES el recurso",
    ("POST", "/api/empresas/{id}/logo"): "la empresa ES el recurso",
    ("GET", "/api/assessment/evaluacion/{token}"): "sin auth: la autorización es el token",
    ("POST", "/api/assessment/evaluacion/{token}/submit"): "sin auth: la autorización es el token",
    ("DELETE", "/api/integraciones/{tipo}"): "scopeado por user_id, no por empresa",
}


def _con_id() -> List[Tuple[str, str]]:
    return [(e.metodo, e.path) for e in endpoints() if "{" in e.path]


def _con_barrera() -> List[Tuple[str, str]]:
    """Endpoints con id de recurso Y gate de sección: los que el contrato del 404 obliga."""
    return [(e.metodo, e.path) for e in endpoints()
            if "{" in e.path and e.seccion and (e.metodo, e.path) not in SIN_BARRERA]


@lru_cache(maxsize=1)
def decisiones_visuales() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """(decisiones que el barrido SÍ verifica, las que declaró NO verificables).

    Se leen del archivo real del barrido (`components/ui/decisionesVisuales.test.ts`), no se
    copian: es el mismo criterio con el que este inventario lee `RUTA_SECCION` y la lista de
    endpoints sin caller. Si mañana una decisión pasa de no-verificable a verificable, este
    documento se entera solo.
    """
    src = sin_comentarios(
        (FRONT / "components/ui/decisionesVisuales.test.ts").read_text(encoding="utf-8"))
    verificadas = [(m.group(1), m.group(2).strip())
                   for m in re.finditer(r'seccion:\s*"(§\d)"[\s\S]{0,400}?que:\s*"([^"]+)"', src)]
    bloque = src[src.index("const NO_VERIFICABLE"):]
    bloque = bloque[:bloque.index("\n}")]
    no_verif = [(m.group(1), m.group(2).strip())
                for m in re.finditer(r'"(§\d) · ([^"]+)":', bloque)]
    return verificadas, no_verif


@lru_cache(maxsize=1)
def brechas_de_diseno() -> List[Tuple[str, str, str]]:
    """(qué falta, evidencia, cita de §2) — medido contra el código, no supuesto.

    🔴 Son las DOS que Franco vio faltando en las capturas, y las dos son invisibles para el
    barrido de decisiones visuales por el mismo motivo estructural: ese barrido verifica que una
    clase ESTÉ donde la decisión dice, y prohíbe el vidrio FUERA de donde §2 lo permite. Ninguna
    de sus dos preguntas puede detectar una decisión que **no se construyó en ningún lado**.
    """
    out: List[Tuple[str, str, str]] = []
    css = "".join((FRONT / "app" / n).read_text(encoding="utf-8", errors="ignore")
                  for n in ("globals.css", "paleta.css", "utilidades.css"))
    if "radial-gradient" not in css.split("scroll")[0] or "9%" not in css:
        out.append((
            "las manchas de fondo (azul al 9%, verde al 7%) no están construidas",
            "app/globals.css pinta `body { @apply bg-background }` — un color plano. Los únicos "
            "`radial-gradient` del front están en app/utilidades.css y son las sombras de scroll "
            "horizontal (negro 0.16 / blanco 0.14), no manchas de color",
            "Fondo con color, suave. Manchas muy diluidas: azul al 9%, verde al 7%."))
    sidebar = (FRONT / "components/layout/Sidebar.tsx").read_text(encoding="utf-8", errors="ignore")
    if "backdrop-blur" not in sidebar:
        out.append((
            "el vidrio del sidebar no está construido",
            "components/layout/Sidebar.tsx usa `bg-sidebar` opaco y su scrim mobile es "
            "`bg-black/50` sin blur. `VIDRIO_PERMITIDO` del barrido lista 4 archivos y el "
            "sidebar no es ninguno: el barrido sólo prohíbe vidrio de más, nunca exige el de menos",
            "Vidrio SOLO en el sidebar y en los modales."))
    return out


# Los cuatro del recorrido manual. 🔴 ÚNICO origen no derivable del repo: los reportó Franco
# probando a mano. Cada uno lleva la evidencia que sí se pudo verificar leyendo el código.
BUGS_DEL_RECORRIDO: List[Tuple[str, str]] = [
    ("clic en el nombre del usuario",
     "components/layout/UserMenu.tsx — verificar qué pasa al hacer clic en el nombre "
     "(¿abre el menú, no hace nada, o navega a una ruta que no existe?)"),
    ("los filtros de objetivos salen desalineados",
     "app/(dashboard)/objetivos/ + components/features/objetivos/ — es la única pantalla que "
     "no monta `<Pagination>` y su barra de filtros convive con el selector de vista "
     "(`TipoObjetivoTabs`), que se agregó el 23/8/2026"),
    ('un 404 de la API se muestra como "Algo salió mal"',
     "components/ui/ErrorState.tsx y app/error.tsx usan ese literal genérico. El backend "
     "distingue 404 de 500 con un `code` propio y la pantalla lo aplana a un solo mensaje"),
    ("SENIOR y senior se cuentan como dos categorías en Distribución de plantilla",
     "services/reportes/_reporte_distribucion.py:33 — `clave = _SIN if ... else crudo` usa el "
     "valor CRUDO. El `.upper()` de la línea de al lado sólo decide si el valor está VACÍO; "
     "no normaliza la clave de agrupación. Afecta al reporte R3 y al KPI de distribución"),
]


@lru_cache(maxsize=1)
def casos() -> List[Caso]:
    """Las familias del punto 5, con su conteo medido contra el código."""
    verificadas, no_verif = decisiones_visuales()
    brechas = brechas_de_diseno()
    return [
        Caso("id INEXISTENTE",
             "todo endpoint que recibe un id, con un uuid que no existe: 404 con el contrato "
             "{error,message,code}, nunca 500",
             "los 24 `maybe_single()` que devolvían 500 (CLAUDE.md · §.single() vs maybe_single). "
             "`tests/test_maybe_single_guarda.py` lo vigila por AST desde adentro; nada lo "
             "vigila desde afuera",
             len(_con_id()), "sí", ""),
        Caso("id de OTRA EMPRESA",
             "el mismo endpoint con un id real de otra empresa: 404 IDÉNTICO al de 'no existe' "
             "— mismo status, mismo code, mismo mensaje. Nunca 403 ni 500",
             "CLAUDE.md · Patrón de barrera de empresa. Es el contrato que el bug de "
             "maybe_single rompía: un recurso ajeno salía 500",
             len(_con_barrera()),
             "sí, sólo sobre datos sembrados",
             "necesita dos empresas con datos propios; hoy hay 2 empresas cargadas"),
        Caso("editar a alguien dado de baja",
             "PUT /api/empleados/{id} y POST /api/recategorizaciones sobre alguien con "
             "estado='baja'. La guarda del egreso rechaza `fecha_efectiva > fecha_egreso` con "
             "422; verificar que lo RETROACTIVO legítimo siga entrando",
             "docs/SEMILLA-SMOKE.md §7 — se descubrió sembrando, con 201 y el legajo pisado",
             2, "sí, sólo sobre datos sembrados",
             "escribe sobre un legajo: sólo sobre los SMK-xx"),
        Caso("contraseña provisoria que nunca vence",
             "entrar por API (POST /api/auth/login + cualquier endpoint) con un usuario que "
             "tiene must_change_password=true y ver que el sistema LO DEJA HACER TODO. Hoy pasa: "
             "el flag lo aplica solo AuthGuard.tsx:29, en el navegador",
             "medido el 23/8/2026 al sembrar los tres usuarios de prueba del smoke. Anotado en "
             "docs/DEUDA-TECNICA.md §1-ter",
             1, "sí",
             "los tres usuarios de smk.* ya tienen el flag bajo; para probarlo hay que crear uno "
             "nuevo y NO cambiarle la contraseña"),
        Caso("los tres roles, uno por uno",
             "el mismo recorrido con smk.admin, smk.gerencia y smk.mando: que gerencia_lectura "
             "reciba 403 en TODA escritura, que mandos_medios reciba 403 fuera de "
             "vacaciones/ausencias, y que dentro de las suyas vea SOLO a sus subordinados",
             "docs/SMOKE-TEST.md declaraba como su límite más grande que los 4 usuarios de "
             "producción son admin_rrhh. Las credenciales las genera la fase `usuarios` de "
             "scripts/semilla_smoke.py",
             3, "sí, sólo sobre datos sembrados",
             "el corte de ownership depende de los manager_id sembrados sobre SMK-xx"),
        Caso("bugs abiertos del recorrido",
             " · ".join(q for q, _ in BUGS_DEL_RECORRIDO),
             "recorrido manual con Franco (23/8/2026). Es el único origen de este documento que "
             "no se deriva del repo",
             len(BUGS_DEL_RECORRIDO), "parcial",
             "el de Distribución es un test de backend; los otros tres son visuales o de "
             "interacción y hoy no hay jsdom en la suite del front"),
        Caso("sistema de diseño §2 y §3",
             "las decisiones punto por punto, incluidas las que el barrido declaró no "
             "verificables y las DOS que están sin construir (ver la tabla de abajo)",
             "docs/SISTEMA-DE-DISENO.md §2 y §3 + components/ui/decisionesVisuales.test.ts",
             len(verificadas) + len(no_verif) + len(brechas), "parcial",
             f"{len(verificadas)} las verifica el barrido por clase CSS; {len(no_verif)} están "
             f"declaradas no verificables desde el código; {len(brechas)} no están construidas"),
    ]
