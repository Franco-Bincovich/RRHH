"""
Las reglas de forma y derivación del legajo (bloque N, 25/8/2026): `utils/legajo_reglas.py` y el
mixin `schemas/_legajo_normalizado.py` que las cuelga de los cuatro schemas de escritura.

🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR (la pregunta obligatoria del
repo): nada está falseado. Las funciones son puras y los schemas son los REALES —no hay doble de
repo ni de Supabase—, así que lo que se ejercita es exactamente el código que corre en producción.
El único riesgo de verde falso sería probar la normalización sobre un valor que ya está
normalizado; por eso cada caso entra con la grafía CRUDA que produjo el bug (`SENIOR` con el
espaciado del Excel) y no con la canónica.
"""
import pytest

from schemas.empleado import EmpleadoCreate, EmpleadoUpdate
from schemas.importacion_nomina_empleados import EmpleadoCreateNomina, EmpleadoUpdateNomina
from schemas.recategorizacion import RecategorizacionCreate, RecategorizacionUpdate
from services._nomina_parsers import VACIOS
from utils.legajo_reglas import (
    VACIOS_LEGAJO, horas_desde_turno, normalizar_categoria, normalizar_seniority,
)

_ALTA = {
    "nombre": "Ana", "apellido": "García", "email_corporativo": "ana@karstec.com",
    "area_id": "22222222-2222-2222-2222-222222222222",
    "empresa_id": "33333333-3333-3333-3333-333333333333",
    "roles": ["Analista"], "modalidad_trabajo": "presencial",
    "tipo_contrato": "efectivo", "fecha_ingreso": "2024-01-01",
}


class TestSeniority:
    @pytest.mark.parametrize("crudo, esperado", [
        ("SENIOR", "Senior"), ("senior", "Senior"), ("  Senior  ", "Senior"),
        ("SEMI SENIOR", "Semi Senior"), ("SEMI   SENIOR", "Semi Senior"),
        ("semi_senior", "Semi Senior"), ("semi-senior", "Semi Senior"),
        ("EXPERT", "Expert"), ("TRAINEE", "Trainee"), ("lider", "Lider"),
    ])
    def test_la_caja_y_el_espaciado_dejan_de_partir_una_categoria_en_dos(self, crudo, esperado):
        """El caso real: producción tenía `senior` (5, del formulario) y `SENIOR` (1, del import)
        como DOS categorías del reporte de distribución."""
        assert normalizar_seniority(crudo) == esperado

    @pytest.mark.parametrize("crudo", ["SENIOR", "senior", "Senior", "semi_senior", "SEMI SENIOR"])
    def test_EL_VALOR_GUARDADO_ES_LA_ETIQUETA_QUE_SE_MUESTRA(self, crudo):
        """🔴 LA DECISIÓN DEL BLOQUE 3, afirmada como propiedad y no como una lista de casos.

        Lo que fija: la salida es presentable tal cual — arranca en mayúscula y no tiene guiones
        bajos. Si mañana alguien vuelve a canonizar en minúscula "porque es más neutro", esto
        rojea, y el rojo dice que la pantalla necesitaría una SEGUNDA regla de presentación (en
        el front Y en el backend) sobre la misma columna.
        """
        salida = normalizar_seniority(crudo)
        assert salida and salida[0].isupper(), f"«{salida}» no es presentable tal cual"
        assert "_" not in salida, f"«{salida}» llegaría con guión bajo a la pantalla"

    def test_un_valor_NUEVO_se_ve_igual_que_los_conocidos(self):
        """La otra mitad de la decisión: un seniority que nadie usó antes no necesita que alguien
        lo agregue a ningún catálogo para verse bien. Es lo que descarta el mapa a mano."""
        assert normalizar_seniority("tech lead") == "Tech Lead"

    def test_un_acronimo_PIERDE_sus_mayusculas_y_esta_declarado(self):
        """⚠️ El límite conocido de la regla, anclado para que no se descubra en producción.
        Se acepta porque `seniority` es una PALABRA; el campo que sí es un código (`categoria`)
        va al revés justamente por esto. Restaurarlo exigiría la lista de excepciones que esta
        decisión evita."""
        assert normalizar_seniority("PM") == "Pm"

    @pytest.mark.parametrize("vacio", ["", "   ", "SIN DATOS", "no aplica", "-", "N/A", None])
    def test_lo_que_significa_sin_dato_se_guarda_como_NULL_y_no_como_categoria(self, vacio):
        assert normalizar_seniority(vacio) is None


