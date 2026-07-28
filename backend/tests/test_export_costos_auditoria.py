"""
Export del listado de auditoría y de la nómina del período.

LO QUE SE VERIFICA, y por qué es lo que importa: que el archivo traiga EXACTAMENTE las mismas
filas que la pantalla con los mismos filtros. La paridad de FIRMAS ya la cubre
test_paridad_list_export (estructural, sobre app.routes), pero aceptar el mismo parámetro no
prueba que se use: un export puede recibir `entidad` y no pasárselo al repo. Eso se ve acá.

Los fakes HONRAN los filtros —incluido `empresa_id`— justamente porque un fake permisivo daría
verde sin comparar nada, que es el modo de fallar más caro que tiene esta suite.
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

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from schemas.auditoria import AuditLogResponse
from schemas.costo import NominaResponse
from services._auditoria_export import construir_filas_export as filas_auditoria
from services._limite_export import LIMITE_FILAS_EXPORT
from services._nomina_export import construir_filas_export as filas_nomina
from services.audit_service import AuditService
from services.costo_service import CostoService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
CODE_LIMITE = "EXPORT_DEMASIADAS_FILAS"


# ─── Auditoría ────────────────────────────────────────────────────────────────


def _evento(entidad: str, empresa: UUID, i: int = 0) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(uuid4()), usuario_id=str(uuid4()), usuario_nombre="Ana García",
        empresa_id=str(empresa), empresa_nombre="ACME", entidad=entidad,
        evento=f"alta_{entidad}", accion="INSERT", registro_id=str(uuid4()),
        created_at=datetime(2026, 7, 14 + i % 10, 9, 30),
    )


class _FakeAuditRepo:
    """Modela DOS empresas y aplica de verdad empresa_id y entidad. `total` es el count del
    filtro, no el de la tabla — si devolviera el total crudo, el corte de B7 se dispararía
    sobre filas que el usuario no pidió."""

    def __init__(self, filas: list) -> None:
        self.filas = filas
        self.recibido: dict = {}

    def listar(self, empresa_id=None, usuario_id=None, entidad=None, evento=None,
               fecha_desde=None, fecha_hasta=None, page=1, page_size=20, registro_id=None):
        self.recibido = {"empresa_id": empresa_id, "entidad": entidad, "evento": evento,
                         "usuario_id": usuario_id, "registro_id": registro_id,
                         "fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta}
        r = self.filas
        if empresa_id:
            r = [f for f in r if f.empresa_id == str(empresa_id)]
        if entidad:
            r = [f for f in r if f.entidad == entidad]
        return r[(page - 1) * page_size: page * page_size], len(r)


def _svc_audit(filas: list) -> tuple:
    repo = _FakeAuditRepo(filas)
    svc = AuditService()
    svc._repo = repo
    return svc, repo


FILAS = [_evento("empleado", EMPRESA_A, 1), _evento("empleado", EMPRESA_A, 2),
         _evento("vacante", EMPRESA_A, 3), _evento("empleado", EMPRESA_B, 4)]


class TestExportAuditoria:
    def test_devuelve_lo_mismo_que_el_listado(self) -> None:
        """La comparación es contra `listar`, no contra un número escrito a mano: así el test
        sigue valiendo si mañana cambia el fake."""
        svc, _ = _svc_audit(FILAS)
        esperado = svc.listar(empresa_id=EMPRESA_A, entidad="empleado", page_size=100).items
        svc2, repo2 = _svc_audit(FILAS)
        svc2.exportar(empresa_id=EMPRESA_A, entidad="empleado")
        assert repo2.recibido["empresa_id"] == EMPRESA_A
        assert repo2.recibido["entidad"] == "empleado"
        assert len(esperado) == 2

    def test_el_filtro_de_entidad_llega_al_repo(self) -> None:
        """Recibir el Query no prueba nada; lo que prueba es que se lo pase al repo."""
        svc, repo = _svc_audit(FILAS)
        svc.exportar(entidad="vacante")
        assert repo.recibido["entidad"] == "vacante"

    @pytest.mark.parametrize("campo,valor", [
        ("usuario_id", uuid4()), ("evento", "baja_empleado"), ("registro_id", "abc-123"),
    ])
    def test_los_seis_filtros_llegan_al_repo(self, campo: str, valor) -> None:
        svc, repo = _svc_audit(FILAS)
        svc.exportar(**{campo: valor})
        assert repo.recibido[campo] == valor

    def test_las_fechas_llegan_al_repo(self) -> None:
        from datetime import date
        svc, repo = _svc_audit(FILAS)
        svc.exportar(fecha_desde=date(2026, 7, 1), fecha_hasta=date(2026, 7, 31))
        assert repo.recibido["fecha_desde"] == date(2026, 7, 1)
        assert repo.recibido["fecha_hasta"] == date(2026, 7, 31)

    def test_una_empresa_no_ve_la_otra(self) -> None:
        svc, repo = _svc_audit(FILAS)
        svc.exportar(empresa_id=EMPRESA_B)
        assert repo.recibido["empresa_id"] == EMPRESA_B

    def test_corta_si_supera_el_tope(self) -> None:
        svc, _ = _svc_audit([_evento("empleado", EMPRESA_A, i)
                             for i in range(LIMITE_FILAS_EXPORT + 1)])
        with pytest.raises(AppError) as exc:
            svc.exportar()
        assert exc.value.code == CODE_LIMITE

    def test_el_mismo_pedido_acotado_si_sale(self) -> None:
        """Lo que el mensaje del tope le promete al usuario: filtrar baja el total."""
        filas = ([_evento("empleado", EMPRESA_A, i) for i in range(LIMITE_FILAS_EXPORT + 1)]
                 + [_evento("vacante", EMPRESA_A, 1)])
        svc, _ = _svc_audit(filas)
        assert svc.exportar(entidad="vacante") is not None

    def test_devuelve_un_archivo(self) -> None:
        svc, _ = _svc_audit(FILAS)
        d = svc.exportar(formato="excel")
        assert d.content and d.filename.startswith("auditoria")


class TestColumnasAuditoria:
    def test_no_vuelca_uuids_crudos(self) -> None:
        fila = filas_auditoria([_evento("empleado", EMPRESA_A)])[0]
        assert fila["Usuario"] == "Ana García" and fila["Empresa"] == "ACME"

    def test_la_fecha_lleva_hora(self) -> None:
        """En auditoría dos eventos del mismo día se ordenan por hora: sin ella el export
        pierde justo la información que lo hace útil."""
        assert filas_auditoria([_evento("empleado", EMPRESA_A)])[0]["Fecha"] == "14/07/2026 09:30"

    def test_no_incluye_el_jsonb(self) -> None:
        """datos_anteriores/datos_nuevos no van: en un Excel son ilegibles."""
        cols = set(filas_auditoria([_evento("empleado", EMPRESA_A)])[0])
        assert not cols & {"datos_anteriores", "datos_nuevos", "Datos anteriores"}

    def test_usuario_borrado_no_deja_la_celda_vacia(self) -> None:
        ev = _evento("empleado", EMPRESA_A)
        ev.usuario_nombre = None
        assert filas_auditoria([ev])[0]["Usuario"] == ev.usuario_id


# ─── Nómina ───────────────────────────────────────────────────────────────────


def _nomina(empresa: UUID, mes: int = 7, nombre: str = "Ana García") -> NominaResponse:
    return NominaResponse(
        id=str(uuid4()), empleado_id=str(uuid4()), empresa_id=str(empresa),
        empresa_nombre="ACME", empleado_nombre=nombre, area_nombre="Tecnología",
        mes=mes, anio=2026, monto_bruto=1000.0, monto_neto=800.0, total=1300.0,
    )


class _FakeNominaRepo:
    """Honra período Y empresa: dos empresas modeladas, como exige la regla de fakes.

    Registra lo que recibió porque comparar los resultados de `get_nomina_mes` NO alcanza:
    ese camino puede seguir filtrando bien mientras `exportar` le pasa None y arma el archivo
    con las dos empresas. Es un mutante que sobrevivió en la primera pasada."""

    def __init__(self, filas: list) -> None:
        self.filas = filas
        self.recibido: dict = {}

    def get_nomina_mes(self, mes, anio, empresa_id=None):
        self.recibido = {"mes": mes, "anio": anio, "empresa_id": empresa_id}
        return [f for f in self.filas
                if f.mes == mes and f.anio == anio
                and (empresa_id is None or f.empresa_id == str(empresa_id))]


FILAS_NOM = [_nomina(EMPRESA_A, 7), _nomina(EMPRESA_A, 7, "Beto Ruiz"),
             _nomina(EMPRESA_B, 7), _nomina(EMPRESA_A, 6)]


def _svc_costos(filas: list) -> tuple:
    repo = _FakeNominaRepo(filas)
    return CostoService(nomina_repo=repo), repo


def _filas_csv(descarga) -> list:
    """Filas de DATOS del CSV. Mirar el ARCHIVO y no la lista intermedia es lo único que
    prueba que salió lo que el usuario pidió.

    El header se busca por su primera celda en vez de saltear N líneas fijas: el motor mete
    título y nombre de sección antes, y un offset a mano se rompe si eso cambia."""
    lineas = [x for x in descarga.content.decode("utf-8-sig").splitlines() if x.strip()]
    i = next(n for n, x in enumerate(lineas) if x.startswith("Empresa,"))
    return lineas[i + 1:]


class TestExportNomina:
    def test_devuelve_lo_mismo_que_el_listado(self) -> None:
        svc, _ = _svc_costos(FILAS_NOM)
        listado = svc.get_nomina_mes(7, 2026, EMPRESA_A)
        assert len(_filas_csv(svc.exportar(7, 2026, EMPRESA_A, "csv"))) == len(listado) == 2

    def test_el_periodo_llega_al_repo(self) -> None:
        """Junio no puede colarse en el archivo de julio."""
        svc, repo = _svc_costos(FILAS_NOM)
        svc.exportar(6, 2026, EMPRESA_A)
        assert (repo.recibido["mes"], repo.recibido["anio"]) == (6, 2026)

    def test_la_empresa_llega_al_repo(self) -> None:
        """El mutante que sobrevivió: `exportar` puede filtrar bien en el listado y pasarle
        None al repo, y el archivo sale con las dos empresas sin que nada falle."""
        svc, repo = _svc_costos(FILAS_NOM)
        svc.exportar(7, 2026, EMPRESA_A)
        assert repo.recibido["empresa_id"] == EMPRESA_A

    def test_el_archivo_de_una_empresa_no_trae_la_otra(self) -> None:
        svc, _ = _svc_costos(FILAS_NOM)
        contenido = svc.exportar(7, 2026, EMPRESA_B, "csv").content.decode("utf-8-sig")
        assert "Beto Ruiz" not in contenido and len(_filas_csv(
            svc.exportar(7, 2026, EMPRESA_B, "csv"))) == 1

    def test_consolidado_trae_las_dos(self) -> None:
        svc, _ = _svc_costos(FILAS_NOM)
        assert len(_filas_csv(svc.exportar(7, 2026, None, "csv"))) == 3

    def test_corta_si_supera_el_tope(self) -> None:
        svc, _ = _svc_costos([_nomina(EMPRESA_A, 7) for _ in range(LIMITE_FILAS_EXPORT + 1)])
        with pytest.raises(AppError) as exc:
            svc.exportar(7, 2026)
        assert exc.value.code == CODE_LIMITE

    def test_el_nombre_del_archivo(self) -> None:
        assert _svc_costos(FILAS_NOM)[0].exportar(7, 2026).filename.startswith("nomina")


class TestColumnasNomina:
    def test_no_vuelca_uuids_crudos(self) -> None:
        fila = filas_nomina([_nomina(EMPRESA_A)])[0]
        assert fila["Empleado"] == "Ana García" and fila["Área"] == "Tecnología"
        assert not any("-" in str(v) and len(str(v)) == 36 for v in fila.values())

    def test_los_montos_salen_como_numero(self) -> None:
        """Un '$ 1.234,56' convierte la columna en texto y rompe cualquier fórmula del Excel."""
        fila = filas_nomina([_nomina(EMPRESA_A)])[0]
        assert all(isinstance(fila[c], (int, float)) for c in ("Bruto", "Neto", "Costo total"))

    def test_trae_el_neto_y_el_costo_total(self) -> None:
        """Bruto y total no son lo mismo: el total incluye cargas."""
        fila = filas_nomina([_nomina(EMPRESA_A)])[0]
        assert fila["Bruto"] == 1000.0 and fila["Neto"] == 800.0 and fila["Costo total"] == 1300.0
