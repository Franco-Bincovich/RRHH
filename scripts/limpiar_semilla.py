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

🔴 QUÉ FILAS SON DE LA SEMILLA lo decide `_semilla_plan_borrado.py`, no este archivo. El corte
es deliberado: **"¿qué se borra?" decide si el limpiador deja basura o toca algo real, y "¿cómo
se borra?" —esto— es un DELETE por lotes.** Antes de tocar el plan, leer ese archivo.

⚠️ LO QUE NO BORRA, Y ES DELIBERADO: los eventos de `auditoria`. La tabla es INMUTABLE por diseño
en este repo. `--con-auditoria` borra también las que apuntan a lo sembrado — **decisión de
Franco**: dejarlas significa que /auditoria muestra el alta de nueve personas que ya no existen.
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

from _semilla_cliente import consola_utf8  # noqa: E402
from _semilla_plan_borrado import ORDEN, plan_de_borrado  # noqa: E402
from integrations.supabase_client import supabase_admin  # noqa: E402

MANIFIESTO = RAIZ / ".semilla-smoke.json"

# 🔴 EL ORDEN ES EL DE LAS FKs Y NO ES INTERCAMBIABLE. `costos_nomina.empleado_id` y

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
    plan = plan_de_borrado(datos)
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
