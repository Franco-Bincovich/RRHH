"""
Tests críticos de flujos de negocio — HR Karstec.
Todos deben pasar antes de hacer deploy. Sin excepciones.

Flujos cubiertos:
  - Health check: /health devuelve 200 con status "ok"
  - Auth: acceso sin token → 401 MISSING_TOKEN
  - Auth: token inválido → 401 INVALID_TOKEN
  - AppError: creación con message, code, status_code
  - Settings: variables requeridas cargan sin error

Ver BASES-DE-DESARROLLO.md — Base 9 para la filosofía de testing.
"""
import os

# Patch env vars antes de cualquier import del proyecto.
# pydantic-settings lee os.environ en el momento de Settings(), que ocurre
# al importar config.settings. Usar setdefault para no pisar un .env real.
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

import httpx
import pytest

from types import SimpleNamespace

from config.settings import settings
from main import app
from services.empleado_catalogos_service import CAMPOS_AUTOCOMPLETABLES, EmpleadoCatalogosService
from utils.errors import AppError
from utils.permisos import Accion, Seccion, puede, require_permission

_TRANSPORT = httpx.ASGITransport(app=app)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=_TRANSPORT, base_url="http://test")


# ─── Health check ─────────────────────────────────────────────────────────────


class TestHealthCheck:
    async def test_returns_200(self) -> None:
        async with _client() as c:
            resp = await c.get("/health")
        assert resp.status_code == 200

    async def test_body_status_ok(self) -> None:
        async with _client() as c:
            resp = await c.get("/health")
        assert resp.json()["status"] == "ok"


# ─── Auth middleware ───────────────────────────────────────────────────────────


class TestAuth:
    async def test_missing_token_returns_401(self) -> None:
        async with _client() as c:
            resp = await c.get("/api/empleados/")
        assert resp.status_code == 401

    async def test_missing_token_code(self) -> None:
        async with _client() as c:
            resp = await c.get("/api/empleados/")
        assert resp.json()["code"] == "MISSING_TOKEN"

    async def test_invalid_token_returns_401(self) -> None:
        async with _client() as c:
            resp = await c.get(
                "/api/empleados/",
                headers={"Authorization": "Bearer esto.no.es.un.jwt.valido"},
            )
        assert resp.status_code == 401

    async def test_invalid_token_code(self) -> None:
        async with _client() as c:
            resp = await c.get(
                "/api/empleados/",
                headers={"Authorization": "Bearer esto.no.es.un.jwt.valido"},
            )
        assert resp.json()["code"] == "INVALID_TOKEN"

    async def test_auditoria_sin_token_401(self) -> None:
        # El gate de auditoría (require_permission AUDITORIA READ) actúa tras el
        # middleware: sin token corta antes, en AuthMiddleware → 401 MISSING_TOKEN.
        async with _client() as c:
            resp = await c.get("/api/auditoria")
        assert resp.status_code == 401
        assert resp.json()["code"] == "MISSING_TOKEN"


# ─── AppError ─────────────────────────────────────────────────────────────────


class TestAppError:
    def test_creates_with_all_fields(self) -> None:
        err = AppError("Empleado no encontrado", "EMPLEADO_NOT_FOUND", 404)
        assert err.message == "Empleado no encontrado"
        assert err.code == "EMPLEADO_NOT_FOUND"
        assert err.status_code == 404

    def test_default_status_code_is_500(self) -> None:
        err = AppError("Error interno", "INTERNAL")
        assert err.status_code == 500

    def test_is_exception(self) -> None:
        err = AppError("Test", "TEST_CODE", 400)
        assert isinstance(err, Exception)

    def test_str_returns_message(self) -> None:
        err = AppError("Mensaje de error", "ERR_CODE", 422)
        assert str(err) == "Mensaje de error"


# ─── Settings ─────────────────────────────────────────────────────────────────


