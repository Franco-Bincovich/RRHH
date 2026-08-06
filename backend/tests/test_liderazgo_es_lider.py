"""
`liderazgo` (texto crudo del CSV) → `es_lider` (el booleano que lee todo el sistema).

La migración 064 creó `liderazgo` y declaró EN UN COMENTARIO que "el parser decide cómo poblar
`es_lider` a partir de él". El parser nunca se escribió, y hasta esta tanda **ningún test
afirmaba nada sobre `liderazgo`**: si el import hubiera dejado de escribirlo, la suite entera
seguía en verde. Eso es lo que se cierra acá.

Lo que se cubre, en cuatro planos:

  1. El PARSER — 'SI'→True, 'NO'→False, y cualquier otra cosa → None (no se afirma nada).
  2. El PAYLOAD que llega a la base, por los DOS caminos (alta y update), que tenían semánticas
     distintas para el mismo valor.
  3. El RESUMEN del import: un valor no reconocido se reporta, no se traga.
  4. El BACKFILL (migración 093) contra el parser, sobre un vocabulario compartido.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · Los casos de 'SI' y 'NO' están PARAMETRIZADOS JUNTOS. Con uno solo, un parser que devolviera
    siempre el mismo booleano —o siempre None— pasaría sin que nadie se entere.
  · `_RepoCaptura` NO guarda el modelo Pydantic: aplica el MISMO filtro que
    `_empleado_write_repo` (`is not None` en el alta, `exclude_none` en el update) y guarda el
    dict resultante. Es la única forma de ver la asimetría que se está arreglando: mirando el
    objeto de entrada, alta y update se ven idénticos y `es_lider` aparece en los dos.
  · El fake de empleados HONRA `empresa_id` (devuelve None si no coincide), como exige la regla
    del repo, y `save`/`update` construyen su respuesta A PARTIR de lo que reciben.
  · El plano 4 no falsea nada: LEE el .sql y lo compara con el parser real sobre la misma lista
    de entradas. Un fake no puede desmentir "estos dos criterios coinciden".
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

import re
from pathlib import Path
from uuid import uuid4

import pytest

from schemas.empleado import EmpleadoResponse
from schemas.importacion_nomina_empleados import build_create, build_update
from services import _nomina_empleados_transforms as tx
from services._nomina_parsers import parse_bool
from services.nomina_empleados_service import NominaEmpleadosImportService

EMPRESA_A = str(uuid4())
AREA_A = str(uuid4())

_COLUMNAS = [
    "Apellido", "Nombre", "DNI", "CUIT", "Sexo", "Edad", "Email", "Fecha Nacimiento",
    "Fecha Ingreso", "Fecha Ingreso Reconocida", "Organismo", "Gerencia", "Sector", "Equipo",
    "Rol", "Seniority", "Categoria", "Modalidad Contratacion", "Co-sourcing",
    "Apellido Superior", "Nombre Superior", "Liderazgo", "Ubicación Física", "Carga Horaria",
    "Product Owner", "Fecha Baja", "Motivo Baja",
]


def _fila_cruda(liderazgo: str) -> dict:
    """Una fila del CSV ya leída por csv.DictReader, con Liderazgo puesto."""
    base = {c: "" for c in _COLUMNAS}
    base.update({
        "Apellido": "Perez", "Nombre": "Ana", "DNI": "30111222", "Organismo": "ACME",
        "Sector": "SISTEMAS", "Rol": "Analista", "Fecha Ingreso": "1/3/2024",
        "Email": "ana@k.com", "Modalidad Contratacion": "RELACION DE DEPENDENCIA",
        "Liderazgo": liderazgo,
    })
    return base


def _csv(liderazgo: str) -> str:
    fila = _fila_cruda(liderazgo)
    return ";".join(_COLUMNAS) + "\r\n" + ";".join(fila[c] for c in _COLUMNAS) + "\r\n"


def _empleado(id_: str, dni: str, es_lider: bool = False) -> EmpleadoResponse:
    return EmpleadoResponse.model_validate({
        "id": id_, "nombre": "N", "apellido": "A", "email_corporativo": f"{dni}@k.com",
        "empresa_id": EMPRESA_A, "area_id": AREA_A, "roles": ["Analista"], "dni": dni,
        "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo", "es_lider": es_lider,
        "fecha_ingreso": "2024-01-01", "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    })


# ── 1. El parser ──────────────────────────────────────────────────────────────

class TestParsearFila:
    @pytest.mark.parametrize("texto,esperado", [("SI", True), ("NO", False)],
                             ids=["si", "no"])
    def test_si_y_no_dan_el_booleano(self, texto: str, esperado: bool) -> None:
        """🔴 LOS DOS EN EL MISMO PARAMETRIZE. Con uno solo, un parser que devolviera siempre
        True (o siempre None) pasaría — que es exactamente el estado anterior a este cambio,
        donde `es_lider` no se producía nunca."""
        assert tx.parsear_fila(_fila_cruda(texto))["es_lider"] is esperado

    @pytest.mark.parametrize("texto", ["si", "No", " SI ", "sI"],
                             ids=["minuscula", "capitalizado", "con-espacios", "mixto"])
    def test_el_caso_y_los_espacios_no_importan(self, texto: str) -> None:
        """El CSV real no es consistente en mayúsculas. Para que falle: que el parser compare
        el texto crudo sin `.strip().upper()`."""
        assert tx.parsear_fila(_fila_cruda(texto))["es_lider"] is not None

    @pytest.mark.parametrize("texto", ["GERENTE DE ÁREA", "S", "TRUE", "1", "OTRO"])
    def test_un_valor_no_reconocido_NO_es_false(self, texto: str) -> None:
        """🔴 EL CASO QUE JUSTIFICA TODO. Mapear "GERENTE DE ÁREA" a False afirmaría que esa
        persona NO es líder, que es lo que nadie dijo. Para que falle: un `bool(...)` o un
        `== 'SI'` en vez de `parse_bool`, que colapsarían todo lo no-'SI' en False."""
        f = tx.parsear_fila(_fila_cruda(texto))
        assert f["es_lider"] is None
        assert f["_liderazgo_no_reconocido"] is True

    def test_la_celda_vacia_no_se_reporta_como_problema(self) -> None:
        """El contrapeso del anterior: vacío también deja `es_lider` en None, pero NO es algo
        que corregir —nadie afirmó nada— y ensuciaría el resumen de cada import."""
        f = tx.parsear_fila(_fila_cruda(""))
        assert f["es_lider"] is None
        assert f["_liderazgo_no_reconocido"] is False

    @pytest.mark.parametrize("texto", ["SI", "NO", "GERENTE DE ÁREA"])
    def test_el_texto_crudo_se_sigue_guardando(self, texto: str) -> None:
        """`liderazgo` NO se reemplaza por el booleano: es el único lugar donde sobrevive el
        texto original. Este es el test que faltaba — hasta ahora, borrar esa línea del parser
        dejaba la suite entera en verde."""
        assert tx.parsear_fila(_fila_cruda(texto))["liderazgo"] == texto


# ── 2. Lo que llega a la base, por los dos caminos ────────────────────────────

class TestElPayloadQueSeEscribe:
    """Se replica el filtro REAL de `_empleado_write_repo`: el alta descarta los None, el update
    usa exclude_none. Mirar el modelo Pydantic no serviría: ahí `es_lider` está en los dos."""

    @staticmethod
    def _alta(texto: str) -> dict:
        f = tx.parsear_fila(_fila_cruda(texto))
        data = build_create(f, EMPRESA_A, AREA_A, "ana@k.com")
        return {k: v for k, v in data.model_dump().items() if v is not None}

    @staticmethod
    def _update(texto: str) -> dict:
        f = tx.parsear_fila(_fila_cruda(texto))
        return build_update(f, AREA_A, "ana@k.com").model_dump(exclude_none=True)

    @pytest.mark.parametrize("texto,esperado", [("SI", True), ("NO", False)], ids=["si", "no"])
    def test_el_alta_escribe_el_valor_derivado(self, texto: str, esperado: bool) -> None:
        assert self._alta(texto)["es_lider"] is esperado

    @pytest.mark.parametrize("texto,esperado", [("SI", True), ("NO", False)], ids=["si", "no"])
    def test_el_update_escribe_el_valor_derivado(self, texto: str, esperado: bool) -> None:
        """El import gana sobre la edición manual (mismo criterio que `manager_id`): un 'NO' del
        CSV pisa un True puesto a mano, y tiene que viajar en el patch para poder hacerlo."""
        assert self._update(texto)["es_lider"] is esperado

    def test_no_reconocido_NO_VIAJA_en_el_update(self) -> None:
        """🔴 LA GARANTÍA PEDIDA: un valor que no entendimos no puede pisar un `es_lider`
        cargado a mano. `exclude_none` lo saca del patch, así que el UPDATE ni menciona la
        columna. Para que falle: que el parser devolviera False en vez de None."""
        assert "es_lider" not in self._update("GERENTE DE ÁREA")

    def test_no_reconocido_tampoco_viaja_en_el_alta(self) -> None:
        """🔴 LA ASIMETRÍA QUE HABÍA. `EmpleadoBase.es_lider` es `bool = False` no-opcional, así
        que ANTES de redeclararlo Optional en `EmpleadoCreateNomina` el False entraba siempre en
        el INSERT: el import afirmaba "no es líder" en cada alta sin que el CSV lo dijera.
        Para que falle: sacar el `es_lider: Optional[bool] = None` de EmpleadoCreateNomina."""
        assert "es_lider" not in self._alta("GERENTE DE ÁREA")

    def test_la_celda_vacia_se_comporta_igual_en_los_dos(self) -> None:
        """Los dos caminos con la MISMA semántica: None = no escribir. Era el objetivo del
        cambio de schema, y sin este test la simetría podría romperse de un lado solo."""
        assert "es_lider" not in self._alta("") and "es_lider" not in self._update("")


# ── 3. El resumen del import lo reporta ───────────────────────────────────────

class _AreaRepo:
    def find_by_id(self, id, empresa_id=None):
        return {"id": str(id), "empresa_id": empresa_id}


class _Audit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


class _Catalogos:
    def empresa_id(self, nombre):
        return EMPRESA_A

    def area_id(self, empresa_id, nombre):
        return AREA_A

    def areas_validadas(self):
        return frozenset({AREA_A})


class _Noop:
    def resolver_y_asignar(self, *a, **k):
        pass

    def crear_si_falta(self, *a, **k):
        pass

    def registrar(self, *a, **k):
        pass

    def resolver(self, *a, **k):
        return 0, []


class _RepoCaptura:
    """HONRA empresa_id. Guarda el PAYLOAD que el repo real escribiría, no el modelo."""

    def __init__(self, existentes=None) -> None:
        self._por_dni = dict(existentes or {})
        self.altas: list = []
        self.updates: list = []

    def find_by_dni(self, dni, empresa_id=None):
        emp = self._por_dni.get(str(dni))
        if emp and empresa_id and emp.empresa_id != str(empresa_id):
            return None
        return emp

    def find_by_legajo(self, legajo, empresa_id=None):
        return None

    def find_by_id(self, id, empresa_id=None):
        return next((e for e in self._por_dni.values() if e.id == str(id)), None)

    def save(self, data, empresa_id):
        self.altas.append({k: v for k, v in data.model_dump().items() if v is not None})
        return _empleado(str(uuid4()), data.dni or "")

    def update(self, id, data, empresa_id=None):
        patch = data.model_dump(exclude_none=True)
        self.updates.append(patch)
        return _empleado(str(id), "30111222", es_lider=patch.get("es_lider", False))

    def dar_de_baja(self, *a, **k):
        return True


def _servicio(existentes=None):
    from services import empleado_service as es

    repo = _RepoCaptura(existentes)
    svc = NominaEmpleadosImportService.__new__(NominaEmpleadosImportService)
    svc._usuario_id = "u1"
    svc._catalogos = _Catalogos()
    svc._empleados = es.EmpleadoService(repo=repo, audit=_Audit(), area_repo=_AreaRepo())
    svc._emp_repo = repo
    svc._audit = _Audit()
    svc._seen_dni = set()
    svc._seen_legajo = set()
    svc._proyectos = _Noop()
    svc._cesiones = _Noop()
    svc._superiores = _Noop()
    return svc, repo


class TestElResumenDelImport:
    def test_un_valor_no_reconocido_se_reporta(self) -> None:
        """🔴 "No se escribe" no alcanza: si además no se dice, el operador cree que quedó
        cargado. La fila SE CARGA igual (no es un error bloqueante) pero sale de `cargados_ok`.
        Para que falle: no agregar "liderazgo" a `faltan` en `_procesar_fila`."""
        svc, _ = _servicio()
        r = svc.importar(_csv("GERENTE DE ÁREA"), "n.csv")
        assert (r.total, r.creados, r.cargados_ok) == (1, 1, 0)
        assert len(r.con_faltantes) == 1
        assert r.con_faltantes[0].faltan == ["liderazgo"]

    @pytest.mark.parametrize("texto", ["SI", "NO", ""], ids=["si", "no", "vacio"])
    def test_un_valor_reconocido_o_vacio_no_ensucia_el_resumen(self, texto: str) -> None:
        """El contrapeso: sin esto, reportar SIEMPRE pasaría el test de arriba y todo import
        quedaría marcado con faltantes."""
        svc, _ = _servicio()
        r = svc.importar(_csv(texto), "n.csv")
        assert (r.cargados_ok, r.con_faltantes) == (1, [])

    def test_end_to_end_el_alta_persiste_el_booleano(self) -> None:
        """El camino completo CSV→payload, para que no quede probado solo por partes."""
        svc, repo = _servicio()
        svc.importar(_csv("SI"), "n.csv")
        assert repo.altas[0]["es_lider"] is True
        assert repo.altas[0]["liderazgo"] == "SI"

    def test_end_to_end_un_no_reconocido_no_pisa_al_lider_existente(self) -> None:
        """🔴 EL ESCENARIO REAL COMPLETO: alguien tildó el checkbox a mano, y después llega un
        CSV con un liderazgo que no entendemos. El update NO tiene que mencionar la columna.
        Para que falle: cualquier cosa que convierta el None en False antes del patch."""
        svc, repo = _servicio({"30111222": _empleado(str(uuid4()), "30111222", es_lider=True)})
        r = svc.importar(_csv("GERENTE DE ÁREA"), "n.csv")
        assert r.actualizados == 1
        assert "es_lider" not in repo.updates[0]


# ── 4. El backfill y el parser coinciden ──────────────────────────────────────

_MIGRACION = Path(__file__).resolve().parent.parent / "migrations" / "093_backfill_es_lider.sql"

_PAR = re.compile(
    r"SET\s+es_lider\s*=\s*(TRUE|FALSE)\s+WHERE\s+upper\(btrim\(liderazgo\)\)\s*=\s*'([^']+)'",
    re.IGNORECASE)

# Vocabulario compartido: se pasa por los DOS criterios y se comparan los resultados. Incluye
# reconocidos, variantes de caso/espacios y señuelos que NINGUNO de los dos debe aceptar.
_VOCABULARIO = ["SI", "NO", "si", "no", " SI ", "Si", "nO",
                "SÍ", "GERENTE DE ÁREA", "S", "N", "TRUE", "1", "", "OTRA COSA"]


def _pares_del_backfill() -> list:
    """[(literal, valor booleano)] tal como los declara la migración."""
    texto = _MIGRACION.read_text(encoding="utf-8")
    return [(literal, valor.upper() == "TRUE") for valor, literal in _PAR.findall(texto)]


def _backfill_simulado(v: str, pares: list):
    """Aplica la regla del .sql: `upper(btrim(v))` contra los literales del WHERE."""
    clave = v.strip().upper()
    for literal, esperado in pares:
        if clave == literal.upper():
            return esperado
    return None   # el WHERE no matchea → la fila no se toca


class TestElBackfillYElParserCoinciden:
    def test_la_migracion_declara_los_dos_mapeos(self) -> None:
        """Guarda contra el falso verde: si la regex dejara de matchear (alguien reformatea el
        SQL), `_pares_del_backfill` daría [] y TODAS las comparaciones de abajo pasarían sin
        haber comparado nada."""
        pares = _pares_del_backfill()
        assert len(pares) >= 2, f"no se extrajo ningún mapeo de {_MIGRACION.name}"
        assert dict((lit.upper(), val) for lit, val in pares) == {"SI": True, "NO": False}

    @pytest.mark.parametrize("valor", _VOCABULARIO)
    def test_mismo_resultado_para_la_misma_entrada(self, valor: str) -> None:
        """🔴 LA INVARIANTE. Si divergen, el backfill deja las 31 filas de una forma y el próximo
        import las escribe de otra, sobre el mismo texto. Se comparan en las DOS direcciones a la
        vez: mismo valor y mismo None (= "no tocar" / "no escribir").
        Para que falle: cambiar el literal de un lado solo, o que la migración pase a escribir
        false por default en el resto."""
        assert _backfill_simulado(valor, _pares_del_backfill()) is parse_bool(valor)

    def test_la_migracion_no_toca_las_filas_sin_mapeo(self) -> None:
        """Que ningún UPDATE del archivo escriba sin comparar `liderazgo` — un
        `SET es_lider = FALSE` suelto convertiría los NULL en "no es líder"."""
        cuerpo = _MIGRACION.read_text(encoding="utf-8")
        sentencias = [s for s in cuerpo.split(";") if "UPDATE" in s and not s.lstrip().startswith("--")]
        assert len(sentencias) >= 2
        for s in sentencias:
            assert "upper(btrim(liderazgo))" in s, f"UPDATE sin filtro por liderazgo: {s[:80]}"
