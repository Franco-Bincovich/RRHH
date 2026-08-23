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

🔴 LOS TRES USUARIOS DE PRUEBA NO DESAPARECEN COMO EL RESTO DE LA SEMILLA, Y ES DELIBERADO.
A los nueve colaboradores y a todo lo que cuelga de ellos los borra un DELETE y dejan de existir.
A los tres usuarios (`smk.admin`, `smk.gerencia`, `smk.mando`) se les **REVOCA EL ACCESO** con
`DELETE /api/usuarios/{id}`, que es una baja BLANDA: `activo=false` + **ban permanente en
Supabase Auth**. La fila queda, y en `/usuarios` se ven como inactivos.

  · **Por qué por la API y no por base:** es la misma regla que sostiene toda la semilla —se
    siembra por la API y se borra por la API cuando la API puede—, y acá pesa más que en ningún
    otro lado: un DELETE desde el script borraría **sin dejar rastro en la auditoría**, que es
    justo lo que no se quiere de un usuario con acceso al sistema.
  · **Por qué la baja blanda alcanza:** la preocupación es "un usuario con contraseña conocida
    sigue siendo un acceso", y eso lo cierra el ban de ~100 años, que le corta el login Y el
    refresh. El `activo=false` solo corta la API.
  · **Por qué está BIEN que queden visibles:** un acceso revocado tiene que verse. Un usuario que
    desaparece de la pantalla es un usuario que nadie puede auditar.
  · **Lo que NO hay que hacer:** agregar `users` a `ORDEN`. Ver `_semilla_baja_usuarios.py`, que
    explica por qué eso sería peor que las dos opciones (deja la identidad viva y sin banear en
    Supabase Auth, invisible desde el sistema).

⚠️ ESTE PASO PIDE CREDENCIAL DE `admin_rrhh` y el resto del limpiador no. Si no hay token, el
borrado por base corre igual y los usuarios quedan avisados como pendientes: es preferible a
abortar la limpieza entera por una credencial que solo hace falta para tres filas.

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

from _semilla_baja_usuarios import dar_de_baja, resumen_plan  # noqa: E402
from _semilla_cliente import consola_utf8  # noqa: E402
from _semilla_plan_borrado import ORDEN, plan_de_borrado, usuarios_sembrados  # noqa: E402
from integrations.supabase_client import supabase_admin  # noqa: E402

MANIFIESTO = RAIZ / ".semilla-smoke.json"
BASE_DEFAULT = "https://sofia-backend-pi.vercel.app"

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
    usuarios = usuarios_sembrados(datos)
    print("PLAN DE BORRADO (en orden de FKs):")
    for tabla, _ in ORDEN:
        print(f"  {tabla:26} {len(plan[tabla]):4} filas")
    linea = resumen_plan(usuarios)
    if linea:
        print(linea)
        print("    ↑ NO se borran: se les revoca el acceso por la API. Ver el encabezado.")
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
    pendientes = _revocar_accesos(usuarios)
    MANIFIESTO.unlink(missing_ok=True)
    print(f"\n✅ Listo. Manifiesto eliminado ({MANIFIESTO.name}).")
    if pendientes:
        print("🔴 QUEDARON ACCESOS VIVOS — revocalos antes de dar la limpieza por terminada:")
        for x in pendientes:
            print(f"   · {x}")
        return 1
    return 0


def _revocar_accesos(usuarios: list) -> list:
    """Da de baja los usuarios de prueba por la API. Devuelve los que quedaron pendientes.

    🔴 La credencial se pide ACÁ y no al principio: es el único paso que la necesita, y pedirla
    de entrada obligaría a tener un token de admin para limpiar datos que se borran por base sin
    ninguno. Si falta, el resto de la limpieza ya corrió y lo que queda se dice fuerte y con
    código 1 — devolver 0 con tres accesos vivos sería el peor final posible para este script.
    """
    if not usuarios:
        return []
    activos = [u for u in usuarios if u.get("activo", True)]
    if not activos:
        print("\n  usuarios de prueba: los 3 ya estaban sin acceso.")
        return []
    print("\nREVOCANDO ACCESOS (por la API, baja blanda — ver el encabezado):")
    try:
        from _semilla_credencial import credencial
        token = credencial(BASE_DEFAULT)
    except SystemExit as exc:
        return [f"{u.get('username') or u['id']} — sin credencial admin: {exc}" for u in activos]
    _bajados, problemas = dar_de_baja(BASE_DEFAULT, token, usuarios)
    return problemas


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
