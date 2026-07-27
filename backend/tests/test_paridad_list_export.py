"""
Invariante list ↔ export: el endpoint de export acepta EXACTAMENTE los mismos filtros que su
listado.

Por qué existe este test y no una revisión a ojo: cuando se rompe, no rompe nada visible. El
usuario filtra la pantalla, exporta, y recibe un archivo con MÁS filas de las que estaba
viendo — sin error, sin aviso. Y es la clase de bug que aparece meses después, cuando alguien
suma un filtro al listado y se olvida del export.

🔴 EL BARRIDO ES AUTOMÁTICO, A PROPÓSITO. Las rutas salen de `app.routes` (la introspección de
FastAPI), no de una lista escrita a mano. Un módulo que se agregue mañana con su export queda
cubierto sin tocar este archivo. **Si un par difiere con motivo legítimo, se declara en
`_EXPORTS_SIN_LISTADO` con su razón — nunca se saca el módulo del barrido.**

Las dos diferencias que SÍ son legítimas y están permitidas para todos los pares:

  · `formato` (pdf/excel/csv/word) existe solo en el export: es cómo sale el archivo, no un
    filtro. En el listado no significaría nada.
  · `page` / `page_size` existen solo en el listado: **el export NO se pagina**, por diseño
    (invariante documentado del repo). Un export paginado entregaría un archivo incompleto.

Cualquier otra diferencia es un bug.
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

import pytest
from fastapi.routing import APIRoute

from main import app

# Sufijos con los que el repo nombra un endpoint de export.
_SUFIJOS_EXPORT = ("/exportar", "/export")

_SOLO_EXPORT = {"formato"}       # cómo sale el archivo, no qué filas salen
_SOLO_LISTADO = {"page", "page_size"}  # el export no se pagina, por diseño

# Exports que legítimamente NO tienen listado con los mismos filtros. Cada entrada lleva su
# razón: si mañana alguien agrega uno acá sin justificarlo, se ve en el diff.
_EXPORTS_SIN_LISTADO: dict[str, str] = {
    # Exporta UN reporte ya generado y guardado, buscado por su id en el path. No es el
    # export de un listado filtrable: el "filtrado" ocurrió al generarlo (POST /generar).
    "/api/reportes/{reporte_id}/exportar": "exporta un reporte puntual por id, no un listado",
}

# Mínimo de pares que el barrido tiene que encontrar. Guarda contra el falso verde: si la
# derivación de rutas se rompe, el barrido devolvería 0 pares y todos los tests pasarían
# sin haber comparado nada.
_MINIMO_PARES_ESPERADOS = 8


def _rutas_get() -> dict[str, set[str]]:
    """path → nombres de sus query params, para cada ruta GET montada en la app."""
    return {
        r.path: {p.name for p in r.dependant.query_params}
        for r in app.routes
        if isinstance(r, APIRoute) and "GET" in r.methods
    }


def _path_listado(path_export: str) -> str:
    """Deriva el path del listado sacándole el sufijo de export."""
    for sufijo in _SUFIJOS_EXPORT:
        if path_export.endswith(sufijo):
            return path_export[: -len(sufijo)]
    raise AssertionError(f"{path_export} no termina en un sufijo de export conocido")


def _paths_export() -> list[str]:
    return sorted(p for p in _rutas_get() if p.endswith(_SUFIJOS_EXPORT))


def _pares() -> list[tuple[str, str]]:
    """(path_export, path_listado) de los exports que tienen listado. Sin las excepciones."""
    rutas = _rutas_get()
    return [
        (exp, _path_listado(exp))
        for exp in _paths_export()
        if exp not in _EXPORTS_SIN_LISTADO and _path_listado(exp) in rutas
    ]


class TestBarrido:
    """El barrido tiene que estar mirando algo. Sin esto, todo lo demás pasa en el vacío."""

    def test_encuentra_exports(self) -> None:
        assert len(_paths_export()) >= _MINIMO_PARES_ESPERADOS

    def test_encuentra_pares(self) -> None:
        assert len(_pares()) >= _MINIMO_PARES_ESPERADOS

    def test_todo_export_tiene_listado_o_excepcion_declarada(self) -> None:
        """Un export sin listado y sin razón escrita es un módulo que se salió del barrido."""
        rutas = _rutas_get()
        huerfanos = [
            exp for exp in _paths_export()
            if exp not in _EXPORTS_SIN_LISTADO and _path_listado(exp) not in rutas
        ]
        assert not huerfanos, (
            f"Exports sin listado y sin excepción declarada: {huerfanos}. "
            "Si es legítimo, agregalo a _EXPORTS_SIN_LISTADO CON su razón."
        )

    def test_las_excepciones_siguen_existiendo(self) -> None:
        """Una excepción que apunta a una ruta borrada es ruido que oculta el próximo caso."""
        rutas = _rutas_get()
        muertas = [p for p in _EXPORTS_SIN_LISTADO if p not in rutas]
        assert not muertas, f"Excepciones que ya no corresponden a ninguna ruta: {muertas}"


@pytest.mark.parametrize("path_export,path_listado", _pares(), ids=lambda v: v)
class TestParidad:
    def test_el_export_acepta_todo_lo_que_acepta_el_listado(
        self, path_export: str, path_listado: str
    ) -> None:
        """La dirección que importa: si el listado filtra por algo, el export TIENE que poder.
        Cuando falla, el archivo descargado trae más filas de las que se ven en pantalla."""
        rutas = _rutas_get()
        faltan = (rutas[path_listado] - _SOLO_LISTADO) - rutas[path_export]
        assert not faltan, (
            f"{path_export} no acepta {sorted(faltan)}, que {path_listado} sí filtra. "
            "El export devolvería más filas de las que muestra el listado."
        )

    def test_el_export_no_tiene_filtros_propios(
        self, path_export: str, path_listado: str
    ) -> None:
        """La dirección inversa: un filtro que solo existe en el export es inalcanzable desde
        la UI, y hace que lo exportado no se corresponda con ninguna pantalla."""
        rutas = _rutas_get()
        sobran = (rutas[path_export] - _SOLO_EXPORT) - rutas[path_listado]
        assert not sobran, (
            f"{path_export} acepta {sorted(sobran)}, que {path_listado} no tiene. "
            "Un filtro solo-export no se corresponde con ninguna vista."
        )

    def test_el_export_acepta_formato(self, path_export: str, path_listado: str) -> None:
        assert "formato" in _rutas_get()[path_export]

    def test_el_export_no_pagina(self, path_export: str, path_listado: str) -> None:
        """Un export paginado entrega un archivo incompleto sin decirlo."""
        assert not (_rutas_get()[path_export] & _SOLO_LISTADO)
