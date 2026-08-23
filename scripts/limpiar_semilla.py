#!/usr/bin/env python3
"""
DESHACE lo que sembró `semilla_smoke.py`. Exactamente eso y nada más.

    python scripts/limpiar_semilla.py            # SOLO muestra el plan (no borra)
    python scripts/limpiar_semilla.py --si       # ejecuta
    python scripts/limpiar_semilla.py --si --con-auditoria

🔴 POR QUÉ ESTE VA POR LA BASE Y EL SEMBRADOR POR LA API, que es la asimetría que hay que
entender antes de tocarlo. Sembrar por la API tiene tres razones (guardas, ejercitar los caminos
de escritura, estados derivados) y NINGUNA de las tres aplica al borrado: no hay guarda que
ejercitar en un DELETE, y sobre todo **la API no puede hacerlo**. `empleados`, `costos_nomina`,
`recategorizaciones` y `offboarding_instancias` NO TIENEN endpoint de borrado —en el caso de
recategorizaciones es una decisión explícita del módulo, no un olvido— y el DELETE de
`perfiles_puesto` es una baja LÓGICA: deja la fila. Un limpiador que solo usara la API dejaría
nueve colaboradores inventados en el padrón sin ninguna forma de sacarlos.

🔴 CÓMO SE DISTINGUE LO SEMBRADO DE LO REAL — DOS CAPAS, en este orden:
  1. **El manifiesto** (`scripts/.semilla-smoke.json`): el id exacto de cada fila creada. Es la
     única capa que sirve para `costos_nomina`, porque esas filas cuelgan de colaboradores
     REALES y una tabla de montos no admite marca de agua.
  2. **La clave natural**, para cuando el manifiesto no está (otra máquina, otro clon): el
     legajo `SMK-xx` y el dominio `@semilla.hrkarstec.site` en los colaboradores, y los nombres
     y títulos literales de `_semilla_padron.py` / `_semilla_catalogo.py` en todo lo demás.
     Todo lo que cuelga de un colaborador sembrado se resuelve por su `empleado_id`.

⚠️ LO QUE NO BORRA, Y ES DELIBERADO: los eventos de `auditoria`. La tabla es INMUTABLE por
diseño en este repo y sus filas son el registro de que alguien escribió algo. Con `--con-auditoria`
se borran también las que apuntan a las filas sembradas — **decisión de Franco, no del script**:
dejarlas significa que /auditoria va a mostrar el alta de nueve personas que ya no existen.
"""
import argparse
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ.parent / "backend"
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(BACKEND))
# `Settings` declara `env_file = ".env"`, que es RELATIVO al directorio de trabajo: sin este
# chdir el import de abajo revienta pidiendo `supabase_url` estando el archivo ahí al lado.
os.chdir(BACKEND)

from _semilla_catalogo import (  # noqa: E402
    CAPACITACIONES, EVENTOS, NOMBRES_LIBRES, OBJETIVOS, PERFILES, VACANTES,
)
from _semilla_padron import DOMINIO, PERSONAS  # noqa: E402
from integrations.supabase_client import supabase_admin  # noqa: E402
from _semilla_cliente import consola_utf8  # noqa: E402

MANIFIESTO = RAIZ / ".semilla-smoke.json"

# 🔴 EL ORDEN ES EL DE LAS FKs Y NO ES INTERCAMBIABLE. `costos_nomina.empleado_id` y
# `offboarding_instancias.empleado_id` son ON DELETE **RESTRICT**: con una sola fila viva de
# cualquiera de las dos, el DELETE del colaborador falla. `empleado_capacitacion` cuelga de las
# dos puntas (capacitación y colaborador) y por eso encabeza.
ORDEN = [
    ("empleado_capacitacion", "asignaciones_formacion"),
    ("capacitaciones", "capacitaciones"),
    ("costos_nomina", "costos_nomina"),
    ("recategorizaciones", "recategorizaciones"),
    ("offboarding_instancias", "offboarding"),
    ("candidatos", "candidatos"),
    ("vacantes", "vacantes"),
    ("objetivos", "objetivos"),
    ("eventos_agenda", "eventos_agenda"),
    ("perfiles_puesto", "perfiles_puesto"),
    ("empleados", "empleados"),
]


def _ids_manifiesto(datos: dict, recurso: str) -> list:
    """Los ids anotados de un recurso. Los valores centinela ("hecho") no son ids: se filtran."""
    return sorted({v for v in (datos.get(recurso) or {}).values()
                   if isinstance(v, str) and v != "hecho"})


def _empleados_por_clave_natural() -> list:
    """Los colaboradores sembrados, por legajo `SMK-xx` Y por el dominio del mail.

    Los DOS criterios y no uno: el legajo es único por empresa (no globalmente) y el mail es
    único en todo el sistema, así que juntos cubren el caso de un legajo repetido entre las dos
    sociedades. Es la red que salva si el manifiesto se perdió.
    """
    legajos = [p["legajo"] for p in PERSONAS]
    por_legajo = supabase_admin.table("empleados").select("id").in_("legajo", legajos).execute()
    por_mail = (supabase_admin.table("empleados").select("id")
                .ilike("email_corporativo", f"%@{DOMINIO}").execute())
    return sorted({r["id"] for r in (por_legajo.data or []) + (por_mail.data or [])})


def _hijas_de(tabla: str, columna: str, ids: list) -> list:
    if not ids:
        return []
    res = supabase_admin.table(tabla).select("id").in_(columna, ids).execute()
    return [r["id"] for r in (res.data or [])]


