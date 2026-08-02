"""
Test del payload de auditoría del import de nómina de empleados: que registro_id sea un uuid
VÁLIDO (id de evento generado, no el literal "lote_nomina" ni None). Antes, el literal rompía
el cast text→uuid en la columna registro_id (uuid NOT NULL) y AuditService tragaba el error →
el evento se perdía en silencio. Sin red: se testea la función pura del payload.
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

from uuid import UUID

from services._audit_payloads_rrhh import payload_importacion_nomina


def test_registro_id_es_uuid_valido_no_literal():
    p = payload_importacion_nomina("nomina.csv", 3, 2, 1, 0, "u1")
    assert p["registro_id"] is not None
    assert p["registro_id"] != "lote_nomina"       # el literal viejo rompía el insert
    UUID(p["registro_id"])                          # castea a uuid sin levantar = válido
    # el resto del payload queda igual
    assert p["entidad"] == "empleado" and p["evento"] == "importacion_nomina"
    assert p["empresa_id"] is None
    # `parcial` va SIEMPRE, no solo en el corte: un import completo lo trae en False. Así quien
    # lee un evento viejo no tiene que adivinar si el campo faltaba o el import fue completo.
    # La comparación es del dict ENTERO, no de claves sueltas, y se mantiene así a propósito: es
    # lo que hace que una clave agregada sin querer al payload de auditoría rompa el test en vez
    # de colarse. (Detectó exactamente eso cuando se sumaron los `superiores_*`.)
    # Los dos `superiores_*` van en 0 cuando no se pasan: un import sin superiores que resolver
    # emite el evento igual, con los contadores en cero, no con las claves ausentes.
    assert p["datos_nuevos"] == {
        "archivo": "nomina.csv", "creados": 3, "actualizados": 2,
        "con_faltantes": 1, "no_cargados": 0, "parcial": False,
        "superiores_resueltos": 0, "superiores_pendientes": 0,
    }


def test_registro_id_es_id_de_evento_distinto_por_llamada():
    # id DE EVENTO (uuid4 generado), no de recurso: cada import genera su propio uuid.
    a = payload_importacion_nomina("a.csv", 1, 0, 0, 0, "u1")
    b = payload_importacion_nomina("b.csv", 1, 0, 0, 0, "u1")
    assert a["registro_id"] != b["registro_id"]
