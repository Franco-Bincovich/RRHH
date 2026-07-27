"""
Filtro por rango de fechas en vacaciones y ausencias.

🔴 LA SEMÁNTICA ES SOLAPAMIENTO, NO CONTENCIÓN, y es lo que fija la mayoría de estos tests:
una solicitud del 25/2 al 5/3 ENTRA cuando se pide marzo. Con contención desaparecería del
listado y del total, y un reporte de ausentismo del mes dejaría afuera justo los casos que
cruzan el borde. Es además la misma semántica que `_periodo_utils._solapa` usa para decidir si
una solicitud cae en un período cerrado: dos definiciones distintas de "pertenece a este
período" dentro del mismo módulo serían un bug esperando.

El repo real habla con Supabase, así que acá se usa un doble del QUERY BUILDER: registra los
`.gte`/`.lte` que se le encadenan y decide con la MISMA condición que Postgres evaluaría. Lo
que se prueba es la traducción rango → predicado, que es donde puede estar el error; que
Postgres compare fechas bien no hace falta probarlo.

El último bloque es el que importa para no romper nada: un mando medio con rango tiene que
recibir la INTERSECCIÓN de sus subordinados con el rango, no uno de los dos ejes.
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

from datetime import date

import pytest

from repositories._rango_fechas import aplicar_rango

# Rango pedido en todos los casos: marzo 2026.
DESDE, HASTA = date(2026, 3, 1), date(2026, 3, 31)


class _QueryDoble:
    """Doble del query builder de Supabase: acumula las cotas que le encadenan."""

    def __init__(self) -> None:
        self.cota_fecha_hasta_min: str | None = None  # de .gte("fecha_hasta", X)
        self.cota_fecha_desde_max: str | None = None  # de .lte("fecha_desde", X)

    def gte(self, columna: str, valor: str):
        assert columna == "fecha_hasta", f"solapamiento acota fecha_hasta por abajo, no {columna}"
        self.cota_fecha_hasta_min = valor
        return self

    def lte(self, columna: str, valor: str):
        assert columna == "fecha_desde", f"solapamiento acota fecha_desde por arriba, no {columna}"
        self.cota_fecha_desde_max = valor
        return self

    def incluye(self, fila_desde: date, fila_hasta: date) -> bool:
        """Evalúa las cotas acumuladas como lo haría Postgres."""
        if self.cota_fecha_hasta_min and str(fila_hasta) < self.cota_fecha_hasta_min:
            return False
        if self.cota_fecha_desde_max and str(fila_desde) > self.cota_fecha_desde_max:
            return False
        return True


def _filtra(fila_desde: date, fila_hasta: date, desde=DESDE, hasta=HASTA) -> bool:
    """¿Una solicitud [fila_desde, fila_hasta] entra en el rango pedido?"""
    return aplicar_rango(_QueryDoble(), desde, hasta).incluye(fila_desde, fila_hasta)


# ─── Solapamiento ─────────────────────────────────────────────────────────────


class TestSolapamiento:
    def test_solapa_al_inicio(self) -> None:
        """Empieza en febrero y termina en marzo: cruza el borde de entrada."""
        assert _filtra(date(2026, 2, 25), date(2026, 3, 5))

    def test_solapa_al_final(self) -> None:
        """Empieza en marzo y termina en abril: cruza el borde de salida."""
        assert _filtra(date(2026, 3, 28), date(2026, 4, 4))

    def test_contenida_entera_en_el_rango(self) -> None:
        assert _filtra(date(2026, 3, 10), date(2026, 3, 15))

    def test_el_rango_contenido_en_la_solicitud(self) -> None:
        """Una licencia larga que se come marzo entero también cuenta."""
        assert _filtra(date(2026, 1, 1), date(2026, 12, 31))

    def test_toca_solo_el_primer_dia(self) -> None:
        """Borde inclusivo: terminar el 1/3 cuenta como marzo."""
        assert _filtra(date(2026, 2, 1), date(2026, 3, 1))

    def test_toca_solo_el_ultimo_dia(self) -> None:
        assert _filtra(date(2026, 3, 31), date(2026, 4, 30))


class TestFueraDelRango:
    def test_termina_antes(self) -> None:
        assert not _filtra(date(2026, 1, 5), date(2026, 2, 28))

    def test_empieza_despues(self) -> None:
        assert not _filtra(date(2026, 4, 1), date(2026, 4, 10))

    def test_un_dia_antes_del_borde(self) -> None:
        assert not _filtra(date(2026, 2, 27), date(2026, 2, 28))

    def test_un_dia_despues_del_borde(self) -> None:
        assert not _filtra(date(2026, 4, 1), date(2026, 4, 1))


class TestContencionNo:
    """Guarda explícita contra que alguien 'corrija' el filtro a contención."""

    @pytest.mark.parametrize("fila_desde,fila_hasta", [
        (date(2026, 2, 25), date(2026, 3, 5)),
        (date(2026, 3, 28), date(2026, 4, 4)),
        (date(2026, 1, 1), date(2026, 12, 31)),
    ])
    def test_las_que_cruzan_el_borde_entran(self, fila_desde: date, fila_hasta: date) -> None:
        assert _filtra(fila_desde, fila_hasta)


# ─── Rangos abiertos ──────────────────────────────────────────────────────────


class TestRangosAbiertos:
    def test_solo_desde_incluye_lo_posterior(self) -> None:
        assert _filtra(date(2026, 6, 1), date(2026, 6, 5), desde=DESDE, hasta=None)

    def test_solo_desde_excluye_lo_anterior(self) -> None:
        assert not _filtra(date(2026, 1, 1), date(2026, 1, 5), desde=DESDE, hasta=None)

    def test_solo_desde_incluye_la_que_sigue_vigente(self) -> None:
        """Empezó en enero pero todavía no terminó: sigue vigente desde el corte."""
        assert _filtra(date(2026, 1, 1), date(2026, 5, 1), desde=DESDE, hasta=None)

    def test_solo_hasta_incluye_lo_anterior(self) -> None:
        assert _filtra(date(2026, 1, 1), date(2026, 1, 5), desde=None, hasta=HASTA)

    def test_solo_hasta_excluye_lo_posterior(self) -> None:
        assert not _filtra(date(2026, 6, 1), date(2026, 6, 5), desde=None, hasta=HASTA)

    @pytest.mark.parametrize("fila_desde,fila_hasta", [
        (date(2020, 1, 1), date(2020, 1, 2)),
        (date(2030, 1, 1), date(2030, 1, 2)),
    ])
    def test_sin_rango_no_filtra_nada(self, fila_desde: date, fila_hasta: date) -> None:
        assert _filtra(fila_desde, fila_hasta, desde=None, hasta=None)

    def test_sin_rango_no_encadena_cotas(self) -> None:
        """No basta con que devuelva todo: no tiene que tocar la query."""
        q = aplicar_rango(_QueryDoble(), None, None)
        assert q.cota_fecha_hasta_min is None and q.cota_fecha_desde_max is None


# ─── Intersección con ownership ───────────────────────────────────────────────


class _FakeOwn:
    """Mando 'jefe' con un subordinado; el resto no es suyo."""

    def find_by_user_id(self, user_id):
        return {"id": "jefe"} if user_id == "jefe" else None

    def ids_subordinados(self, empleado_id):
        return ["sub"] if empleado_id == "jefe" else []

    def ids_empleados_por_area(self, empresa_id, area_id):
        return ["jefe", "sub", "ajeno"]


class _RepoEspia:
    """Registra empleado_ids Y el rango con los que el service llama al repo."""

    def __init__(self) -> None:
        self.empleado_ids = "no-llamado"
        self.rango: tuple = ()

    def find_all(self, empresa_id, empleado_ids, page, page_size, estado=None, today=None,
                 *, desde=None, hasta=None):
        self.empleado_ids, self.rango = empleado_ids, (desde, hasta)
        return [], 0


class _RepoEspiaAus(_RepoEspia):
    def find_all(self, empresa_id, empleado_ids, tipo_id, page, page_size, *, desde=None, hasta=None):
        self.empleado_ids, self.rango = empleado_ids, (desde, hasta)
        return [], 0


class TestInterseccionConOwnership:
    """El rango y el ownership son ejes DISJUNTOS que se componen: uno no reemplaza al otro.

    Si el filtro de fechas se colara por un `.eq()` nuevo en el repo en vez de convivir con el
    canal de ownership, este bloque seguiría verde mientras el listado devuelve empleados
    ajenos — por eso se verifica que las DOS cosas lleguen juntas en la misma llamada.
    """

    def _servicio_vacaciones(self, repo):
        from services.vacaciones_service import VacacionesService
        return VacacionesService(repo=repo, ownership_repo=_FakeOwn())

    def _servicio_ausencias(self, repo):
        from services.ausencias_service import AusenciasService
        return AusenciasService(repo=repo, ownership_repo=_FakeOwn())

    def test_vac_mando_con_rango_manda_los_dos_ejes(self) -> None:
        repo = _RepoEspia()
        self._servicio_vacaciones(repo).get_all(
            "jefe", "mandos_medios", fecha_desde=DESDE, fecha_hasta=HASTA)
        assert sorted(repo.empleado_ids) == ["jefe", "sub"]   # ownership intacto
        assert repo.rango == (DESDE, HASTA)                   # y el rango también viaja

    def test_aus_mando_con_rango_manda_los_dos_ejes(self) -> None:
        repo = _RepoEspiaAus()
        self._servicio_ausencias(repo).get_all(
            "jefe", "mandos_medios", fecha_desde=DESDE, fecha_hasta=HASTA)
        assert sorted(repo.empleado_ids) == ["jefe", "sub"]
        assert repo.rango == (DESDE, HASTA)

    def test_vac_el_rango_no_ensancha_el_ownership(self) -> None:
        """El ajeno del área NO puede aparecer por poner un rango amplio."""
        repo = _RepoEspia()
        self._servicio_vacaciones(repo).get_all(
            "jefe", "mandos_medios", area_id="area-1", fecha_desde=None, fecha_hasta=None)
        assert "ajeno" not in repo.empleado_ids

    def test_vac_admin_con_rango_no_restringe_empleados(self) -> None:
        repo = _RepoEspia()
        self._servicio_vacaciones(repo).get_all(
            "admin", "admin_rrhh", fecha_desde=DESDE, fecha_hasta=HASTA)
        assert repo.empleado_ids is None                      # sin restricción de empleado
        assert repo.rango == (DESDE, HASTA)


class TestExportUsaElMismoFiltro:
    """El export tiene que devolver el mismo conjunto que el listado con los mismos filtros.
    Se verifica que llegue al repo el MISMO par (empleado_ids, rango) por los dos caminos."""

    def test_vacaciones(self) -> None:
        from services.vacaciones_service import VacacionesService
        listado, export = _RepoEspia(), _RepoEspia()
        VacacionesService(repo=listado, ownership_repo=_FakeOwn()).get_all(
            "jefe", "mandos_medios", fecha_desde=DESDE, fecha_hasta=HASTA)
        VacacionesService(repo=export, ownership_repo=_FakeOwn()).exportar(
            "jefe", "mandos_medios", fecha_desde=DESDE, fecha_hasta=HASTA)
        assert (sorted(export.empleado_ids), export.rango) == (sorted(listado.empleado_ids), listado.rango)

    def test_ausencias(self) -> None:
        from services.ausencias_service import AusenciasService
        listado, export = _RepoEspiaAus(), _RepoEspiaAus()
        AusenciasService(repo=listado, ownership_repo=_FakeOwn()).get_all(
            "jefe", "mandos_medios", fecha_desde=DESDE, fecha_hasta=HASTA)
        AusenciasService(repo=export, ownership_repo=_FakeOwn()).exportar(
            "jefe", "mandos_medios", fecha_desde=DESDE, fecha_hasta=HASTA)
        assert (sorted(export.empleado_ids), export.rango) == (sorted(listado.empleado_ids), listado.rango)
