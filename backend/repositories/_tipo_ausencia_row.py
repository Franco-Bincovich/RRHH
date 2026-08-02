"""
El SELECT de tipos_ausencia y su mapper a schema. Fuente de verdad ÚNICA de las dos cosas.

Molde: `_empleado_row.py`, que hace exactamente esto para empleados y por el mismo motivo — que
la forma de la lectura y la traducción a schema no puedan divergir entre dos lugares. Vive
aparte además porque `tipos_ausencia_repo.py` llegó a 102 contra un límite de 100 al sumarle la
jerarquía.
"""
from schemas.ausencias import TipoAusenciaResponse

TABLE = "tipos_ausencia"

# 🔴 EL EMBED DEL PADRE VA DESAMBIGUADO, y no es opcional. Desde la migración 088 la tabla se
# apunta a sí misma, y esa única FK se puede recorrer en los DOS sentidos (hacia el padre o hacia
# los hijos): un `tipos_ausencia(nombre)` a secas se lee perfecto y PostgREST lo rechaza con
# 300 PGRST201. Es la clase de bug que dejó 6 reportes en blanco en producción.
#
# Se desambigua POR COLUMNA (`padre:padre_id`) y no por constraint, siguiendo el precedente de
# `_empleado_row.py` con `manager:manager_id`: dice el sentido, se lee, y no se rompe si algún
# día la constraint se renombra.
SELECT = ("id, nombre, es_base, activo, empresa_id, cuenta_ausentismo, padre_id, "
          "padre:padre_id(nombre)")


def row(fila: dict) -> TipoAusenciaResponse:
    """Aplana el embed del padre a `padre_nombre`. El embed llega como dict anidado o None."""
    padre = fila.get("padre") or {}
    return TipoAusenciaResponse.model_validate(
        {**{k: v for k, v in fila.items() if k != "padre"},
         "padre_nombre": padre.get("nombre")})
