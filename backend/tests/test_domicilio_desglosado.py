"""
Domicilio desglosado: los seis campos estructurados del legajo (migración 081).

🚨 QUÉ TIENE QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR.
La pregunta no es retórica: en tandas anteriores un fake que ordenaba en Python y un render
sin `useEffect` pasaron los dos con el código roto. Acá el modo de falla sería un
`_FakeRepo.save()` que devuelve un `EmpleadoResponse` PREFABRICADO ignorando el `data` que
recibe. Con ese fake, "el alta persiste los seis campos" da verde **aunque los campos nunca
salgan del schema**: el test estaría afirmando algo sobre su propia constante.

Por eso el fake de acá **construye la respuesta A PARTIR de lo que le llega** y guarda el
estado en un dict, como una base: `save` persiste el payload recibido y `update` aplica el
patch sobre lo guardado. Recién así, si un campo se cae del schema o del `model_dump`, el
test lo ve.

🚨 Y HONRA `empresa_id`: `find_by_id` devuelve None cuando el empleado es de otra empresa,
igual que el WHERE real. Un fake permisivo daría verde sobre la barrera.

Los campos NACEN VACÍOS: `domicilio` estaba 0/19 en producción, así que no hubo migración de
datos ni parseo de texto libre. Estos tests cubren lo que se cargue de acá en adelante.
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

from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from schemas._provincias import PROVINCIAS
from schemas.empleado import EmpleadoCreate, EmpleadoResponse, EmpleadoUpdate
from services._empleados_export import construir_filas_export
from services.empleado_service import EmpleadoService

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()

SEIS = {
    "domicilio_calle": "Av. Rivadavia",
    "domicilio_numero": "S/N",
    "domicilio_piso_depto": "4 B",
    "domicilio_localidad": "Bell Ville",
    "domicilio_provincia": "Córdoba",
    "domicilio_cp": "2550",
}

_BASE = dict(
    nombre="Ana", apellido="Lopez", email_corporativo="a@x.com", roles=["Dev"],
    modalidad_trabajo="remoto", tipo_contrato="indefinido", fecha_ingreso=date(2026, 1, 1),
)


class _FakeEmpRepo:
    """Guarda de verdad lo que recibe. Ver la advertencia de la cabecera: un fake que
    devolviera un Response prefabricado haría pasar estos tests con los campos rotos."""

    def __init__(self) -> None:
        self.filas: dict = {}

    def _responder(self, id_: str) -> EmpleadoResponse:
        return EmpleadoResponse(**self.filas[id_])

    def find_by_legajo(self, *a, **k):
        return None

    def find_by_id(self, id, empresa_id=None):
        fila = self.filas.get(str(id))
        if not fila:
            return None
        if empresa_id and fila["empresa_id"] != str(empresa_id):
            return None  # HONRA empresa_id, como el WHERE real
        return self._responder(str(id))

    def save(self, data: EmpleadoCreate, empresa_id):
        # Espeja el repo real: payload = model_dump() sin los None. Si un campo no está en el
        # schema, tampoco llega acá — que es exactamente lo que el test tiene que detectar.
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        id_ = str(uuid4())
        self.filas[id_] = {
            **payload, "id": id_, "empresa_id": str(empresa_id),
            "area_id": str(payload["area_id"]), "estado": "activo",
            "created_at": datetime(2026, 1, 1, 9, 0),
        }
        return self._responder(id_)

    def update(self, id, data: EmpleadoUpdate, empresa_id=None):
        fila = self.filas.get(str(id))
        if not fila or (empresa_id and fila["empresa_id"] != str(empresa_id)):
            return None
        fila.update({k: v for k, v in data.model_dump(exclude_none=True).items()})
        return self._responder(str(id))

    def soft_delete(self, id, empresa_id=None):
        return True


class _Audit:
    def registrar(self, **kw) -> None:
        pass


class _AreaRepoPermisivo:
    """Permisivo A PROPÓSITO: este archivo cubre el domicilio, no el gate de área (ese vive en
    test_empleado_area_empresa.py, con un fake que sí honra empresa_id)."""

    def find_by_id(self, id, empresa_id=None):
        return SimpleNamespace(id=str(id), empresa_id=empresa_id)


def _svc():
    repo = _FakeEmpRepo()
    return EmpleadoService(repo=repo, audit=_Audit(), area_repo=_AreaRepoPermisivo()), repo


def _crear(svc, **extra) -> EmpleadoResponse:
    return svc.create_empleado(
        EmpleadoCreate(**_BASE, area_id=uuid4(), empresa_id=EMPRESA_A, **extra),
        created_by="u1", empresa_id=EMPRESA_A,
    )


# ─── Alta ─────────────────────────────────────────────────────────────────────


class TestAlta:
    def test_persiste_los_seis(self) -> None:
        svc, _ = _svc()
        e = _crear(svc, **SEIS)
        assert {c: getattr(e, c) for c in SEIS} == SEIS

    @pytest.mark.parametrize("campo", sorted(SEIS))
    def test_cada_campo_por_separado(self, campo: str) -> None:
        """Uno por uno: un dict comparado entero puede pasar por casualidad si el schema
        arrastra el valor de otro campo."""
        svc, _ = _svc()
        assert getattr(_crear(svc, **{campo: SEIS[campo]}), campo) == SEIS[campo]

    def test_sin_ninguno_es_camino_feliz(self) -> None:
        """Los seis son opcionales: el alta sin domicilio no puede fallar ni inventar valores."""
        svc, _ = _svc()
        e = _crear(svc)
        assert all(getattr(e, c) is None for c in SEIS)

    def test_el_numero_admite_texto(self) -> None:
        """Existen "S/N", "1234 bis", "KM 4": un entero los rechazaría."""
        svc, _ = _svc()
        for valor in ("S/N", "1234 bis", "KM 4"):
            assert _crear(svc, domicilio_numero=valor).domicilio_numero == valor

    def test_el_crudo_sigue_existiendo(self) -> None:
        """`domicilio` no se borró: es el destino de lo que no encaje en los estructurados."""
        svc, _ = _svc()
        assert _crear(svc, domicilio="Lo que sea, sin desglosar").domicilio is not None


class TestEdicion:
    def test_completa_los_estructurados_sobre_una_fila_que_solo_tiene_el_crudo(self) -> None:
        """El caso real de migración: alguien abre un legajo viejo y desglosa el texto libre
        a mano. El crudo NO se pisa — sigue ahí como referencia."""
        svc, _ = _svc()
        e = _crear(svc, domicilio="Av. Rivadavia S/N, 4 B, Bell Ville")
        editado = svc.update_empleado(e.id, EmpleadoUpdate(**SEIS), empresa_id=EMPRESA_A,
                                      usuario_id="u1")
        assert {c: getattr(editado, c) for c in SEIS} == SEIS
        assert editado.domicilio == "Av. Rivadavia S/N, 4 B, Bell Ville"

    def test_una_edicion_parcial_no_borra_el_resto(self) -> None:
        svc, _ = _svc()
        e = _crear(svc, **SEIS)
        editado = svc.update_empleado(e.id, EmpleadoUpdate(domicilio_cp="5000"),
                                      empresa_id=EMPRESA_A, usuario_id="u1")
        assert editado.domicilio_cp == "5000"
        assert editado.domicilio_localidad == "Bell Ville"

    def test_no_se_edita_un_empleado_de_otra_empresa(self) -> None:
        svc, _ = _svc()
        e = _crear(svc)
        from utils.errors import AppError
        with pytest.raises(AppError) as exc:
            svc.update_empleado(e.id, EmpleadoUpdate(**SEIS), empresa_id=EMPRESA_B,
                                usuario_id="u1")
        assert exc.value.status_code == 404


# ─── Provincia: lista cerrada ─────────────────────────────────────────────────


class TestProvincia:
    def test_son_veinticuatro(self) -> None:
        """23 provincias + CABA. Fuente: apis.datos.gob.ar/georef (IGN)."""
        assert len(PROVINCIAS) == 24

    def test_no_hay_repetidas(self) -> None:
        assert len(set(PROVINCIAS)) == 24

    @pytest.mark.parametrize("provincia", [
        "Córdoba", "Neuquén", "Tucumán", "Entre Ríos", "Río Negro",          # con tilde
        "Ciudad Autónoma de Buenos Aires", "Santiago del Estero",             # compuestos
        "Tierra del Fuego, Antártida e Islas del Atlántico Sur",              # con comas
    ])
    def test_las_validas_pasan(self, provincia: str) -> None:
        svc, _ = _svc()
        assert _crear(svc, domicilio_provincia=provincia).domicilio_provincia == provincia

    @pytest.mark.parametrize("invalida", [
        "Cordoba",        # sin tilde: el valor "casi correcto" es el que más se cuela
        "CÓRDOBA",        # mayúsculas
        "CABA",           # abreviatura de uso corriente
        "Buenos aires",   # case distinto
        "Montevideo",     # no es argentina
        "Cba",
    ])
    def test_las_invalidas_dan_422_sin_llegar_al_service(self, invalida: str) -> None:
        """La validación es del schema, así que el valor inválido nunca toca el repo. Se
        verifica sobre el repo, no solo sobre la excepción: rechazar y persistir igual sería
        el peor de los dos mundos."""
        _, repo = _svc()
        with pytest.raises(ValidationError):
            EmpleadoCreate(**_BASE, area_id=uuid4(), empresa_id=EMPRESA_A,
                           domicilio_provincia=invalida)
        assert repo.filas == {}

    def test_vacia_es_valida(self) -> None:
        """No cargar provincia tiene que seguir siendo posible."""
        svc, _ = _svc()
        assert _crear(svc, domicilio_provincia=None).domicilio_provincia is None


class TestUnaSolaFuenteDeLaLista:
    """🔴 La lista vive en UN lugar por lado y el front la PIDE al backend. Si alguien la
    copia al frontend, las dos se separan en silencio y el usuario termina eligiendo del
    select una opción que el backend rechaza con 422."""

    def test_el_front_no_tiene_su_propia_copia(self) -> None:
        front = Path(__file__).resolve().parent.parent.parent / "frontend"
        sospechosos = []
        for f in front.rglob("*.ts*"):
            if "node_modules" in f.parts or ".next" in f.parts:
                continue
            texto = f.read_text(encoding="utf-8", errors="ignore")
            # Tres jurisdicciones juntas en un mismo archivo = alguien pegó la lista.
            if sum(p in texto for p in ("Neuquén", "Entre Ríos", "Santiago del Estero")) >= 3:
                sospechosos.append(f.name)
        assert not sospechosos, (
            f"La lista de provincias parece duplicada en el front: {sospechosos}. "
            "Tiene que pedirse a /api/empleados/provincias — ver services/provincias.ts."
        )

    def test_el_endpoint_de_catalogo_existe(self) -> None:
        from fastapi.routing import APIRoute

        from main import app
        rutas = [r.path for r in app.routes if isinstance(r, APIRoute)]
        assert "/api/empleados/provincias" in rutas


# ─── Export ───────────────────────────────────────────────────────────────────


def _empleado_export(**over) -> EmpleadoResponse:
    base = dict(
        id="e1", nombre="Ana", apellido="Lopez", area_id="ar1", roles=["Dev"],
        modalidad_trabajo="remoto", tipo_contrato="indefinido",
        fecha_ingreso=date(2026, 1, 1), estado="activo", created_at=datetime(2026, 1, 1, 9, 0),
    )
    base.update(over)
    return EmpleadoResponse(**base)


class TestExport:
    def test_incluye_provincia_y_localidad(self) -> None:
        fila = construir_filas_export([_empleado_export(**SEIS)])[0]
        assert fila["Provincia"] == "Córdoba" and fila["Localidad"] == "Bell Ville"

    def test_no_incluye_calle_numero_ni_piso(self) -> None:
        """Solo las dos agregables: en un listado, calle/número/piso no responden nada."""
        cols = set(construir_filas_export([_empleado_export(**SEIS)])[0])
        assert not (cols & {"Calle", "Número", "Piso / Depto", "Código postal"})

    def test_sin_domicilio_las_celdas_quedan_vacias_sin_romper(self) -> None:
        fila = construir_filas_export([_empleado_export()])[0]
        assert fila["Provincia"] is None and fila["Localidad"] is None
