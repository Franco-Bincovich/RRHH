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
    _FORMA, CODIGO_INVALIDO, MAX_LARGO, MIN_LARGO, canonico, normalizar,
)
from services._vacante_codigo_choque import CODIGO_DUPLICADO, asegurar_unico  # noqa: E402
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

class TestLaConversion:
    """🔴 CAPITAL HUMANO ESCRIBE TEXTO NATURAL. El sistema lo convierte, no lo rebota.

    Los casos NO son formas canónicas con variaciones: son títulos de puesto como los escribiría
    una persona. Ése es el punto de la feature — el CHECK anterior rechazaba «Lider de equipo», y
    un campo que rebota lo único que alguien va a escribir termina cargado como `L1`.
    """

    @pytest.mark.parametrize("escrito,esperado", [
        ("Lider de equipo", "LIDER-DE-EQUIPO"),
        ("Analista Sr.", "ANALISTA-SR"),
        ("Ecónomo 2026", "ECONOMO-2026"),                    # acento
        ("Diseño UX/UI", "DISENO-UX-UI"),                    # ñ y barra
        ("  Jefe   de   Logística  ", "JEFE-DE-LOGISTICA"),  # espacios de más → UN guion
        ("Analista (Turno noche)", "ANALISTA-TURNO-NOCHE"),  # paréntesis
        ("Ventas, Interior", "VENTAS-INTERIOR"),             # coma
        ("--eco-2026--", "ECO-2026"),                        # bordes
        ("ECO-2026", "ECO-2026"),                            # ya canónico: no lo toca
    ], ids=lambda v: repr(v))
    def test_convierte_lo_que_escribe_una_persona(self, escrito, esperado) -> None:
        assert normalizar(escrito) == esperado

    @pytest.mark.parametrize("uno,otro", [
        ("Lider de equipo", "LIDER DE EQUIPO"),
        ("Lider de equipo", "lider.de.equipo"),
        ("Ecónomo 2026", "Economo 2026"),
    ], ids=lambda v: repr(v))
    def test_dos_textos_que_dan_EL_MISMO_codigo(self, uno, otro) -> None:
        """🔴 Es la mitad de la unicidad: si estos dos no colapsaran al mismo canónico, el
        segundo se guardaría como una búsqueda distinta y el matcher tendría dos candidatas para
        el mismo asunto. Ver `test_la_unicidad_se_mide_sobre_el_CANONICO`."""
        assert normalizar(uno) == normalizar(otro)

    @pytest.mark.parametrize("malo", [
        "", "   ", None, "-", "...", "AB", "Ñú", "2026", "123 / 456", "( )",
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
        assert normalizar("Eco 2026") == "ECO-2026", "con una letra alcanza"

    def test_el_mensaje_habla_del_CODIGO_RESULTANTE_no_del_texto_tipeado(self) -> None:
        """La pantalla muestra la conversión debajo del campo, así que nombrar el resultado es lo
        que conecta lo que escribió con lo que el sistema entendió. "«ÑÚ» es muy corto" sería
        incomprensible; "«NU» es muy corto" se entiende de inmediato."""
        with pytest.raises(AppError) as e:
            normalizar("Ñú")
        assert "«NU»" in e.value.message
        assert str(MIN_LARGO) in e.value.message

    def test_canonico_NO_valida_porque_la_pantalla_convierte_mientras_se_escribe(self) -> None:
        """`canonico` existe separada de `normalizar` para la vista previa en vivo: un texto a
        medio tipear todavía no es un error. Si la pantalla usara `normalizar`, cada tecla
        levantaría una excepción hasta llegar al tercer carácter."""
        assert canonico("Li") == "LI"
        assert canonico("") == ""
        assert canonico("...") == ""


class TestElLargoRechazaNoRecorta:
    """🔴 LA DECISIÓN MÁS CARA DEL MÓDULO, y por eso tiene su propia clase.

    Recortar en silencio produce **dos códigos iguales a partir de textos distintos**, y ahí la
    segunda búsqueda se rechaza como duplicada de una que su autor nunca escribió — o el aviso
    sale publicado con un código que esa persona no vio nunca.
    """

    LARGO = "Responsable de Administracion y Finanzas del Grupo para la Region Centro"

    def test_pasarse_del_maximo_es_un_rechazo(self) -> None:
        with pytest.raises(AppError) as e:
            normalizar(self.LARGO)
        assert e.value.code == CODIGO_INVALIDO
        assert str(MAX_LARGO) in e.value.message, "no dice cuál es el máximo"
        assert "acortá" in e.value.message.lower(), "no dice qué hacer"

    def test_EL_CONTRASTE_no_devuelve_un_codigo_recortado(self) -> None:
        """Sin esto, un `normalizar` que devolviera `codigo[:MAX_LARGO]` pasaría el test de arriba
        si además levantara... y no lo haría. Se afirma que NO existe ningún retorno."""
        with pytest.raises(AppError):
            normalizar(self.LARGO)
        assert len(canonico(self.LARGO)) > MAX_LARGO, "el caso de prueba dejó de ser largo"

    def test_dos_titulos_distintos_que_un_recorte_habria_colapsado(self) -> None:
        """El caso concreto que justifica el rechazo: los dos empiezan igual y sólo se separan
        después del carácter 40. Recortados a 30 serían el MISMO código."""
        a = "Analista de Sistemas Senior con especializacion en datos"
        b = "Analista de Sistemas Senior con especializacion en redes"
        assert canonico(a)[:30] == canonico(b)[:30], "el caso de prueba ya no colapsa"
        assert canonico(a) != canonico(b), "enteros son distintos, que es lo que se preserva"

    def test_el_maximo_es_60_porque_con_30_rebotaba_una_vacante_REAL(self) -> None:
        """🔴 "Analista de Sistemas Semi Senior" es el título de VAC-0002, una de las cinco
        búsquedas cargadas en producción. Canoniza a 32 caracteres: con el techo de 30 que puso la
        122, esa búsqueda no se podría dar de alta con su propio nombre."""
        assert MAX_LARGO == 60
        codigo = normalizar("Analista de Sistemas Semi Senior")
        assert codigo == "ANALISTA-DE-SISTEMAS-SEMI-SENIOR"
        assert len(codigo) == 32 > 30


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

    def test_la_unicidad_se_mide_sobre_el_CANONICO(self) -> None:
        """🔴 EL REQUISITO. El doble tiene `ECO-2026` tomado; se da de alta «Ecónomo 2026», que es
        texto distinto y el MISMO código. Tiene que rechazarse nombrando a la dueña.

        ¿Qué tendría que ser distinto para que falle? Que `crear` consultara con el texto crudo:
        `find_by_codigo("Ecónomo 2026")` no encontraría nada, el alta pasaría el chequeo previo, y
        el choque lo cazaría recién el índice — sin poder nombrar a la dueña."""
        repo = _Repo()
        repo.usados["LIDER-DE-EQUIPO"] = V_DUEÑA          # ya existe, cargada así
        with pytest.raises(AppError) as e:
            crear(repo, _Audit(), _create("Lider de equipo"), "u1")   # texto distinto, mismo código
        assert e.value.code == CODIGO_DUPLICADO
        assert "«LIDER-DE-EQUIPO»" in e.value.message, "el mensaje no habla del canónico"
        assert "Analista contable" in e.value.message
        assert repo.guardados == []


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

    def test_el_front_tambien_saca_los_acentos(self) -> None:
        """🔴 La regla que MÁS caro sale si se separa: el front mostraría "Se va a usar:
        ECÓNOMO-2026" y el backend guardaría `ECONOMO-2026`. La vista previa —que existe
        justamente para que nadie se sorprenda con lo que se guardó— estaría mintiendo."""
        texto = self.FRONT.read_text(encoding="utf-8")
        assert 'normalize("NFD")' in texto, "el front no descompone: la ñ y las tildes sobrevivirían"
        assert "\\p{Mn}" in texto, "el front no tira las marcas diacríticas"

    def test_el_front_trata_TODO_lo_no_alfanumerico_como_separador(self) -> None:
        """Si el front colapsara sólo espacios y el backend todo, «Analista Sr.» daría
        `ANALISTA-SR.` en la vista previa y `ANALISTA-SR` en la base."""
        texto = self.FRONT.read_text(encoding="utf-8")
        assert "[^A-Z0-9]+" in texto, "el front usa otro conjunto de separadores"

    def test_las_dos_puntas_convierten_IGUAL_los_casos_del_enunciado(self) -> None:
        """La contracara de los tres tests de arriba, que miran el TEXTO del archivo: éste
        verifica el RESULTADO sobre los casos que Capital Humano va a escribir. Sin él, un espejo
        que tuviera los mismos literales pero en otro orden pasaría igual."""
        assert canonico("Lider de equipo") == "LIDER-DE-EQUIPO"
        assert canonico("Analista Sr.") == "ANALISTA-SR"
        assert canonico("Ecónomo 2026") == "ECONOMO-2026"


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
