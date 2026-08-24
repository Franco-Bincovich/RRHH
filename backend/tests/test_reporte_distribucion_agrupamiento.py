"""
El agrupamiento del reporte de distribución: dos grafías que solo difieren en la caja son UNA
categoría, y la etiqueta que se muestra es determinista.

🔴 POR QUÉ EXISTE. `empleados.seniority` tiene DOS escritores con vocabularios distintos: el
formulario escribe minúsculas (`senior`, `semi_senior`) y el import de nómina escribe el Excel
tal cual, en mayúsculas (`SENIOR`, `EXPERT`, `TRAINEE`). Como la clave de agrupamiento era el
valor CRUDO, `SENIOR` y `senior` salían como dos filas: en producción, medido el 23/8/2026, eran
1 y 5 — el reporte partía en dos los 6 seniors de la empresa, y el dashboard también, porque
reusa este mismo generador.

🔴 LO QUE ESTE ARCHIVO **NO** AFIRMA, y está acá para que nadie lo lea de más: que el
vocabulario quedó unificado. `tipo_contrato` tiene `RELACION DE DEPENDENCIA` y `efectivo`, que
NO son la misma palabra escrita distinto y ninguna normalización de caja junta. Hay un test que
lo fija explícitamente, para que la limitación esté escrita en el código y no solo en un
comentario.

⚠️ Qué tendría que ser distinto para que estos tests puedan fallar: se le pasan filas con las
dos grafías del MISMO valor y se cuentan las categorías resultantes. Con la implementación vieja
—clave = valor crudo— el conteo da 2 donde tiene que dar 1 y el bloque entero rojea. Verificado
por mutación.
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

from services.reportes._reporte_distribucion import _agrupar

_SIN = "Sin especificar"


def _filas(campo: str, valores: list) -> list[dict]:
    return [{campo: v} for v in valores]


def _por_categoria(salida: list[dict]) -> dict:
    return {f["categoria"]: f["total"] for f in salida}


class TestDosGrafiasSonUnaCategoria:
    def test_el_caso_de_produccion_senior_y_SENIOR(self) -> None:
        """5 `senior` del formulario + 1 `SENIOR` del import = 6 seniors, no 5 y 1."""
        salida = _agrupar(_filas("seniority", ["senior"] * 5 + ["SENIOR"]), "seniority")
        assert _por_categoria(salida) == {"senior": 6}

    def test_tambien_ignora_el_espaciado(self) -> None:
        """`normalizar_nombre` colapsa espacios: un doble espacio del Excel no crea categoría."""
        salida = _agrupar(_filas("turno", ["8 A 17 HS.", "8  A  17 HS."]), "turno")
        assert sum(f["total"] for f in salida) == 2
        assert len(salida) == 1

    def test_valores_realmente_distintos_siguen_separados(self) -> None:
        """La contracara: agrupar de más sería peor que agrupar de menos."""
        salida = _agrupar(_filas("seniority", ["senior", "semi_senior", "junior"]), "seniority")
        assert _por_categoria(salida) == {"senior": 1, "semi_senior": 1, "junior": 1}


class TestLaEtiquetaQueSeMuestra:
    def test_gana_la_grafia_mas_frecuente(self) -> None:
        """No se inventa texto: la etiqueta sale del dato, y es la que la empresa realmente usa."""
        salida = _agrupar(_filas("seniority", ["senior"] * 5 + ["SENIOR"]), "seniority")
        assert salida[0]["categoria"] == "senior"

    def test_si_manda_la_mayuscula_se_muestra_la_mayuscula(self) -> None:
        """La regla es la frecuencia, no 'siempre minúsculas': el dato manda en las dos direcciones."""
        salida = _agrupar(_filas("seniority", ["SENIOR"] * 4 + ["senior"]), "seniority")
        assert salida[0]["categoria"] == "SENIOR"

    def test_el_empate_se_rompe_alfabeticamente_y_no_por_orden_de_llegada(self) -> None:
        """🔴 DETERMINISMO. La query no lleva ORDER BY: con "la primera que aparezca", el mismo
        reporte podría decir SENIOR un día y senior al siguiente sin que cambiara un dato."""
        a = _agrupar(_filas("seniority", ["SENIOR", "senior"]), "seniority")
        b = _agrupar(_filas("seniority", ["senior", "SENIOR"]), "seniority")
        assert a[0]["categoria"] == b[0]["categoria"] == "SENIOR"

    def test_no_se_titlecasea_el_texto_libre(self) -> None:
        """`turno` es texto libre: normalizar la PRESENTACIÓN lo arruinaría ('8 A 17 Hs.')."""
        salida = _agrupar(_filas("turno", ["8 A 17 HS."] * 3), "turno")
        assert salida[0]["categoria"] == "8 A 17 HS."


class TestLoQueNoCambia:
    def test_los_vacios_siguen_cayendo_en_sin_especificar_y_al_final(self) -> None:
        salida = _agrupar(_filas("seniority", [None, "", "  ", "SIN DATOS", "n/a", "senior"]), "seniority")
        assert _por_categoria(salida) == {"senior": 1, _SIN: 5}
        assert salida[-1]["categoria"] == _SIN

    def test_el_orden_es_por_total_desc(self) -> None:
        salida = _agrupar(_filas("seniority", ["b", "b", "a"]), "seniority")
        assert [f["categoria"] for f in salida] == ["b", "a"]

    def test_el_empate_de_TOTALES_se_desempata_por_nombre_y_no_por_orden_de_llegada(self) -> None:
        """Las filas se pasan en orden c, b, a A PROPÓSITO: sin el desempate por nombre, `sorted`
        es estable y las devolvería en ese mismo orden, o sea el orden en que la base entregó las
        filas — que no está definido, porque la query no lleva ORDER BY. El reporte cambiaría de
        forma entre corridas sin que cambiara un solo dato.
        (Escrito así tras un mutation check: la primera versión de este test usaba valores cuyo
        orden de llegada YA coincidía con el alfabético, así que sacar el desempate lo dejaba en
        verde — probaba el orden por total, no la estabilidad que su nombre prometía.)"""
        salida = _agrupar(_filas("seniority", ["c", "b", "a"]), "seniority")
        assert [f["categoria"] for f in salida] == ["a", "b", "c"]

    def test_sin_filas_no_hay_categorias(self) -> None:
        assert _agrupar([], "seniority") == []


class TestLaLimitacionDeclarada:
    def test_normalizar_la_caja_NO_unifica_vocabularios_distintos(self) -> None:
        """🔴 Es el punto que este arreglo NO resuelve, escrito como test para que no se lea de
        más. `efectivo` (formulario) y `RELACION DE DEPENDENCIA` (import) son palabras distintas:
        si son la misma categoría lo decide RRHH, y se cierra con una lista cerrada + traducción
        en el import + un UPDATE de lo ya cargado (bloque N), no acá."""
        salida = _agrupar(
            _filas("tipo_contrato", ["RELACION DE DEPENDENCIA"] * 30 + ["efectivo"] * 10 + ["HONORARIOS"]),
            "tipo_contrato",
        )
        assert _por_categoria(salida) == {
            "RELACION DE DEPENDENCIA": 30, "efectivo": 10, "HONORARIOS": 1,
        }
