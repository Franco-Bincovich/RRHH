"""
BARRIDO ESTRUCTURAL — todo endpoint de ESCRITURA con id de recurso en el path recibe `Request`.

🔴 ES EL MODO DE FALLA MÁS DIFÍCIL DE VER LEYENDO, y por eso necesita un barrido y no una
revisión. Los otros falsos positivos de la barrera de empresa se detectan siguiendo un
parámetro (el router lo recibe y el service lo ignora); acá NO HAY NINGÚN PARÁMETRO QUE SEGUIR:
el handler simplemente no toma `Request`, así que `empresa_id` no existe en ninguna capa y el
código se lee perfectamente coherente. Encontrado el 23/8/2026 en
`PUT /api/onboarding/{instancia_id}/tareas/{tarea_id}/completar`, que con el header de la
empresa A y la instancia de la B devolvía 200 y completaba la tarea ajena.

**El eje es el PATH, no el método**: un endpoint que CREA (`POST /clientes`) recibe la empresa
en el body y ahí manda el form, no el header — es la regla "mirar = sidebar manda · hacer = el
form manda". El que ya trae un id de recurso de afuera es el que tiene algo que validar.

Las excepciones se declaran UNA POR UNA con su razón, y hay un test que verifica que ninguna
apunte a una ruta que ya no existe: una excepción muerta es ruido que oculta el próximo caso.
"""
import ast
import pathlib

ROUTERS = pathlib.Path(__file__).resolve().parent.parent / "routers"
METODOS_ESCRITURA = {"post", "put", "patch", "delete"}

# (archivo, MÉTODO, path) → por qué este endpoint no necesita la empresa del request.
# 🔴 Son las mismas 8 que la Fase 2 marcó NO APLICA, más las que nacieron después con su motivo.
SIN_EMPRESA_DECLARADOS: dict[tuple[str, str, str], str] = {
    ("empresa.py", "PUT", "/{id}"):
        "la EMPRESA es el recurso: acotar por empresa sería filtrar la empresa por sí misma",
    ("empresa.py", "PATCH", "/{id}/activa"): "ídem: la empresa es el recurso",
    ("empresa.py", "POST", "/{id}/logo"): "ídem: la empresa es el recurso",
    ("integraciones.py", "DELETE", "/{tipo}"):
        "scopeado por user_id, no por empresa: una integración es de la persona",
    ("usuarios_escrituras.py", "DELETE", "/{user_id}"):
        "los usuarios no cuelgan de una empresa (decisión de producto)",
    ("assessment.py", "POST", "/evaluacion/{token}/submit"):
        "público sin auth: la autorización ES el token, no hay request.state.empresa",
    ("clientes_escrituras.py", "PUT", "/{id}"):
        "el catálogo de clientes es GLOBAL desde el bloque L (migs 108/109): sin empresa_id",
    ("clientes_escrituras.py", "DELETE", "/{id}"): "ídem: catálogo global",
    ("perfiles_puesto_escrituras.py", "PUT", "/{id}"):
        "perfiles_puesto no tiene empresa_id: es catálogo del grupo (perfil_puesto_service:10)",
    ("perfiles_puesto_escrituras.py", "DELETE", "/{id}"): "ídem: catálogo del grupo",
    ("evaluaciones_resultados.py", "DELETE", "/lotes/{lote_id}"):
        "la empresa sale de lote.empresa_id (autoritativo), no del header — Vista vs Acción",
    ("horas_cliente_escrituras.py", "DELETE", "/{hora_id}"):
        "las horas de un cliente son del cliente: la vista no se recorta por empresa (bloque L)",
}


def _endpoints_de_escritura() -> list[tuple[str, str, str, str, bool]]:
    """(archivo, MÉTODO, path, handler, recibe_request) de cada endpoint de escritura."""
    encontrados: list[tuple[str, str, str, str, bool]] = []
    for archivo in sorted(ROUTERS.glob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in nodo.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                if dec.func.attr not in METODOS_ESCRITURA:
                    continue
                base = dec.func.value
                if not (isinstance(base, ast.Name) and base.id.startswith("router")):
                    continue
                path = dec.args[0].value if dec.args and isinstance(dec.args[0], ast.Constant) else ""
                params = nodo.args.args + nodo.args.kwonlyargs
                recibe = any(
                    (isinstance(p.annotation, ast.Name) and p.annotation.id == "Request")
                    for p in params
                )
                encontrados.append((archivo.name, dec.func.attr.upper(), path, nodo.name, recibe))
    return encontrados


ENDPOINTS = _endpoints_de_escritura()
CON_ID = [e for e in ENDPOINTS if "{" in e[2]]


def test_guarda_de_minimo_endpoints_de_escritura() -> None:
    """Sin esto, un cambio en el descubrimiento devolvería 0 endpoints y todo pasaría en el
    vacío — el falso verde que este repo ya pagó cuatro veces."""
    assert len(ENDPOINTS) >= 100, f"solo {len(ENDPOINTS)} endpoints de escritura descubiertos"
    assert len(CON_ID) >= 50, f"solo {len(CON_ID)} con id de recurso en el path"


def test_todo_endpoint_con_id_recibe_request_o_esta_declarado() -> None:
    sin_request = [
        (a, m, p, h) for a, m, p, h, recibe in CON_ID
        if not recibe and (a, m, p) not in SIN_EMPRESA_DECLARADOS
    ]
    assert not sin_request, (
        "endpoints de escritura con id de recurso que no reciben Request (no hay forma de "
        "acotar por empresa): " + "\n".join(f"{a} {m} {p} → {h}" for a, m, p, h in sin_request)
    )


def test_ninguna_excepcion_apunta_a_una_ruta_que_ya_no_existe() -> None:
    """Una excepción muerta es ruido que oculta el próximo caso."""
    reales = {(a, m, p) for a, m, p, _, _ in ENDPOINTS}
    muertas = [k for k in SIN_EMPRESA_DECLARADOS if k not in reales]
    assert not muertas, f"excepciones declaradas sobre rutas inexistentes: {muertas}"


def test_toda_excepcion_declara_su_razon() -> None:
    vacias = [k for k, razon in SIN_EMPRESA_DECLARADOS.items() if not razon.strip()]
    assert not vacias, f"excepciones sin razón escrita: {vacias}"
