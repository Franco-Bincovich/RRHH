"""
Tope de filas de los exports: avisar en vez de entregar un archivo cortado.

🔴 EL TEST QUE MÁS IMPORTA ES TestTodosLosExportsChequean. Es el equivalente del test
estructural de paridad de B2: barre TODOS los services con export y verifica que cada uno
invoque el chequeo. Sin él, el próximo export que se agregue nace sin control y nadie se
entera hasta que un usuario recibe un archivo incompleto — que es exactamente el bug que esta
tanda vino a cerrar, y es invisible por definición.

El resto fija el contrato del helper: el borde exacto, que el mensaje sea accionable y traiga
los números reales, y que el conteo respete los filtros (porque "usá los filtros para acotar"
es la salida que le ofrecemos al usuario: si acotar no bajara el total, el consejo sería
mentira).
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

import importlib
from types import SimpleNamespace

from schemas.inventario import ItemResponse

import pytest

from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from utils.errors import AppError

CODE = "EXPORT_DEMASIADAS_FILAS"


def _error(total: int) -> AppError:
    with pytest.raises(AppError) as exc:
        verificar_limite_export(total)
    return exc.value


# ─── El contrato del helper ───────────────────────────────────────────────────


class TestLimite:
    @pytest.mark.parametrize("total", [0, 1, 500, LIMITE_FILAS_EXPORT - 1])
    def test_por_debajo_no_corta(self, total: int) -> None:
        assert verificar_limite_export(total) is None

    def test_exactamente_en_el_limite_no_corta(self) -> None:
        """El borde va explícito: el tope es el MÁXIMO ACEPTADO, no el primer rechazado."""
        assert verificar_limite_export(LIMITE_FILAS_EXPORT) is None

    def test_uno_por_encima_corta(self) -> None:
        assert _error(LIMITE_FILAS_EXPORT + 1).code == CODE

    def test_el_status_es_422(self) -> None:
        assert _error(LIMITE_FILAS_EXPORT + 1).status_code == 422


class TestMensaje:
    def test_incluye_el_total_real(self) -> None:
        assert "123.456" in _error(123456).message

    def test_incluye_el_maximo(self) -> None:
        """El literal va A PROPÓSITO en vez de derivarse de la constante: derivarlo haría que
        el test espeje la implementación y deje de poder ver un cambio de formato (el separador
        de miles con punto). El assert de arriba ata el literal al tope, así que si el tope se
        mueve el test falla pidiendo que se actualice, en vez de quedar viejo en silencio."""
        assert LIMITE_FILAS_EXPORT == 20000, "cambió el tope: actualizá el literal de abajo"
        assert "20.000" in _error(123456).message

    def test_dice_que_hacer(self) -> None:
        """Accionable, no solo descriptivo."""
        assert "filtros" in _error(123456).message.lower()

    def test_sin_jerga_tecnica(self) -> None:
        """El usuario es de RRHH: no puede leer nombres de params ni de tablas."""
        msg = _error(123456).message.lower()
        assert not any(t in msg for t in ("page_size", "query", "timeout", "postgrest", "null"))

    def test_no_nombra_un_filtro_que_puede_no_existir(self) -> None:
        """"Acotá por fechas" sería imposible de seguir en empleados, que no filtra por fecha."""
        assert "fecha" not in _error(123456).message.lower()


# ─── El barrido: TODOS los services con export chequean ───────────────────────

# (módulo, clase, método). El barrido es explícito y no por introspección de disco porque
# cada export tiene su propia firma; lo que se verifica es que NINGUNO quede sin chequeo.
#
# 🔴 LA CLASE PUEDE SER `None`: EL EXPORT NO SIEMPRE ES UN MÉTODO. El 24/8/2026
# `ObjetivoService.exportar` se mudó a `services/_objetivos_export.py` como FUNCIÓN LIBRE —el
# service estaba en 142/150 y había que hacerle lugar a la auditoría del módulo— y este barrido
# lo cazó en el acto, que es exactamente para lo que está. La salida NO era sacar objetivos de la
# lista: era enseñarle al barrido la forma que el repo ya usa en los write paths extraídos por
# límite de líneas (`_vacaciones_write`, `_costos_write`, `_objetivos_write`), donde la lógica
# vive en funciones que reciben el repo. Con `None`, la entrada apunta al módulo y a la función.
EXPORTS = [
    ("services.empleado_service", "EmpleadoService", "exportar"),
    ("services.vacaciones_service", "VacacionesService", "exportar"),
    ("services.ausencias_service", "AusenciasService", "exportar"),
    ("services.asignacion_service", "AsignacionService", "exportar"),
    ("services.inventario_items_service", "InventarioItemsService", "exportar"),
    ("services.inventario_asignaciones_service", "InventarioAsignacionesService", "exportar"),
    # Función libre: el export de objetivos vive en el satélite, no en el service. Ver arriba.
    ("services._objetivos_export", None, "exportar"),
    ("services.evaluacion_reportes_service", "EvaluacionReportesService", "exportar"),
    ("services.costo_service", "CostoService", "exportar"),
    ("services.audit_service", "AuditService", "exportar"),
    ("services.usuario_service", "UsuarioService", "exportar"),
    ("services.empresa_service", "EmpresaService", "exportar"),
    ("services.onboarding_templates_service", "OnboardingTemplatesService", "exportar"),
    ("services.vacaciones_pendientes_service", "VacacionesPendientesService", "exportar"),
    ("services.vacante_service", "VacanteService", "exportar"),
    ("services.offboarding_service", "OffboardingService", "exportar"),
    ("services.cliente_service", "ClienteService", "exportar"),
    ("services.horas_cliente_service", "HorasClienteService", "exportar"),
    ("services.perfil_puesto_service", "PerfilPuestoService", "exportar"),
    ("services.recategorizacion_service", "RecategorizacionService", "exportar"),
]

# Exports que legítimamente NO chequean, con su razón. Si alguno se agrega acá sin
# justificarlo, se ve en el diff.
_SIN_CHEQUEO: dict[str, str] = {
    # Exporta UN reporte ya generado y guardado, por id. No es el export de un listado: no hay
    # filtros que acotar ni un total que pueda crecer.
    "services.reporte_export_service": "exporta un reporte puntual por id, no un listado",
    # Reporte de auditoría: ya está acotado a un mes por construcción y la pantalla no ofrece
    # otro filtro con el que angostarlo. Conserva su truncado DECLARADO (una nota en el propio
    # archivo que dice cuántas filas quedaron afuera). Ver el comentario en el módulo.
    "services.reportes._reporte_auditoria": "acotado a un mes; trunca con nota declarada",
}


class TestTodosLosExportsChequean:
    """Que exista el helper no sirve de nada si un service no lo llama."""

    def test_el_barrido_no_esta_vacio(self) -> None:
        """Guarda contra el falso verde: si la lista quedara vacía, todo lo de abajo pasaría
        sin haber mirado nada."""
        assert len(EXPORTS) >= 20

    @pytest.mark.parametrize("modulo,clase,metodo", EXPORTS, ids=lambda v: (v or "<módulo>").split(".")[-1])
    def test_importa_el_chequeo(self, modulo: str, clase: str, metodo: str) -> None:
        mod = importlib.import_module(modulo)
        assert hasattr(mod, "verificar_limite_export"), (
            f"{modulo} no importa verificar_limite_export. Si es legítimo, declaralo en "
            "_SIN_CHEQUEO CON su razón — no lo saques del barrido."
        )

    @pytest.mark.parametrize("modulo,clase,metodo", EXPORTS, ids=lambda v: (v or "<módulo>").split(".")[-1])
    def test_lo_invoca_en_el_export(self, modulo: str, clase: str, metodo: str) -> None:
        """Importarlo no alcanza: tiene que estar en el cuerpo de `exportar`."""
        import inspect
        mod = importlib.import_module(modulo)
        destino = getattr(mod, clase) if clase else mod
        fuente = inspect.getsource(getattr(destino, metodo))
        assert "verificar_limite_export(" in fuente, (
            f"{modulo}.{clase or '<módulo>'}.{metodo} importa el chequeo pero no lo llama."
        )

    def test_las_excepciones_declaradas_siguen_existiendo(self) -> None:
        """Una excepción que apunta a un módulo borrado es ruido que tapa el próximo caso."""
        for modulo in _SIN_CHEQUEO:
            importlib.import_module(modulo)

    def test_las_excepciones_tienen_razon(self) -> None:
        assert all(razon.strip() for razon in _SIN_CHEQUEO.values())


# ─── El conteo respeta los filtros ────────────────────────────────────────────


class _RepoPorFiltro:
    """Devuelve menos filas cuando se filtra: modela que acotar BAJA el total."""

    def __init__(self, sin_filtro: int, con_filtro: int) -> None:
        self.sin_filtro, self.con_filtro = sin_filtro, con_filtro

    def find_all(self, empresa_id=None, estado=None, area_id=None, page=1, page_size=20):
        # CUALQUIER filtro acota, no solo `estado`: si el fake solo mirara uno, un filtro nuevo
        # que no bajara el total pasaría inadvertido y el consejo "usá los filtros" sería falso.
        n = self.con_filtro if (estado or area_id) else self.sin_filtro
        # 🔴 EL TOTAL ES EL DEL FILTRO Y LAS FILAS SE RECORTAN, como hace el repo real con
        # `count="exact"` + `.range()`. Es lo que hace falsable el test del límite: si el fake
        # devolviera `len(pagina)` como total, un export que se lleva 20 filas de 30.000 pasaría
        # el tope sin chistar y el archivo saldría incompleto — el bug que este módulo cierra.
        ini = (page - 1) * page_size
        # SimpleNamespace y no dict: construir_filas_export lee atributos, no claves.
        # 🔴 ItemResponse REAL y no SimpleNamespace: desde que el export va por el listado, las
        # filas pasan por el wrapper Pydantic, que valida el TIPO de cada item. `model_construct`
        # las arma sin correr validación de campos — acá se mide el conteo, no el mapeo.
        filas = [ItemResponse.model_construct(
            empresa_nombre="ACME", nombre=f"item-{i}", tipo="notebook", descripcion=None,
            numero_serie=None, estado="disponible", costo=None, asignado_a=None, notas=None,
            fecha_alta=None, created_at=None,
        ) for i in range(n)]
        return filas[ini:ini + page_size], n


class TestElConteoRespetaLosFiltros:
    """La salida que le ofrecemos al usuario es "usá los filtros". Si filtrar no bajara el
    total, el mensaje sería un consejo que no se puede seguir."""

    def _exportar(self, repo, **kw):
        from services.inventario_items_service import InventarioItemsService
        return InventarioItemsService(repo=repo).exportar(**kw)

    def test_sin_filtro_supera_y_corta(self) -> None:
        repo = _RepoPorFiltro(LIMITE_FILAS_EXPORT + 10, 3)
        with pytest.raises(AppError) as exc:
            self._exportar(repo)
        assert exc.value.code == CODE

    def test_con_filtro_baja_del_limite_y_exporta(self) -> None:
        """El mismo pedido, acotado, sí sale — que es lo que el mensaje promete."""
        repo = _RepoPorFiltro(LIMITE_FILAS_EXPORT + 10, 3)
        assert self._exportar(repo, estado="disponible") is not None

    def test_el_total_del_mensaje_es_el_filtrado(self) -> None:
        """No el total de la tabla: el número que ve el usuario tiene que ser el de SU consulta.

        El número esperado se DERIVA del tope en vez de ir literal: acá lo que se prueba es de
        cuál de los dos conteos sale el mensaje, no cómo se formatea (eso lo cubre
        `TestMensaje::test_incluye_el_maximo`, que sí lleva literal). Con el literal, mover el
        tope rompía este test por un motivo que no tiene nada que ver con lo que verifica."""
        filtrado = LIMITE_FILAS_EXPORT + 7
        repo = _RepoPorFiltro(9999, filtrado)
        with pytest.raises(AppError) as exc:
            self._exportar(repo, estado="disponible")
        assert f"{filtrado:,}".replace(",", ".") in exc.value.message
        # La otra mitad, que faltaba: que el total de la TABLA no se cuele en el mensaje.
        assert "9.999" not in exc.value.message
