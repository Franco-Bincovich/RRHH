"""
BARRIDO ESTRUCTURAL nº 54 — **todo filtro que un endpoint de lectura ACEPTA, o lo manda el front,
o está declarado con su razón.** Un filtro publicado que ninguna pantalla puede usar es una
promesa que no existe.

🔴 EL AGUJERO QUE CIERRA, Y POR QUÉ LOS DOS BARRIDOS QUE YA HABÍA NO PUEDEN VERLO. El repo tiene
dos guardias sobre los filtros y **los dos comparan LISTADO contra EXPORT**:
`tests/test_paridad_list_export.py` (empareja los `Query` de cada par de endpoints por
introspección) y `frontend/services/filtros-export.test.ts` (compara las dos traducciones del
front entre sí). Ninguno mira **backend contra front**. Un filtro que el backend acepta y que
NINGUNA de las dos puntas del front manda pasa los dos en verde: el par listado/export coincide
perfecto — en cero.

Por ese hueco se colaron **cinco filtros** hasta el 25/8/2026, encontrados a mano en tres tandas
distintas: `periodicidad` y `area` en objetivos —este último **con un endpoint de catálogo propio,
`/api/objetivos/areas-conocidas`, sin un solo llamador**— y `area_id`/`empleado_id`/`proyecto_id`
en vacaciones pendientes, cuya tabla ignoraba la barra de filtros de su propia pantalla. Los tres
hallazgos fueron manuales; sin este barrido el sexto también lo sería.

🔑 EL FRONT SE LEE, NO SE DUPLICA. La lista de qué manda cada servicio sale de los archivos reales
de `frontend/services/`, igual que `test_espejo_permisos.py` lee `permisos.ts` en vez de mantener
una copia. Un inventario a mano de "qué filtros usa el front" sería el espejo manual que este repo
ya paga en `permisos.ts` ↔ `permisos.py`.

⚠️ QUÉ NO PUEDE VER, dicho de frente: que el filtro llegue al SERVICIO pero no tenga un control en
la pantalla. Este barrido mira la capa `services/` del front, no los `_campos*.ts`. Un filtro
cableado en el service y sin control es alcanzable (por URL, por un link del dashboard) y es un
caso mucho más benigno que uno que ninguna función sabe mandar. La matriz de
`docs/MATRIZ-FILTROS.md` es la que cubre esa cuarta capa, a mano.
"""
import os
import re
import sys
from pathlib import Path

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

import pytest  # noqa: E402

_RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_RAIZ / "scripts"))

from _inv_backend import _crudo                    # noqa: E402
from _inv_llamadas import llamadas_por_funcion     # noqa: E402

_FRONT = _RAIZ / "frontend"

# No son filtros de pantalla y por eso no entran al barrido:
#   · `page`/`page_size` los pone el paginador y el export NO se pagina, por diseño.
#   · `formato` es cómo sale el archivo, no un recorte del conjunto.
#   · `limite` es un techo de filas, no un filtro (sólo lo tiene el historial de mails).
_NO_SON_FILTROS = {"page", "page_size", "formato", "limite"}


def _norm(path: str) -> str:
    """`/api/x/{lote_id}/y` -> `/api/x/{}/y`.

    🔴 SIN ESTO EL BARRIDO MIENTE, y de la peor forma. FastAPI nombra sus parámetros de path
    (`{lote_id}`) y el lector del front no puede saber cómo se llama del otro lado, así que los
    normaliza a `{}`. Comparar sin normalizar hace que TODA ruta dinámica se vea como "el front no
    la llama" — cuatro filtros de evaluaciones aparecían como huérfanos estando cableados. Es el
    mismo normalizador que usan los cinco módulos de `scripts/_inv_*`.
    """
    return re.sub(r"\{[^}]*\}", "{}", path)

