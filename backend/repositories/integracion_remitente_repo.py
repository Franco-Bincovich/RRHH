"""
La CASILLA DEL SISTEMA: qué integración de Google se usa como remitente de los mails.

Repo propio y no un par de métodos en `integracion_repo` por dos razones. Aquel está en 92/100.
Y de fondo son dos preguntas distintas: `IntegracionRepo` contesta *"¿qué integraciones tiene
ESTE usuario?"* —siempre scopeada por `user_id`— y esto contesta *"¿cuál es la casilla
institucional?"*, que es una sola en todo el sistema y no cuelga de quién pregunta.

## 🔴 POR QUÉ EXISTE (decisión de producto, 2/8/2026)

`usuario_integraciones` es POR USUARIO y no tiene `empresa_id`. Sin esto, un mail saldría de la
casilla personal del humano que apretó el botón — y **un proceso automático no tendría de qué
cuenta salir**, porque no hay `user_id` que aportar.

Y el motivo decisivo no es ese: es que **el circuito de prueba y el real tienen que ser el
mismo**. Con la casilla del sistema, pasar de la cuenta personal de prueba a la casilla de RRHH
es reconectar otra cuenta al mismo usuario técnico: cero código, y lo que se probó es lo que va
a producción. Con "sale del que disparó", probar con la personal y después mudarse son dos
circuitos distintos y el segundo queda sin probar.

## ⚠️ BAJAR AL USUARIO QUE SOSTIENE LA CASILLA APAGA EL ENVÍO DE TODO EL SISTEMA

`usuario_integraciones` es POR USUARIO, así que la casilla del sistema cuelga de una persona
concreta. Dar de baja a esa persona apaga el envío de mails de todo el sistema, no solo el suyo.
(La FK `usuario_integraciones.user_id → users(id)` es además `ON DELETE CASCADE`; desde el 3/8 la
baja es blanda, así que el CASCADE ya no se dispara por esa vía — pero el `activo=false` apaga el
envío igual, porque la integración queda colgando de un usuario inactivo. **El agujero existe
aunque el CASCADE nunca corra.**)

✅ **YA HAY GUARDA, y avisa al DAR DE BAJA en vez de al MANDAR:**
`usuario_service._ensure_no_es_remitente` rechaza esa baja con **409
`USUARIO_ES_REMITENTE_SISTEMA`** y un mensaje que dice a dónde ir a designar otra casilla. El
motivo por el que no estaba —`usuario_service` en 149/150— desapareció al extraer el alta a
`_usuario_alta.py`. Es una guarda de APLICACIÓN: el CASCADE de la FK no se tocó.

Segunda red, para el caso en que igual se quede sin casilla (p. ej. alguien desconecta la cuenta
de Google): `get_remitente()` devuelve None, el mailer corta con `MAIL_SIN_REMITENTE` y la
pantalla de configuración muestra que no hay casilla configurada.

🔴 **`get_remitente()` DEVUELVE LA FILA ENTERA (`select("*")`) Y DE AHÍ SALE EL `user_id`.**
Dos consumidores dependen de ese campo: la guarda de la baja y `mailer/engine._remitente`.
Angostar el `select` a las columnas "que se usan" haría que los dos leyeran `None` **en
silencio** —la guarda dejaría de proteger y el mailer cortaría creyendo que no hay casilla—.
Hay un test que lo fija (`test_usuarios.py::TestLaFilaDelRemitenteTraeElUserId`).
"""
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

_TABLE = "usuario_integraciones"


class IntegracionRemitenteRepo:
    def get_remitente(self) -> Optional[dict]:
        """La integración de Google marcada como casilla del sistema. None si no hay ninguna.

        No se acota por `user_id` A PROPÓSITO —es la única lectura del módulo que no lo hace—:
        justamente la pregunta es cuál es la casilla institucional, sin importar quién pregunta.
        `maybe_single()` y no `single()`: "todavía nadie la configuró" es un estado válido y
        esperable (es el estado inicial), no un error 500.
        """
        res = (supabase_admin.table(_TABLE)
               .select("*")
               .eq("tipo", "google").eq("es_remitente_sistema", True)
               .maybe_single().execute())
        return res.data if res else None

    def set_remitente(self, user_id: UUID) -> None:
        """Marca la integración de `user_id` como casilla del sistema, y desmarca cualquier otra.

        🔴 DESMARCA PRIMERO, MARCA DESPUÉS — el orden no es estético. El índice único parcial de
        la migración 087 garantiza que haya UNA SOLA fila con `es_remitente_sistema = true`:
        marcar antes de desmarcar violaría esa restricción y el cambio fallaría entero.

        Es idempotente: volver a marcar la que ya estaba desmarca (a sí misma) y vuelve a marcar.
        """
        (supabase_admin.table(_TABLE)
         .update({"es_remitente_sistema": False})
         .eq("tipo", "google").eq("es_remitente_sistema", True)
         .execute())
        (supabase_admin.table(_TABLE)
         .update({"es_remitente_sistema": True})
         .eq("user_id", str(user_id)).eq("tipo", "google")
         .execute())
