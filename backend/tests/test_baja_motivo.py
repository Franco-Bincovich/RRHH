"""
El motivo de la baja llega a `empleados.motivo_baja` por las DOS vías, sin pisarse entre sí.

## Qué cerró esto (20/8/2026)

`empleados.motivo_baja` existe desde la migración 064 como TEXTO LIBRE, para las bajas históricas
del CSV de nómina, y su único lector es `_reporte_movimientos` — el listado nominal del reporte de
**Altas y bajas**. Pero la efectivización del offboarding escribía `estado='baja'` y
`fecha_egreso` y **no tocaba esa columna**, teniendo el motivo guardado en
`offboarding_instancias.motivo_egreso`. Resultado: **toda baja hecha por offboarding salía como
"Sin especificar"** en el único reporte que pregunta por qué se fue la gente. El dato existía y no
llegaba. Hoy no se nota porque las dos tablas están en cero.

## 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR

  1. **Se faltea el CLIENTE de Supabase, no el repo.** `dar_de_baja` corre de verdad, con su
     `.update({...})` real y con la condicional del motivo adentro. Con un fake de repo, la
     condicional —que es TODO el punto del test (c)— no se ejecutaría nunca y los tres pasarían
     con ella borrada.

  2. **El motor APLICA los `.update()` sobre las filas**, no los registra: el test (b) lee con
     otra query lo que el (a) escribió. Un fake que solo capturara el patch no podría mostrar que
     el reporte cambia de "Sin especificar" al motivo real.

  3. **El texto libre del padrón y el motivo de la instancia son DISTINTOS entre sí**
     (`"Se fue a la competencia"` vs `"renuncia"`). Si fueran iguales, un `dar_de_baja` que
     pisara siempre la columna pasaría el test (c) igual que uno que no la toca.

  4. **El padrón tiene las DOS personas**: una que se va por offboarding y otra que ya venía con
     su texto libre del import. Con una sola, la mitad de la regla no se puede desmentir.
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

from datetime import date  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from typing import List, Optional  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402

from services._offboarding_efectivizar import efectivizar  # noqa: E402

EMPRESA = "11111111-1111-1111-1111-111111111111"
AREA = {"nombre": "Sistemas"}

HOY = date.today()
INGRESO = date(2020, 1, 15)
EGRESO = date(HOY.year, HOY.month, 1)

# 🔴 Distintos entre sí a propósito (punto 3 del encabezado).
MOTIVO_INSTANCIA = "renuncia"            # vocabulario cerrado de offboarding_instancias
TEXTO_LIBRE_NOMINA = "Se fue a la competencia"   # texto libre del CSV de nómina


def _fila(id_: str, apellido: str, estado: str = "activo", **extra) -> dict:
    fila = {
        "id": id_,
        "nombre": "Nom",
        "apellido": apellido,
        "area_id": "22222222-2222-2222-2222-222222222222",
        "empresa_id": EMPRESA,
        "roles": ["Analista"],
        "modalidad_trabajo": "presencial",
        "tipo_contrato": "permanente",
        "fecha_ingreso": str(INGRESO),
        "fecha_egreso": None,
        "motivo_baja": None,
        "estado": estado,
        "created_at": "2020-01-15T12:00:00+00:00",
        "areas": AREA,
    }
    fila.update(extra)
    return fila


class _Q:
    """Motor mínimo en memoria sobre una lista de dicts COMPARTIDA: filtra, lee y ESCRIBE."""

    def __init__(self, filas: List[dict]) -> None:
        self._todas = filas          # la lista viva: los updates se ven en las lecturas siguientes
        self._filtros: List = []
        self._patch: Optional[dict] = None
        self._single = False

    # ── lectura ──
    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filtros.append(lambda r, c=col, v=val: str(r.get(c)) == str(v))
        return self

    def neq(self, col, val):
        self._filtros.append(lambda r, c=col, v=val: str(r.get(c)) != str(v))
        return self

    def gte(self, col, val):
        self._filtros.append(lambda r, c=col, v=val: r.get(c) is not None and str(r[c]) >= str(v))
        return self

    def lte(self, col, val):
        self._filtros.append(lambda r, c=col, v=val: r.get(c) is not None and str(r[c]) <= str(v))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    # ── escritura ──
    def update(self, patch: dict):
        self._patch = patch
        return self

    def execute(self):
        filas = [r for r in self._todas if all(f(r) for f in self._filtros)]
        if self._patch is not None:
            for r in filas:
                r.update(self._patch)     # muta la fila viva
        if self._single:
            return SimpleNamespace(data=filas[0] if filas else None, count=len(filas))
        return SimpleNamespace(data=filas, count=len(filas))


class _DB:
    def __init__(self, filas: List[dict]) -> None:
        self.filas = filas

    def table(self, _nombre: str) -> _Q:
        return _Q(self.filas)


class _RepoOffboarding:
    """La instancia con su motivo. `find_instancia_min` devuelve lo que el SELECT real trae."""

    def __init__(self, empleado_id: str, motivo: Optional[str] = MOTIVO_INSTANCIA) -> None:
        self.completados: List[str] = []
        self._inst = {"id": "i1", "empleado_id": empleado_id, "estado": "iniciado",
                      "empresa_id": EMPRESA, "motivo_egreso": motivo}

    def find_instancia_min(self, instancia_id: str, empresa_id=None):
        return dict(self._inst)

    def marcar_completado(self, instancia_id: str, empresa_id=None) -> None:
        self.completados.append(instancia_id)


class _Audit:
    def registrar(self, **kw) -> None:
        pass


@pytest.fixture
def db(monkeypatch):
    """Padrón de dos personas + el cliente falseado en los módulos que lo consultan.

    `_empleado_baja_repo` es donde vive `dar_de_baja` desde el 20/8/2026: si faltara acá, el
    test no fallaría con un fake incompleto — saldría a la red con el cliente real.
    """
    import repositories._empleado_baja_repo as baja_mod
    import repositories._empleado_lookup_repo as lookup_mod
    import services.reportes._reporte_movimientos as mov_mod

    filas = [
        _fila("e-off", "Offboarding"),
        # Ya de baja por el import de nómina: fecha y texto libre puestos por esa vía.
        _fila("e-nom", "Nomina", estado="baja",
              fecha_egreso=str(EGRESO), motivo_baja=TEXTO_LIBRE_NOMINA),
    ]
    cliente = _DB(filas)
    for mod in (baja_mod, lookup_mod, mov_mod):
        monkeypatch.setattr(mod, "supabase_admin", cliente, raising=False)
    return cliente


def _empleado_repo():
    import repositories.empleado_repo as mod

    return mod.EmpleadoRepo()


def _por_id(db, id_: str) -> dict:
    return next(r for r in db.filas if r["id"] == id_)


class TestEfectivizarCopiaElMotivoDeLaInstancia:

    def test_deja_motivo_baja_con_el_valor_de_la_instancia(self, db) -> None:
        off = _RepoOffboarding("e-off")
        efectivizar(off, _empleado_repo(), _Audit(), uuid4(), EGRESO, UUID(EMPRESA), "u1")
        assert _por_id(db, "e-off")["motivo_baja"] == MOTIVO_INSTANCIA

    def test_y_sigue_escribiendo_estado_y_fecha_en_el_mismo_update(self, db) -> None:
        """El motivo se SUMA al UPDATE de siempre, no lo reemplaza. Una baja sin fecha se cae del
        headcount y del conteo de bajas de todos los meses a la vez."""
        off = _RepoOffboarding("e-off")
        efectivizar(off, _empleado_repo(), _Audit(), uuid4(), EGRESO, UUID(EMPRESA), "u1")
        fila = _por_id(db, "e-off")
        assert fila["estado"] == "baja" and fila["fecha_egreso"] == str(EGRESO)

    def test_una_instancia_SIN_motivo_no_inventa_ninguno(self, db) -> None:
        """🔴 No hay fallback ni default. Si la instancia no trae motivo, la columna queda como
        estaba: escribir `"otro"` sería afirmar algo que nadie dijo, y el reporte ya sabe decir
        "Sin especificar" ante el vacío."""
        off = _RepoOffboarding("e-off", motivo=None)
        efectivizar(off, _empleado_repo(), _Audit(), uuid4(), EGRESO, UUID(EMPRESA), "u1")
        fila = _por_id(db, "e-off")
        assert fila["motivo_baja"] is None
        assert fila["estado"] == "baja", "la baja se hace igual: el motivo no es una guarda"


class TestElReporteDeAltasYBajasLoMuestra:
    """La otra punta: que el dato llegue a la única pantalla que lo pregunta.

    Sin este test, el copiado podría estar bien y el reporte seguir diciendo "Sin especificar"
    por leer otra columna — que es exactamente el bug que este cambio cierra.
    """

    def _bajas(self) -> List[dict]:
        from services.reportes._reporte_movimientos import generate_altas_bajas

        return generate_altas_bajas(EGRESO.month, EGRESO.year, UUID(EMPRESA))["bajas"]

    def test_antes_de_efectivizar_esa_persona_no_es_una_baja(self, db) -> None:
        """Premisa verificada, no supuesta: si ya figurara como baja, el test de abajo no
        probaría que la efectivización la puso ahí."""
        assert [b["empleado"] for b in self._bajas()] == ["Nomina, Nom"]

    def test_despues_de_efectivizar_el_motivo_es_el_de_la_instancia(self, db) -> None:
        off = _RepoOffboarding("e-off")
        efectivizar(off, _empleado_repo(), _Audit(), uuid4(), EGRESO, UUID(EMPRESA), "u1")
        motivos = {b["empleado"]: b["motivo"] for b in self._bajas()}
        assert motivos["Offboarding, Nom"] == MOTIVO_INSTANCIA
        assert motivos["Offboarding, Nom"] != "Sin especificar", (
            "es literalmente el bug que este cambio cierra"
        )

    def test_sin_motivo_el_reporte_sigue_diciendo_sin_especificar(self, db) -> None:
        """El vacío se sigue tratando como antes. El reporte no cambió: cambió lo que le llega."""
        off = _RepoOffboarding("e-off", motivo=None)
        efectivizar(off, _empleado_repo(), _Audit(), uuid4(), EGRESO, UUID(EMPRESA), "u1")
        motivos = {b["empleado"]: b["motivo"] for b in self._bajas()}
        assert motivos["Offboarding, Nom"] == "Sin especificar"


class TestElMotivoViajaEnLaQueryDeLaInstancia:
    """🔴 ESTA CLASE EXISTE PORQUE UN MUTATION CHECK LA PIDIÓ, y vale escribir por qué.

    Todo lo de arriba le pasa a `efectivizar` un `_RepoOffboarding` que devuelve el motivo venga
    o no en el SELECT. Con eso, **sacarle `motivo_egreso` a la query real de
    `find_instancia_min` dejaba los diez tests en verde** mientras en producción el motivo nunca
    habría llegado: la fila real no lo traería y `instancia.get("motivo_egreso")` sería `None`.

    Es la regla del repo aplicada: **lo que tiene que viajar EN LA QUERY se verifica un escalón
    más abajo**, falseando el cliente de Supabase y capturando el `.select()`. Molde:
    `TestElOrdenLoPoneLaQuery` (`test_historial_salarial.py`).
    """

    def _spec(self, monkeypatch) -> str:
        import repositories.offboarding_repo as mod

        capturado: List[str] = []

        class _Espia:
            def select(self, spec, *a, **k):
                capturado.append(spec)
                return self

            def eq(self, *a, **k):
                return self

            def maybe_single(self):
                return self

            def execute(self):
                return SimpleNamespace(data=None)

        monkeypatch.setattr(mod, "supabase_admin",
                            type("C", (), {"table": lambda s, t: _Espia()})())
        mod.OffboardingRepo().find_instancia_min("i1", UUID(EMPRESA))
        return capturado[0]

    def test_el_select_pide_motivo_egreso(self, monkeypatch) -> None:
        assert "motivo_egreso" in self._spec(monkeypatch)

    def test_y_sigue_pidiendo_las_otras_cuatro(self, monkeypatch) -> None:
        """Contracara: agregar una columna no puede haber pisado las que ya viajaban. `estado` y
        `empleado_id` los usa la efectivización para sus guardas; `empresa_id`, la barrera."""
        spec = self._spec(monkeypatch)
        assert all(c in spec for c in ("id", "empresa_id", "estado", "empleado_id"))


class TestLaBajaPorNominaConservaSuTextoLibre:
    """🔴 EL TEST QUE PROTEGE LA CONDICIONAL, y el motivo por el que `motivo` es opcional.

    El import de nómina escribe el texto libre de la columna `Motivo Baja` del CSV en el
    `update_empleado` de la fila, y **recién después** llama a `dar_de_baja`
    (`_nomina_empleados_baja.aplicar_vinculos`). Si `dar_de_baja` metiera `motivo_baja: None` en
    el patch cuando no le pasan motivo, borraría ese texto en silencio y en cada corrida mensual.
    """

    def test_dar_de_baja_sin_motivo_no_toca_la_columna(self, db) -> None:
        repo = _empleado_repo()
        # El orden real del import: primero el texto libre (ya está en el padrón), después la baja.
        assert repo.dar_de_baja("e-nom", EGRESO, UUID(EMPRESA)) is True
        assert _por_id(db, "e-nom")["motivo_baja"] == TEXTO_LIBRE_NOMINA

    def test_y_el_reporte_sigue_mostrando_ese_texto(self, db) -> None:
        from services.reportes._reporte_movimientos import generate_altas_bajas

        _empleado_repo().dar_de_baja("e-nom", EGRESO, UUID(EMPRESA))
        bajas = generate_altas_bajas(EGRESO.month, EGRESO.year, UUID(EMPRESA))["bajas"]
        assert {b["empleado"]: b["motivo"] for b in bajas}["Nomina, Nom"] == TEXTO_LIBRE_NOMINA

    def test_CONTRACARA_con_motivo_si_lo_escribe(self, db) -> None:
        """Sin esto, un `dar_de_baja` que IGNORARA el motivo siempre pasaría el test de arriba.
        La condicional tiene que distinguir los dos casos, no rechazar los dos."""
        repo = _empleado_repo()
        repo.dar_de_baja("e-nom", EGRESO, UUID(EMPRESA), MOTIVO_INSTANCIA)
        assert _por_id(db, "e-nom")["motivo_baja"] == MOTIVO_INSTANCIA

    def test_la_cadena_completa_pasa_el_motivo(self, db) -> None:
        """`EmpleadoRepo.dar_de_baja` es un delegador: si se olvidara de reenviar el cuarto
        argumento, los tests de efectivizar rojearían pero nadie diría por qué. Esto lo aísla."""
        repo = _empleado_repo()
        repo.dar_de_baja("e-off", EGRESO, UUID(EMPRESA), "despido")
        assert _por_id(db, "e-off")["motivo_baja"] == "despido"
