"""
El flujo de CARGA de nómina: el upsert de una fila y el chequeo de qué períodos ya existen.

SALIÓ DE `nomina_repo.py`, que estaba en 119/100 al sumarle la paginación del listado. Molde:
`_empleado_write_repo.py` y `_vacante_write_repo.py`.

🔑 POR QUÉ ESTAS DOS JUNTAS, si una escribe y la otra lee. Las dos sirven al MISMO flujo: el
preview del import llama a `periodos_cargados` para marcar qué filas del CSV son actualización y
cuáles altas, y el confirmar llama a `save_nomina` para persistirlas. Cortar por "read/write"
las habría separado y dejado a la de lectura sola en el repo, sin nada que la explique. El corte
que sirve es por CASO DE USO.

⚠️ `save_nomina` también lo usa la edición manual de una fila (`_costos_write.cargar_nomina`), que
no es el import — pero es el mismo upsert con el mismo `on_conflict`, y ésa es justamente la razón
por la que hay UNA sola función: dos upserts sobre `UNIQUE (empleado_id, anio, mes)` que se
separaran darían dos formas distintas de resolver el mismo conflicto.
"""
from integrations.supabase_client import supabase_admin
from repositories._nomina_row import SELECT as _NOM_SEL
from repositories._nomina_row import TABLE as _NOM
from repositories._nomina_row import row as _to_nomina
from schemas.costo import NominaCreate, NominaResponse
from utils.errors import AppError


def guardar(data: NominaCreate) -> NominaResponse:
    """Upsert de nómina. empresa_id se hereda del empleado (FK compuesta garantiza coherencia)."""
    empleado_id = str(data.empleado_id)  # UUID → str: sale a PostgREST en el .eq() Y en el payload
    emp_res = (
        supabase_admin.table("empleados")
        .select("empresa_id")
        .eq("id", empleado_id)
        .maybe_single()
        .execute()
    )
    if not emp_res.data or not emp_res.data.get("empresa_id"):
        raise AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
    cargas = max(0.0, data.monto_bruto - data.monto_neto)
    payload = {
        "empleado_id": empleado_id, "mes": data.mes, "anio": data.anio,
        "salario_bruto": data.monto_bruto, "cargas_sociales": cargas,
        "empresa_id": str(emp_res.data["empresa_id"]),
    }
    upsert_res = supabase_admin.table(_NOM).upsert(payload, on_conflict="empleado_id,anio,mes").execute()
    row_res = (
        supabase_admin.table(_NOM).select(_NOM_SEL)
        .eq("id", upsert_res.data[0]["id"]).single().execute()
    )
    return _to_nomina(row_res.data)


def periodos_cargados(empresa_id: str) -> set[tuple]:
    """Conjunto de (empleado_id, anio, mes) ya registrados en la empresa.

    Lo usa el PREVIEW del import de nómina para marcar `es_actualizacion`. Vivía en
    `nomina_csv_service` como query suelta: es la única tabla de este repo y no tenía por
    qué resolverla el service.
    """
    res = supabase_admin.table(_NOM).select("empleado_id,anio,mes").eq("empresa_id", empresa_id).execute()
    return {(r["empleado_id"], int(r["anio"]), int(r["mes"])) for r in (res.data or [])}
