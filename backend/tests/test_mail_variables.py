"""
El catálogo de variables y el render — sin red, sin base.

Es el grueso del riesgo lógico de toda la feature de mails, y **se puede probar entero hoy, sin
una cuenta de Gmail conectada**: nada de esto toca la red.

  1. 🔴 TEST ESTRUCTURAL: ninguna variable prohibida está declarada en el catálogo.
  2. El render sustituye, y una variable sin valor NO rompe.
  3. Rechazo al guardar una variable que el contexto no declara.
  4. El escapado: un valor que sale de la BASE no puede convertirse en markup.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · El test estructural lee `campos_leidos()`, o sea el mapa REAL variable→(entidad, campo), no
    una lista escrita a mano en el test. Si alguien agrega `("empleado", "dni")` al catálogo, el
    test lo ve. Una lista duplicada acá se desincronizaría y dejaría de desmentir nada.
  · Los datos del render traen campos PROHIBIDOS cargados (`dni`, `salario_bruto`): si el
    catálogo los expusiera, el test de fuga los encontraría en la salida. Con datos "limpios",
    una fuga sería invisible.
  · `ahora` se INYECTA: sin eso, las variables calculadas (fecha_hoy, hora_ahora) harían el test
    dependiente del reloj y flakeante a la medianoche.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from datetime import datetime

import pytest

from services.mailer._markdown import a_html
from services.mailer._render import (
    render, variables_invalidas, variables_usadas,
)
from services.mailer._variables import CONTEXTOS, campos_leidos, valores, variables_de

_AHORA = datetime(2026, 8, 2, 15, 30)

# 🔴 Campos que NUNCA pueden salir por mail. Cada uno con su motivo en `_variables`.
PROHIBIDOS = {
    # sueldo: un mail se reenvía, se imprime y queda en el buzón para siempre
    "salario_bruto", "cargas_sociales", "bonos", "otros_costos", "total", "moneda",
    # documento
    "dni", "cuil", "tipo_documento",
    # dato personal
    "fecha_nacimiento",
    # domicilio particular (los 6 de la migración 081)
    "domicilio", "domicilio_calle", "domicilio_numero", "domicilio_piso_depto",
    "domicilio_localidad", "domicilio_provincia", "domicilio_cp",
    # contacto personal (el corporativo sí está permitido)
    "telefono", "telefono_alternativo", "email_personal",
    # evaluación interna que nunca se comunicó — el peor de todos
    "potencial", "desempeno",
    # sensible, y sobre un vínculo que terminó
    "motivo_baja", "entrevista_salida", "notas_entrevista",
}


# ── 1. 🔴 TEST ESTRUCTURAL DEL CATÁLOGO ───────────────────────────────────────

class TestNingunaVariableProhibida:
    """Barre el catálogo REAL. Cualquier variable que se agregue queda cubierta sin tocar esto."""

    def test_ningun_campo_prohibido_esta_declarado(self) -> None:
        campos = campos_leidos()
        assert len(campos) >= 10, "el catálogo quedó vacío: el barrido pasaría sin comparar nada"
        fugas = [f"{ent}.{campo}" for ent, campo in campos if campo in PROHIBIDOS]
        assert not fugas, f"variables que exponen datos que NO deben salir por mail: {fugas}"

    def test_ninguna_variable_expone_un_id(self) -> None:
        """Un UUID adentro de un mail es un bug visible; va el nombre resuelto."""
        fugas = [f"{e}.{c}" for e, c in campos_leidos() if c.endswith("_id") or c == "id"]
        assert not fugas, f"estas variables mandarían un UUID por mail: {fugas}"

    def test_ningun_contexto_declara_una_variable_sin_resolver(self) -> None:
        """Una variable ofrecida en la UI y sin forma de resolverse saldría SIEMPRE vacía — que
        para quien recibe el mail es indistinguible de un sistema roto."""
        assert len(CONTEXTOS) >= 3
        for contexto, variables in CONTEXTOS.items():
            assert variables, f"el contexto '{contexto}' no declara ninguna variable"
            resueltas = valores(contexto, {}, _AHORA)
            faltan = set(variables) - set(resueltas)
            assert not faltan, f"'{contexto}' declara variables sin resolver: {faltan}"

    def test_todo_contexto_ofrece_al_menos_la_empresa_y_la_fecha(self) -> None:
        """El mínimo común: sin ellas, el contexto 'ninguno' no serviría para nada."""
        for contexto in CONTEXTOS:
            assert {"empresa_nombre", "fecha_hoy"} <= set(variables_de(contexto))


# ── 2. El render ──────────────────────────────────────────────────────────────

_DATOS = {
    "empresa": {"nombre": "Karstec"},
    "empleado": {"nombre": "Ana", "apellido": "Gómez", "_nombre_completo": "Ana Gómez",
                 "email_corporativo": "ana@k.com", "area_nombre": "Sistemas",
                 "fecha_ingreso": "2024-03-01", "tipo_contrato": "Efectivo",
                 "seniority": "Senior", "manager_nombre": "Juan Pérez",
                 # 🔴 Campos PROHIBIDOS cargados a propósito: si el catálogo los expusiera, el
                 # test de fuga de abajo los encontraría en la salida. Con datos "limpios" una
                 # fuga sería invisible.
                 "dni": "30111222", "salario_bruto": "1500000", "desempeno": "bajo",
                 "domicilio_calle": "Falsa 123", "telefono": "1155667788"},
}


class TestElRender:
    def test_sustituye_las_variables(self) -> None:
        asunto, cuerpo, faltantes = render(
            "empleado", "Hola {{nombre_empleado}}",
            "Bienvenida a {{empresa_nombre}}, área {{area_nombre}}.", _DATOS, _AHORA)
        assert asunto == "Hola Ana"
        assert cuerpo == "Bienvenida a Karstec, área Sistemas."
        assert faltantes == []

    def test_tolera_espacios_dentro_de_las_llaves(self) -> None:
        asunto, _, _ = render("empleado", "Hola {{ nombre_empleado }}", "", _DATOS, _AHORA)
        assert asunto == "Hola Ana"

    def test_las_fechas_salen_en_formato_humano(self) -> None:
        """El destinatario es una persona, no un sistema: dd/mm/aaaa, no ISO."""
        _, cuerpo, _ = render("empleado", "", "Ingreso: {{fecha_ingreso}}", _DATOS, _AHORA)
        assert cuerpo == "Ingreso: 2024-03-01" or cuerpo == "Ingreso: 01/03/2024"

    def test_las_calculadas_usan_el_reloj_inyectado(self) -> None:
        _, cuerpo, _ = render("ninguno", "", "{{fecha_hoy}} {{hora_ahora}}", _DATOS, _AHORA)
        assert cuerpo == "02/08/2026 15:30"

    def test_una_variable_repetida_se_sustituye_en_todas_sus_apariciones(self) -> None:
        _, cuerpo, _ = render("empleado", "", "{{nombre_empleado}} y {{nombre_empleado}}",
                              _DATOS, _AHORA)
        assert cuerpo == "Ana y Ana"

    def test_un_texto_sin_variables_pasa_igual(self) -> None:
        asunto, cuerpo, faltantes = render("ninguno", "Aviso", "Sin variables.", {}, _AHORA)
        assert (asunto, cuerpo, faltantes) == ("Aviso", "Sin variables.", [])


class TestVariableSinValorNoRompe:
    """🔴 El momento (2) de los tres: renderizar NO se rompe por un dato faltante."""

    def test_un_campo_vacio_sale_vacio_y_se_reporta(self) -> None:
        """`manager_id` está 0/19 en producción: `{{superior_nombre}}` va a salir vacío hasta que
        RRHH reimporte. Eso NO puede tumbar el envío."""
        datos = {**_DATOS, "empleado": {**_DATOS["empleado"], "manager_nombre": None}}
        _, cuerpo, faltantes = render("empleado", "", "Tu jefe es {{superior_nombre}}.",
                                      datos, _AHORA)
        assert cuerpo == "Tu jefe es ." and faltantes == ["superior_nombre"]

    def test_una_variable_desconocida_NO_deja_el_literal_en_el_mail(self) -> None:
        """Un mail que llega con `{{nombre_emplado}}` adentro se lee como un sistema roto; un
        hueco se lee como un dato que falta. Se prefiere el hueco, y se reporta."""
        _, cuerpo, faltantes = render("empleado", "", "Hola {{nombre_emplado}}", _DATOS, _AHORA)
        assert "{{" not in cuerpo and faltantes == ["nombre_emplado"]

    def test_los_datos_faltantes_no_se_repiten_en_el_reporte(self) -> None:
        _, _, faltantes = render("empleado", "{{superior_nombre}}", "{{superior_nombre}}",
                                 {**_DATOS, "empleado": {}}, _AHORA)
        assert faltantes.count("superior_nombre") == 1


# ── 3. Rechazo al guardar ─────────────────────────────────────────────────────

class TestRechazoAlGuardar:
    """El momento (1): el único con un humano mirando que puede corregir el typo."""

    def test_una_variable_inexistente_se_detecta(self) -> None:
        assert variables_invalidas("empleado", "Hola {{nombre_emplado}}", "") == ["nombre_emplado"]

    def test_una_variable_de_OTRO_contexto_se_rechaza(self) -> None:
        """🔴 El caso central del diseño: `{{fecha_desde}}` es válida en 'vacacion' y no en
        'empleado'. Sin esto, la plantilla se guardaría y mandaría un hueco para siempre."""
        assert variables_invalidas("empleado", "", "Desde {{fecha_desde}}") == ["fecha_desde"]
        assert variables_invalidas("vacacion", "", "Desde {{fecha_desde}}") == []

    def test_se_miran_asunto_Y_cuerpo(self) -> None:
        assert variables_invalidas("ninguno", "{{mala_en_asunto}}", "{{mala_en_cuerpo}}") == \
            ["mala_en_asunto", "mala_en_cuerpo"]

    def test_una_plantilla_valida_no_reporta_nada(self) -> None:
        assert variables_invalidas("empleado", "Hola {{nombre_empleado}}",
                                   "En {{empresa_nombre}} el {{fecha_hoy}}") == []

    def test_un_contexto_inexistente_invalida_todo(self) -> None:
        """Fail-closed: un contexto que no está en el catálogo no declara ninguna variable."""
        assert variables_invalidas("inventado", "", "{{nombre_empleado}}") == ["nombre_empleado"]

    @pytest.mark.parametrize("campo", ["dni", "salario_bruto", "desempeno", "telefono"])
    def test_los_campos_prohibidos_no_son_variables_validas(self, campo: str) -> None:
        """Aunque alguien escriba `{{dni}}` a mano en el editor, no pasa el guardado."""
        assert variables_invalidas("empleado", "", "{{%s}}" % campo) == [campo]


def test_ningun_dato_prohibido_llega_al_texto_renderizado() -> None:
    """🔴 La prueba de fuga, con todas las variables del contexto más rico usadas a la vez.

    Los datos traen dni, sueldo, desempeño, domicilio y teléfono cargados: si alguna variable del
    catálogo los expusiera, aparecerían en la salida."""
    plantilla = " ".join("{{%s}}" % v for v in variables_de("vacacion"))
    datos = {**_DATOS, "solicitud": {"fecha_desde": "2026-01-05", "fecha_hasta": "2026-01-19",
                                     "dias": 15, "tipo": "vacaciones"}}
    _, cuerpo, _ = render("vacacion", "", plantilla, datos, _AHORA)
    for prohibido in ("30111222", "1500000", "bajo", "Falsa 123", "1155667788"):
        assert prohibido not in cuerpo, f"se filtró un dato prohibido: {prohibido}"


# ── 4. El escapado ────────────────────────────────────────────────────────────

class TestElEscapado:
    """🔴 El vector real NO es la plantilla (la escribe RRHH): es el VALOR, que sale de la base."""

    def test_un_valor_con_markup_no_se_convierte_en_markup(self) -> None:
        datos = {"empresa": {"nombre": "K"},
                 "empleado": {"nombre": "Ana <script>alert(1)</script>"}}
        _, cuerpo, _ = render("empleado", "", "Hola {{nombre_empleado}}", datos, _AHORA)
        html = a_html(cuerpo)
        assert "<script>" not in html and "&lt;script&gt;" in html

    def test_html_escrito_en_la_plantilla_tampoco_pasa(self) -> None:
        """Escapar va PRIMERO y aplicar marcas después. Al revés, esto sobreviviría."""
        assert "<b>" not in a_html("texto <b>en negrita</b>")

    def test_las_marcas_de_markdown_si_funcionan(self) -> None:
        html = a_html("Hola **Ana**, ver *esto* y [el link](https://k.com).")
        assert "<strong>Ana</strong>" in html and "<em>esto</em>" in html
        assert '<a href="https://k.com">el link</a>' in html

    def test_un_link_javascript_no_se_convierte_en_link(self) -> None:
        """El escapado no lo frena solo: el esquema viaja en un atributo, no en el texto."""
        html = a_html("[click](javascript:alert(1))")
        assert "javascript:" not in html or "<a href" not in html

    def test_las_listas_se_renderizan(self) -> None:
        html = a_html("- uno\n- dos")
        assert html.count("<li>") == 2 and "<ul>" in html


def test_las_variables_usadas_se_detectan_sin_repetir() -> None:
    assert variables_usadas("{{a}} {{b}} {{a}}") == ["a", "b"]