class TestCategoria:
    @pytest.mark.parametrize("crudo, esperado", [
        ("c6", "C6"), ("C6", "C6"), ("  c 6 ", "C 6"), ("categoria a", "CATEGORIA A"),
    ])
    def test_es_un_codigo_asi_que_normaliza_a_MAYUSCULA(self, crudo, esperado):
        assert normalizar_categoria(crudo) == esperado

    @pytest.mark.parametrize("numero", ["3", "10", "07"])
    def test_ACEPTA_NUMEROS_PELADOS_y_los_deja_intactos(self, numero):
        """🔴 BLOQUE 4. La categoría es el nivel dentro del seniority y producción ya tiene un
        `3` cargado. Cualquier validación que exigiera una letra inicial expulsaría ese valor
        real; `upper()` no toca los dígitos."""
        assert normalizar_categoria(numero) == numero


class TestHorasDesdeTurno:
    @pytest.mark.parametrize("turno, horas", [
        ("8 A 17 HS.", 8),        # 28 de las 31 filas de producción, y las 10 con horas dicen 8
        ("8 A 14 HS.", 5),
        ("10 A 18 HS.", 7),
        ("7.30 A 16.30 HS.", 8),
        ("8 a 17 hs", 8),         # tipeado a mano en el formulario
        ("9:00 A 18:00", 8),
        ("8-17", 8),
        ("22 A 7", 8),            # nocturno: cruza la medianoche
    ])
    def test_los_formatos_reales_de_la_columna_Carga_Horaria(self, turno, horas):
        assert horas_desde_turno(turno) == horas

    @pytest.mark.parametrize("turno", [
        None, "", "SIN DATOS", "jornada completa", "8 A 8", "8 A 9",
        "8.15 A 17.00", "8 A 17 A 20", "99 A 100",
    ])
    def test_lo_que_no_se_puede_leer_devuelve_None_y_NO_un_numero_inventado(self, turno):
        """🔴 `"8 A 9"` está acá a propósito: una hora de ventana menos una de almuerzo da CERO,
        y escribir 0 en `horas_contrato` afirmaría una jornada de cero horas. `"8.15 A 17.00"`
        también: 7,75 horas no es un entero y la columna es `integer` — redondear en silencio
        sería inventar el cuarto de hora que falta."""
        assert horas_desde_turno(turno) is None


class TestElMixinAlcanzaALosCuatroSchemas:
    """🔴 EL PUNTO ENTERO DE QUE LA REGLA VIVA EN UN MIXIN. `empleados.seniority` tiene TRES
    escritores (formulario, import de nómina, recategorización) y los tres pasan por alguno de
    estos cuatro schemas. Una regla escrita en un service alcanzaría a uno solo, y el otro
    seguiría escribiendo la grafía que la regla venía a evitar."""

    def test_el_alta_manual_normaliza(self):
        e = EmpleadoCreate(**_ALTA, seniority="SENIOR", categoria="c6")
        assert (e.seniority, e.categoria) == ("Senior", "C6")

    def test_la_edicion_normaliza(self):
        e = EmpleadoUpdate(seniority="  SENIOR ", categoria=" c6 ")
        assert (e.seniority, e.categoria) == ("Senior", "C6")

    def test_el_alta_del_import_de_nomina_normaliza(self):
        e = EmpleadoCreateNomina(**_ALTA, seniority="EXPERT", categoria="c3")
        assert (e.seniority, e.categoria) == ("Expert", "C3")

    def test_el_update_del_import_de_nomina_normaliza(self):
        e = EmpleadoUpdateNomina(seniority="TRAINEE", categoria="c1")
        assert (e.seniority, e.categoria) == ("Trainee", "C1")


