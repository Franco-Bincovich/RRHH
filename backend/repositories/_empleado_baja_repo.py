"""
La ÚNICA escritura física de `estado='baja'`: `dar_de_baja`.

Salió de `_empleado_write_repo.py` el 20/8/2026, que estaba en 99/100 y no admitía el campo del
motivo. El corte NO es por tamaño: allá quedan `guardar` y `actualizar`, que son el CRUD
GENÉRICO —escriben lo que les mandan—, y esto es una OPERACIÓN DE NEGOCIO con nombre propio que
decide por su cuenta qué columnas toca. Eran tres funciones en un archivo llamado "write path" y
una de las tres no era eso.

⚠️ El inventario de escrituras de estado (`tests/test_estado_preingreso_escrituras.py`) declara
este archivo por RUTA, así que la mudanza lo hizo rojear y su declaración se actualizó en el
mismo commit. Es el barrido funcionando, no un daño colateral.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin
from repositories._empleado_row import TABLE, with_empresa


def dar_de_baja(empleado_id: str, fecha_egreso: date, empresa_id: Optional[UUID] = None,
                motivo: Optional[str] = None) -> bool:
    """Da de baja a un empleado: `estado='baja'`, `fecha_egreso` y el motivo, en un solo UPDATE.

    🔴 ES LA ÚNICA ESCRITURA DE `estado='baja'` QUE QUEDA EN EL REPO, y por eso siempre lleva la
    fecha. Acá vivía además `baja_logica`, que ponía el estado SIN fecha; se borró junto con
    `DELETE /api/empleados/{id}`, su único caller a través de la cadena. Que no exista más es la
    parte importante: una baja sin `fecha_egreso` no cae en ningún período, así que la persona
    desaparecía del headcount y no aparecía en el conteo de bajas de ningún mes — se evaporaba de
    los dos lados del reporte a la vez.

    Sus DOS callers son el momento en que la salida efectivamente ocurrió:
    `_offboarding_efectivizar` (alguien la confirma desde la ficha) y `_nomina_empleados_baja`
    (el import de nómina trae una columna `Fecha Baja`). La baja es lógica (estado + fecha_egreso),
    nunca física — así el histórico de costos sigue incluyendo a los que ya no están.

    ═══════════════════════════════════════════════════════════════════════════════════════
    🔴 `motivo` ES OPCIONAL, Y SI NO VIENE **LA COLUMNA NO SE TOCA**. Es load-bearing.
    ═══════════════════════════════════════════════════════════════════════════════════════
    Los dos callers llenan `empleados.motivo_baja` de formas distintas:

      · **efectivizar** lo pasa acá, copiado de `offboarding_instancias.motivo_egreso`.
      · **el import de nómina** NO lo pasa: ya escribió el texto libre de la columna `Motivo Baja`
        del CSV en el `update_empleado` de esa misma fila, y `dar_de_baja` corre DESPUÉS
        (`_nomina_empleados_baja.aplicar_vinculos`).

    Si el patch incluyera `motivo_baja: None` cuando el motivo no viene, **el import borraría el
    texto que acababa de escribir dos líneas antes**, en silencio y en cada corrida mensual. Por
    eso la clave se agrega sólo si hay valor, y no con un `or ""` ni con un default.

    Args:
        empleado_id: UUID (str) del empleado a dar de baja.
        fecha_egreso: fecha de egreso a registrar.
        empresa_id: si se provee, restringe el WHERE a esa empresa.
        motivo: qué se escribe en `motivo_baja`. None = no tocar la columna (ver arriba).

    Returns:
        True si se actualizó alguna fila; False si el empleado no existe o no pertenece a la empresa.
    """
    # 🔴 EL DICT VA LITERAL DENTRO DEL `.update(...)`, no armado en una variable, y no es estilo.
    # El inventario de escrituras de estado (`tests/_barrido_escrituras_estado.py`) detecta la
    # forma `dict` exigiendo que el primer argumento de `.update()` SEA un dict literal en el AST.
    # Con `.update(patch)` esta —que es la ÚNICA escritura física de 'baja'— desaparecía del
    # barrido en silencio, sin que nada rojeara: es exactamente el modo de falla que ese archivo
    # documenta con la forma `splat`. El motivo entra por `**`, que conserva el literal.
    motivo_col = {"motivo_baja": motivo} if motivo else {}
    stmt = with_empresa(
        supabase_admin.table(TABLE)
        .update({"estado": "baja", "fecha_egreso": str(fecha_egreso), **motivo_col})
        .eq("id", empleado_id),
        empresa_id,
    )
    return bool(stmt.execute().data)