class TestSettings:
    def test_required_vars_loaded(self) -> None:
        assert settings.supabase_url
        assert settings.supabase_anon_key
        assert settings.supabase_service_key
        assert settings.jwt_secret
        assert settings.anthropic_api_key

    def test_defaults_are_valid(self) -> None:
        assert settings.jwt_expiration_minutes > 0
        assert settings.refresh_token_expiration_days > 0
        assert settings.allowed_origins

    def test_allowed_origins_list_parses(self) -> None:
        origins = settings.allowed_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1
        assert all(o.strip() == o for o in origins)


# ─── Permisos (núcleo funcional, Entrega 2) ─────────────────────────────────────


class TestPermisos:
    def test_admin_rrhh_read_y_write_cualquier_seccion(self) -> None:
        assert puede("admin_rrhh", Seccion.OBJETIVOS, Accion.READ) is True
        assert puede("admin_rrhh", Seccion.OBJETIVOS, Accion.WRITE) is True

    def test_gerencia_lectura_solo_read(self) -> None:
        assert puede("gerencia_lectura", Seccion.COSTOS, Accion.READ) is True
        assert puede("gerencia_lectura", Seccion.COSTOS, Accion.WRITE) is False

    def test_mandos_medios_vacaciones_y_ausencias(self) -> None:
        assert puede("mandos_medios", Seccion.VACACIONES, Accion.READ) is True
        assert puede("mandos_medios", Seccion.VACACIONES, Accion.WRITE) is True
        assert puede("mandos_medios", Seccion.AUSENCIAS, Accion.READ) is True
        assert puede("mandos_medios", Seccion.AUSENCIAS, Accion.WRITE) is True

    def test_mandos_medios_otra_seccion_denegada(self) -> None:
        assert puede("mandos_medios", Seccion.OBJETIVOS, Accion.READ) is False
        assert puede("mandos_medios", Seccion.OBJETIVOS, Accion.WRITE) is False

    def test_auditoria_lectura_admin_y_gerencia_no_mandos(self) -> None:
        assert puede("admin_rrhh", Seccion.AUDITORIA, Accion.READ) is True
        assert puede("gerencia_lectura", Seccion.AUDITORIA, Accion.READ) is True
        assert puede("mandos_medios", Seccion.AUDITORIA, Accion.READ) is False
        assert puede("gerencia_lectura", Seccion.AUDITORIA, Accion.WRITE) is False

    def test_fail_closed_rol_none(self) -> None:
        assert puede(None, Seccion.VACACIONES, Accion.READ) is False

    def test_fail_closed_rol_inexistente(self) -> None:
        assert puede("inexistente", Seccion.VACACIONES, Accion.READ) is False

    def test_fail_closed_accion_invalida(self) -> None:
        assert puede("admin_rrhh", Seccion.VACACIONES, "delete") is False


# ─── require_permission (dependency wrapper) ────────────────────────────────────


def _req(rol: object = "__missing__") -> SimpleNamespace:
    """Request mínimo: solo .state.user, que es lo que require_permission lee."""
    if rol == "__missing__":
        return SimpleNamespace(state=SimpleNamespace())
    return SimpleNamespace(state=SimpleNamespace(user={"rol": rol} if rol is not None else None))


class TestRequirePermission:
    async def test_gerencia_write_lanza_forbidden(self) -> None:
        dep = require_permission(Seccion.EMPLEADOS, Accion.WRITE)
        with pytest.raises(AppError) as exc:
            await dep(_req("gerencia_lectura"))
        assert exc.value.code == "FORBIDDEN"
        assert exc.value.status_code == 403

    async def test_admin_write_no_lanza(self) -> None:
        dep = require_permission(Seccion.EMPLEADOS, Accion.WRITE)
        assert await dep(_req("admin_rrhh")) is None

    async def test_mandos_medios_vacaciones_write_no_lanza(self) -> None:
        dep = require_permission(Seccion.VACACIONES, Accion.WRITE)
        assert await dep(_req("mandos_medios")) is None

    async def test_mandos_medios_costos_write_lanza_forbidden(self) -> None:
        dep = require_permission(Seccion.COSTOS, Accion.WRITE)
        with pytest.raises(AppError) as exc:
            await dep(_req("mandos_medios"))
        assert exc.value.code == "FORBIDDEN"

    async def test_fail_closed_sin_user(self) -> None:
        dep = require_permission(Seccion.VACACIONES, Accion.READ)
        with pytest.raises(AppError) as exc:
            await dep(_req())
        assert exc.value.code == "FORBIDDEN"

    async def test_fail_closed_user_sin_rol(self) -> None:
        dep = require_permission(Seccion.VACACIONES, Accion.READ)
        with pytest.raises(AppError) as exc:
            await dep(_req(None))
        assert exc.value.code == "FORBIDDEN"