# Filtros que el backend acepta y que el front NO manda a propósito, con su razón. Una excepción
# sin razón es la que nadie revisa; una que apunte a un filtro que ya no existe es ruido que tapa
# el próximo caso — los dos últimos tests cubren las dos cosas.
DECLARADOS: dict[tuple[str, str], str] = {
    ("/api/integraciones/google/callback", "code"):
        "los tres query params de este endpoint los pone GOOGLE en el redirect del OAuth, no "
        "nuestro front. Un wrapper en services/ que los mandara sería directamente incorrecto: "
        "el navegador llega acá desde el consent screen, no desde una pantalla nuestra.",
    ("/api/integraciones/google/callback", "state"):
        "ídem `code`: lo genera nuestro backend al ARRANCAR el flujo y lo devuelve Google. Ver "
        "`services/_oauth_state.py` — es el nonce de un solo uso, no un filtro.",
    ("/api/integraciones/google/callback", "error"):
        "ídem `code`: lo manda Google cuando el usuario RECHAZA el consentimiento.",
    ("/api/empleados/valores-conocidos", "campo"):
        "no es un filtro del listado: es CUÁL columna se quiere autocompletar, o sea el recurso "
        "que se pide. El front lo manda siempre (`fetchValoresConocidos(campo)`), pero como "
        "argumento posicional interpolado en la URL y no como una clave literal, así que el "
        "detector no lo ve. Declararlo es más honesto que aflojar el detector.",
}

# Filtros que el front SÍ manda, pero cuyas claves no viven en `frontend/services/`: el servicio
# hace pass-through de un objeto de filtros y el vocabulario está en el archivo de tipos.
#
# 🔴 ES UNA LISTA APARTE DE `DECLARADOS` Y NO UN CAJÓN DE SASTRE. Las dos dicen "no rojees", pero
# afirman cosas OPUESTAS: `DECLARADOS` dice *"esto no se manda, y está bien"*; esto dice *"esto SÍ
# se manda, y el detector no puede verlo"*. Meterlas en la misma lista convertiría un hecho
# verificable en una excusa, que es cómo se pudren las listas de excepciones.
# Y por eso cada entrada nombra el ARCHIVO donde está la clave: el test de abajo lo comprueba, así
# que esto no es una promesa sino una afirmación chequeada.
TRADUCE_AFUERA: dict[tuple[str, str], tuple[str, str]] = {
    ("/api/mails", "estado"): (
        "frontend/types/plantillas.ts",
        "`fetchHistorialMails` hace `new URLSearchParams(filtrosActivos(filtros))`: pasa el objeto "
        "ENTERO, así que lo que viaja es exactamente lo que declara `MailsFiltros`. No hay un "
        "traductor con claves literales que el detector pueda leer — el vocabulario ES el tipo.",
    ),
    ("/api/mails", "fecha_desde"): (
        "frontend/types/plantillas.ts", "ídem `estado`: viaja por el pass-through de `MailsFiltros`.",
    ),
    ("/api/mails", "fecha_hasta"): (
        "frontend/types/plantillas.ts", "ídem `estado`: viaja por el pass-through de `MailsFiltros`.",
    ),
}


def _filtros_backend() -> dict[str, set]:
    """path -> filtros que el GET acepta. Por introspección de `app.routes`, nunca una lista."""
    rutas, _solo_flag, _publicas = _crudo()
    out: dict[str, set] = {}
    for (metodo, path), route in rutas.items():
        if metodo != "GET":
            continue
        qs = {p.name for p in route.dependant.query_params if p.name not in _NO_SON_FILTROS}
        if qs:
            out[_norm(path)] = qs
    return out


