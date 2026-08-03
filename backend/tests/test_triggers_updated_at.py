"""
Barrido estructural: db/schema.sql ↔ migracionAWS/.../077_recrear_triggers_updated_at.sql.

🔴 QUÉ CLASE DE BUG CIERRA
La 077 recrea los triggers `updated_at` en RDS con una LISTA HARDCODEADA. Una tabla nueva
con columna `updated_at` queda afuera sin que nada avise, y el síntoma no es un error: es
`updated_at` congelado en el alta, para siempre, en silencio. Cuando este barrido se corrió
por primera vez ya habían quedado afuera CINCO: `usuario_integraciones` (mig 032),
`vacaciones_pendientes` (083), `parametros_empresa` y `reglas_vacaciones_escala` (085) y
`plantillas_mail` (087). Arreglar esas cinco no cierra nada: la sexta nace con el mismo
agujero. Lo que lo cierra es este barrido.

🔴 Y NO ERA SOLO DEUDA DE AWS. De las cinco, dos —`usuario_integraciones` y
`plantillas_mail`— tampoco tenían el trigger EN PRODUCCIÓN, porque sus migraciones no lo
declararon: su `updated_at` estaba congelado hoy, en Supabase, sin que nada lo dijera. Eso
lo arregla `backend/migrations/091_triggers_updated_at_faltantes.sql`, que es otro archivo
porque la 077 nunca corre contra Supabase. Este test NO cubre ese lado —solo compara
schema.sql contra la 077—, así que si algún día se agrega una tabla con `updated_at` hay
que acordarse de declararle el trigger en SU PROPIA migración además de en la 077.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
No hay fake: los dos leen los archivos REALES del repo y se comparan entre sí. Fallan si
alguien agrega a `db/schema.sql` una tabla con `updated_at` y no toca la 077 (test 1), o si
la 077 crea un trigger sobre una tabla que ya no existe o perdió la columna (test 2 — en
RDS eso aborta la migración entera). Para que dejen de poder fallar habría que romper el
parseo, y de eso se ocupa la guarda de mínimo: si el regex deja de matchear, las listas
salen vacías y el `>=` avisa en vez de dar verde sobre cero comparaciones.

EXCEPCIONES: las tablas SIN columna `updated_at` no entran en el barrido y no hay que
declararlas — la lista de candidatos se DERIVA del schema, no se escribe a mano. Por eso
`horas_proyecto`, `adjuntos`, `periodos_cerrados` y `oauth_states` quedan afuera solas.
"""
import re
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[2]
_SCHEMA = _RAIZ / "backend" / "db" / "schema.sql"
_MIG_077 = _RAIZ / "migracionAWS" / "backend" / "migrations" / "077_recrear_triggers_updated_at.sql"

# Mínimos: hoy son 41 y 41. Si el parseo se rompe, esto avisa en vez de comparar vacío
# contra vacío. Subirlos cuando crezca de verdad es un renglón; bajarlos, nunca.
_MIN_TABLAS = 41
_MIN_TRIGGERS = 41


def _tablas_con_updated_at() -> set[str]:
    """Tablas de db/schema.sql cuyo CREATE TABLE declara una columna updated_at."""
    src = _SCHEMA.read_text(encoding="utf-8")
    cuerpos = re.findall(r"CREATE TABLE public\.(\w+)\s*\((.*?)\n\);", src, re.S)
    return {nombre for nombre, cuerpo in cuerpos if "updated_at" in cuerpo}


def _tablas_con_trigger() -> set[str]:
    """Tablas sobre las que la 077 crea un trigger BEFORE UPDATE."""
    return set(re.findall(r"BEFORE UPDATE ON public\.(\w+)", _MIG_077.read_text(encoding="utf-8")))


def test_toda_tabla_con_updated_at_tiene_su_trigger_en_la_077():
    """Una tabla con `updated_at` y sin trigger en RDS queda con el dato congelado en el
    alta, sin error y sin aviso. Es el modo de falla que la 077 vino a evitar y el que su
    lista hardcodeada reintroduce cada vez que nace una tabla."""
    tablas = _tablas_con_updated_at()
    assert len(tablas) >= _MIN_TABLAS, (
        f"El parseo de schema.sql devolvió {len(tablas)} tablas con updated_at, menos que el "
        f"mínimo {_MIN_TABLAS}. Sin esta guarda el test compararía un conjunto vacío y pasaría."
    )
    faltan = tablas - _tablas_con_trigger()
    assert not faltan, (
        f"Tablas con columna updated_at SIN trigger en la 077: {sorted(faltan)}. "
        "En RDS su updated_at nunca se va a actualizar. Agregar el bloque "
        "DROP TRIGGER IF EXISTS + CREATE TRIGGER en migracionAWS/.../077."
    )


def test_la_077_no_crea_triggers_sobre_tablas_que_no_existen():
    """El reverso: un trigger sobre una tabla borrada (o que perdió `updated_at`) NO es
    ruido inocuo — en RDS el CREATE TRIGGER aborta y se lleva puesta la migración entera,
    así que las tablas que venían DESPUÉS en el archivo se quedan sin trigger."""
    triggers = _tablas_con_trigger()
    assert len(triggers) >= _MIN_TRIGGERS, (
        f"El parseo de la 077 devolvió {len(triggers)} triggers, menos que el mínimo "
        f"{_MIN_TRIGGERS}. Sin esta guarda el test no compararía nada."
    )
    sobran = triggers - _tablas_con_updated_at()
    assert not sobran, (
        f"La 077 crea triggers sobre tablas que no existen en schema.sql o no tienen "
        f"updated_at: {sorted(sobran)}. En RDS eso aborta la migración."
    )
