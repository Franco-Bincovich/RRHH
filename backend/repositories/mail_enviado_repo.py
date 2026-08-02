"""
Log de mails enviados (migración 087): qué se mandó, a quién y con qué texto.

⚠️ ESTA TABLA CONTIENE DATOS PERSONALES POR DEFINICIÓN — nombre, dirección y el cuerpo entero.
Dos consecuencias que no son negociables y que este repo hace cumplir por omisión:

  · **NO HAY MÉTODO DE EXPORT, y no se le agrega uno "por comodidad".** Un Excel con el texto de
    todos los mails enviados es exactamente el archivo que no se quiere que circule. Por eso este
    repo tampoco expone un `find_all` paginado con `count="exact"`: la única lectura es
    `ultimos()`, acotada por un límite duro, que sirve para diagnosticar "no me llegó" y no para
    llevarse la tabla.
  · La lectura se gatea por `Seccion.CONFIGURACION` en el router. Nunca abierta.

El log también es lo que hace posible la IDEMPOTENCIA: `ya_enviado()` contesta "¿ya le mandé
esta plantilla a esta persona hoy?", que es lo que evita que un reintento tras un timeout mande
de nuevo los mails que sí salieron.
"""
from datetime import date, datetime, time, timezone
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

_TABLE = "mail_enviado"


class MailEnviadoRepo:
    def registrar(self, fila: dict) -> Optional[dict]:
        """Guarda un envío (exitoso o fallido). Devuelve la fila creada, o None si el insert
        no devolvió nada — el caller no debe romper por eso: el mail ya salió."""
        res = supabase_admin.table(_TABLE).insert(fila).execute()
        return (res.data or [None])[0]

    def ya_enviado(self, plantilla_clave: str, empleado_id: str,
                   desde: Optional[datetime] = None) -> bool:
        """¿Ya se envió ESTA plantilla a ESTE empleado desde `desde`? (default: hoy, UTC).

        🔴 Es la consulta que sostiene el reintento continuable. El peor caso del envío masivo no
        es que tarde: es mandar 30 mails, morir en el timeout de Vercel, y que el reintento mande
        esos 30 DE NUEVO. Con esto, el reintento saltea los que ya salieron.

        Solo cuenta los `estado = 'enviado'`: un intento FALLIDO no bloquea el reintento — al
        contrario, reintentarlo es exactamente lo que se quiere.

        `desde` por default es el comienzo del día UTC y no "las últimas 24 h": la ventana móvil
        haría que el mismo lote reintentado a las 23:50 y a las 00:10 se comporte distinto según
        la hora, que es la clase de bug que aparece una vez cada tanto y nadie reproduce.
        """
        if desde is None:
            desde = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
        res = (supabase_admin.table(_TABLE).select("id")
               .eq("plantilla_clave", plantilla_clave)
               .eq("empleado_id", str(empleado_id))
               .eq("estado", "enviado")
               .gte("created_at", desde.isoformat())
               .limit(1).execute())
        return bool(res.data)

    def ultimos(self, empresa_id: Optional[UUID] = None, limite: int = 50) -> List[dict]:
        """Los últimos envíos, para diagnosticar. Acotado por un límite DURO.

        No se pagina y no se expone un total a propósito (ver el encabezado): esto responde
        "¿salió el mail de Fulano?", no "dame todo el historial"."""
        q = (supabase_admin.table(_TABLE)
             .select("id, empresa_id, plantilla_clave, destinatario, asunto_render, estado, error, created_at")
             .order("created_at", desc=True).limit(min(limite, 200)))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return q.execute().data or []