def _por_nombre(tabla: str, columna: str, valores: list) -> list:
    res = supabase_admin.table(tabla).select("id").in_(columna, valores).execute()
    return [r["id"] for r in (res.data or [])]


def _plan(datos: dict) -> dict:
    """`{tabla: [ids]}`. Une lo anotado con lo que la clave natural encuentra: la unión es lo que
    hace que un manifiesto incompleto (corrida cortada a la mitad) igual limpie todo."""
    empleados = sorted(set(_ids_manifiesto(datos, "empleados")) | set(_empleados_por_clave_natural()))
    caps = sorted(set(_ids_manifiesto(datos, "capacitaciones")) |
                  set(_por_nombre("capacitaciones", "nombre", [c["nombre"] for c in CAPACITACIONES])))
    vacantes = sorted(set(_ids_manifiesto(datos, "vacantes")) |
                      set(_por_nombre("vacantes", "titulo", [v["titulo"] for v in VACANTES])))
    asignaciones = sorted(set(_ids_manifiesto(datos, "asignaciones_formacion")) |
                          set(_hijas_de("empleado_capacitacion", "capacitacion_id", caps)) |
                          set(_hijas_de("empleado_capacitacion", "empleado_id", empleados)) |
                          set(_por_nombre("empleado_capacitacion", "nombre_libre", NOMBRES_LIBRES)))
    return {
        "empleado_capacitacion": asignaciones,
        "capacitaciones": caps,
        # 🔴 SOLO POR MANIFIESTO. Estas filas cuelgan de colaboradores REALES: no hay clave
        # natural que las separe de una carga de RRHH del mismo mes. Sin manifiesto no se tocan.
        "costos_nomina": _ids_manifiesto(datos, "costos_nomina"),
        "recategorizaciones": sorted(set(_ids_manifiesto(datos, "recategorizaciones")) |
                                     set(_hijas_de("recategorizaciones", "empleado_id", empleados))),
        "offboarding_instancias": sorted(set(_ids_manifiesto(datos, "offboarding")) |
                                         set(_hijas_de("offboarding_instancias", "empleado_id", empleados))),
        "candidatos": sorted(set(_ids_manifiesto(datos, "candidatos")) |
                             set(_hijas_de("candidatos", "vacante_id", vacantes))),
        "vacantes": vacantes,
        "objetivos": sorted(set(_ids_manifiesto(datos, "objetivos")) |
                            set(_por_nombre("objetivos", "titulo", [o["titulo"] for o in OBJETIVOS]))),
        "eventos_agenda": sorted(set(_ids_manifiesto(datos, "eventos_agenda")) |
                                 set(_por_nombre("eventos_agenda", "nombre", [e["nombre"] for e in EVENTOS]))),
        "perfiles_puesto": sorted(set(_ids_manifiesto(datos, "perfiles_puesto")) |
                                  set(_por_nombre("perfiles_puesto", "nombre", [p["nombre"] for p in PERFILES]))),
        "empleados": empleados,
    }


def _borrar(tabla: str, ids: list) -> int:
    """DELETE por lotes de 100: PostgREST manda el `in.(...)` en la URL y con 62 uuid ya pesa."""
    total = 0
    for i in range(0, len(ids), 100):
        lote = ids[i:i + 100]
        res = supabase_admin.table(tabla).delete().in_("id", lote).execute()
        total += len(res.data or [])
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="Borra los datos sembrados por semilla_smoke.py.")
    ap.add_argument("--si", action="store_true", help="ejecuta el borrado (sin esto solo muestra)")
    ap.add_argument("--con-auditoria", action="store_true",
                    help="borra también los eventos de auditoría de estas filas (ver el encabezado)")
    args = ap.parse_args()
    consola_utf8()

    datos = json.loads(MANIFIESTO.read_text(encoding="utf-8")) if MANIFIESTO.exists() else {}
    if not datos:
        print(f"⚠️  Sin manifiesto en {MANIFIESTO}: se limpia SOLO por clave natural.\n"
              "   `costos_nomina` queda intacta — es la única sin clave natural posible.\n")
    plan = _plan(datos)
    print("PLAN DE BORRADO (en orden de FKs):")
    for tabla, _ in ORDEN:
        print(f"  {tabla:26} {len(plan[tabla]):4} filas")
    if not args.si:
        print("\nNada borrado. Volvé a correrlo con --si para ejecutar.")
        return 0

    todos = [i for tabla, _ in ORDEN for i in plan[tabla]]
    print("\nBORRANDO:")
    for tabla, _ in ORDEN:
        borradas = _borrar(tabla, plan[tabla])
        print(f"  {tabla:26} {borradas:4} borradas")
    if args.con_auditoria:
        print(f"  auditoria                  {_borrar_auditoria(todos):4} borradas")
    MANIFIESTO.unlink(missing_ok=True)
    print(f"\n✅ Listo. Manifiesto eliminado ({MANIFIESTO.name}).")
    return 0


def _borrar_auditoria(registro_ids: list) -> int:
    """Los eventos de auditoría de las filas borradas. Ver el encabezado: NO es el default."""
    total = 0
    for i in range(0, len(registro_ids), 100):
        res = (supabase_admin.table("auditoria").delete()
               .in_("registro_id", registro_ids[i:i + 100]).execute())
        total += len(res.data or [])
    return total


if __name__ == "__main__":
    raise SystemExit(main())
