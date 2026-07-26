"""Tests de no-regresión de E2: ReporteExportService delega al motor genérico sin cambiar la descarga.

Verifica que el filename sale byte-idéntico a la fórmula vieja (reporte_<uuid>.<ext>), que el
media_type de pdf/excel no cambió, y que un reporte inexistente lanza 404. Usa un repo fake.
"""
import re
from types import SimpleNamespace
from uuid import UUID

import pytest

from services.reporte_export_service import ReporteExportService
from utils.errors import AppError

# Réplica EXACTA de la lógica del viejo _reporte_export_descarga (referencia de no-regresión).
_OLD_SAFE_RE = re.compile(r"[^\w\s\-áéíóúüñÁÉÍÓÚÜÑ]")
_OLD_META = {"pdf": ("application/pdf", "pdf"),
             "excel": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")}


def _old_filename(reporte_id: UUID, formato: str) -> tuple[str, str]:
    media_type, ext = _OLD_META[formato]
    safe = _OLD_SAFE_RE.sub("", str(reporte_id))[:40]
    return f"reporte_{safe}.{ext}", media_type


class _FakeRepo:
    def __init__(self, reporte: object) -> None:
        self._reporte = reporte

    def find_by_id(self, _id: str) -> object:
        return self._reporte


_RID = UUID("550e8400-e29b-41d4-a716-446655440000")
_EMP_A = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_EMP_B = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _reporte(empresa_id=None) -> SimpleNamespace:
    return SimpleNamespace(
        nombre="Headcount — Enero 2026", empresa_id=empresa_id,
        datos={"total_empleados": 5, "por_area": [{"area": "Tec", "total": 5}]},
    )


_REPORTE = _reporte()


class TestNoRegresion:
    @pytest.mark.parametrize("formato", ["pdf", "excel"])
    def test_filename_y_media_type_identicos(self, formato: str) -> None:
        svc = ReporteExportService(repo=_FakeRepo(_REPORTE))
        d = svc.build_export(_RID, formato)
        old_name, old_mt = _old_filename(_RID, formato)
        assert d.filename == old_name      # byte-idéntico a la fórmula vieja
        assert d.media_type == old_mt
        assert len(d.content) > 0

    def test_pdf_es_pdf(self) -> None:
        svc = ReporteExportService(repo=_FakeRepo(_REPORTE))
        assert svc.build_export(_RID, "pdf").content[:4] == b"%PDF"

    def test_reporte_inexistente_404(self) -> None:
        svc = ReporteExportService(repo=_FakeRepo(None))
        with pytest.raises(AppError) as exc:
            svc.build_export(_RID, "pdf")
        assert exc.value.status_code == 404
        assert exc.value.code == "REPORTE_NOT_FOUND"


class TestValidacionEmpresa:
    def test_reporte_de_otra_empresa_es_404(self) -> None:
        # reporte de empresa A, request en empresa B → 404 (mismo code que "no encontrado")
        svc = ReporteExportService(repo=_FakeRepo(_reporte(empresa_id=_EMP_A)))
        with pytest.raises(AppError) as exc:
            svc.build_export(_RID, "pdf", _EMP_B)
        assert exc.value.status_code == 404 and exc.value.code == "REPORTE_NOT_FOUND"

    def test_reporte_consolidado_null_es_visible(self) -> None:
        # reporte consolidado (empresa_id null) → exportable desde cualquier empresa
        svc = ReporteExportService(repo=_FakeRepo(_reporte(empresa_id=None)))
        assert len(svc.build_export(_RID, "pdf", _EMP_B).content) > 0

    def test_reporte_de_la_propia_empresa_ok(self) -> None:
        svc = ReporteExportService(repo=_FakeRepo(_reporte(empresa_id=_EMP_A)))
        assert len(svc.build_export(_RID, "pdf", _EMP_A).content) > 0

    def test_modo_consolidado_del_request_permite_cualquiera(self) -> None:
        # request sin empresa activa (None = "Todas") → puede exportar un reporte de cualquier empresa
        svc = ReporteExportService(repo=_FakeRepo(_reporte(empresa_id=_EMP_A)))
        assert len(svc.build_export(_RID, "pdf", None).content) > 0
