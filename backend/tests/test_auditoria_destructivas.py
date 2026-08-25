"""
🔴 BARRIDO ESTRUCTURAL — toda escritura que BORRA FÍSICAMENTE emite un evento de auditoría, o
está declarada acá con su razón.

Es el barrido que le faltaba al repo el día que un objetivo real de Karstec desapareció sin dejar
rastro. **El motivo, el eje elegido y por qué no alcanza `test_auditoria_coherente` están en el
encabezado de `tests/_barrido_destructivas.py`** — leerlo antes de tocar este archivo, porque la
pregunta "¿por qué destructivas y no todas las escrituras?" ya está contestada ahí con la medición
que la respalda.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
  · El descubrimiento es por AST sobre `repositories/` + el grafo de llamadas de
    `_barrido_auditoria`. NO hay lista escrita a mano de qué mirar: un módulo nuevo que borre
    entra solo. Lo único escrito a mano son las EXCEPCIONES, y hay un test que verifica que
    ninguna apunte a algo que ya no existe.
  · Verificado por mutación al escribirlo: sacándole el `audit.registrar` a
    `_objetivos_write.eliminar`, el test rojea nombrándolo. Con la línea puesta, verde.
  · Las dos guardas de mínimo corren ANTES de comparar: si el descubrimiento se rompe, esto falla
    en vez de pasar habiendo mirado cero borrados.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from tests._barrido_destructivas import (  # noqa: E402
    call_sites, metodos_destructivos, sin_auditar,
)

# ─────────────────────────────────────────────────────────────────────────────
# Borrados físicos SIN evento, declarados. La clave es `archivo::funcion`.
#
# 🔴 SON DOS GRUPOS Y NO HAY QUE CONFUNDIRLOS. El primero es HIGIENE TÉCNICA: filas que el
# sistema escribe y borra solo, sin que ningún usuario decida nada. El segundo es DEUDA REAL:
# acciones que alguien aprieta en una pantalla y que hoy no dejan rastro. Mezclarlos convertiría
# esta lista en el "no sé" que `test_auditoria_coherente` explica que hay que evitar — por eso
# cada entrada dice de cuál de los dos es.
# ─────────────────────────────────────────────────────────────────────────────
_SIN_EVENTO_DECLARADAS: dict[str, str] = {
    # ── HIGIENE TÉCNICA — no son eventos de negocio ──────────────────────────
    "services/_oauth_state.py::consumir":
        "HIGIENE. El DELETE *ES* la verificación del nonce de un solo uso (por eso es un delete y "
        "no un select+delete: así el uso único es atómico). Auditar cada consumo llenaría la "
        "tabla de eventos por un detalle del protocolo, y el hecho de negocio —se conectó una "
        "cuenta de Google— lo audita `integracion_service`.",
    "services/_oauth_state.py::generar":
        "HIGIENE. Purga de states vencidos, colgada del camino que los crea para no necesitar un "
        "job. Borra filas que ya no sirven para nada; no hay decisión de nadie que registrar.",
    "services/_sesion_horas.py::emitir":
        "HIGIENE. Purga de sesiones vencidas del link público, mismo patrón que la de OAuth.",
    "services/superiores_pendientes_service.py::SuperioresPendientesService.resolver":
        "HIGIENE. `empleado_superior_pendiente` es una tabla de TRABAJO del import de nómina, no un "
        "registro de negocio: resolver un pendiente lo saca de la "
        "cola. 🚩 El cambio REAL que produce —asignarle el superior a un empleado— sí se audita, "
        "porque va por el update del legajo.",
    "services/configuracion_service.py::ConfiguracionService.set_escala":
        "HIGIENE, con matiz. `replace_escala` es un reemplazo del set completo (borrar+insertar) "
        "y no una baja: al terminar hay una escala, no un hueco. 🚩 DEUDA MENOR aun así — nadie "
        "puede saber quién la cambió. Entra con el resto de /configuracion.",
    "services/screening_config_service.py::ScreeningConfigService.restaurar_defaults":
        "HIGIENE. Borra la parametrización PROPIA para volver a la default del sistema: al "
        "terminar hay configuración, no un vacío. Mismo caso que `set_escala`.",

    # ── DEUDA REAL — el usuario borra desde una pantalla y no queda rastro ────
    # 🟢 VACÍA DESDE EL 25/8/2026. Acá vivían ONCE entradas: las once escrituras que borraban
    # desde una pantalla sin dejar evento, el mismo agujero que se cobró el objetivo de Karstec.
    # Se cerraron todas en la tanda de "los arreglos que quedaron del smoke": áreas, horas de
    # proyecto, integraciones, plantillas de mail, proyectos, asignaciones de proyecto, ítems de
    # inventario, formaciones, asignaciones de formación, plantillas de onboarding y sus tareas.
    #
    # 🔴 CERRARLAS NO FUE "AGREGAR ONCE `audit.registrar`". El barrido nº 8
    # (`test_auditoria_coherente`) exige que un módulo que audita ALGO audite TODO, así que cada
    # baja arrastró el CRUD entero de su módulo: son 31 escrituras y 8 archivos de payloads
    # nuevos (`_audit_payloads_areas`, `_integraciones`, `_plantillas_mail`, `_proyectos`,
    # `_capacitaciones`, `_inventario`, `_onboarding_templates`, más el `_horas` que ya existía).
    # Eso es lo que la regla del nº 8 compra, y por qué no se podían cerrar "a medias".
    #
    # ⚠️ NO SE BORRA ESTE BLOQUE DE COMENTARIO AUNQUE EL DICT NO TENGA DEUDA. La lista vuelve a
    # llenarse el día que alguien agregue un borrado sin evento, y el test de abajo exige que
    # cada entrada diga si es HIGIENE o DEUDA justamente para que esa distinción no se diluya.
}

# ─────────────────────────────────────────────────────────────────────────────
# Guardas de mínimo — ~25% por debajo de lo medido el 24/8/2026 (12 métodos de repo, 28 sitios),
# igual que en `test_auditoria_coherente`. El margen absorbe la baja normal del repo —que borra
# código muerto y parte archivos seguido— pero no una ROTURA del descubrimiento, que no baja un
# 25%: colapsa a cero. Si el AST deja de parsear o cambia la estructura de directorios, estos dos
# conteos se van al piso y el archivo falla ACÁ en vez de pasar sin haber mirado nada.
# ─────────────────────────────────────────────────────────────────────────────
_MINIMO_METODOS_DESTRUCTIVOS = 9
_MINIMO_CALL_SITES = 21


class TestElBarridoEstaMirandoAlgo:
    """Sin esto, todo lo de abajo pasa en el vacío."""

    def test_descubre_metodos_de_repo_que_borran(self) -> None:
        n = len(metodos_destructivos())
        assert n >= _MINIMO_METODOS_DESTRUCTIVOS, (
            f"solo {n} métodos de repo con delete físico (mínimo "
            f"{_MINIMO_METODOS_DESTRUCTIVOS}). No es que se dejó de borrar: es que la detección "
            "del `.delete()` de PostgREST se rompió.")

    def test_descubre_los_call_sites(self) -> None:
        """La guarda que más importa: es el conjunto que el test de abajo compara."""
        n = len(call_sites())
        assert n >= _MINIMO_CALL_SITES, (
            f"solo {n} sitios de services/ que borran físico (mínimo {_MINIMO_CALL_SITES}): la "
            "resolución de escrituras de `_barrido_auditoria` dejó de mapear los repos.")


class TestTodoBorradoFisicoDejaRastro:

    def test_ningun_borrado_fisico_sin_evento(self) -> None:
        """LA REGLA. Un DELETE físico es irreversible: el evento es el único registro que queda."""
        nuevos = [f"{arch}::{qual}" for arch, qual, _ in sin_auditar()
                  if f"{arch}::{qual}" not in _SIN_EVENTO_DECLARADAS]
        assert not nuevos, (
            f"Borrados FÍSICOS sin evento de auditoría: {nuevos}.\n"
            "Después de un DELETE no queda fila que mirar: si esto no emite un evento, lo que "
            "se borró no se puede reconstruir ni saber quién lo hizo. Es el agujero exacto por "
            "el que se perdió un objetivo de Karstec en agosto de 2026.\n"
            "Agregá el evento (molde: `services/_audit_payloads_objetivos.py`) o declaralo en "
            "_SIN_EVENTO_DECLARADAS CON su razón y diciendo si es HIGIENE o DEUDA.")

    def test_las_declaradas_siguen_sin_evento(self) -> None:
        """Dirección inversa: una declaración que ya no corresponde —porque se le agregó el
        evento, o porque la función se borró o se renombró— es ruido que tapa el próximo caso.
        Es lo que impide que esta lista se convierta en el cajón donde nadie mira."""
        vigentes = {f"{arch}::{qual}" for arch, qual, _ in sin_auditar()}
        obsoletas = [k for k in _SIN_EVENTO_DECLARADAS if k not in vigentes]
        assert not obsoletas, (
            f"Declaraciones que ya no corresponden: {obsoletas}. O se auditó (sacala de la "
            "lista) o la función se movió (actualizá la clave).")

    def test_toda_declaracion_tiene_razon_escrita(self) -> None:
        """Una lista pelada no se puede auditar: en seis meses nadie sabe por qué está cada una."""
        sin_razon = [k for k, v in _SIN_EVENTO_DECLARADAS.items() if len(v.strip()) < 30]
        assert not sin_razon, f"Declaraciones sin razón escrita: {sin_razon}"

    def test_la_deuda_esta_separada_de_la_higiene(self) -> None:
        """Las dos clases se distinguen POR ESCRITO, y las dos existen.

        Sin esto, la lista se degrada sola: alcanza con que alguien declare la próxima deuda con
        el tono de una higiene para que deje de ser un pendiente y pase a ser una decisión. El
        test no juzga la clasificación —eso lo hace quien lee— pero sí exige que el archivo siga
        distinguiéndolas, que es lo que lo mantiene siendo un inventario y no un cajón.

        🟢 `deuda` PUEDE ESTAR VACÍA Y ESO NO ES UN FALLO — desde el 25/8/2026 lo está. Hasta ese
        día el test exigía `assert deuda` para cazar que alguien "diluyera la marca" reetiquetando
        una deuda como higiene. Esa exigencia dejó de tener sentido en el momento en que las once
        deudas se cerraron de verdad: mantenerla obligaría a inventar una deuda para que el test
        pase, que es exactamente el incentivo contrario al que se buscaba. Lo que SÍ se conserva
        —y es lo que cierra el agujero— es que toda entrada declare su clase: una deuda nueva no
        puede entrar sin decir que lo es."""
        deuda = [k for k, v in _SIN_EVENTO_DECLARADAS.items() if "DEUDA" in v]
        higiene = [k for k, v in _SIN_EVENTO_DECLARADAS.items() if "HIGIENE" in v]
        assert higiene, "ninguna declaración marcada como HIGIENE"
        sin_clase = [k for k in _SIN_EVENTO_DECLARADAS if k not in set(deuda) | set(higiene)]
        assert not sin_clase, (
            f"Declaraciones sin decir si son HIGIENE o DEUDA: {sin_clase}. La diferencia es si "
            "hay algo que hacer o no, y es lo único que hace útil a esta lista.")
