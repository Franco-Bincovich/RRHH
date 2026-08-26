#!/usr/bin/env python3
"""
NORMALIZA lo que YA ESTÁ CARGADO en `empleados.seniority` y `empleados.categoria`, aplicándoles
la misma regla que desde el 25/8/2026 aplica el código al escribir (`utils/legajo_reglas.py`).

    python scripts/normalizar_legajo.py            # SOLO muestra qué filas tocaría (no escribe)
    python scripts/normalizar_legajo.py --aplicar  # escribe

🔴 ES UN SCRIPT Y NO UNA MIGRACIÓN, A PROPÓSITO. Nació como `migrations/122_...sql` y se movió
acá el 25/8/2026 por dos razones que valen para cualquier corrección futura de datos:
  · **No cambia el schema.** Una migración declara la forma de la base; esto corrige VALORES.
    Mezclarlos hace que `000_run_all` sobre una base nueva ejecute un UPDATE que no tiene nada
    que corregir, y que el historial de migraciones deje de leerse como la historia del modelo.
  · **Un UPDATE sobre datos reales se MIRA antes de correrse.** Una migración se aplica y se
    entera después; acá el default es no escribir nada y mostrar fila por fila qué cambiaría,
    con el valor viejo y el nuevo al lado. Escribir exige `--aplicar`.

🔴 LA REGLA NO SE REESCRIBE ACÁ: se IMPORTA de `utils.legajo_reglas`. Es el punto entero. Si este
script tuviera su propia versión del `lower()`/`upper()`, la corrección de lo viejo y la
normalización de lo nuevo podrían divergir — y quedaría la mitad de la tabla en un formato y la
mitad en otro, que es peor que no haber normalizado nada: el combobox ofrecería las dos grafías
como dos opciones, que es exactamente el problema que todo esto viene a cerrar.

⚠️ IDEMPOTENTE: correrlo dos veces no cambia nada la segunda vez, porque compara el valor actual
contra su forma canónica y sólo escribe los que difieren. Eso además evita disparar el trigger de
`updated_at` sobre filas que ya están bien.

⚠️ NO TOCA `empleados.gerencia`, aunque también sea texto libre del import. Esa columna es la
agrupación del organigrama y su valor tiene que seguir coincidiendo con el NOMBRE del proyecto
homónimo que creó `_nomina_proyectos` a partir del mismo texto. Normalizarla de un lado y no del
otro rompería esa correspondencia. El porqué completo está en `db/schema.sql`.
"""
import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ.parent / "backend"
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(BACKEND))
# `Settings` declara `env_file = ".env"`, RELATIVO al directorio de trabajo: sin este chdir el
# import de abajo revienta pidiendo `supabase_url` estando el archivo ahí al lado.
os.chdir(BACKEND)

from integrations.supabase_client import supabase_admin           # noqa: E402
from utils.legajo_reglas import (                                 # noqa: E402
    normalizar_categoria, normalizar_seniority,
)

# Columna -> la función canónica que le corresponde. La asimetría (una PALABRA va con mayúscula
# inicial, un CÓDIGO va en mayúsculas) está explicada en `utils/legajo_reglas.py`; acá sólo se
# cablea, no se decide.
REGLAS = {"seniority": normalizar_seniority, "categoria": normalizar_categoria}

_SELECT = "id, apellido, nombre, " + ", ".join(REGLAS)


def _cambios() -> list[dict]:
    """Las filas que cambiarían, con el valor viejo y el nuevo por columna. No escribe nada."""
    filas = supabase_admin.table("empleados").select(_SELECT).execute().data or []
    salida = []
    for f in filas:
        parches = {}
        for col, regla in REGLAS.items():
            actual = f.get(col)
            canonico = regla(actual)
            # `!=` cubre los tres casos de una: cambio de caja, limpieza de espacios/guiones, y
            # un literal de "sin dato" ('SIN DATOS', 'N/A'…) que pasa a NULL.
            if actual != canonico:
                parches[col] = (actual, canonico)
        if parches:
            salida.append({"id": f["id"],
                           "quien": f"{f.get('apellido') or ''}, {f.get('nombre') or ''}".strip(", "),
                           "parches": parches})
    return salida


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Normaliza seniority y categoria de los empleados ya cargados.")
    ap.add_argument("--aplicar", action="store_true",
                    help="escribe los cambios. Sin esto sólo los muestra.")
    args = ap.parse_args()

    cambios = _cambios()
    total = (supabase_admin.table("empleados").select("id", count="exact")
             .limit(1).execute().count or 0)

    if not cambios:
        print(f"Nada que normalizar: las {total} filas ya están en su forma canónica.")
        return 0

    print(f"{len(cambios)} de {total} empleados cambiarían:\n")
    for c in cambios:
        for col, (viejo, nuevo) in c["parches"].items():
            print(f"  {c['quien']:<34} {col:<10} {viejo!r:>16}  →  {nuevo!r}")

    if not args.aplicar:
        print("\n(no se escribió nada — volvé a correrlo con --aplicar)")
        return 0

    for c in cambios:
        payload = {col: nuevo for col, (_viejo, nuevo) in c["parches"].items()}
        supabase_admin.table("empleados").update(payload).eq("id", c["id"]).execute()
    print(f"\nListo: {len(cambios)} filas actualizadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
