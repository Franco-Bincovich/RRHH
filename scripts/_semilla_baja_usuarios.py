"""
LA BAJA DE LOS TRES USUARIOS DE PRUEBA. Es el ÚNICO paso del limpiador que va por la API.

🔴 POR QUÉ, SI TODO EL RESTO DEL LIMPIADOR VA POR LA BASE. Son dos razones y la segunda es la
que manda:

  1. **Es la misma regla que sostiene toda la semilla: se siembra por la API y se borra por la
     API cuando la API puede hacerlo.** El resto del limpiador va por base porque la API
     LITERALMENTE no puede —`empleados`, `costos_nomina`, `recategorizaciones` y
     `offboarding_instancias` no tienen endpoint de baja—, no porque ir por base sea preferible.
     Acá el endpoint existe y hace exactamente lo que hay que hacer. Un camino paralelo prueba
     algo que el sistema nunca hace.

  2. **Un `DELETE` desde el script borraría sin dejar rastro en la auditoría**, que es justo lo
     que no se quiere de un usuario con acceso. `DELETE /api/usuarios/{id}` emite su evento
     (`payload_baja_usuario`), así que queda escrito quién revocó qué y cuándo.

🔴 EL RESULTADO ES UNA BAJA BLANDA, NO UNA FILA BORRADA — Y ES SUFICIENTE. El endpoint hace las
dos mitades (`services/usuario_service.py:92`):
    · `activo=false` → el middleware responde 403 `USUARIO_INACTIVO` en cada request;
    · **ban permanente en Supabase Auth** (`ban_duration = "876000h"`, ~100 años) → no puede
      loguearse NI renovar token. `/api/auth/refresh` es pública y no pasa por el middleware, así
      que sin el ban seguiría emitiéndose tokens para siempre: las dos mitades hacen falta.
La preocupación real —"un usuario inactivo con contraseña conocida sigue siendo un acceso"— la
cierra el ban, no el `activo=false`. Y que los tres queden VISIBLES en `/usuarios` como inactivos
es correcto: **un acceso revocado tiene que verse.**

🚨 LA ALTERNATIVA QUE SE DESCARTÓ, para que nadie la reintente: `supabase_admin.auth.admin.
delete_user(uid)` sí es un borrado real y cascadea a `public.users`. Se descartó por las dos
razones de arriba. Y agregar `users` a `ORDEN` como una tabla más sería PEOR que las dos: dejaría
`public.users` borrado y `auth.users` **vivo y sin banear** —el ban solo ocurre en el camino de la
API—, o sea una identidad con contraseña conocida en Supabase Auth que ninguna pantalla del
sistema puede mostrar para revocarla. Un acceso invisible es peor que uno inactivo.
"""
from typing import List, Optional, Tuple

import httpx

TIMEOUT = 30.0


def _detalle(res: httpx.Response) -> str:
    try:
        cuerpo = res.json()
        return str(cuerpo.get("code") or cuerpo.get("message") or res.text[:120])
    except Exception:                                    # noqa: BLE001
        return res.text[:120]


def dar_de_baja(base: str, token: str, usuarios: List[dict]) -> Tuple[int, List[str]]:
    """Da de baja los usuarios por `DELETE /api/usuarios/{id}`. Devuelve (bajados, problemas).

    Los que YA están inactivos se saltean: el endpoint los aceptaría igual, pero volver a
    banear a alguien baneado agrega un evento de auditoría que no corresponde a ninguna decisión
    nueva. Es el mismo criterio que `Cliente.hito` aplica en el sembrador.

    ⚠️ NO ABORTA ANTE UN FALLO. Un 409 en uno (es la casilla del sistema) no puede impedir que
    los otros dos pierdan el acceso — dejar accesos vivos por un error ajeno es el peor final
    posible para un limpiador.
    """
    bajados, problemas = 0, []
    with httpx.Client(base_url=base.rstrip("/"), timeout=TIMEOUT) as cli:
        for u in usuarios:
            if not u.get("activo", True):
                print(f"  {u.get('username') or u['id']:16} ya estaba inactivo · se saltea")
                continue
            res = cli.delete(f"/api/usuarios/{u['id']}",
                             headers={"Authorization": f"Bearer {token}"})
            if res.status_code == 204:
                bajados += 1
                print(f"  {u.get('username') or u['id']:16} acceso revocado "
                      "(activo=false + ban permanente)")
                continue
            # 🔴 El 409 tiene nombre propio y hay que decirlo: el usuario que sostiene la casilla
            # de correo del sistema NO se puede dar de baja (`USUARIO_ES_REMITENTE_SISTEMA`).
            # Si un usuario de prueba quedó de remitente, hay que reasignar la casilla primero.
            detalle = _detalle(res)
            problemas.append(f"{u.get('username') or u['id']} → {res.status_code} · {detalle}")
            print(f"  ✗ {u.get('username') or u['id']:16} {res.status_code} · {detalle}")
    return bajados, problemas


def resumen_plan(usuarios: List[dict]) -> Optional[str]:
    """La línea del plan en seco. `None` si no hay ninguno sembrado."""
    if not usuarios:
        return None
    activos = [u for u in usuarios if u.get("activo", True)]
    detalle = ", ".join(f"{u.get('username') or u['id']} ({u.get('rol')})" for u in usuarios)
    return (f"  {'users (baja por API)':26} {len(activos):4} accesos a revocar "
            f"de {len(usuarios)} sembrados\n    {detalle}")
