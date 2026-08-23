"""
FASE `usuarios`: crea los tres usuarios de prueba (uno por rol), les arma la jerarquía al de
`mandos_medios` y deja las credenciales listas en `scripts/.smoke.env`.

🔴 LA CONTRASEÑA QUE QUEDA NO ES LA QUE DEVUELVE EL ALTA, y no es un rodeo. `POST /api/usuarios`
genera una temporal y marca `must_change_password=true`; ese flag **lo aplica solamente el
AuthGuard del navegador** (`frontend/components/layout/AuthGuard.tsx:29`), que redirige a
`/cambiar-password` en TODA pantalla. O sea que con la temporal el smoke por API andaría y el
smoke por navegador —la mitad que motivó todo esto— no llegaría a ver una sola pantalla. Por eso
la fase hace los tres pasos: alta → login con la temporal → `POST /api/usuarios/cambiar-password`
con una contraseña fuerte generada acá. Ese endpoint baja el flag como efecto, que es lo que
destraba el navegador.
⚠️ Que el backend NO exija ese cambio es un AGUJERO, no una comodidad: está anotado en
`docs/DEUDA-TECNICA.md` y como caso a probar en `docs/INVENTARIO-SMOKE.md`. Esta fase lo esquiva
para los tres de prueba; no lo cierra para nadie más.

🔴 LA CONTRASEÑA NO SE IMPRIME NUNCA. Va a un archivo y la consola solo dice que se escribió: lo
que se imprime queda en el historial de PowerShell, en texto plano y sin vencimiento — que es la
misma razón por la que `_semilla_credencial.py` existe. El archivo está en `.gitignore`
(verificado antes de escribirlo) y es de UN SOLO USO: se borra al terminar el smoke, y el propio
archivo dice cómo.

⚠️ IDEMPOTENCIA, con una diferencia respecto del resto de la semilla. El alta pasa por
`obtener_o_crear` como todo lo demás, pero **la contraseña solo existe en el momento del alta**:
si el usuario ya estaba (manifiesto o clave natural), esta fase NO puede recuperarla ni
regenerarla, y lo dice. Para rehacer las credenciales hay que limpiar los tres y volver a
sembrar. Es preferible a resetear contraseñas en silencio sobre usuarios que quizás alguien esté
usando.
"""
import secrets
from pathlib import Path
from typing import Dict, List, Optional

from _semilla_cliente import Cliente, login
from _semilla_usuarios import A_CARGO, JEFE, USUARIOS

ARCHIVO = Path(__file__).resolve().parent / ".smoke.env"

# Mismo alfabeto sin ambiguos que usa el backend en `services/_usuario_alta._ALFABETO`: estas
# credenciales se leen de un archivo y se tipean a mano en un navegador, y una `l` que era un `1`
# se paga con un login fallido que parece un bug de permisos.
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789@#$%&*"


def _generar(n: int = 20) -> str:
    """Contraseña aleatoria con `secrets` (CSPRNG), 20 chars. El tope del backend es 72 (bcrypt)."""
    return "".join(secrets.choice(_ALFABETO) for _ in range(n))


def _buscar_usuario(cli: Cliente, email: str) -> Optional[str]:
    """Clave natural del usuario: su email, único en `public.users`."""
    for u in cli.get("/api/usuarios").get("items", []):
        if (u.get("email") or "").lower() == email.lower():
            return str(u["id"])
    return None


def _crear(cli: Cliente, base: str, u: dict, empleado_id: Optional[str]) -> Optional[str]:
    """Alta + cambio de contraseña. Devuelve la contraseña final, o None si ya existía/falló."""
    cuerpo = {"nombre": u["nombre"], "apellido": u["apellido"], "email": u["email"],
              "username": u["username"], "rol": u["rol"]}
    if empleado_id:
        cuerpo["empleado_id"] = empleado_id
    estado: Dict[str, Optional[str]] = {"temporal": None}

    def alta() -> str:
        res = cli.pedir("POST", "/api/usuarios", json_body=cuerpo)
        estado["temporal"] = res["password_temporal"]
        return res["id"]

    uid = cli.obtener_o_crear("usuarios", u["clave"], crear=alta,
                              buscar=lambda: _buscar_usuario(cli, u["email"]))
    if not uid or not estado["temporal"]:
        return None                       # ya existía: la contraseña no es recuperable
    definitiva = _generar()
    token = login(base, u["username"], estado["temporal"])
    propio = Cliente(base, token, pausa=cli.pausa)
    try:
        propio.pedir("POST", "/api/usuarios/cambiar-password",
                     json_body={"password_actual": estado["temporal"],
                                "password_nueva": definitiva})
    finally:
        propio.cerrar()
    return definitiva