class TestLaRecategorizacionEscribeElMismoVocabularioEnSUS_DOS_LADOS:
    """🔴 EL BUG QUE INTRODUJO LA PROPIA NORMALIZACIÓN, y por eso este bloque existe aparte.

    La recategorización escribe en DOS lados: la FILA DEL HISTORIAL (`seniority_nueva`) y el
    LEGAJO del empleado (por `EmpleadoUpdate`). El segundo pasa por `LegajoNormalizado`; el
    primero no lo hacía, porque su campo se llama distinto y un `field_validator` se ata al
    nombre. Resultado: tipear "SENIOR" dejaba al empleado en `Senior` y a la fila diciendo
    **`Senior → SENIOR`** — un cambio que no ocurrió, en la pantalla cuyo único trabajo es contar
    qué cambió. `seniority_anterior` sale de `empleado.seniority`, o sea del lado ya normalizado.

    ⚠️ Qué tendría que ser distinto para que estos tests puedan fallar: nada está falseado, son
    los schemas reales. Y entran con la grafía CRUDA que produce el bug ("SENIOR", no "Senior"):
    con el valor ya canónico pasarían con el mixin borrado.
    """

    def test_el_alta_de_la_fila_de_historial_normaliza(self):
        r = RecategorizacionCreate(
            empleado_id="11111111-1111-1111-1111-111111111111",
            seniority_nueva="SENIOR", categoria_nueva="c6", motivo="ascenso")
        assert (r.seniority_nueva, r.categoria_nueva) == ("Senior", "C6")

    def test_la_edicion_de_la_fila_de_historial_normaliza(self):
        assert RecategorizacionUpdate(seniority_nueva="semi_senior").seniority_nueva == "Semi Senior"

    def test_las_dos_puntas_de_la_MISMA_fila_coinciden(self):
        """El test que importa: lo que se guarda en el empleado y lo que se guarda en el
        historial tienen que ser el MISMO string, o la fila afirma un cambio inexistente."""
        en_el_legajo = EmpleadoUpdate(seniority="SENIOR").seniority
        en_el_historial = RecategorizacionCreate(
            empleado_id="11111111-1111-1111-1111-111111111111",
            seniority_nueva="SENIOR", motivo="x").seniority_nueva
        assert en_el_legajo == en_el_historial == "Senior"


class TestLaDerivacionDeHorasNoPisaLoCargadoAMano:
    def test_sin_horas_en_el_payload_se_derivan_del_turno(self):
        """El caso del import de nómina: manda `turno` (columna "Carga Horaria") y NUNCA mandó
        `horas_contrato`. Era 0 de 31 filas importadas."""
        assert EmpleadoCreate(**_ALTA, turno="8 A 17 HS.").horas_contrato == 8

    def test_con_horas_en_el_payload_MANDA_EL_PAYLOAD(self):
        """🔴 La precedencia ES la feature: quien escribe un número lo escribió por algo (una
        jornada reducida acordada). Una derivación que lo pise vuelve el campo no-editable."""
        assert EmpleadoCreate(**_ALTA, turno="8 A 17 HS.", horas_contrato=6).horas_contrato == 6

    def test_sin_turno_no_se_inventa_nada(self):
        assert EmpleadoCreate(**_ALTA).horas_contrato is None

    def test_un_turno_ilegible_deja_las_horas_vacias(self):
        assert EmpleadoCreate(**_ALTA, turno="jornada completa").horas_contrato is None

    def test_un_update_que_no_habla_del_turno_no_toca_las_horas(self):
        """Un patch de una sola clave no puede tener efectos sobre columnas que no nombra."""
        assert EmpleadoUpdate(nombre="Ana").horas_contrato is None


def test_la_lista_de_vacios_de_utils_es_espejo_de_la_del_parser_de_nomina():
    """🔴 `utils/legajo_reglas.VACIOS_LEGAJO` REDECLARA `services/_nomina_parsers.VACIOS` en vez
    de importarla, para no invertir la capa (utils no puede depender de services). Dos copias que
    se separen darían dos definiciones de "no hay dato" sobre la misma columna: este test es lo
    único que impide que se separen."""
    assert VACIOS_LEGAJO == VACIOS
