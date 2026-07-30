#!/usr/bin/env python3
"""
Smoke test profundo de TODA la superficie HTTP del backend, contra un entorno real.

POR QUÉ EXISTE: la suite de pytest tiene 1117 tests y NO detectó los 6 reportes rotos, el
listado de plantillas roto ni el KPI leyendo una columna vacía. El motivo es estructural: el
fake de Supabase implementa `select(*a, **k)` IGNORANDO el argumento, así que acepta cualquier
spec de columnas —exista o no— y no replica la resolución de FKs de PostgREST. Esa familia de
bugs solo aparece pegándole al PostgREST real. Esto es lo que hace eso.

NO vive en tests/ a propósito: necesita red y un token real, así que no puede ser parte de la
suite ni romperla cuando no hay conexión.

🔴 CERO ESCRITURAS. Se corre contra PRODUCCIÓN, con datos reales.
El script solo emite GET. Las rutas de escritura se tocan ÚNICAMENTE en el barrido de auth, y
SIN TOKEN: el AuthMiddleware responde 401 antes de que el request llegue al router, así que no
hay handler que pueda persistir nada. Es la única excepción y está acotada acá.

USO
    export SMOKE_TOKEN="eyJ..."                 # ver docs/SMOKE-TEST.md para obtenerlo
    ./venv/bin/python scripts/smoke_test.py --salida ../docs/SMOKE-TEST.md

    --base URL         backend a probar (default: producción)
    --conteos ARCHIVO  JSON {tabla: filas} para distinguir "vacío normal" de "vacío roto"
    --sin-auth         solo el barrido de 401 y rutas públicas (no necesita token)
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Env mínimo para poder IMPORTAR la app y leer su tabla de rutas. No se usa para conectarse a
# nada: el script habla con el backend desplegado por HTTP. Con valores reales en el entorno,
# estos no pisan nada (setdefault).
for _k, _v in {
    "SUPABASE_URL": "https://smoke.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.smoke.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.smoke.service",
    "JWT_SECRET": "smoke-" + "x" * 40, "ANTHROPIC_API_KEY": "sk-ant-smoke",
    "RESEND_API_KEY": "re_smoke",
}.items():
    os.environ.setdefault(_k, _v)

import httpx  # noqa: E402

from scripts import _smoke_barridos as bar  # noqa: E402
from scripts import _smoke_reporte as rep  # noqa: E402
from scripts import _smoke_rutas as rt  # noqa: E402

BASE_DEFAULT = "https://sofia-backend-pi.vercel.app"
TIMEOUT = 45.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Smoke test profundo del backend (solo lectura).")
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--conteos", type=Path, help="JSON {tabla: filas} para el cruce vacío/roto")
    ap.add_argument("--salida", type=Path, help="ruta del reporte markdown")
    ap.add_argument("--sin-auth", action="store_true", help="solo 401 y públicas; no pide token")
    args = ap.parse_args()

    from main import app  # import tardío: necesita el env de arriba

    rutas = rt.enumerar(app)
    rt.verificar_minimo(rutas)
    print(f"Superficie: {len(rutas)} rutas ({sum(1 for r in rutas if r.es_get)} GET) · base {args.base}\n")

    conteos = json.loads(args.conteos.read_text()) if args.conteos else None
    resultados: List[rep.Resultado] = []
    with httpx.Client(base_url=args.base, timeout=TIMEOUT, follow_redirects=True) as cli:
        print("→ auth (sin token, todas las rutas)")
        resultados += bar.barrer_auth(cli, rutas)
        print("→ rutas públicas")
        resultados += bar.barrer_publicas(cli)

        if not args.sin_auth:
            token = os.environ.get("SMOKE_TOKEN", "").strip()
            if not token:
                raise SystemExit(
                    "ABORTADO: falta SMOKE_TOKEN. Exportalo o corré con --sin-auth.\n"
                    "Cómo obtenerlo: docs/SMOKE-TEST.md")
            bar.verificar_token(cli, token)
            _, _, emp = bar.get(cli, "/api/empresas", token, None)
            empresa = rt.extraer_id(emp)
            print(f"→ GET autenticados (empresa activa: {empresa or 'ninguna'})")
            resultados += bar.barrer_gets(cli, rutas, token, empresa, conteos, rt.TABLA_DE)

    res = rep.resumen(resultados)
    rep.imprimir_consola(resultados, res)
    if args.salida:
        args.salida.write_text(_markdown(args, resultados, res, rutas), encoding="utf-8")
        print(f"\n  reporte → {args.salida}")
    return 1 if res[rep.ROTO] else 0


def _markdown(args, resultados, res, rutas) -> str:
    """Reporte completo. El cuerpo narrativo del doc lo mantiene una persona; esto regenera
    las secciones de datos."""
    from datetime import datetime, timezone

    return "\n".join([
        "<!-- Generado por backend/scripts/smoke_test.py — no editar a mano las tablas -->",
        f"\n_Corrida: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · base `{args.base}` · "
        f"{len(rutas)} rutas enumeradas_\n",
        f"**{res[rep.ROTO]} ROTO · {res[rep.SOSPECHOSO]} SOSPECHOSO · "
        f"{res[rep.NO_PROBADO]} NO PROBADO · {res[rep.OK]} OK**\n",
        "## Hallazgos", rep.hallazgos(resultados),
        "\n## Los 10 más lentos\n", rep.top_lentos(resultados),
        "\n## Resultados por módulo", rep.tabla_markdown(resultados),
    ])


if __name__ == "__main__":
    raise SystemExit(main())
