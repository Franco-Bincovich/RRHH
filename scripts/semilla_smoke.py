#!/usr/bin/env python3
"""
SEMILLA DE DATOS DE PRUEBA para el recorrido con Capital Humano. Siembra las ocho tablas que
están en cero, POR LA API — nunca por INSERT directo.

🔴 POR QUÉ POR LA API Y NO POR SQL, que es lo que decide todo lo demás en estos archivos:
  1. Un INSERT se saltea las guardas, y entonces el smoke prueba filas que el sistema nunca
     habría producido. Es el "padrón del fake" aplicado a producción.
  2. Sembrar por la API EJERCITA los caminos de escritura: si algo está roto, aparece acá y no
     en el recorrido. Varios de estos endpoints nunca corrieron contra la base real.
  3. Los estados derivados —`fecha_egreso` y `motivo_baja` de una baja, los `*_anterior` de una
     recategorización, la `empresa_id` que cada fila hereda de su padre— los calcula el backend.
     A mano quedan inconsistentes, y la pantalla muestra la inconsistencia.

    $env:SEMILLA_TOKEN = "eyJ..."                 # o SEMILLA_USUARIO / SEMILLA_PASSWORD
    python scripts/semilla_smoke.py --solo perfiles
    python scripts/semilla_smoke.py

🔴 LA CREDENCIAL NUNCA VA POR LA LÍNEA DE COMANDOS: queda en el historial de PowerShell, en texto
plano. Ver `_credencial`.

    --base URL      backend a sembrar (default: producción)
    --pausa SEG     espera entre escrituras (default 0.15; ver `_semilla_cliente`)
    --solo FASE     una sola fase, repetible: perfiles · personas · recategorizaciones ·
                    offboarding · eventos · nomina · formacion · objetivos · vacantes

🔴 RE-EJECUTABLE: correrlo dos veces no duplica nada. Las dos capas que lo garantizan —el
manifiesto y la clave natural— están explicadas en `_semilla_cliente.Cliente.obtener_o_crear`.

🔴 SE DESHACE CON `scripts/limpiar_semilla.py`, que borra exactamente esto y nada más. Sembrar
sin poder limpiar deja nueve colaboradores inventados en el padrón el día de la entrega.

⚠️ NO TOCA A LOS 31 COLABORADORES REALES. La única fase que los nombra es la de nómina, que les
agrega filas en una tabla HIJA (`costos_nomina`) sin modificar el legajo. Los preingresos y las
bajas van sobre gente nueva, y las recategorizaciones también — el porqué de eso último está en
`_semilla_padron.py` y es la decisión menos obvia de esta tanda.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _semilla_fases_catalogo as cat  # noqa: E402
import _semilla_fases_formacion as form  # noqa: E402
import _semilla_fases_licencias as lic  # noqa: E402
import _semilla_fases_nomina as nom  # noqa: E402
import _semilla_fases_personas as per  # noqa: E402
import _semilla_fases_usuarios as usr  # noqa: E402
from _semilla_cliente import Cliente, TokenVencido, consola_utf8  # noqa: E402
from _semilla_credencial import credencial  # noqa: E402
from _semilla_guarda import ColaboradorReal, exigir_sembrado  # noqa: E402
from _semilla_padron import DOMINIO  # noqa: E402

BASE_DEFAULT = "https://sofia-backend-pi.vercel.app"
FASES = ["perfiles", "personas", "usuarios", "recategorizaciones", "offboarding", "eventos",
         "ausencias", "vacaciones", "nomina", "formacion", "objetivos", "vacantes"]


def _contexto(cli: Cliente) -> dict:
    """Lo que la siembra necesita del sistema vivo: empresas, áreas, usuarios y el padrón real.

    🔴 EL PADRÓN REAL SE FILTRA POR EL DOMINIO DE LA MARCA. Si no, una segunda corrida le
    cargaría nómina a los colaboradores que la corrida anterior sembró, y el conteo de "31 filas
    por mes" empezaría a crecer solo sin que nadie lo pidiera.
    """
    empresas = [e for e in cli.get("/api/empresas")["items"] if e.get("activa", True)]
    if not empresas:
        raise SystemExit("ABORTADO: no hay empresas activas. La semilla no crea empresas.")
    areas = {e["id"]: cli.get("/api/areas/opciones", params={"empresa_id": e["id"]})
             for e in empresas}
    vacias = [e["nombre"] for e in empresas if not areas[e["id"]]]
    if vacias:
        raise SystemExit(f"ABORTADO: sin áreas cargadas en {', '.join(vacias)}. "
                         "Todo colaborador necesita un área; la semilla no crea áreas.")
    usuarios = [str(u["id"]) for u in cli.get("/api/usuarios")["items"]]
    if not usuarios:
        raise SystemExit("ABORTADO: no hay usuarios activos y los objetivos cuelgan de uno "
                         "(`objetivos.responsable_id` es FK a `users`, no a `empleados`).")
    reales = []
    for e in empresas:
        pagina = cli.get("/api/empleados", params={"page_size": 100}, empresa=e["id"])
        reales += [dict(i, empresa_id=e["id"]) for i in pagina["items"]
                   if DOMINIO not in (i.get("email_corporativo") or "")]
    print(f"  contexto: {len(empresas)} empresas · "
          f"{sum(len(v) for v in areas.values())} áreas · {len(usuarios)} usuarios · "
          f"{len(reales)} colaboradores reales\n")
    return dict(empresas=empresas, areas=areas, usuarios=usuarios, reales=reales)


def _correr(cli: Cliente, ctx: dict, fases: list, base: str) -> dict:
    """Corre las fases pedidas en el orden del ciclo de vida. Devuelve lo sembrado por fase."""
    principal = ctx["empresas"][0]["id"]
    personas = {}
    if "personas" in fases:
        personas = per.sembrar_empleados(cli, ctx["empresas"], ctx["areas"])
    if not personas:
        # Las fases de abajo necesitan los ids de los 9. Si no se sembraron en esta corrida,
        # salen del manifiesto: es lo que permite `--solo offboarding` en una corrida aparte.
        personas = _desde_manifiesto(cli, ctx)
    if "perfiles" in fases:
        cat.sembrar_perfiles(cli)
    if "usuarios" in fases:
        # Va DESPUÉS de personas y ANTES de offboarding, y las dos mitades importan: necesita a
        # SMK-10 y a los cuatro a cargo ya creados, y conviene colgar la jerarquía antes de que
        # las bajas se efectivicen — un `PUT /api/empleados` sobre alguien ya dado de baja es
        # justo el caso que `docs/SEMILLA-SMOKE.md` §7 dejó anotado como pregunta abierta.
        usr.sembrar_usuarios(cli, base, personas)
    if "recategorizaciones" in fases:
        per.sembrar_recategorizaciones(cli, personas)
    if "offboarding" in fases:
        per.sembrar_offboarding(cli, personas)
    if "eventos" in fases:
        cat.sembrar_eventos(cli, principal)
    if "ausencias" in fases:
        lic.sembrar_ausencias(cli, personas, exigir_sembrado)
    if "vacaciones" in fases:
        lic.sembrar_vacaciones(cli, personas, exigir_sembrado)
    if "nomina" in fases:
        nom.sembrar_nomina(cli, ctx["reales"])
    if "formacion" in fases:
        form.sembrar_formacion(cli, principal, ctx["reales"])
    if "objetivos" in fases:
        cat.sembrar_objetivos(cli, principal, ctx["usuarios"])
    if "vacantes" in fases:
        cat.sembrar_vacantes(cli, principal, ctx["areas"][principal])
    return personas


def _desde_manifiesto(cli: Cliente, ctx: dict) -> dict:
    """Reconstruye `{legajo: {...}}` de una corrida anterior, para poder correr fases sueltas."""
    from _semilla_padron import PERSONAS

    anotados = cli.manifiesto.datos.get("empleados") or {}
    empresas = ctx["empresas"]
    return {p["legajo"]: dict(p, id=anotados[p["legajo"]],
                              empresa_id=empresas[i % len(empresas)]["id"])
            for i, p in enumerate(PERSONAS) if p["legajo"] in anotados}


def _reporte(cli: Cliente) -> int:
    """Los fallos, agrupados. Un fallo NO es un obstáculo del script: es el hallazgo que esta
    corrida existe para producir, porque varios de estos caminos nunca se usaron de verdad."""
    if not cli.fallos:
        print("\n✅ Sin fallos: todos los endpoints de escritura respondieron OK.")
        return 0
    print(f"\n🔴 {len(cli.fallos)} FALLOS DE API — cada uno es un hallazgo, no un obstáculo:")
    for f in cli.fallos:
        print(f"  · [{f['fase']}] {f['detalle']}\n"
              f"      {f['metodo']} {f['ruta']} → {f['status']}\n      {f['cuerpo']}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Siembra datos de prueba por la API.")
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--pausa", type=float, default=0.15)
    ap.add_argument("--solo", action="append", choices=FASES,
                    help="corre una sola fase (repetible)")
    args = ap.parse_args()
    consola_utf8()

    token = credencial(args.base)

    cli = Cliente(args.base, token, args.pausa)
    print(f"Sembrando en {args.base}\n")
    interrumpida = ""
    try:
        ctx = _contexto(cli)
        _correr(cli, ctx, args.solo or FASES, args.base)
    except TokenVencido as exc:
        # 🔴 El token dura ~1 hora. Al primer 401 se PARA: seguir mandando requests con una
        # credencial muerta llenaría el reporte de fallos falsos y dejaría fases con ids a medias.
        interrumpida = (
            f"\n🔴 TOKEN VENCIDO O INVÁLIDO — la corrida se detuvo acá:\n   {exc}\n"
            "   Lo sembrado hasta este punto ESTÁ en el manifiesto y no se pierde.\n"
            "   Sacá un token nuevo y volvé a correr: las fases ya hechas se saltean solas.")
    except ColaboradorReal as exc:
        interrumpida = f"\n🔴 {exc}"
    finally:
        salida = _reporte(cli)
        if interrumpida:
            print(interrumpida)
            salida = 1
        print(f"\nManifiesto: {cli.manifiesto.ruta}")
        print("Para deshacer: python scripts/limpiar_semilla.py --si")
        cli.cerrar()
    return salida


if __name__ == "__main__":
    raise SystemExit(main())
