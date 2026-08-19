"""
🔴 BARRIDO ESTRUCTURAL — falla cuando alguien construye algo que nadie llama.

POR QUÉ EXISTE. Un símbolo sin caller no rompe nada: no hay excepción, no hay 500, la suite
sigue verde. Lo que hay es una feature que el usuario no puede alcanzar, y que se lee como
"implementada" en la doc y en el código. Este repo ya juntó DOS casos, y cada uno bloqueaba un
módulo entero:
  · `set_remitente()` — existía, estaba documentado y testeado. Sin caller, el módulo de mails
    no tenía casilla de sistema y era inalcanzable.
  · `POST /api/plantillas/enviar` — montado, testeado, y sin ninguna pantalla que lo llame.
Los dos se encontraron A MANO. Este barrido es para no depender de eso.

🔑 EL ALCANCE ES `services/` + `repositories/` COMPLETO, NO SOLO LOS `_*.py`. Es deliberado:
`set_remitente` vive en `repositories/integracion_remitente_repo.py`, un repo SIN guion bajo. Un
barrido acotado a los satélites habría nacido en verde y ciego al caso que lo motiva — que es
exactamente el falso verde que el repo persigue en todos sus barridos.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · El mecanismo (AST + introspección de `app.routes`) descubre solo; no hay ninguna lista
    escrita a mano de qué mirar. Un módulo o un endpoint que se agregue mañana entra solo.
  · Los SIETE falsos positivos que producían ~48 huérfanos falsos están cubiertos y explicados
    uno por uno en `tests/_barrido_callers.py`. Sin ellos el barrido nace en rojo y se apaga.
  · Guardas de mínimo ANTES de comparar (abajo): si el descubrimiento se rompe, esto falla en
    vez de pasar en el vacío habiendo mirado cero símbolos.
  · Las excepciones se verifican en las DOS direcciones: que lo huérfano esté declarado, y que
    lo declarado siga huérfano. Una lista de excepciones que nadie limpia se vuelve basura.

🚩 LO QUE NO CUBRE: llamadas dinámicas (`repo[nombre]()`), símbolos alcanzados solo por
`Depends()`, y paths que el front arme concatenando fuera de un literal. Los tres sobre-cuentan
callers (dan por vivo algo muerto), nunca al revés: el barrido no puede inventar un huérfano.
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

from tests._barrido_callers import (  # noqa: E402
    clasificar_simbolos, endpoints_sin_front, paths_del_front, rutas_backend,
)

# ── Motivos compartidos ───────────────────────────────────────────────────────

_MAILS = ("🔴 PENDIENTE, NO INTENCIONAL. `POST /api/plantillas/enviar` YA se conectó (el botón "
          "'Enviar' de PlantillasSection), pero esta función sigue sin punta: es la que permitiría "
          "decir 'quedan 12 de 50' después de un corte parcial. Hoy el modal de envío lo resuelve "
          "de otra forma —reintentar el mismo grupo, apoyado en la idempotencia del backend—, así "
          "que sale de esta lista cuando la pantalla muestre los pendientes, o se borra.")

_PARA_TESTS = ("existe PARA el test estructural, por diseño, y su docstring lo dice. No tiene "
               "caller de producción y no debe tenerlo.")

_RECAT = ("el backend de recategorizaciones se construyó primero y el front es la sesión "
          "siguiente. DISPARADOR: sale de esta lista cuando exista "
          "frontend/app/(dashboard)/recategorizaciones/ con su services/recategorizaciones.ts, "
          "y la ruta anidada cuando la ficha del empleado tenga su octava sección. Si para "
          "entonces sigue acá, el módulo quedó publicado e inalcanzable.")

_PERFILES = ("el backend de perfiles de puesto se construyó primero y el front es la sesión "
             "siguiente. DISPARADOR: sale de esta lista cuando exista "
             "frontend/app/(dashboard)/perfiles-puesto/ con su services/perfilesPuesto.ts. Si "
             "para entonces sigue acá, el módulo quedó publicado e inalcanzable — el caso "
             "POST /api/plantillas/enviar.")

# ── Símbolos sin caller declarados ────────────────────────────────────────────
# Cada entrada lleva su razón: si alguien agrega una acá sin justificarla, se ve en el diff.

_SIMBOLOS_SIN_CALLER: dict[str, str] = {
    "repositories/assessment_campanas_repo.py::AssessmentCampanasRepo.mark_link_completed":
        "assessment está apagado por ASSESSMENT_ENABLED (router desmontado). El módulo entero "
        "queda fuera de alcance hasta que se encienda; que un link nunca se marque completado se "
        "revisa ahí, no acá.",

    "services/mail_envio_service.py::destinatarios_pendientes": _MAILS,

    "services/mailer/_variables.py::campos_leidos": _PARA_TESTS,
    "services/_nomina_empleados_transforms.py::HEADERS_OPCIONALES": _PARA_TESTS,
}

# ── Endpoints sin caller en el front declarados ───────────────────────────────

_ENDPOINTS_SIN_FRONT: dict[tuple[str, str], str] = {
    ("GET", "/health"): "infraestructura: lo consulta el chequeo post-deploy, no una pantalla.",


    ("GET", "/api/integraciones/google/callback"):
        "lo invoca el REDIRECT de Google, no el front. Un wrapper en services/ sería incorrecto.",

    # ✅ El link público de carga de horas YA NO ESTÁ ACÁ. Sus cuatro endpoints estuvieron
    # declarados exactamente una tanda —desde que el barrido dejó de ser ciego a los módulos
    # gateados por flag hasta que se construyó `app/horas/`— y el disparador escrito en su razón
    # ("sale de esta lista cuando exista app/horas/") se cumplió. El propio barrido pidió que se
    # sacaran: `test_las_excepciones_siguen_sin_caller` da rojo cuando algo declarado empieza a
    # tener caller. Es el ciclo que esta lista pretende, funcionando.

    # 🔴 EFECTIVIZACIÓN DE LA BAJA — NO es completitud REST: es la mitad backend de un fix que
    # todavía no tiene botón. Por eso lleva DISPARADOR explícito y no una razón permanente.
    # Hasta este cambio, `POST /api/offboarding` daba de baja al empleado en el acto, con la fecha
    # prevista en el futuro: la persona desaparecía del headcount con treinta días por delante.
    # Ahora la baja la escribe este endpoint, y alguien la tiene que confirmar.
    # SALE DE ESTA LISTA cuando `frontend/services/offboarding.ts` tenga su `efectivizarBaja` y la
    # ficha del proceso tenga el botón con su cartel de confirmación (molde: EliminarVacanteButton).
    # 🚩 MIENTRAS SIGA ACÁ, LA BAJA NO SE PUEDE EFECTIVIZAR DESDE LA UI, y eso es un estado a
    # medias que hay que cerrar en la sesión de front: los offboardings quedan abiertos para
    # siempre y ningún empleado pasa nunca a `baja`. El propio barrido lo va a pedir:
    # `test_las_excepciones_siguen_sin_caller` da rojo cuando algo declarado empieza a tener caller.
    ("POST", "/api/offboarding/{instancia_id}/efectivizar"):
        "la baja EFECTIVA del empleado + cierre de la instancia. Backend del fix de offboarding; "
        "el botón de la ficha se construye en la sesión de front que sigue.",

    # 🔴 IMPORT DE FORMACIÓN (A5, 19/8/2026) — la mitad backend, con DISPARADOR explícito.
    # El flujo entero (preview → confirmar, con 22 tests por HTTP) existe y la pantalla todavía
    # no: la UI del import quedó para la sesión de front, molde ImportarNominaCSVModal.
    # SALE DE ESTA LISTA cuando `frontend/services/` tenga el wrapper del preview/confirmar y la
    # pantalla de Formación su modal de import. 🚩 MIENTRAS SIGA ACÁ, el Excel solo se puede
    # importar por HTTP directo. El propio barrido lo va a pedir cuando el front llegue:
    # `test_las_excepciones_siguen_sin_caller` da rojo cuando algo declarado gana caller.
    ("POST", "/api/importacion/formacion/preview"):
        "preview del import del Excel de Formación. Backend de A5; el modal del front es la "
        "sesión que sigue.",
    ("POST", "/api/importacion/formacion/confirmar"):
        "confirmación del import del Excel de Formación. Misma sesión de front pendiente que "
        "el preview.",

    # 🔴 ACTIVACIÓN DEL PREINGRESO — mismo caso que el de arriba y en el extremo contrario del
    # ciclo: es la mitad backend de una feature cuya pantalla es una tanda aparte (el bloque B,
    # "próximos ingresos"). Lleva DISPARADOR, no razón permanente.
    # A3.2 alcanzó hasta acá a propósito: el front de esta sesión se limitó a los dos archivos
    # que BLOQUEABAN el type-check (`types/empleado.ts` y `_camposEmpleados.ts`), porque sin
    # ellos un preingreso que llegue por la API rompe `next build`.
    # SALE DE ESTA LISTA cuando `frontend/services/empleados.ts` tenga su `activarEmpleado` y la
    # ficha tenga el botón con su confirmación (molde: EliminarVacanteButton).
    # 🚩 MIENTRAS SIGA ACÁ, UN PREINGRESO NO SE PUEDE ACTIVAR DESDE LA UI. Es un estado a medias
    # con una consecuencia concreta: se pueden CREAR preingresos por el alta, y quedan sin forma
    # de pasar a `activo` salvo por el PUT del legajo —que no valida que la fecha de ingreso haya
    # ocurrido, que es justamente la guarda que este endpoint existe para aplicar—.
    ("POST", "/api/empleados/{id}/activar"):
        "el pase de preingreso a activo. Backend de la feature de preingresos; la pantalla de "
        "próximos ingresos y su botón son el bloque B.",

    # 🔴 EL PUENTE CANDIDATO→EMPLEADO — tercer caso del mismo patrón, y el que cierra el ciclo.
    # Con `/efectivizar` (la salida) y `/activar` (el ingreso), este es la ENTRADA: los tres son
    # la mitad backend de un acto cuyo botón vive en una tanda de front aparte.
    # Lleva DISPARADOR, no razón permanente.
    # SALE DE ESTA LISTA cuando `frontend/services/candidatos.ts` tenga su `contratarCandidato` y
    # la ficha del candidato tenga el botón con su formulario de tres campos (email corporativo,
    # roles, fecha de ingreso) y su confirmación. Molde: `EliminarVacanteButton`.
    # 🚩 MIENTRAS SIGA ACÁ, UN CANDIDATO EN OFERTA NO SE PUEDE CONTRATAR DESDE LA UI. La
    # consecuencia concreta: `candidatos.estado` sigue sin tener un solo escritor alcanzable, así
    # que en producción ningún candidato va a llegar nunca a `contratado` y la columna que A4.1
    # revivió se queda otra vez sin datos — con la diferencia de que ahora el camino existe.
    ("POST", "/api/candidatos/{id}/contratar"):
        "el puente candidato→empleado: crea el legajo en `preingreso` y marca la postulación "
        "como contratada. Backend de A4.2; el botón y su formulario son la tanda de front.",

    # Completitud REST: quedan publicados a propósito. El front resuelve lo mismo por otra vía
    # (el listado ya filtra, la baja va por offboarding), pero el endpoint es correcto y barato.
    # ✅ `DELETE /api/empleados/{id}` YA NO ESTÁ ACÁ: se BORRÓ junto con su cadena entera
    # (deactivate_empleado → desactivar → soft_delete → baja_logica → payload_baja_empleado).
    # Estaba declarado como "completitud REST", y esa razón no se sostenía: escribía
    # `estado='baja'` SIN `fecha_egreso`, así que la persona desaparecía del headcount y no
    # aparecía en el conteo de bajas de ningún mes. La baja real va por
    # `POST /api/offboarding/{id}/efectivizar`, que siempre escribe la fecha.
    ("GET", "/api/vacaciones-pendientes/empleado/{empleado_id}"):
        "completitud REST: el listado ya acepta `empleado_id` como Query y es el que usa el front.",
    ("GET", "/api/ausencias/{id}"): "completitud REST: el front nunca pide una ausencia sola.",
    ("GET", "/api/capacitaciones/{id}"): "completitud REST: el front nunca pide una sola.",
    ("GET", "/api/eventos/{id}"):
        "completitud REST: el modal de edición recibe el objeto entero del listado, así que "
        "pedir la fila de vuelta sería una ida a la red por lo que la pantalla ya tiene. Es el "
        "MISMO caso que /api/clientes/{id}, y por eso services/eventos.ts nace sin su "
        "`fetchEvento` en vez de con un wrapper que nadie llama.",
    ("GET", "/api/clientes/{id}"):
        "completitud REST: el modal de edición recibe el objeto entero del listado, así que "
        "pedir la fila de vuelta sería una ida a la red por lo que la pantalla ya tiene. Su "
        "wrapper `fetchCliente` se borró el 2026-08-10 tras nacer sin caller; este barrido no "
        "lo vio porque `updateCliente`/`deleteCliente` escriben el MISMO literal de path.",

    # 🔴 PERFILES DE PUESTO — las 6 rutas del módulo, declaradas porque el BACKEND se construyó
    # primero y el front es la sesión siguiente. NO es "completitud REST": es una feature a
    # medio cablear, y por eso lleva un DISPARADOR explícito en vez de una razón permanente.
    # SALEN DE ESTA LISTA cuando exista `frontend/app/(dashboard)/perfiles-puesto/` con su
    # `services/perfilesPuesto.ts`. Si para entonces siguen acá, el módulo quedó publicado e
    # inalcanzable — exactamente el caso `POST /api/plantillas/enviar`.
    # El propio barrido lo va a pedir: `test_las_excepciones_siguen_sin_caller` da rojo cuando
    # algo declarado empieza a tener caller.
    # 🔴 OBJETIVOS / catálogos — mismo caso y mismo disparador que perfiles y recategorizaciones:
    # el backend de la feature 2.4 se construyó primero (sesión 1 de 3) y el front es la sesión 3.
    # NO es completitud REST: este endpoint tiene un consumidor concreto y planificado —el
    # selector de vista (anual / operativos) del formulario y de la barra de filtros—, que hoy
    # todavía no existe.
    # SALE DE ESTA LISTA cuando `frontend/services/objetivos.ts` tenga su `fetchCamposObjetivo`.
    # Si para entonces sigue acá, el vocabulario quedó publicado y el front lo hardcodeó igual,
    # que es exactamente lo que el endpoint existe para evitar.
    ("GET", "/api/objetivos/campos"):
        "el vocabulario cerrado de `tipo` (anual/operativo) servido para que el front no lo "
        "escriba por su cuenta. Backend de la sesión 1 de 3; lo consume el selector de vista "
        "que se construye en la sesión 3 del front.",
    ("GET", "/api/objetivos/areas-conocidas"):
        "el pool de áreas ya usadas, para el desplegable del filtro por área. Backend de la "
        "sesión 2 de 3; lo consume la barra de filtros que se construye en la sesión 3 del "
        "front. SALE DE ESTA LISTA junto con /campos, con el mismo disparador.",

    # 🔴 RECATEGORIZACIONES — mismo caso y mismo disparador que perfiles: el backend se
    # construyó primero. Las 6 rutas, incluida la anidada bajo el empleado que alimenta la
    # octava sección de la ficha.
    ("GET", "/api/recategorizaciones"): _RECAT,
    ("POST", "/api/recategorizaciones"): _RECAT,
    ("GET", "/api/recategorizaciones/exportar"): _RECAT,
    ("GET", "/api/recategorizaciones/{id}"): _RECAT,
    ("PUT", "/api/recategorizaciones/{id}"): _RECAT,
    ("GET", "/api/empleados/{empleado_id}/recategorizaciones"): _RECAT,

    # ✅ `GET /api/eventos/pendientes` YA NO ESTÁ ACÁ: su "sesión 2" llegó (A6, 19/8/2026) y la
    # tarjeta del dashboard consume `GET /api/dashboard/atencion`, que devuelve los eventos
    # pendientes JUNTO con las alertas calculadas. El endpoint viejo quedaba huérfano para
    # siempre y se BORRÓ (la lógica sigue viva en `EventoAgendaService.pendientes`, ahora con el
    # panel como caller). Su disparador decía "sale de esta lista cuando el dashboard lo llame";
    # el dashboard llama al reemplazo, así que salió por la otra puerta — con la ruta.

    # 🔴 PANEL "REQUIERE TU ATENCIÓN" (A6, 19/8/2026) — la mitad backend, con DISPARADOR.
    # El flujo entero (calculadas + manuales + resolver) existe y la tarjeta del dashboard
    # todavía no. SALE DE ESTA LISTA cuando `frontend/` tenga el wrapper de `/atencion` y el
    # dashboard pinte el panel. 🚩 MIENTRAS SIGA ACÁ, las alertas solo se ven por HTTP directo.
    ("GET", "/api/dashboard/atencion"):
        "el panel 'Requiere tu atención' del dashboard. Backend de A6; la tarjeta del front es "
        "la sesión que sigue.",
    ("POST", "/api/dashboard/atencion/resolver"):
        "resuelve una alerta manual del panel. Misma sesión de front pendiente que el GET.",

    ("GET", "/api/perfiles-puesto"): _PERFILES,
    ("GET", "/api/perfiles-puesto/campos"): _PERFILES,
    ("GET", "/api/perfiles-puesto/exportar"): _PERFILES,
    ("GET", "/api/perfiles-puesto/{id}"): _PERFILES,
    ("POST", "/api/perfiles-puesto"): _PERFILES,
    ("PUT", "/api/perfiles-puesto/{id}"): _PERFILES,
    ("DELETE", "/api/perfiles-puesto/{id}"): _PERFILES,

    # Acá vivían las 19 rutas de la familia `ev_*`, declaradas porque los routers seguían
    # montados sin UI que los llamara. Se BORRARON el 2026-08-11 (bloque J5a) junto con sus
    # 17 archivos: ya no hay ruta que declarar. Las 5 tablas `ev_*` siguen en la base hasta
    # que corra la migración de J5b.
}

# ── Guardas de mínimo ─────────────────────────────────────────────────────────
# Criterio: ~25% por debajo del valor real de hoy (916 símbolos, 210 rutas, 196 paths del front).
# El margen absorbe la baja normal del repo —que borra código muerto y parte archivos seguido—
# sin absorber una ROTURA del descubrimiento, que no baja un 25%: colapsa. Si `_BAJO_BARRIDO`
# deja de matchear, si `app.routes` no se puede introspeccionar o si cambia la raíz del front,
# el conteo se va a cero o a una fracción, y eso es lo que estas tres guardas muerden.
_MINIMO_SIMBOLOS = 700
_MINIMO_RUTAS = 180
_MINIMO_PATHS_FRONT = 140


class TestElBarridoEstaMirandoAlgo:
    """Sin esto, todo lo de abajo pasa en el vacío."""

    def test_descubre_simbolos(self) -> None:
        _, _, total = clasificar_simbolos()
        assert total >= _MINIMO_SIMBOLOS, (
            f"El barrido solo encontró {total} símbolos públicos (mínimo {_MINIMO_SIMBOLOS}). "
            "No es que se borró código: es que el descubrimiento se rompió.")

    def test_descubre_rutas(self) -> None:
        assert len(rutas_backend()) >= _MINIMO_RUTAS

    def test_descubre_llamadas_del_front(self) -> None:
        """Si el front no se lee, TODOS los endpoints saldrían huérfanos a la vez."""
        assert len(paths_del_front()) >= _MINIMO_PATHS_FRONT


class TestSimbolosSinCaller:

    def test_ningun_simbolo_huerfano_sin_declarar(self) -> None:
        """Bucket 1: nadie lo llama, ni siquiera un test."""
        huerfanos, _, _ = clasificar_simbolos()
        nuevos = [s for s in huerfanos if s not in _SIMBOLOS_SIN_CALLER]
        assert not nuevos, (
            f"Símbolos públicos que nadie llama: {nuevos}. Si falta la punta del cable río "
            "arriba, conectala; si está muerto, borralo; si es legítimo, declaralo en "
            "_SIMBOLOS_SIN_CALLER CON su razón.")

    def test_ningun_simbolo_solo_de_tests_sin_declarar(self) -> None:
        """Bucket 2, el peligroso: PARECE vivo porque la suite lo ejercita.

        Es el caso `set_remitente`: documentado, testeado, y sin un solo caller de producción.
        Un test verde sobre un símbolo inalcanzable no prueba la feature: prueba la función."""
        _, solo_tests, _ = clasificar_simbolos()
        nuevos = [s for s in solo_tests if s not in _SIMBOLOS_SIN_CALLER]
        assert not nuevos, (
            f"Símbolos cuyo ÚNICO caller está en tests/: {nuevos}. La suite los ejercita pero "
            "producción no los alcanza — verificá que la feature tenga punta antes de darla por "
            "hecha.")

    def test_las_excepciones_siguen_sin_caller(self) -> None:
        """Dirección inversa: una excepción que ya tiene caller (o que apunta a un símbolo
        borrado) es ruido que oculta el próximo caso."""
        huerfanos, solo_tests, _ = clasificar_simbolos()
        vigentes = set(huerfanos) | set(solo_tests)
        obsoletas = [s for s in _SIMBOLOS_SIN_CALLER if s not in vigentes]
        assert not obsoletas, (
            f"Excepciones que ya no corresponden: {obsoletas}. O el símbolo consiguió caller "
            "(sacalo de la lista) o se borró (sacalo igual).")


class TestEndpointsSinCaller:

    def test_ningun_endpoint_sin_front_sin_declarar(self) -> None:
        """Bucket 3: la ruta existe, está montada y responde, y ninguna pantalla la llama."""
        nuevos = [par for par in endpoints_sin_front() if par not in _ENDPOINTS_SIN_FRONT]
        assert not nuevos, (
            f"Endpoints que el front nunca llama: {nuevos}. Es una feature publicada e "
            "inalcanzable — como POST /api/plantillas/enviar. Conectala o declarala CON razón.")

    def test_las_excepciones_siguen_sin_caller(self) -> None:
        vigentes = set(endpoints_sin_front())
        montadas = set(rutas_backend())
        obsoletas = [
            par for par in _ENDPOINTS_SIN_FRONT
            if par not in vigentes and par in montadas          # ya lo llama el front
        ]
        assert not obsoletas, (
            f"Endpoints declarados sin front que AHORA sí se llaman: {obsoletas}. Sacalos.")

    def test_ninguna_excepcion_apunta_a_una_ruta_borrada(self) -> None:
        montadas = set(rutas_backend())
        muertas = [par for par in _ENDPOINTS_SIN_FRONT if par not in montadas]
        assert not muertas, f"Excepciones que ya no corresponden a ninguna ruta: {muertas}"

    def test_toda_excepcion_tiene_razon_escrita(self) -> None:
        """Una lista pelada no se puede auditar: en seis meses nadie sabe por qué está cada una."""
        sin_razon = [k for k, v in {**_ENDPOINTS_SIN_FRONT}.items() if len(v.strip()) < 20]
        sin_razon += [k for k, v in _SIMBOLOS_SIN_CALLER.items() if len(v.strip()) < 20]
        assert not sin_razon, f"Excepciones sin razón escrita: {sin_razon}"