def _asignar_a_cargo(cli: Cliente, personas: Dict[str, dict]) -> int:
    """Cuelga a los cuatro de `A_CARGO` del jefe, con `PUT /api/empleados/{id}`.

    🔴 SOLO SOBRE COLABORADORES SEMBRADOS. Cambiarle el `manager_id` a alguien de Karstec es
    modificar un legajo real, y la jerarquía es justo el dato que RRHH empezó a cargar a mano
    (11 de 31). `personas` viene de la fase de personas o del manifiesto, así que todo lo que
    entra acá lleva legajo `SMK-xx`; el `assert` lo hace explícito en vez de confiar.
    """
    jefe = personas.get(JEFE)
    if not jefe:
        print(f"    ⚠️  sin {JEFE} sembrado: el mando medio queda sin gente a cargo")
        return 0
    puestos = 0
    for legajo in A_CARGO:
        sub = personas.get(legajo)
        if not sub:
            continue
        assert legajo.startswith("SMK-"), f"{legajo} no es un colaborador sembrado"
        # 🔴 La base RECHAZA un jefe de otra empresa (trigger `trg_emp_empleados`, migración 094)
        # y el backend lo devuelve como 500 opaco. Se saltea acá con un mensaje que se entiende,
        # en vez de mandar el request y anotar un fallo que parece un bug del endpoint.
        if sub["empresa_id"] != jefe["empresa_id"]:
            print(f"    ⚠️  {legajo} es de otra empresa que {JEFE}: la base no acepta ese "
                  "manager_id (trg_emp_empleados). Se saltea — ver _semilla_usuarios.py")
            continue
        if cli.hito("manager_asignado", legajo, lambda s=sub: cli.pedir(
                "PUT", f"/api/empleados/{s['id']}", empresa=s["empresa_id"],
                json_body={"manager_id": jefe["id"]})):
            puestos += 1
    return puestos


def _escribir(credenciales: List[dict], base: str) -> None:
    """Deja `scripts/.smoke.env` con las tres credenciales y su instructivo de borrado."""
    lineas = [
        "# CREDENCIALES DE LOS TRES USUARIOS DE PRUEBA DEL SMOKE — uno por rol.",
        "# Las generó scripts/semilla_smoke.py (fase `usuarios`). NO se imprimieron en consola.",
        "#",
        "# 🔴 ESTE ARCHIVO ES DE UN SOLO USO. Al terminar el smoke, borralo:",
        "#      Remove-Item scripts\\.smoke.env",
        "#   Es lo único del repo con una contraseña utilizable contra producción. Está en",
        "#   .gitignore, así que no se commitea — pero sigue en disco hasta que lo borres.",
        "#",
        "# 🔴 BORRARLO NO REVOCA NADA: los usuarios siguen vivos. Para sacarlos del sistema hay",
        "#   que correr scripts/limpiar_semilla.py --si, que les da de baja el acceso por la API",
        "#   (activo=false + ban permanente en Auth). Leer el encabezado de ese archivo.",
        "#",
        f"# Backend: {base}",
        "",
    ]
    for c in credenciales:
        lineas += [f"# {c['rol']} — {c['para']}",
                   f"SMOKE_{c['clave'].upper()}_USUARIO={c['username']}",
                   f"SMOKE_{c['clave'].upper()}_PASSWORD={c['password']}", ""]
    ARCHIVO.write_text("\n".join(lineas), encoding="utf-8")


def sembrar_usuarios(cli: Cliente, base: str, personas: Dict[str, dict]) -> None:
    """Los tres usuarios de prueba + la jerarquía del mando medio + `.smoke.env`."""
    print("→ usuarios de prueba (uno por rol)")
    puestos = _asignar_a_cargo(cli, personas)
    print(f"    {JEFE} ← {puestos} colaboradores a cargo ({', '.join(A_CARGO)}). "
          "SMK-05, 07 y 09 quedan afuera: son el control del ownership")
    credenciales: List[dict] = []
    for u in USUARIOS:
        emp = (personas.get(u["legajo"]) or {}).get("id") if u["legajo"] else None
        if u["legajo"] and not emp:
            print(f"    ✗ {u['rol']}: sin {u['legajo']} sembrado, el vínculo de ownership "
                  "quedaría vacío — se saltea")
            continue
        try:
            password = _crear(cli, base, u, emp)
        except Exception as exc:                        # noqa: BLE001 — un fallo no corta la fase
            cli.anotar_fallo("usuarios", f"crear {u['username']}", exc)
            continue
        if password is None:
            print(f"    = {u['username']:14} ya existía · la contraseña NO es recuperable "
                  "(limpiá y resembrá para regenerarla)")
            continue
        credenciales.append(dict(u, password=password))
        print(f"    {u['username']:14} · {u['rol']:17} · contraseña generada")
    if credenciales:
        _escribir(credenciales, base)
        print(f"    credenciales escritas en {ARCHIVO.name} ({len(credenciales)} de 3)")