def _claves_por_archivo() -> dict[str, set]:
    """archivo de services/ -> claves de query que aparecen en él, con la prosa enmascarada.

    Se cubren las cuatro formas que el repo usa para armar una query: `params.set("k", …)`, la
    clave de un objeto literal (`{ area_id: f.areaId }`), el shorthand (`{ entidad }`) y el
    literal interpolado (`?anio=${…}`).

    ⚠️ EL DETECTOR SOBRECUENTA A PROPÓSITO, y hay que saberlo: la segunda forma matchea CUALQUIER
    `clave:`, incluida la declaración de un tipo (`estado?: string`). O sea que un servicio que
    DECLARA un filtro en su interfaz y no lo manda cuenta como si lo mandara. Se eligió así porque
    la versión estricta daba **31 falsos positivos** contra el código real —el repo arma sus
    queries de cuatro formas distintas y con traductores compartidos—, y un barrido con treinta
    excepciones es un barrido que nadie mira. La dirección del error es la correcta para esta
    herramienta: no acusar de más. Lo que sigue cazando —y está verificado por mutación— es el
    caso que importa: el filtro que NO aparece por ningún lado del front.

    Enmascarar comentarios no es opcional: varios servicios explican
    EN PROSA qué filtro NO mandan y por qué —`vacacionesPendientes.ts` lo hacía hasta hoy— y un
    barrido por texto plano contaría esa explicación como si el filtro estuviera cableado, que es
    el falso VERDE exacto que hay que evitar.
    """
    out: dict[str, set] = {}
    for f in sorted((_FRONT / "services").glob("*.ts")):
        if ".test." in f.name:
            continue
        src = f.read_text(encoding="utf-8")
        src = re.sub(r"/\*(?:.|\n)*?\*/", "", src)
        src = re.sub(r"//[^\n]*", "", src)
        claves = set(re.findall(r'\.(?:set|append)\(\s*"([^"]+)"', src))
        claves |= set(re.findall(r"([a-z_][a-z0-9_]*)\s*\??\s*:", src))       # clave de objeto o de tipo
        claves |= set(re.findall(r"[{,]\s*([a-z_][a-z0-9_]*)\s*[,}]", src))    # shorthand `{ entidad }`
        claves |= set(re.findall(r"[?&]([a-z_]+)=", src))
        # Los servicios que IMPORTAN un traductor de otro archivo de `services/` heredan sus
        # claves. Un salto, no el cierre transitivo — y SÓLO imports de valor: un `import type`
        # trae la FORMA de un filtro, no el cable que lo manda, y contarlo daría verde sobre un
        # servicio que declara el tipo y no manda nada (el caso exacto de `vacacionesPendientes`
        # antes del 25/8/2026, que importaba `VacacionesFiltros` como tipo sin usar ninguno).
        vecinos = re.findall(r'^import\s+(?!type\b)[^;\n]*from\s+"@/services/(\w+)"', src, re.M)
        out["services/" + f.name] = (claves, {"services/" + v + ".ts" for v in vecinos})
    resuelto = {}
    for archivo, (claves, vecinos) in out.items():
        heredadas = set()
        for v in vecinos:
            if v in out:
                heredadas |= out[v][0]
        resuelto[archivo] = claves | heredadas
    return resuelto


def _mandados_por_path() -> dict[str, set]:
    """path del backend -> unión de las claves de TODOS los archivos que lo llaman.

    🔴 LA UNIDAD ES EL ARCHIVO, NO LA FUNCIÓN, y es deliberado: en este repo la traducción
    filtros→params vive en UNA función compartida por el listado y el export (`queryVacaciones`,
    `queryProyectos`, `queryObjetivos`…), así que mirar el cuerpo de `fetchX` sola daría cero
    claves y marcaría como huérfanos filtros que sí viajan. Se sobrecuenta a propósito: la
    dirección correcta para este barrido es no acusar de más.
    """
    claves = _claves_por_archivo()
    out: dict[str, set] = {}
    for (archivo, _fn), destinos in llamadas_por_funcion().items():
        for metodo, path in destinos:
            if metodo == "GET":
                out.setdefault(_norm(path), set()).update(claves.get(archivo, set()))
    return out


BACKEND = _filtros_backend()
MANDADOS = _mandados_por_path()
HUERFANOS = sorted(
    (path, filtro)
    for path, filtros in BACKEND.items()
    for filtro in sorted(filtros)
    if filtro not in MANDADOS.get(path, set())
)


