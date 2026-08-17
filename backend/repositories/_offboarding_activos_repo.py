"""
Acceso a `offboarding_activos` — el equipamiento corporativo que hay que devolver al salir.

Extraído de `offboarding_repo.py`, que llegó a 104/100 al sumarle el cierre de la instancia.

🔑 CRITERIO DE CORTE: UN ARCHIVO POR TABLA. `offboarding_repo.py` queda con
`offboarding_instancias` y este archivo se lleva `offboarding_activos`. No se cortó por
lecturas/escrituras —el otro candidato— porque `create_offboarding` inserta la instancia y
enseguida RELEE sus activos para devolver el response: por ese eje el archivo de escritura tendría
que importar del de lectura y el corte no quedaría limpio en ninguna de las dos direcciones.

⚠️ LOS ACTIVOS NO SE ALCANZAN POR EMPRESA, Y NO ES UN OLVIDO. `offboarding_activos` sí tiene
`empresa_id` (se lo escribe el alta), pero la barrera del módulo va sobre la INSTANCIA: el service
valida `find_instancia_min(id, empresa_id)` y recién entonces toca los activos por `instancia_id`.
Agregar acá un `.eq("empresa_id", ...)` "por consistencia" no compraría seguridad —ya está
comprobada aguas arriba— y sí agregaría un segundo lugar donde acordarse de pasarla, que es
exactamente cómo nacen los filtros que fallan en silencio.

Funciones libres, no una clase: `OffboardingRepo` las delega en una línea y los call sites no
cambian. Mismo molde que `_empleado_write_repo.py`.
"""
from datetime import date
from typing import List

from integrations.supabase_client import supabase_admin
from repositories._offboarding_row import TABLA_ACTIVOS as _OA

# Los cuatro que se le crean a todo offboarding nuevo. Es un catálogo fijo en código, no una
# tabla: son los mismos para toda la empresa y nadie pidió configurarlos.
DEFAULT_ACTIVOS = [
    ("laptop",            "Computadora portátil de trabajo"),
    ("tarjeta_acceso",    "Tarjeta de acceso al edificio"),
    ("licencia_software", "Licencias de software corporativo"),
    ("celular",           "Teléfono corporativo"),
]


def activos_de(instancia_id: str) -> List[dict]:
    """Los activos de una instancia. Lista vacía si no tiene (no None: el caller los cuenta)."""
    res = supabase_admin.table(_OA).select("*").eq("instancia_id", instancia_id).execute()
    return res.data or []


def crear_por_defecto(instancia_id: str, empresa_id: str) -> None:
    """Siembra los cuatro activos por defecto de una instancia recién creada, en UN insert."""
    supabase_admin.table(_OA).insert([
        {"instancia_id": instancia_id, "tipo_activo": t, "descripcion": d,
         "estado": "pendiente", "empresa_id": empresa_id}
        for t, d in DEFAULT_ACTIVOS
    ]).execute()


def update_activo(instancia_id: str, activo_id: str, devuelto: bool) -> bool:
    """Marca un activo como devuelto o lo revierte a pendiente.

    El `.eq("instancia_id", ...)` además del `.eq("id", ...)` es la barrera: sin él, un activo_id
    de otra instancia se actualizaría igual. Devuelve False si el activo no es de esa instancia,
    que es lo que el service traduce a 404."""
    patch: dict = {"estado": "devuelto" if devuelto else "pendiente"}
    if devuelto:
        patch["fecha_devolucion"] = str(date.today())
    res = supabase_admin.table(_OA).update(patch).eq("id", activo_id).eq(
        "instancia_id", instancia_id
    ).execute()
    return bool(res.data)
