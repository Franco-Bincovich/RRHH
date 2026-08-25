"""
🔴 BARRIDO ESTRUCTURAL — **toda tabla en la que el código puede CREAR filas la conoce el
limpiador de la semilla (`ORDEN`), o está declarada acá con su razón. Y lo mismo con los buckets
de Storage.**

═══════════════════════════════════════════════════════════════════════════════════════════
EL BUG QUE CIERRA
═══════════════════════════════════════════════════════════════════════════════════════════
El smoke con navegador escribe en producción. Lo que escribe lo limpia `limpiar_semilla.py`, y
lo que ese limpiador SABE borrar es `ORDEN`, una lista escrita a mano en
`scripts/_semilla_plan_borrado.py`. **Una tabla que el smoke toca y que no está en esa lista deja
filas en producción para siempre, y nadie se entera**: el limpiador termina en verde diciendo
cuántas borró, y las que no conoce ni las cuenta.

Ya pasó dos veces en la corrida del 23-24/8/2026:
  · **`reportes_generados`** — el recorrido generó reportes y las filas quedaron. Este barrido
    la habría marcado ANTES de correr el smoke.
  · **DOS ARCHIVOS HUÉRFANOS EN STORAGE** — se encontraron mirando `storage.objects` a mano, no
    con el limpiador, porque el limpiador **no sabe que Storage existe**. Ver la regla de abajo.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR?
  · El descubrimiento es por AST y resuelve el nombre de la tabla en tres pasos (literal,
    constante de módulo, constante importada) — el motor y su porqué están en
    `tests/_barrido_tablas.py`. Sin el paso 3 quedaban 123 call sites sin resolver y el barrido
    habría reportado de MENOS, en silencio, que en un barrido de cobertura es el peor resultado.
  · `ORDEN` se lee del archivo real, por AST. Un import arrastraría `Settings()` y un cliente de
    Supabase de verdad adentro de la suite.
  · Verificado en las DOS direcciones al escribirlo: se le sacó `objetivos` a `ORDEN` y rojeó
    nombrándola; se declaró una tabla inexistente y rojeó también.
  · Las tres guardas de mínimo corren ANTES de comparar.
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

from pathlib import Path  # noqa: E402

from tests._barrido_tablas import (  # noqa: E402
    buckets_del_storage, orden_del_limpiador, sin_resolver, tablas_que_crean_filas,
)

_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"

# ─────────────────────────────────────────────────────────────────────────────
# Tablas donde el código crea filas y que `ORDEN` NO incluye, declaradas.
#
# 🔴 TRES CLASES, y la diferencia es si hay algo que hacer:
#   · **FUERA DE ALCANCE** — el limpiador no las toca por decisión, no por olvido.
#   · **CASCADE** — las borra la base al borrar su padre, que sí está en ORDEN.
#   · **🔴 HUECO** — el smoke puede dejar filas ahí y nadie las limpia. Es lo que este barrido
#     existe para que no se pueda agregar en silencio.
# ─────────────────────────────────────────────────────────────────────────────
_FUERA_DE_ORDEN: dict[str, str] = {
    # ── FUERA DE ALCANCE ─────────────────────────────────────────────────────
    "auditoria": "FUERA DE ALCANCE. `auditoria` es INMUTABLE por diseño y no se limpia nunca: "
                 "borrar eventos de auditoría es exactamente lo que un log de auditoría no puede "
                 "permitir. Las filas que deje el smoke quedan, y está bien que queden.",
    "users": "FUERA DE ALCANCE de `ORDEN` a propósito: los tres usuarios de prueba NO se borran, "
             "se dan de BAJA y por la API (`_semilla_baja_usuarios.py`). El plan los resuelve "
             "aparte, en `usuarios_sembrados()`, y su encabezado explica por qué.",
    "empresas": "FUERA DE ALCANCE. La semilla NO crea empresas: usa las dos reales. Una tabla "
                "que el smoke no puede poblar no tiene nada que limpiar.",
    "clientes": "FUERA DE ALCANCE de `ORDEN`. El cliente sembrado se resuelve en "
                "`_semilla_cliente.py`, que lo da de baja LÓGICA (`activo=False`) en vez de "
                "borrarlo: `horas_proyecto.cliente_id` es una FK sin ON DELETE y un DELETE "
                "físico revienta contra la constraint.",
    "oauth_states": "FUERA DE ALCANCE. Se autopurga: la creación de states borra los vencidos, y "
                    "el consumo borra el usado. TTL 10 minutos.",
    "sesiones_horas": "FUERA DE ALCANCE. Se autopurga igual que oauth_states. TTL 30 minutos.",
    "intentos_identificacion": "FUERA DE ALCANCE. Es el log FORENSE del link público de horas: "
                               "borrarlo perdería justamente el registro de quién intentó entrar. "
                               "Mismo criterio que `auditoria`.",
    "empleado_superior_pendiente": "FUERA DE ALCANCE. Tabla de TRABAJO del import de nómina: la "
                                   "segunda pasada la reescribe entera cada vez. El smoke no "
                                   "corre imports de nómina (necesitan el archivo real de RRHH).",

    # ── CASCADE: las borra la base con su padre, que sí está en ORDEN ─────────
    "objetivo_responsables": "CASCADE. Puente de `objetivos`, que SÍ está en ORDEN. La FK es ON "
                             "DELETE CASCADE, así que se van con el objetivo sembrado.",

    # ── 🔴 HUECOS: el smoke puede dejar filas y nadie las limpia ──────────────
    "reportes_generados": "🔴 HUECO CONOCIDO — es LA tabla que motivó este barrido. El recorrido "
                          "del smoke del 23/8/2026 generó reportes y las filas quedaron en "
                          "producción. 🚩 Salida: sumarla a `ORDEN` con su forma de identificar "
                          "lo sembrado (el `generado_por` de los usuarios de prueba), que es "
                          "trabajo del seeder y no de este test.",
    "adjuntos": "🔴 HUECO, y el peor de los tres porque tiene DOS mitades. El smoke puede subir "
                "un adjunto: queda la fila Y el objeto en Storage. La fila no la limpia nadie, y "
                "el objeto tampoco — ver la regla de buckets de abajo. 🚩 Salida: sumarla a "
                "`ORDEN` Y hacer que el limpiador borre del bucket.",
    "vacaciones_pendientes": "🔴 HUECO. El smoke puede cargar días pendientes desde /vacaciones. "
                             "Cuelga del colaborador sembrado, así que la clave natural es su "
                             "`empleado_id` — la misma que ya usan `solicitudes_vacaciones` y "
                             "`solicitudes_ausencia` en `plan_de_borrado`. 🚩 Salida: una línea.",
    "mail_enviado": "🔴 HUECO DECLARADO SIN URGENCIA. El envío real de mails NO es automatizable "
                    "(no se puede desenviar), así que el smoke no lo ejercita y hoy no deja "
                    "filas. Queda anotada por si algún día se prueba el circuito con la casilla "
                    "de prueba.",
    "evaluacion_lotes": "🔴 HUECO DECLARADO SIN URGENCIA. El import de evaluaciones no es "
                        "automatizable (necesita los dos CSV reales de RRHH). Si alguna vez se "
                        "siembra un lote, el borrado ya existe (`delete_lote` + CASCADE) y sólo "
                        "hay que llamarlo.",
    "evaluacion_equivalencias": "🔴 HUECO DECLARADO SIN URGENCIA. Hermana de la anterior, con una "
                                "vuelta propia: NO cascadea al borrar el lote (cuelga de "
                                "`empresa_id`), así que sobreviviría a mano.",
    "presupuesto_areas": "🔴 HUECO. `POST /api/costos/presupuesto` la escribe. ⚠️ Hoy ese endpoint "
                         "es inalcanzable desde la UI (lo declara `test_callers_huerfanos`), así "
                         "que el smoke con navegador no puede llegar — pero el día que se le "
                         "ponga botón, empieza a dejar filas.",
    "parametros_screening": "🔴 HUECO. La configuración de screening se escribe desde "
                            "/configuracion. El smoke puede tocarla y no vuelve sola al default.",
    "usuario_integraciones": "🔴 HUECO. Conectar o desconectar una integración escribe acá. El "
                             "smoke no puede completar un OAuth real, así que hoy no la toca.",
    "planes_carrera_hitos": "🔴 HUECO. Cuelga de `planes_carrera`, del módulo de SUCESIÓN, que "
                            "está apagado en el front por dos flags. El smoke no llega.",
    "offboarding_activos": "🔴 REVISAR: no es una tabla de `schema.sql` sino el nombre que un "
                           "repo le pasa a `.table()`. Si es una VISTA, no se puede insertar y "
                           "esta entrada sobra; si es una tabla real, es un hueco. 🚩 Salida: "
                           "mirarla en el catálogo y cerrar la duda en una línea.",
}

# ~25% por debajo de lo medido el 24/8/2026 (47 tablas que crean filas, 27 en ORDEN, 3 buckets).
_MINIMO_TABLAS = 35
_MINIMO_ORDEN = 20
_MINIMO_BUCKETS = 3
# Call sites cuyo nombre no se resuelve. Medidos: 11. Si crecen mucho, el barrido empieza a
# reportar de menos SIN FALLAR, que es el modo de falla que hay que impedir.
_MAXIMO_SIN_RESOLVER = 20


class TestElBarridoEstaMirandoAlgo:
    """Sin esto, todo lo de abajo pasa en el vacío."""

    def test_descubre_tablas_que_crean_filas(self) -> None:
        n = len(tablas_que_crean_filas())
        assert n >= _MINIMO_TABLAS, (
            f"solo {n} tablas con insert/upsert (mínimo {_MINIMO_TABLAS}): la resolución del "
            "nombre de tabla se rompió. Ver `tests/_barrido_tablas.py`.")

    def test_lee_el_orden_del_limpiador(self) -> None:
        n = len(orden_del_limpiador())
        assert n >= _MINIMO_ORDEN, (
            f"solo {n} tablas en ORDEN (mínimo {_MINIMO_ORDEN}): el parseo de "
            "`scripts/_semilla_plan_borrado.py` dejó de encontrar la lista.")

    def test_no_se_pierde_de_vista_lo_que_no_puede_resolver(self) -> None:
        """🔴 LA GUARDA QUE MÁS IMPORTA. Un call site sin resolver NO rompe nada: simplemente no
        se cuenta, y el barrido queda en verde habiendo mirado menos tablas. Es el falso verde
        por omisión, que es el que nadie nota."""
        pendientes = sin_resolver()
        assert len(pendientes) <= _MAXIMO_SIN_RESOLVER, (
            f"{len(pendientes)} call sites sin resolver el nombre de tabla (máximo "
            f"{_MAXIMO_SIN_RESOLVER}): {pendientes[:8]}. El barrido está mirando de menos.")


class TestElLimpiadorAlcanzaLoQueElCodigoEscribe:

    def test_toda_tabla_que_crea_filas_esta_en_orden_o_declarada(self) -> None:
        """LA REGLA. Una tabla fuera de las dos listas deja filas en producción sin que nadie
        se entere: el limpiador termina en verde y ni las cuenta."""
        nuevas = sorted(tablas_que_crean_filas() - set(orden_del_limpiador()) - set(_FUERA_DE_ORDEN))
        assert not nuevas, (
            f"El código crea filas en {nuevas} y el limpiador de la semilla no las conoce.\n"
            "Si el smoke puede llegar ahí, esas filas quedan en PRODUCCIÓN para siempre.\n"
            "Agregala a ORDEN en `scripts/_semilla_plan_borrado.py` (y su forma de identificar "
            "lo sembrado en `plan_de_borrado`), o declarala arriba CON su razón y su clase.")

    def test_las_declaradas_siguen_fuera_de_orden(self) -> None:
        """Dirección inversa: una declaración que ya no corresponde es ruido que tapa la próxima."""
        en_orden = set(orden_del_limpiador())
        obsoletas = sorted(t for t in _FUERA_DE_ORDEN if t in en_orden)
        assert not obsoletas, (
            f"Estas ya están en ORDEN: {obsoletas}. Sacalas de la lista de declaradas.")

    def test_las_declaradas_siguen_existiendo_en_el_codigo(self) -> None:
        """Una declaración sobre una tabla que el código ya no escribe también es ruido."""
        escritas = tablas_que_crean_filas()
        fantasmas = sorted(t for t in _FUERA_DE_ORDEN if t not in escritas)
        assert not fantasmas, (
            f"El código ya no crea filas en {fantasmas}: sacalas de la lista de declaradas.")

    def test_toda_declaracion_tiene_razon_y_clase(self) -> None:
        sin_razon = [t for t, r in _FUERA_DE_ORDEN.items() if len(r.strip()) < 40]
        assert not sin_razon, f"Declaraciones sin razón escrita: {sin_razon}"
        sin_clase = [t for t, r in _FUERA_DE_ORDEN.items()
                     if not any(c in r for c in ("FUERA DE ALCANCE", "CASCADE", "HUECO", "REVISAR"))]
        assert not sin_clase, (
            f"Declaraciones sin decir si son FUERA DE ALCANCE, CASCADE o HUECO: {sin_clase}. "
            "La diferencia es si hay algo que hacer, y es lo único que hace útil a esta lista.")

    def test_los_huecos_siguen_declarados(self) -> None:
        """Que la clase HUECO exista y no se diluya: son la lista de tareas del próximo seeder."""
        huecos = [t for t, r in _FUERA_DE_ORDEN.items() if "HUECO" in r]
        assert huecos, "ninguna declaración marcada como HUECO: ¿se cerraron todas, o se diluyó la marca?"


class TestElLimpiadorTambienTieneQueMirarStorage:
    """
    🔴 EL HALLAZGO DE FONDO, Y SE PORTA TAL CUAL A S3.

    Los dos archivos huérfanos de la corrida del 23/8/2026 **no los encontró el limpiador**: se
    encontraron mirando `storage.objects` a mano. El limpiador no sabe que Storage existe — su
    plan es `{tabla: [ids]}` y no tiene una sola línea de buckets.

    Y hay una razón de producto además de la del smoke: **borrar un adjunto por la API borra la
    fila y DEJA EL ARCHIVO.** `AdjuntoService.eliminar` hace un soft delete y su propio docstring
    lo dice — *"NO borra el objeto de Storage"*—, mientras que `_adjuntos_masivo.eliminar_todos`
    (el que corre al borrar la entidad padre) SÍ lo borra físicamente. O sea que **el camino que
    el usuario usa todos los días deja el archivo y el otro no**, y como nada purga los adjuntos
    en estado `eliminado`, el objeto queda huérfano para siempre.

    ⚠️ ESO SE PORTA TAL CUAL A S3, y ahí el costo cambia de naturaleza: en Supabase Storage es
    espacio; en S3 es una factura mensual por objetos que ninguna fila referencia y que nadie
    puede enumerar desde la aplicación. Es exactamente la clase de cosa que hay que decidir ANTES
    del cutover, no después.

    Este test no arregla nada de eso: **fija que los tres buckets existan y que el limpiador
    todavía no los conozca**, para que el día que alguien los cablee, el rojo lo obligue a venir
    acá a borrar esta declaración y a escribir qué hizo.
    """

    def test_hay_tres_buckets_declarados_en_el_punto_unico(self) -> None:
        buckets = buckets_del_storage()
        assert len(buckets) >= _MINIMO_BUCKETS, (
            f"solo {len(buckets)} buckets leídos de integrations/storage.py: {buckets}. "
            "La lectura de las constantes se rompió.")
        assert {"documentos", "cvs", "avatars"} <= buckets

    def test_el_limpiador_todavia_no_borra_de_storage(self) -> None:
        """🔴 ESTE TEST ESTÁ ESCRITO AL REVÉS A PROPÓSITO: afirma que la limpieza NO existe.

        Es un recordatorio ejecutable de una deuda conocida, no una regla que proteja un
        comportamiento. Cuando alguien la cierre, este test se pone en ROJO — y ese rojo es el
        que lo obliga a pasar por acá, borrar esta declaración y actualizar el encabezado. Sin
        él, la deuda se cierra en silencio y la explicación de por qué existía se pierde.

        🚩 QUÉ HACER CUANDO ROJEE: borrar este test, sacar la mitad de Storage del encabezado, y
        sacar de `_FUERA_DE_ORDEN` la parte de `adjuntos` que habla del objeto huérfano.
        """
        fuentes = "\n".join(p.read_text(encoding="utf-8")
                            for p in _SCRIPTS.glob("*.py"))
        toca_storage = any(b in fuentes for b in ("storage.borrar", "from_(", ".remove("))
        assert not toca_storage, (
            "🎉 El limpiador de la semilla ahora SÍ toca Storage. Ver el 🚩 del docstring: "
            "borrá este test y actualizá el encabezado de la clase.")
