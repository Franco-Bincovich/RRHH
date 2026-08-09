"""
El código de la vacante (`VAC-0001`, migración 097): generación sin colisión, lookup del matcher,
y que el valor llegue de verdad hasta el schema.

## 🔴 POR QUÉ EL FAKE DE SUPABASE MODELA LA SECUENCIA **Y** EL ÍNDICE ÚNICO

El código NO lo calcula Python: lo pone el DEFAULT de la base (`nextval`). Un fake que devolviera
siempre un código libre haría **imposible desmentir la guarda de unicidad** — el test pasaría con
cualquier implementación, incluida la que este diseño existe para evitar ("leer el máximo y sumar
uno", que colisiona con dos altas simultáneas).

Por eso `_FakeSupabase` implementa las dos mitades de la base real:

  · un **contador** que solo avanza (`nextval`), que es lo que hace que dos altas seguidas no
    puedan compartir código; y
  · un **índice único sobre `upper(codigo)`** que **LEVANTA EXCEPCIÓN** si el payload trae un
    código ya usado.

La segunda es la que le da dientes al archivo: `test_un_codigo_repetido_lo_rechaza_la_base`
fuerza la colisión a propósito para probar que el fake SÍ puede fallar. Sin ese test, un fake
permisivo se vería idéntico a uno estricto.

## Lo que estos tests NO cubren, para no venderlos de más

No corren SQL: la migración 097 no se ejecuta acá. Que `nextval` sea atómico es una propiedad de
Postgres, no algo que un test de Python pueda verificar. Lo que sí se verifica es lo único que
depende de nosotros: **que la aplicación no le dispute el código a la base** —no lo manda en el
INSERT y no lo calcula leyendo un máximo—, que es exactamente donde se metería la carrera.
`TestLaMigracionNoTieneCarrera` mira el SQL como texto, que es todo lo que se puede mirar sin
una base.
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

import repositories.vacante_repo as repo_mod  # noqa: E402
from repositories._vacante_row import _vrow  # noqa: E402
from schemas.vacante import VacanteCreate, VacanteResponse  # noqa: E402

_MIGRACION = Path(__file__).resolve().parent.parent / "migrations" / "097_vacantes_codigo.sql"
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
    return fake


def _crear(repo) -> VacanteResponse:
    return repo.save(VacanteCreate(empresa_id=EMPRESA, titulo="Analista", area_id=AREA,
                                   tipo_contrato="efectivo"))


# ── 1. La generación ──────────────────────────────────────────────────────────

class TestGeneracion:

    def test_dos_altas_seguidas_no_comparten_codigo(self, base) -> None:
        """El caso del enunciado. Con la secuencia, dos altas consecutivas no pueden coincidir.

        ¿Qué tendría que ser distinto en el fake para que falle? Que el contador no avanzara —o
        que la aplicación mandara el código en el payload—: ahí las dos altas traerían el mismo
        valor y, además, la segunda chocaría con el índice único del propio fake.
        """
        repo = repo_mod.VacanteRepo()
        a, b = _crear(repo), _crear(repo)
        assert a.codigo != b.codigo
        assert (a.codigo, b.codigo) == ("VAC-0001", "VAC-0002")

    def test_el_alta_no_manda_el_codigo_lo_pone_la_base(self, base) -> None:
        """🔴 La invariante que evita la carrera: la app NO le disputa el código a la base.

        Si el payload trajera `codigo`, el DEFAULT no se aplicaría y el valor saldría de donde
        sea que la app lo calculó — que es exactamente donde dos altas simultáneas colisionan.
        """
        _crear(repo_mod.VacanteRepo())
        assert "codigo" not in base.insertados[0], (
            f"el INSERT manda el código: {base.insertados[0].get('codigo')!r}. Lo pone el DEFAULT")

    def test_un_codigo_repetido_lo_rechaza_la_base(self, base) -> None:
        """🔴 EL TEST QUE LE DA DIENTES AL FAKE. Fuerza la colisión que los otros dan por
        imposible: si el doble no modelara el índice único, esto pasaría en silencio y todo el
        archivo estaría afirmando sobre un fake que no puede desmentir nada."""
        base.filas.append({"id": str(uuid4()), "codigo": "VAC-0001", "area_id": str(AREA)})
        base.usados.add("VAC-0001")
        with pytest.raises(_CodigoDuplicado):
            base.table("vacantes").insert({"codigo": "vac-0001", "titulo": "X"}).execute()

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
        rechazaría y el alta fallaría sin que nadie entienda por qué."""
        sql = _MIGRACION.read_text(encoding="utf-8")
        assert "[0-9]{4,}" in sql and "[0-9]{4}$" not in sql


# ── 2. El lookup del matcher ──────────────────────────────────────────────────

class TestLookupPorCodigo:

    @pytest.fixture
    def repo(self, base):
        r = repo_mod.VacanteRepo()
        _crear(r)                                          # queda como VAC-0001
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

    def test_no_se_puede_elegir_el_codigo_desde_afuera(self) -> None:
        """Ni al crear ni al editar: lo pone la base. Si `VacanteCreate` lo aceptara, viajaría en
        el payload del insert y le ganaría al DEFAULT."""
        from schemas.vacante import VacanteUpdate
        assert "codigo" not in VacanteCreate.model_fields
        assert "codigo" not in VacanteUpdate.model_fields
