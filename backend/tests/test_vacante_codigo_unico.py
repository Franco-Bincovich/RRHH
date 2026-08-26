"""
`services/_vacante_codigo.py` y su cableado en `_vacante_write`: la forma del código y la
garantía de que no se repita.

Archivo aparte de `test_vacante_codigo.py` porque cubren UNIDADES distintas: aquél mira la
COLUMNA (que el valor viaje al INSERT, que el índice lo defienda, que llegue al schema) y éste
mira la REGLA de aplicación (normalizar, rechazar con un mensaje que se entiende, y traducir el
choque de la base). Un solo archivo mezclaría el vocabulario de la base con el del negocio.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL DOBLE PARA QUE ESTOS TESTS PUEDAN FALLAR?

1. 🔴 **El repo doble tiene un código YA USADO y `find_by_codigo` lo devuelve.** Un doble que
   devolviera siempre `None` haría que `asegurar_unico` no pueda fallar nunca — el modo de falla
   que este módulo existe para cerrar sería inalcanzable.
2. 🔴 **Y además LEVANTA el error del índice** cuando le insertan uno repetido, aunque el chequeo
   previo lo haya dejado pasar. Es lo único que puede desmentir la traducción del choque: sin eso
   se podría borrar el `try` entero de `_vacante_write` y todo quedaría en verde, con la carrera
   real devolviendo un 500 en producción.
3. **El doble compara sin distinguir mayúsculas**, como el índice `upper(codigo)` real. Si
   comparara exacto, `eco-2026` contra `ECO-2026` pasaría y el test de normalización no probaría
   nada.
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
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.vacante import VacanteCreate, VacanteUpdate  # noqa: E402
from services._vacante_codigo import (  # noqa: E402
    _FORMA, CODIGO_DUPLICADO, CODIGO_INVALIDO, MAX_LARGO, MIN_LARGO, asegurar_unico, normalizar,
)
from services._vacante_write import actualizar, crear  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA, AREA = uuid4(), uuid4()
V_DUEÑA = str(uuid4())


class _Repo:
    """UNA vacante ya cargada con `ECO-2026`, en la empresa "DOSUBA".

    🔴 `save`/`update` LEVANTAN si el código ya está usado, aunque `asegurar_unico` haya pasado:
    es el índice único de la base modelado en el doble, y es lo que hace que la traducción del
    choque se pueda desmentir. `forzar_carrera` simula la ventana entre el SELECT y el INSERT —
    la fila aparece recién en el momento de escribir.
    """

    def __init__(self, forzar_carrera: bool = False) -> None:
        self.usados = {"ECO-2026": V_DUEÑA}
        self.forzar_carrera = forzar_carrera
        self.guardados = []

    def _fila(self, codigo, vid=None):
        return SimpleNamespace(id=vid or V_DUEÑA, codigo=codigo, titulo="Analista contable",
                               empresa_id=str(EMPRESA), empresa_nombre="DOSUBA", area_id=str(AREA),
                               estado="nueva")

    def find_by_codigo(self, codigo):
        if self.forzar_carrera:           # todavía no existe... para el SELECT previo
            return None
        vid = self.usados.get(codigo.upper())
        return self._fila(codigo.upper(), vid) if vid else None

    def find_by_id(self, vid, empresa_id=None):
        return self._fila("ECO-2026", str(vid))

    def _escribir(self, codigo, vid):
        # La otra sesión ya commiteó: de acá en adelante el SELECT la ve. Va ANTES del choque a
        # propósito — es lo que le permite a `choque_de_codigo` volver a consultar y NOMBRAR a la
        # dueña, que es todo el valor del mensaje.
        self.forzar_carrera = False
        if codigo and codigo.upper() in self.usados and self.usados[codigo.upper()] != vid:
            raise RuntimeError(
                'duplicate key value violates unique constraint "vacantes_codigo_uq"')
        self.guardados.append(codigo)
        return self._fila(codigo or "ECO-2026", vid)

    def save(self, data: VacanteCreate):
        return self._escribir(data.codigo, str(uuid4()))

    def update(self, vid, data: VacanteUpdate, empresa_id=None):
        return self._escribir(data.codigo, str(vid))


class _Audit:
    def __init__(self) -> None:
        self.eventos = []

    def registrar(self, **kw):
        self.eventos.append(kw)


def _create(codigo: str) -> VacanteCreate:
    return VacanteCreate(empresa_id=EMPRESA, codigo=codigo, titulo="Nueva", area_id=AREA,
                         tipo_contrato="efectivo")


# ── 1. La forma ───────────────────────────────────────────────────────────────

class TestNormalizar:

    @pytest.mark.parametrize("escrito", [
        "ECO-2026", "eco-2026", " eco-2026 ", "ECO 2026", "eco_2026", "ECO.2026",
        "ECO  -  2026", "--ECO-2026--",
    ], ids=lambda v: repr(v))
    def test_todas_estas_formas_son_el_mismo_codigo(self, escrito) -> None:
        """El índice único ya es sobre `upper(codigo)`, así que estas variantes NO podían
        convivir. Sin normalizar, lo que cambia es qué se MUESTRA: la ficha, el aviso de LinkedIn
        y el export mostrarían la variante que le salió a quien lo cargó primero."""
        assert normalizar(escrito) == "ECO-2026"

    @pytest.mark.parametrize("malo", [
        "", "   ", None, "-", "AB", "2026", "123-456", "ECO%2026", "ECO_%", "ECÓ-2026",
        "A" * 31,
    ], ids=lambda v: repr(v))
    def test_lo_que_no_se_puede_usar_como_codigo(self, malo) -> None:
        with pytest.raises(AppError) as e:
            normalizar(malo)
        assert e.value.code == CODIGO_INVALIDO
        assert e.value.status_code == 422

    def test_un_codigo_solo_numerico_se_rechaza_y_ese_es_el_punto(self) -> None:
        """🔴 `2026` matchearía cualquier "2026" suelto en un asunto —"CV 2026", "Postulación
        2026"— y mandaría el CV a esa búsqueda sin que nada falle. Es la misma clase de decisión
        que el mínimo de 4 dígitos que tenía el matcher viejo: la permisividad llega hasta donde
        no puede inventar una respuesta distinta."""
        with pytest.raises(AppError):
            normalizar("2026")
        assert normalizar("ECO2026") == "ECO2026", "con una letra alcanza"

    def test_el_mensaje_dice_QUE_HACER_y_no_solo_que_esta_mal(self) -> None:
        with pytest.raises(AppError) as e:
            normalizar("ECÓ 2026")
        assert "ECO-2026" in e.value.message, "el mensaje no muestra un ejemplo utilizable"
        assert "letra" in e.value.message


# ── 2. La unicidad ────────────────────────────────────────────────────────────

class TestNoSePuedeRepetir:

    def test_el_mensaje_NOMBRA_la_busqueda_que_ya_lo_tiene(self) -> None:
        """🔴 Es el requisito, no un adorno: "código duplicado" deja a Capital Humano adivinando
        entre 5 búsquedas hoy y 200 el año que viene. El mensaje tiene que decir A CUÁL ir."""
        with pytest.raises(AppError) as e:
            asegurar_unico(_Repo(), "ECO-2026")
        assert e.value.code == CODIGO_DUPLICADO and e.value.status_code == 409
        assert "Analista contable" in e.value.message, "no dice qué búsqueda lo tiene"
        assert "DOSUBA" in e.value.message, "no dice en qué sociedad está"
        assert "cambiale el código" in e.value.message, "no dice qué hacer"

    def test_EL_CONTRASTE_un_codigo_libre_pasa(self) -> None:
        asegurar_unico(_Repo(), "LOG-01")

    def test_una_vacante_no_choca_CONSIGO_MISMA(self) -> None:
        """Sin `excepto_id`, guardar una búsqueda sin tocarle el código la haría chocar con su
        propia fila: editar el título sería imposible."""
        asegurar_unico(_Repo(), "ECO-2026", excepto_id=V_DUEÑA)

    def test_el_alta_con_un_codigo_ya_usado_no_crea_nada(self) -> None:
        repo, audit = _Repo(), _Audit()
        with pytest.raises(AppError) as e:
            crear(repo, audit, _create("eco-2026"), "u1")
        assert e.value.code == CODIGO_DUPLICADO
        assert repo.guardados == [], "escribió igual"
        assert audit.eventos == [], "auditó un alta que no ocurrió"

    def test_la_edicion_a_un_codigo_ajeno_tampoco(self) -> None:
        repo = _Repo()
        repo.usados["LOG-01"] = str(uuid4())          # de OTRA búsqueda
        with pytest.raises(AppError) as e:
            actualizar(repo, _Audit(), V_DUEÑA, VacanteUpdate(codigo="log-01"))
        assert e.value.code == CODIGO_DUPLICADO

    def test_el_alta_normaliza_antes_de_guardar(self) -> None:
        repo = _Repo()
        vac = crear(repo, _Audit(), _create(" log 01 "), "u1")
        assert repo.guardados == ["LOG-01"] and vac.codigo == "LOG-01"


class TestLaCarreraLaResuelveLaBase:
    """🔴 LA MITAD QUE EL CHEQUEO PREVIO NO PUEDE CUBRIR.

    Entre el `SELECT` de `asegurar_unico` y el `INSERT` hay una ventana: otra sesión puede
    escribir el mismo código. Con una sola persona cargando búsquedas casi nunca se ve; con dos,
    aparece el día menos pensado. El doble la fuerza con `forzar_carrera`.
    """

    def test_el_choque_del_indice_sale_como_el_MISMO_409_y_no_como_un_500(self) -> None:
        repo = _Repo(forzar_carrera=True)
        with pytest.raises(AppError) as e:
            crear(repo, _Audit(), _create("ECO-2026"), "u1")
        assert e.value.code == CODIGO_DUPLICADO and e.value.status_code == 409
        assert "Analista contable" in e.value.message, (
            "en la carrera el mensaje tiene que nombrar igual a la dueña: se vuelve a consultar")

    def test_UN_FALLO_QUE_NO_ES_EL_INDICE_SE_RELANZA_TAL_CUAL(self) -> None:
        """El contraste que impide tragarse cualquier error de base detrás de "código duplicado":
        eso mandaría a Capital Humano a cambiar un código que estaba perfecto."""
        class _RepoRoto(_Repo):
            def save(self, data):
                raise RuntimeError("connection reset by peer")

        with pytest.raises(RuntimeError, match="connection reset"):
            crear(_RepoRoto(), _Audit(), _create("LOG-01"), "u1")


# ── 3. El espejo del front ────────────────────────────────────────────────────

class TestElFrontDiceLoMismo:
    """🔴 `frontend/components/features/vacantes/codigoVacante.ts` valida la MISMA forma para no
    hacer viajar un código mal escrito. Es un espejo manual, y este test es lo único que impide
    que se separe.

    El viaje va del BACKEND AL FRONT —un test de Python que abre un `.ts`— porque la autoridad es
    de este lado: el CHECK de la migración 122 es el que rechaza de verdad. Mismo criterio y
    misma dirección que `test_espejo_permisos.py`.

    ⚠️ Compara las TRES reglas, no el texto de los mensajes: los mensajes son de pantalla y no
    tienen por qué coincidir palabra por palabra con los del backend.
    """

    FRONT = (Path(__file__).resolve().parents[2] / "frontend" / "components" / "features"
             / "vacantes" / "codigoVacante.ts")

    def test_el_archivo_del_front_existe(self) -> None:
        """Guarda: si se renombró, todo lo de abajo pasaría por no encontrar nada que comparar."""
        assert self.FRONT.exists(), f"no está {self.FRONT}: ¿se renombró el espejo?"

    def test_los_limites_de_largo_coinciden(self) -> None:
        texto = self.FRONT.read_text(encoding="utf-8")
        assert f"CODIGO_MIN = {MIN_LARGO}" in texto
        assert f"CODIGO_MAX = {MAX_LARGO}" in texto

    def test_la_forma_coincide(self) -> None:
        """El regex del front, escrito tal cual el del backend. Si divergen, un código pasa de un
        lado y lo rechaza el otro — y el que decide es siempre el de acá."""
        texto = self.FRONT.read_text(encoding="utf-8")
        assert _FORMA.pattern in texto, f"el front no valida `{_FORMA.pattern}`"

    def test_la_regla_de_al_menos_una_letra_esta_en_los_dos(self) -> None:
        texto = self.FRONT.read_text(encoding="utf-8")
        assert "/[A-Z]/" in texto, "el front no exige al menos una letra: `2026` viajaría"


# ── 4. El evento de auditoría ─────────────────────────────────────────────────

def test_el_alta_deja_el_codigo_en_el_evento() -> None:
    """El código es lo que se pega en el aviso: si alguien pregunta después "¿con qué código
    salió publicada?", el log tiene que contestarlo."""
    audit = _Audit()
    crear(_Repo(), audit, _create("LOG-01"), "u1")
    assert audit.eventos[0]["datos_nuevos"]["codigo"] == "LOG-01"


def test_cambiar_el_codigo_queda_auditado_con_el_valor_VIEJO_y_el_nuevo() -> None:
    """🔴 Es el diff que contesta por qué un CV dejó de matchear: el aviso publicado lleva el
    código viejo. Sale gratis del diff genérico de `actualizar` (`tocados`), y por eso este test
    existe — para que un refactor que enumere campos no lo deje afuera en silencio."""
    audit = _Audit()
    actualizar(_Repo(), audit, V_DUEÑA, VacanteUpdate(codigo="LOG-01"))
    ev = audit.eventos[0]
    assert ev["datos_anteriores"]["codigo"] == "ECO-2026"
    assert ev["datos_nuevos"]["codigo"] == "LOG-01"
