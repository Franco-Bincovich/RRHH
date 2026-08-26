"""
El código de la vacante EN LA BASE: que viaje en el INSERT, que el índice único lo defienda, que
el lookup del matcher lo encuentre, y que llegue hasta el schema.

## 🔴 CAMBIÓ LA PREMISA EL 26/8/2026 — LO ESCRIBE CAPITAL HUMANO, YA NO LA SECUENCIA

Hasta la migración 122 el código lo ponía el DEFAULT de la base y este archivo probaba, entre
otras cosas, que la aplicación NO lo mandara. Ahora es un campo del formulario y esas dos
aserciones están DADAS VUELTA, no borradas: `test_el_alta_manda_el_codigo_que_eligio_la_persona`
y `test_se_puede_elegir_y_corregir_desde_afuera` ocupan el lugar de las que decían lo contrario.
Borrarlas habría dejado sin vigilancia justo el punto donde ahora entra el valor.

El DEFAULT y la secuencia SIGUEN EXISTIENDO como red (una fila que entre por afuera de la app
nace con código igual), y el fake los conserva: por eso el insert sin `codigo` todavía emite uno.

## 🔴 POR QUÉ EL FAKE DE SUPABASE MODELA LA SECUENCIA **Y** EL ÍNDICE ÚNICO

El índice es ahora LA garantía: con el código escrito a mano, dos altas simultáneas con el mismo
valor son una carrera real. Un fake que aceptara cualquier código haría **imposible desmentir la
guarda de unicidad** — el test pasaría con cualquier implementación, incluida una que confiara
sólo en el `SELECT` previo.

Por eso `_FakeSupabase` implementa las dos mitades de la base real:

  · un **contador** que solo avanza (`nextval`), que es lo que hace que dos altas seguidas no
    puedan compartir código; y
  · un **índice único sobre `upper(codigo)`** que **LEVANTA EXCEPCIÓN** si el payload trae un
    código ya usado.

La segunda es la que le da dientes al archivo: `test_un_codigo_repetido_lo_rechaza_la_base`
fuerza la colisión a propósito para probar que el fake SÍ puede fallar. Sin ese test, un fake
permisivo se vería idéntico a uno estricto.

## Lo que estos tests NO cubren, para no venderlos de más

No corren SQL: ni la 097 ni la 122 se ejecutan acá, así que el CHECK de formato de la base no se
prueba en este archivo (la forma la valida `services/_vacante_codigo.py`, y eso vive en
`test_vacante_codigo_unico.py`). Que el índice único sea atómico es una propiedad de Postgres, no
algo que un test de Python pueda verificar. Lo que sí se verifica es lo que depende de nosotros:
que el valor viaje, que nadie lo calcule leyendo un máximo, y que la migración declare el índice
GLOBAL y case-insensitive. Las dos clases `TestLaMigracion*` miran el SQL como texto, que es todo
lo que se puede mirar sin una base.
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

import inspect  # noqa: E402
import re  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import repositories._vacante_write_repo as write_mod  # noqa: E402
import repositories.vacante_repo as repo_mod  # noqa: E402
from repositories._vacante_row import _vrow  # noqa: E402
from schemas.vacante import VacanteCreate, VacanteResponse  # noqa: E402

_MIGRACIONES = Path(__file__).resolve().parent.parent / "migrations"
_MIGRACION = _MIGRACIONES / "097_vacantes_codigo.sql"
_MIGRACION_122 = _MIGRACIONES / "122_vacantes_codigo_manual.sql"
_MIGRACION_123 = _MIGRACIONES / "123_vacantes_codigo_texto_natural.sql"
EMPRESA, AREA = uuid4(), uuid4()


# ── el doble de Supabase: secuencia + índice único ────────────────────────────

class _CodigoDuplicado(Exception):
    """Lo que levanta el índice único de Postgres ante un `upper(codigo)` repetido."""


class _Q:
    def __init__(self, base: "_FakeSupabase") -> None:
        self._b, self._filtros, self._modo = base, [], None

    def select(self, *a, **k):
        return self

    def eq(self, campo, valor):
        self._filtros.append(("eq", campo, str(valor)))
        return self

    def ilike(self, campo, valor):
        self._filtros.append(("ilike", campo, str(valor)))
        return self

    def maybe_single(self):
        self._modo = "single"
        return self

    def insert(self, payload):
        self._b.insertados.append(dict(payload))
        fila = dict(payload)
        # El DEFAULT de la base: solo se aplica si la aplicación NO mandó código.
        if "codigo" not in fila or fila["codigo"] is None:
            self._b.seq += 1
            fila["codigo"] = f"VAC-{self._b.seq:04d}"
        clave = fila["codigo"].upper()
        if clave in self._b.usados:                       # ← el índice único, con dientes
            raise _CodigoDuplicado(f"duplicate key value violates unique constraint: {clave}")
        self._b.usados.add(clave)
        fila.setdefault("id", str(uuid4()))
        fila.setdefault("created_at", datetime.now(timezone.utc))
        self._b.filas.append(fila)
        self._modo = "insert"
        self._insertada = fila
        return self

    def execute(self):
        if self._modo == "insert":
            return type("R", (), {"data": [self._insertada]})()
        filas = self._b.filas
        for tipo, campo, valor in self._filtros:
            if tipo == "eq":
                filas = [f for f in filas if str(f.get(campo)) == valor]
            else:                                         # ilike sin comodines = igualdad ci
                filas = [f for f in filas if str(f.get(campo, "")).upper() == valor.upper()]
        return type("R", (), {"data": filas[0] if filas else None})()


class _FakeSupabase:
    def __init__(self) -> None:
        self.filas, self.insertados, self.usados, self.seq = [], [], set(), 0

    def table(self, _nombre):
        return _Q(self)


@pytest.fixture
def base(monkeypatch) -> _FakeSupabase:
    fake = _FakeSupabase()
    monkeypatch.setattr(repo_mod, "supabase_admin", fake)
    # El write path se mudó a su satélite al partir el repo (estaba en 100/100): sin este
    # segundo parche, `save`/`update` salen a la red de verdad y el test se cuelga.
    monkeypatch.setattr(write_mod, "supabase_admin", fake)
    return fake


def _crear(repo, codigo: str = "ECO-2026") -> VacanteResponse:
    return repo.save(VacanteCreate(empresa_id=EMPRESA, codigo=codigo, titulo="Analista",
                                   area_id=AREA, tipo_contrato="efectivo"))


# ── 1. La generación ──────────────────────────────────────────────────────────

class TestGeneracion:

    def test_el_alta_manda_el_codigo_que_eligio_la_persona(self, base) -> None:
        """🔴 DADO VUELTA EL 26/8/2026. Acá vivía `test_el_alta_no_manda_el_codigo_lo_pone_la_base`,
        que exigía lo contrario: que `codigo` NO estuviera en el payload, para que se aplicara el
        DEFAULT. Con la mig 122 el código lo escribe Capital Humano y tiene que viajar; el test
        se invierte en vez de borrarse, porque el punto que vigila es el mismo —de dónde sale el
        valor— y sin él nadie notaría que el campo dejó de llegar al INSERT.
        """
        vac = _crear(repo_mod.VacanteRepo(), "ECO-2026")
        assert base.insertados[0].get("codigo") == "ECO-2026", (
            "el INSERT no manda el código elegido: se aplicaría el DEFAULT y la búsqueda nacería "
            "con un VAC-000N que nadie pidió")
        assert vac.codigo == "ECO-2026"

    def test_el_DEFAULT_sigue_siendo_la_red_si_no_llega_ninguno(self, base) -> None:
        """La secuencia no se sacó (ver el encabezado de la 122): una fila que entre por afuera de
        la aplicación —un INSERT a mano, un import futuro— sigue naciendo con código en vez de
        fallar contra el NOT NULL. Es la mitad que el test invertido de arriba dejaría sin mirar.
        """
        base.table("vacantes").insert({"titulo": "X"}).execute()
        assert base.filas[-1]["codigo"] == "VAC-0001"

    def test_dos_altas_con_el_mismo_codigo_no_pueden_convivir(self, base) -> None:
        """El caso del enunciado, ahora que el valor lo elige una persona: la SEGUNDA no entra.

        ¿Qué tendría que ser distinto en el fake para que falle? Que no modelara el índice único
        sobre `upper(codigo)`: ahí las dos filas quedarían con el mismo código y el matcher se
        rompería para siempre — el único bug de este módulo que no se puede reparar después,
        porque el aviso ya salió publicado.
        """
        repo = repo_mod.VacanteRepo()
        _crear(repo, "ECO-2026")
        with pytest.raises(_CodigoDuplicado):
            _crear(repo, "eco-2026")     # distinta caja, el MISMO código

    def test_un_codigo_repetido_lo_rechaza_la_base(self, base) -> None:
        """🔴 EL TEST QUE LE DA DIENTES AL FAKE. Fuerza la colisión que los otros dan por
        imposible: si el doble no modelara el índice único, esto pasaría en silencio y todo el
        archivo estaría afirmando sobre un fake que no puede desmentir nada."""
        base.filas.append({"id": str(uuid4()), "codigo": "ECO-2026", "area_id": str(AREA)})
        base.usados.add("ECO-2026")
        with pytest.raises(_CodigoDuplicado):
            base.table("vacantes").insert({"codigo": "eco-2026", "titulo": "X"}).execute()

    def test_ningun_codigo_se_calcula_leyendo_el_maximo(self) -> None:
        """La carrera descartada, buscada en el código: nadie ordena por `codigo` para sumar uno.

        Es la forma que tendría el anti-patrón —`order("codigo", desc=True)` o un `max()` sobre
        la columna— y no existe en ningún repo ni service. Sin esta guarda, alguien podría
        agregarlo "para cerrar los huecos de la secuencia" y reintroducir la colisión."""
        sospechosos = []
        for carpeta in ("repositories", "services"):
            for py in (Path(__file__).resolve().parent.parent / carpeta).rglob("*.py"):
                texto = py.read_text(encoding="utf-8")
                if re.search(r"""(order\(\s*["']codigo|max\(\s*["']codigo)""", texto):
                    sospechosos.append(py.name)
        assert not sospechosos, f"calculan el código leyendo el máximo: {sospechosos}"


class TestLaMigracionNoTieneCarrera:
    """La 097 como texto: es lo único verificable sin una base."""

    def test_el_contador_es_una_secuencia_atomica(self) -> None:
        sql = _MIGRACION.read_text(encoding="utf-8")
        assert "CREATE SEQUENCE" in sql and "nextval('vacantes_codigo_seq')" in sql

    def test_el_unico_es_global_y_case_insensitive(self) -> None:
        """Global: sin `empresa_id` en el índice. Case-insensitive: sobre `upper(codigo)`.

        Las dos mitades importan. Por empresa, dos empresas emiten el mismo código y el matcher
        no puede desempatar. Sensible a mayúsculas, `VAC-0001` y `vac-0001` conviven y el lookup
        (que es `ilike`) encuentra DOS filas — un 500, no un 404."""
        sql = _MIGRACION.read_text(encoding="utf-8")
        indice = next(ln for ln in sql.splitlines() if "CREATE UNIQUE INDEX" in ln)
        assert "upper(codigo)" in indice
        assert "empresa_id" not in indice

    def test_la_columna_queda_not_null(self) -> None:
        sql = _MIGRACION.read_text(encoding="utf-8")
        assert "ALTER COLUMN codigo SET NOT NULL" in sql
        assert "UPDATE vacantes" in sql, "sin backfill, el SET NOT NULL falla si hay filas"

    def test_el_formato_admite_mas_de_cuatro_digitos(self) -> None:
        """`lpad` no trunca: la vacante 10.000 emite VAC-10000. Con `{4}` exacto el CHECK la
        rechazaría y el alta fallaría sin que nadie entienda por qué. ⚠️ Este CHECK ya no rige:
        lo reemplaza el de la 122. Se conserva porque la 097 sigue siendo la migración que hay que
        correr primero en un rebuild, y su texto tiene que seguir siendo coherente consigo mismo."""
        sql = _MIGRACION.read_text(encoding="utf-8")
        assert "[0-9]{4,}" in sql and "[0-9]{4}$" not in sql


class TestLaMigracion122:
    """La 122 como texto: qué ensancha y, sobre todo, qué NO toca."""

    def test_reemplaza_el_check_viejo_en_vez_de_agregarle_otro(self) -> None:
        """Dos CHECKs sobre la misma columna se cumplen por AND: dejar el de la 097 haría que
        `ECO-2026` siguiera siendo rechazado y la feature no funcionara, sin ningún error que
        apunte a la migración."""
        sql = _MIGRACION_122.read_text(encoding="utf-8")
        assert "DROP CONSTRAINT IF EXISTS vacantes_codigo_formato" in sql
        assert "ADD CONSTRAINT vacantes_codigo_formato" in sql

    def test_NO_toca_el_indice_unico(self) -> None:
        """🔴 La unicidad global es lo único que impide que dos búsquedas compartan código, y con
        el valor escrito a mano pasó a ser LA garantía. Un `DROP INDEX` acá sería el bug más caro
        del módulo."""
        sql = _MIGRACION_122.read_text(encoding="utf-8")
        assert "DROP INDEX" not in sql.upper()
        assert "vacantes_codigo_uq" in sql, "la migración ni siquiera menciona el índice que cuida"

    def test_NO_dropea_la_secuencia_ni_el_default(self) -> None:
        """Se conservan como red. Ver `test_el_DEFAULT_sigue_siendo_la_red_si_no_llega_ninguno`."""
        sql = _MIGRACION_122.read_text(encoding="utf-8").upper()
        assert "DROP SEQUENCE" not in sql and "DROP DEFAULT" not in sql

    def test_el_check_nuevo_exige_al_menos_una_letra(self) -> None:
        """Un código puramente numérico (`2026`) matchearía cualquier "2026" suelto en un asunto
        y mandaría el CV a esa búsqueda sin que nada falle. Es la misma clase de decisión que el
        mínimo de 4 dígitos que tenía la 097."""
        sql = _MIGRACION_122.read_text(encoding="utf-8")
        assert "codigo ~ '[A-Z]'" in sql

    def test_los_codigos_viejos_siguen_siendo_validos(self) -> None:
        """Las 5 vacantes de producción tienen `VAC-000N` y NO se renombran: el aviso ya está
        publicado con ese código. La migración no puede invalidarlas."""
        import re as _re
        assert _re.match(r"^[A-Z0-9]+(-[A-Z0-9]+)*$", "VAC-0001")
        assert 3 <= len("VAC-0001") <= 30 and _re.search(r"[A-Z]", "VAC-0001")


class TestLaMigracion123:
    """La 123 como texto: sube el techo de largo de 30 a 60, y no toca nada más.

    🔴 ES UNA MIGRACIÓN NUEVA Y NO UN RETOQUE DE LA 122 porque **la 122 YA CORRIÓ** — verificado
    contra el catálogo vivo el 26/8/2026: el CHECK en producción es el suyo. Una migración que ya
    corrió es historia y no se reescribe.
    """

    def test_sube_el_techo_a_60(self) -> None:
        """Con 30, "Analista de Sistemas Semi Senior" —el título de VAC-0002, una de las cinco
        vacantes reales— no se puede cargar por su nombre: canoniza a 32."""
        sql = _MIGRACION_123.read_text(encoding="utf-8")
        assert "BETWEEN 3 AND 60" in sql
        assert "AND 30" not in sql, "quedó el techo viejo"

    def test_reemplaza_el_check_en_vez_de_agregarle_otro(self) -> None:
        """Dos CHECKs sobre la misma columna se cumplen por AND: dejar el de la 122 haría que el
        techo efectivo siguiera siendo 30, sin ningún error que apunte a la migración."""
        sql = _MIGRACION_123.read_text(encoding="utf-8")
        assert "DROP CONSTRAINT IF EXISTS vacantes_codigo_formato" in sql
        assert "ADD CONSTRAINT vacantes_codigo_formato" in sql

    def test_NO_toca_el_indice_unico_ni_la_secuencia(self) -> None:
        sql = _MIGRACION_123.read_text(encoding="utf-8").upper()
        assert "DROP INDEX" not in sql and "DROP SEQUENCE" not in sql
        assert "VACANTES_CODIGO_UQ" in sql, "ni siquiera menciona el índice que cuida"

    def test_conserva_las_otras_dos_reglas_del_formato(self) -> None:
        """Ensancha el largo, no la forma: un código con acentos o de puros números sigue afuera."""
        sql = _MIGRACION_123.read_text(encoding="utf-8")
        assert "^[A-Z0-9]+(-[A-Z0-9]+)*$" in sql
        assert "codigo ~ '[A-Z]'" in sql

    def test_el_schema_declara_el_mismo_techo_que_la_migracion(self) -> None:
        """🔴 `db/schema.sql` es la fuente de RECONSTRUCCIÓN: si se queda en 30, el rebuild en RDS
        levanta una base que rechaza códigos que producción acepta. Es el tercer desfasaje de este
        archivo que el repo ya pagó."""
        schema = (Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text(encoding="utf-8")
        linea = next(ln for ln in schema.splitlines() if "vacantes_codigo_formato" in ln)
        assert "<= 60" in linea, f"schema.sql quedó con otro techo: {linea.strip()[:120]}"


# ── 2. El lookup del matcher ──────────────────────────────────────────────────

class TestLookupPorCodigo:

    @pytest.fixture
    def repo(self, base):
        r = repo_mod.VacanteRepo()
        _crear(r, "VAC-0001")
        return r

    @pytest.mark.parametrize("escrito", ["VAC-0001", "vac-0001", "Vac-0001", "vAc-0001"])
    def test_encuentra_sin_importar_las_mayusculas(self, repo, escrito) -> None:
        """El código llega del asunto de un mail que escribió un candidato.

        ¿Qué tendría que ser distinto en el fake para que falle? Que el `ilike` del fake
        comparara sin `.upper()`: ahí `vac-0001` no encontraría nada y el test rojearía — que es
        justo lo que pasaría en producción si el repo usara `eq`.
        """
        assert repo.find_by_codigo(escrito) is not None
        assert repo.find_by_codigo(escrito).codigo == "VAC-0001"

    def test_no_encuentra_un_codigo_inexistente(self, repo) -> None:
        assert repo.find_by_codigo("VAC-9999") is None

    def test_la_query_usa_ilike_y_no_eq(self, base) -> None:
        """🔴 Un escalón MÁS ABAJO: lo que tiene que viajar en la query se verifica capturando la
        query, no el resultado. Un fake "inteligente" que comparara sin distinguir mayúsculas
        dejaría pasar un `eq` real, y en Postgres `eq` SÍ distingue. Molde:
        `TestElOrdenLoPoneLaQuery` de test_historial_salarial."""
        capturado: list = []
        original = _Q.ilike

        def espia(self, campo, valor):
            capturado.append((campo, valor))
            return original(self, campo, valor)

        _Q.ilike = espia
        try:
            repo_mod.VacanteRepo().find_by_codigo("vac-0007")
        finally:
            _Q.ilike = original
        assert capturado == [("codigo", "vac-0007")], "el lookup no viaja como ilike sobre codigo"

    def test_el_lookup_no_filtra_por_empresa(self) -> None:
        """El código es único GLOBAL: filtrar por la empresa del header haría que un mail
        entrante resolviera o no según qué empresa estuviera mirando el usuario."""
        assert "empresa" not in inspect.signature(repo_mod.VacanteRepo.find_by_codigo).parameters


# ── 3. Que el código LLEGUE al front ──────────────────────────────────────────

class TestElCodigoLlegaAlSchema:
    """🔴 Contra el MAPPER REAL (`_vrow`), no contra un fake del service.

    Ya pasó TRES veces en este repo que el `select` traía la columna y el schema la descartaba en
    silencio (PresupuestoResponse, CandidatoResponse, `liderazgo`). Pydantic ignora los campos
    extra por defecto: si `VacanteResponse` no declarara `codigo`, el valor se perdería sin un
    solo error y la pantalla mostraría un hueco.
    """

    def _fila_cruda(self) -> dict:
        return {
            "id": str(uuid4()), "codigo": "VAC-0042", "titulo": "Analista",
            "area_id": str(AREA), "empresa_id": str(EMPRESA), "estado": "nueva",
            "created_at": datetime.now(timezone.utc),
            "areas": {"nombre": "Sistemas"}, "empresas": {"nombre": "Karstec"},
        }

    def test_el_mapper_real_lo_expone(self) -> None:
        """¿Qué tendría que ser distinto para que falle? Que se saque `codigo` del schema: el
        mapper seguiría corriendo sin error y el atributo desaparecería."""
        assert _vrow(self._fila_cruda()).codigo == "VAC-0042"

    def test_el_schema_lo_declara_y_es_obligatorio(self) -> None:
        """Declarado Y requerido. Con un `Optional[str] = None`, una fila sin código mapearía a
        `None` y el aviso saldría con un hueco en vez de fallar donde se puede ver."""
        campo = VacanteResponse.model_fields.get("codigo")
        assert campo is not None, "VacanteResponse no declara `codigo`: el mapper lo descartaría"
        assert campo.is_required(), "`codigo` con default: una vacante sin código pasaría muda"

    def test_una_fila_sin_codigo_no_mapea(self) -> None:
        """El contrapositivo del anterior: si la columna faltara, se rompe acá y no en la ficha."""
        fila = self._fila_cruda()
        del fila["codigo"]
        with pytest.raises(Exception):
            _vrow(fila)

    def test_se_puede_elegir_y_corregir_desde_afuera(self) -> None:
        """🔴 DADO VUELTA EL 26/8/2026. Acá vivía `test_no_se_puede_elegir_el_codigo_desde_afuera`,
        que exigía que ninguno de los dos schemas declarara `codigo`. Con la mig 122 lo escribe
        Capital Humano: es OBLIGATORIO al crear (una búsqueda sin código no puede recibir CVs) y
        OPCIONAL al editar (el caso típico es corregir un typo que ya se pegó en el aviso).
        """
        from schemas.vacante import VacanteUpdate
        assert VacanteCreate.model_fields["codigo"].is_required(), (
            "opcional al crear = una búsqueda puede nacer sin código y quedar muda")
        assert not VacanteUpdate.model_fields["codigo"].is_required(), (
            "obligatorio al editar = no se puede cambiar el título sin re-mandar el código")
