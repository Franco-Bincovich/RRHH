"""
Transforms puros del import de Formación: estado, fechas, clasificación de filas y matcheo.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?

Nada que falsear: los módulos bajo prueba son PUROS (sin I/O), así que acá no hay fake que pueda
mentir — cada aserción ejercita la función real con el dato real. Lo que sí puede mentir es un
test SIN CONTRASTE: un `traducir_estado` que devolviera None para todo pasaría "rechaza En
pausa", y un `clasificar` que rechazara todo pasaría "rechaza la fila solo-Año". Por eso cada
rechazo tiene al lado su caso que SÍ pasa, y cada traducción su valor distinto.

Verificado por reversión el 19/8/2026 (editar → correr → restaurar):
  · sacar "finalizado" del diccionario → rojean los dos tests de la traducción;
  · derivar con día 28 en vez de 1 → rojea el de fechas;
  · indexar UN solo orden → rojea el del orden invertido;
  · aflojar el rechazo de estado desconocido a un default → rojea el de "En pausa".
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

from services import _formacion_import_transforms as tx  # noqa: E402
from services._formacion_import_valores import derivar_fechas, duracion_horas  # noqa: E402
from services._formacion_matcheo import IndiceEmpleados, pares_parecidos  # noqa: E402


# ─── Estado: diccionario explícito, nunca un default ─────────────────────────

class TestTraduccionEstado:
    def test_los_dos_valores_del_excel_real(self) -> None:
        assert tx.traducir_estado("Finalizado") == "completado"
        assert tx.traducir_estado("Sin iniciar") == "pendiente"

    def test_caja_y_acentos_no_importan(self) -> None:
        assert tx.traducir_estado("FINALIZADO") == "completado"
        assert tx.traducir_estado("  sin  Iniciar ") == "pendiente"

    def test_los_canonicos_del_check_entran_tal_cual(self) -> None:
        assert tx.traducir_estado("completado") == "completado"
        assert tx.traducir_estado("En curso") == "en_curso"
        assert tx.traducir_estado("pendiente") == "pendiente"

    def test_un_valor_desconocido_da_none_no_un_default(self) -> None:
        """🔴 La decisión 2: "En pausa" NO cae a pendiente. El DEFAULT de la columna haría
        exactamente eso en silencio; el diccionario lo impide."""
        assert tx.traducir_estado("En pausa") is None
        assert tx.traducir_estado("") is None


# ─── Fechas derivadas: primer día del mes ────────────────────────────────────

class TestDerivarFechas:
    def test_completado_lleva_las_dos_fechas(self) -> None:
        assert derivar_fechas("2026", "marzo", "completado") == ("2026-03-01", "2026-03-01", None)

    def test_pendiente_lleva_solo_asignacion(self) -> None:
        fa, fc, aviso = derivar_fechas("2026", "Marzo", "pendiente")
        assert (fa, fc, aviso) == ("2026-03-01", None, None), "la caja del mes no puede importar"

    def test_setiembre_es_septiembre(self) -> None:
        assert derivar_fechas("2026", "Setiembre", "pendiente")[0] == "2026-09-01"

    def test_sin_mes_no_hay_fecha_y_hay_aviso(self) -> None:
        fa, fc, aviso = derivar_fechas("2026", "", "completado")
        assert fa is None and fc is None
        assert aviso and "reporte" in aviso, "el aviso tiene que decir la consecuencia"

    def test_anio_ilegible_tampoco_deriva(self) -> None:
        fa, _, aviso = derivar_fechas("2023/2024", "marzo", "completado")
        assert fa is None and aviso

    def test_duracion_acepta_coma_y_rechaza_texto(self) -> None:
        assert duracion_horas("6") == 6.0 and duracion_horas("6,5") == 6.5
        assert duracion_horas("seis") is None and duracion_horas("") is None


# ─── Clasificación de filas ──────────────────────────────────────────────────

def _fila(**overrides) -> dict:
    base = {"anio": "2026", "mes": "marzo", "proyecto": None, "colaborador": "Alcaraz Valeria",
            "titulo": "Explorando la IA", "tipo": None, "entidad": None, "modalidad": None,
            "duracion": None, "estado_crudo": "Finalizado"}
    return {**base, **overrides}


class TestClasificar:
    def test_la_fila_completa_pasa(self) -> None:
        """El CONTRASTE de todos los rechazos de abajo: sin esto, rechazar todo pasa en verde."""
        assert tx.clasificar(_fila()) is None

    def test_solo_anio_se_rechaza_con_su_propio_motivo(self) -> None:
        motivo = tx.clasificar(_fila(colaborador="", titulo="", estado_crudo=""))
        assert motivo and "solo trae el Año" in motivo

    def test_sin_titulo_o_sin_colaborador_se_rechaza(self) -> None:
        assert "Título" in tx.clasificar(_fila(titulo=""))
        assert "Colaborador" in tx.clasificar(_fila(colaborador=""))

    def test_estado_desconocido_nombra_el_valor_y_el_vocabulario(self) -> None:
        motivo = tx.clasificar(_fila(estado_crudo="En pausa"))
        assert "En pausa" in motivo and "Finalizado" in motivo

    def test_faltantes_compara_sin_acentos(self) -> None:
        """"Titulo" tipeado sin acento cuenta como "Título" — el rebote de objetivos, evitado."""
        assert tx.faltantes(["Año", "Titulo", "Colaborador", "Estado"]) == []
        assert tx.faltantes(["Año", "Colaborador", "Estado"]) == [tx.COL_TITULO]


# ─── Matcheo: los dos órdenes, sin fuzzy para asignar ────────────────────────

_PADRON = [
    {"id": "e1", "nombre": "Valeria", "apellido": "Alcaraz"},
    {"id": "e2", "nombre": "Morella", "apellido": "Ponce"},
    {"id": "e3", "nombre": "Camila", "apellido": "Quiroga"},
]


class TestMatcheo:
    def test_matchea_en_los_dos_ordenes(self) -> None:
        idx = IndiceEmpleados(_PADRON)
        assert idx.resolver("Quiroga Camila")[0] == "e3"
        assert idx.resolver("Camila Quiroga")[0] == "e3"

    def test_acentos_y_caja_no_importan(self) -> None:
        assert IndiceEmpleados(_PADRON).resolver("  alcaráz VALERIA ")[0] == "e1"

    def test_una_letra_distinta_no_matchea(self) -> None:
        """🔴 Nada de fuzzy para ASIGNAR: "Ponce Morela" (typo del padrón "Ponce Morella") va a
        nombre_libre, no a e2 — un parecido le colgaría la formación a la persona equivocada."""
        empleado, motivo = IndiceEmpleados(_PADRON).resolver("Ponce Morela")
        assert empleado is None and "sin candidato" in motivo

    def test_dos_homonimos_dan_ambiguo_no_eligen(self) -> None:
        idx = IndiceEmpleados(_PADRON + [{"id": "e9", "nombre": "Camila", "apellido": "Quiroga"}])
        empleado, motivo = idx.resolver("Quiroga Camila")
        assert empleado is None and "más de un empleado" in motivo


class TestParesParecidos:
    def test_el_par_invertido_con_una_letra_se_reporta(self) -> None:
        """El caso real del archivo: Pesce Morela / Morella Pesce. Uno matchea, el otro no."""
        pares = pares_parecidos(["Ponce Morela", "Morella Ponce"],
                                {"Ponce Morela": None, "Morella Ponce": "e2"})
        assert len(pares) == 1 and "letra" in pares[0][2]

    def test_el_par_que_resolvio_a_la_misma_persona_no_se_reporta(self) -> None:
        """El matcheo por los dos órdenes ya los unificó: avisar acá sería ruido sin decisión."""
        assert pares_parecidos(["Quiroga Camila", "Camila Quiroga"],
                               {"Quiroga Camila": "e3", "Camila Quiroga": "e3"}) == []

    def test_dos_nombres_distintos_de_verdad_no_se_reportan(self) -> None:
        """El contraste del detector: sin esto, reportar TODOS los pares pasaría los dos de
        arriba igual."""
        assert pares_parecidos(["Alcaraz Valeria", "Quiroga Camila"],
                               {"Alcaraz Valeria": "e1", "Quiroga Camila": "e3"}) == []

    def test_mismo_nombre_invertido_sin_resolver_se_reporta_como_orden(self) -> None:
        pares = pares_parecidos(["Cattaneo Matias", "Matias Cattaneo"],
                                {"Cattaneo Matias": None, "Matias Cattaneo": None})
        assert len(pares) == 1 and "orden" in pares[0][2]