# ─── Valores conocidos / autocompletado del legajo (A1.2) ───────────────────────


class _FakeRolesRepo:
    """Repo fake que evita tocar Supabase en los tests del whitelist."""
    def get_valores_conocidos(self, campo: str) -> list[str]:
        return ["Capital Humano", "Sistemas"]

    def get_seleccionables(self, empresa_id: object) -> list[dict]:
        self.empresa_id = empresa_id  # captura para aserción
        return [{"id": "1", "nombre": "Ana", "apellido": "García"}]


class TestValoresConocidos:
    def test_whitelist_tiene_9_campos(self) -> None:
        assert len(CAMPOS_AUTOCOMPLETABLES) == 9

    def test_campo_fuera_de_whitelist_lanza_400(self) -> None:
        svc = EmpleadoCatalogosService(roles_repo=_FakeRolesRepo())
        with pytest.raises(AppError) as exc:
            svc.get_valores_conocidos("email_corporativo")
        assert exc.value.code == "CAMPO_INVALIDO"
        assert exc.value.status_code == 400

    def test_campo_valido_devuelve_lista(self) -> None:
        svc = EmpleadoCatalogosService(roles_repo=_FakeRolesRepo())
        assert svc.get_valores_conocidos("gerencia") == ["Capital Humano", "Sistemas"]


# ─── Manager / superior inmediato (A1.6a) ───────────────────────────────────────


def _empleado_row(**extra: object) -> dict:
    """Row mínimo válido para EmpleadoResponse (campos requeridos del schema)."""
    base = {
        "id": "11111111-1111-1111-1111-111111111111",
        "nombre": "Ana", "apellido": "García",
        "email_corporativo": "ana@karstec.com",
        "area_id": "22222222-2222-2222-2222-222222222222",
        "roles": ["Analista"], "modalidad_trabajo": "presencial",
        "tipo_contrato": "efectivo", "fecha_ingreso": "2024-01-01",
        "estado": "activo", "created_at": "2024-01-01T00:00:00Z",
    }
    base.update(extra)
    return base


class TestManagerRow:
    def test_manager_nombre_resuelto_apellido_nombre(self) -> None:
        from repositories._empleado_row import row as _row
        row = _empleado_row(
            manager_id="33333333-3333-3333-3333-333333333333",
            manager={"nombre": "Carlos", "apellido": "Pérez"},
        )
        emp = _row(row)
        assert emp.manager_id == "33333333-3333-3333-3333-333333333333"
        assert emp.manager_nombre == "Pérez, Carlos"

    def test_sin_manager_nombre_none(self) -> None:
        from repositories._empleado_row import row as _row
        emp = _row(_empleado_row())
        assert emp.manager_nombre is None


# ─── Empleados seleccionables (superior inmediato, A1.6b) ────────────────────────


class TestSeleccionables:
    def test_service_delega_al_repo_y_pasa_empresa(self) -> None:
        from uuid import UUID
        fake = _FakeRolesRepo()
        svc = EmpleadoCatalogosService(roles_repo=fake)
        empresa = UUID("44444444-4444-4444-4444-444444444444")
        result = svc.get_seleccionables(empresa)
        assert result == [{"id": "1", "nombre": "Ana", "apellido": "García"}]
        assert fake.empresa_id == empresa
