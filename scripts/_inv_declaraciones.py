"""
LO QUE SE DECLARA A MANO, porque la razón es de PRODUCTO y no se lee del código.

🔴 ARCHIVO PROPIO Y NO DOS CONSTANTES MÁS EN `_inv_casos.py`, que ya se pasó de las 200 líneas
cuando la primera creció. El corte no es por tamaño: **todo lo demás de este inventario se
DESCUBRE recorriendo el código —`app.routes`, el árbol de `app/`, el grafo de imports— y estas
dos listas no se pueden descubrir de ninguna manera.** Que `empresas/{id}` no valide empresa no
es un descuido que un barrido pueda detectar: es que la empresa ES el recurso. Mezclarlas con los
conteos hacía que se leyeran como una medición más, que es exactamente cómo se colaron los seis
del catálogo global durante meses.

⚠️ CADA ENTRADA LLEVA SU RAZÓN Y SE VERIFICA. El barrido de `tests/test_inventario_smoke.py`
comprueba que la ruta declarada siga existiendo: una excepción que apunta a un endpoint borrado
es ruido que tapa el próximo caso.
"""
from typing import Dict, Tuple

# 🔴 Los endpoints que NO APLICAN para la barrera de empresa, con su razón. Citado de CLAUDE.md,
# sección "Patrón de barrera de empresa" — salvo los siete de abajo, que salieron de correr el
# smoke contra producción el 23/8/2026.
#
# 🔴 LOS 6 DE LOS CATÁLOGOS GLOBALES, y su ausencia no era cosmética. `clientes` y
# `perfiles_puesto` NO TIENEN COLUMNA `empresa_id` —el catálogo es del grupo, no de una
# sociedad— así que pedirles barrera es pedirles un filtro que dejaría el catálogo VACÍO sin
# ningún error. Los dos repos lo dicen de frente en su encabezado (`perfil_puesto_repo.py`:
# «NO HAY BARRERA DE EMPRESA, Y NO ES UN OLVIDO»), pero este inventario los contaba dentro de
# los 104 igual: una lista que le pide a seis endpoints exactamente lo que su código prohíbe.
# El daño no es el conteo sino que el que la lea dentro de un mes va a "arreglar" el catálogo
# global. Medido en vivo: el listado devuelve los mismos 5 perfiles y los mismos 4 clientes con
# cualquiera de las dos empresas en el header.
SIN_BARRERA: Dict[Tuple[str, str], str] = {
    ("DELETE", "/api/usuarios/{user_id}"): "los usuarios no cuelgan de una empresa",
    ("GET", "/api/empresas/{id}"): "la empresa ES el recurso",
    ("PUT", "/api/empresas/{id}"): "la empresa ES el recurso",
    ("PATCH", "/api/empresas/{id}/activa"): "la empresa ES el recurso",
    ("POST", "/api/empresas/{id}/logo"): "la empresa ES el recurso",
    ("GET", "/api/assessment/evaluacion/{token}"): "sin auth: la autorización es el token",
    ("POST", "/api/assessment/evaluacion/{token}/submit"): "sin auth: la autorización es el token",
    ("DELETE", "/api/integraciones/{tipo}"): "scopeado por user_id, no por empresa",
    ("GET", "/api/clientes/{id}"): "catálogo GLOBAL: la tabla no tiene empresa_id",
    ("PUT", "/api/clientes/{id}"): "catálogo GLOBAL: la tabla no tiene empresa_id",
    ("DELETE", "/api/clientes/{id}"): "catálogo GLOBAL: la tabla no tiene empresa_id",
    ("GET", "/api/perfiles-puesto/{id}"): "catálogo GLOBAL: la tabla no tiene empresa_id",
    ("PUT", "/api/perfiles-puesto/{id}"): "catálogo GLOBAL: la tabla no tiene empresa_id",
    ("DELETE", "/api/perfiles-puesto/{id}"): "catálogo GLOBAL: la tabla no tiene empresa_id",
    # 🔴 L9: las horas de un cliente son DEL CLIENTE. Ninguna de las cuatro superficies de "Horas
    # por cliente" se recorta por empresa, y la baja tampoco: `horas_cliente_service.eliminar` lo
    # declara en su docstring («Sin recorte por empresa (L9): se borra por `id`, que es lo único
    # que identifica la fila»). Medido en vivo el 23/8/2026: con el header de la empresa A borra
    # una carga de la B y devuelve 204. Es la decisión, no un agujero — el reparto por sociedad
    # se muestra desglosado adentro de cada cliente y la pantalla avisa que el selector no manda.
    ("DELETE", "/api/horas-cliente/{hora_id}"): "L9: las horas son del CLIENTE, no de la empresa",
}

# 🔴 Los endpoints que dan 404 pero NO con el contrato `{error, message, code}` de la app.
# Declarado el 23/8/2026, corriendo la familia «id INEXISTENTE» contra producción: los dos de
# assessment devuelven `{"detail": "Not Found"}`, que es el 404 DE PLATAFORMA de FastAPI.
#
# 🔑 Y ES LO CORRECTO, no un bug: con `ASSESSMENT_ENABLED=false` el router NO SE MONTA, así que
# para FastAPI esas rutas no existen y responden igual que cualquier URL inventada — que es
# justamente lo que CLAUDE.md busca («nunca un 403 ni un mensaje que confirme que el módulo está
# ahí»). Lo que estaba mal era la FAMILIA: afirmaba el contrato para sus 115 filas y dos de ellas
# no lo pueden cumplir por diseño. Una familia que promete de más se lee como cobertura.
CONTRATO_404_APARTE: Dict[Tuple[str, str], str] = {
    ("GET", "/api/assessment/evaluacion/{token}"):
        "flag apagado: el router no se monta y sale el 404 de plataforma",
    ("GET", "/api/assessment/resultados/{resultado_id}"):
        "flag apagado: el router no se monta y sale el 404 de plataforma",
    ("POST", "/api/assessment/evaluacion/{token}/submit"):
        "flag apagado: el router no se monta y sale el 404 de plataforma",
    ("POST", "/api/assessment/campanas/{campana_id}/links"):
        "flag apagado: el router no se monta y sale el 404 de plataforma",
}