def test_hay_algo_que_barrer():
    """Guarda contra el falso verde: si la introspección o el lector del front se rompen, los dos
    conjuntos quedan vacíos y todo lo de abajo pasa sin haber comparado nada."""
    assert len(BACKEND) >= 40, f"sólo {len(BACKEND)} endpoints con filtros: la introspección falló"
    assert sum(len(v) for v in BACKEND.values()) >= 90, "muy pocos filtros descubiertos"
    assert len(MANDADOS) >= 40, f"sólo {len(MANDADOS)} paths alcanzados desde el front"


def test_el_detector_del_front_reconoce_las_tres_formas():
    """El detector es la mitad que puede romperse en silencio: si dejara de matchear, TODO filtro
    se vería como huérfano y la lista de excepciones crecería para acallarlo. Se ancla contra tres
    servicios reales, uno por forma de armar la query."""
    claves = _claves_por_archivo()
    assert "estado" in claves["services/empleados.ts"], "no detecta `params.set(\"estado\", …)`"
    assert "area_id" in claves["services/proyectos.ts"], "no detecta la clave de objeto literal"
    assert "anio" in claves["services/horasCliente.ts"], "no detecta el filtro de período"


@pytest.mark.parametrize("caso", HUERFANOS, ids=lambda c: f"{c[0]}::{c[1]}")
def test_todo_filtro_publicado_lo_manda_el_front(caso):
    """🔴 EL BARRIDO. Contra el código del 24/8/2026 rojeaba con los cinco filtros que se
    encontraron a mano: `area` y `periodicidad` de objetivos, y los tres de vacaciones pendientes.
    """
    path, filtro = caso
    if (path, filtro) in DECLARADOS:
        pytest.skip(DECLARADOS[(path, filtro)])
    if (path, filtro) in TRADUCE_AFUERA:
        pytest.skip(TRADUCE_AFUERA[(path, filtro)][1])
    assert False, (
        f"`{path}` acepta el filtro `{filtro}` y ninguna función de `frontend/services/` se lo "
        f"manda: es un filtro publicado que ninguna pantalla puede usar. Cablealo, declaralo en "
        f"DECLARADOS con su razón, o sacalo del router."
    )


@pytest.mark.parametrize("clave", sorted(DECLARADOS) + sorted(TRADUCE_AFUERA))
def test_ninguna_excepcion_apunta_a_un_filtro_que_ya_no_existe(clave):
    """Una excepción muerta es ruido que tapa el próximo caso real."""
    path, filtro = clave
    assert path in BACKEND, f"`{path}` ya no es un endpoint de lectura: sacá la excepción"
    assert filtro in BACKEND[path], f"`{path}` ya no acepta `{filtro}`: sacá la excepción"


@pytest.mark.parametrize("clave", sorted(DECLARADOS))
def test_toda_excepcion_explica_algo(clave):
    """La razón es el contenido de la lista, no un campo a completar."""
    assert len(DECLARADOS[clave].strip()) >= 60, f"la excepción de {clave} no explica nada"


@pytest.mark.parametrize("clave", sorted(TRADUCE_AFUERA))
def test_lo_declarado_como_traducido_afuera_ESTA_de_verdad_ahi(clave):
    """🔴 LO QUE CONVIERTE ESTA LISTA EN UNA AFIRMACIÓN CHEQUEADA Y NO EN UNA EXCUSA. Cada entrada
    dice "el front SÍ manda este filtro, y su clave vive en tal archivo": esto abre el archivo y
    lo comprueba. Si alguien saca el campo del tipo —que es la forma exacta en que este filtro
    dejaría de viajar— el test rojea nombrando cuál, en vez de seguir tapándolo para siempre.
    """
    archivo, _razon = TRADUCE_AFUERA[clave]
    _path, filtro = clave
    fuente = (_RAIZ / archivo).read_text(encoding="utf-8")
    assert re.search(rf"\b{re.escape(filtro)}\s*\??\s*:", fuente), (
        f"`{filtro}` ya no figura en {archivo}: o dejó de viajar, o se mudó. Revisá la entrada."
    )
