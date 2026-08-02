"""
Tests del parser de los dos CSV de evaluaciones (fase 2) — archivos sintéticos, sin red.

Cubre: decode por BOM (incluido UTF-16), separador ';', números con espacios/coma, celdas
vacías = no aplica, normalización de TIPO EVALUACION (+ desconocido = problema de fila),
derivación de perfil, cruce A+B (nota_final null sin error, anomalía inversa), identidad
acento/espacio-insensible, dato crudo basura en SECTOR, y encoding no determinable.
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

from services import _evaluacion_import_transforms as tx
from services.evaluacion_import_service import parsear


# ── Helpers de construcción de archivos ──────────────────────────────────────

def _archivo(headers: list[str], filas: list[dict], encoding: str = "utf-8") -> bytes:
    lineas = [";".join(headers)] + [";".join(str(f.get(h, "")) for h in headers) for f in filas]
    return "\r\n".join(lineas).encode(encoding)


def _notas(filas: list[dict], encoding: str = "utf-8") -> bytes:
    return _archivo(tx.HEADERS_NOTAS, filas, encoding)


def _desglose(filas: list[dict], encoding: str = "utf-8") -> bytes:
    return _archivo(tx.HEADERS_DESGLOSE, filas, encoding)


def _ev(apellido: str, nombre: str, tipo: str, **comps) -> dict:
    return {"APELLIDO EVALUADO": apellido, "NOMBRE EVALUADO": nombre, "TIPO EVALUACION": tipo, **comps}


# ── decodificar ──────────────────────────────────────────────────────────────

def test_decodifica_utf16_con_bom():
    assert tx.decodificar("café ñandú".encode("utf-16")) == "café ñandú"


def test_decodifica_utf8_bom_y_plano():
    assert tx.decodificar("hola".encode("utf-8-sig")) == "hola"
    assert tx.decodificar("hola".encode("utf-8")) == "hola"


def test_decodifica_encoding_indeterminable_falla():
    with pytest.raises(ValueError):
        tx.decodificar(b"\xf1\xe9")  # latin-1 'ñé', sin BOM, inválido como UTF-8


def test_decodifica_utf16le_sin_bom():
    # El bug real: UTF-16LE SIN BOM. Bytes 'O\x00R\x00G\x00...' — no lo agarra la detección por BOM.
    crudo = "ORGANISMO;NOTA FINAL".encode("utf-16-le")
    assert crudo[:2] == b"\x4f\x00" and crudo[:2] not in (b"\xff\xfe", b"\xfe\xff")  # sin BOM
    assert tx.decodificar(crudo) == "ORGANISMO;NOTA FINAL"


def test_detecta_utf16_le_be_y_no_utf8():
    # La heurística se mudó al lector compartido (`_import_csv`) al unificar los dos
    # decodificadores: es la MISMA función, solo cambió de módulo. Las aserciones no se tocaron.
    from services._import_encoding import _detectar_utf16_sin_bom as _detectar

    assert _detectar("ORGANISMO".encode("utf-16-le")) == "utf-16-le"
    assert _detectar("ORGANISMO".encode("utf-16-be")) == "utf-16-be"
    assert _detectar("ORGANISMO;GERENCIA".encode("utf-8")) is None


# ── helpers puros ────────────────────────────────────────────────────────────

def test_clave_identidad_ignora_acentos_y_espacios():
    assert tx.clave_identidad("  Peña ", "José  Luis") == tx.clave_identidad("PENA", "Jose Luis")


def test_parse_nota_espacios_coma_vacio_e_invalido():
    assert tx.parse_nota("  8.89") == 8.89
    assert tx.parse_nota(" 10,00") == 10.0
    assert tx.parse_nota("") is None
    assert tx.parse_nota(None) is None
    with pytest.raises(ValueError):
        tx.parse_nota("N/A")


def test_normalizar_tipo_mapea_y_rechaza():
    assert tx.normalizar_tipo("AUTOEVALUACION LIDER") == "AUTOEVALUACION_LIDER"
    assert tx.normalizar_tipo(" superior  inmediato ") == "SUPERIOR_INMEDIATO"
    with pytest.raises(ValueError):
        tx.normalizar_tipo("JEFE DIRECTO")


# ── parseo integral ──────────────────────────────────────────────────────────

def test_utf16le_sin_bom_notas_se_cruza_con_desglose_utf8():
    # Reproduce el caso de producción: notas en UTF-16LE sin BOM, desglose en UTF-8.
    notas = _notas([{"APELLIDO EVALUADO": "GODOY", "NOMBRE EVALUADO": "SOL", "NOTA FINAL": " 8.50"}], encoding="utf-16-le")
    desglose = _desglose([_ev("GODOY", "SOL", "AUTOEVALUACION", AUTOGESTION="9.00")])
    r = parsear(notas, desglose)
    assert r.problemas == [] and r.anomalias == []  # sin problema de cabecera, sin anomalía de 0 filas
    assert r.evaluados[0].nota_final == 8.5


def test_notas_cero_filas_es_anomalia():
    # Notas que no aporta filas (acá: cabecera equivocada) NO puede pasar como "todos sin nota".
    notas = "\r\n".join(["COLUMNA_RARA;OTRA", "x;y"]).encode("utf-8")
    r = parsear(notas, _desglose([_ev("GODOY", "SOL", "AUTOEVALUACION", AUTOGESTION="9")]))
    assert any("no aportó ninguna nota" in a for a in r.anomalias)
    assert r.evaluados[0].nota_final is None


def test_utf16_notas_se_cruza_con_desglose_utf8():
    notas = _notas([{"APELLIDO EVALUADO": "GODOY", "NOMBRE EVALUADO": "SOL", "NOTA FINAL": " 8.50"}], encoding="utf-16")
    desglose = _desglose([_ev("GODOY", "SOL", "AUTOEVALUACION", AUTOGESTION=" 9.00", EMPATIA="7,5")])
    r = parsear(notas, desglose)
    assert r.problemas == [] and r.anomalias == []
    assert len(r.evaluados) == 1
    ev = r.evaluados[0]
    assert ev.nota_final == 8.5 and ev.perfil == "general"
    assert {(x.competencia, x.nota) for x in ev.resultados} == {("AUTOGESTION", 9.0), ("EMPATIA", 7.5)}


def _nota(apellido, nombre, nota="7"):
    return {"APELLIDO EVALUADO": apellido, "NOMBRE EVALUADO": nombre, "NOTA FINAL": nota}


def test_perfil_lider_por_competencia_exclusiva_y_orden():
    # COMUNICACION es competencia exclusiva de líder (orden 15); AUTOGESTION no (orden 1).
    desglose = _desglose([
        _ev("VACAS", "AGUSTIN", "AUTOEVALUACION LIDER", AUTOGESTION="9", COMUNICACION="8"),
    ])
    r = parsear(_notas([_nota("VACAS", "AGUSTIN")]), desglose)
    ev = r.evaluados[0]
    assert ev.perfil == "lider" and r.anomalias == []  # tipo líder corrobora la competencia
    ordenes = {x.competencia: x.orden for x in ev.resultados}
    assert ordenes["AUTOGESTION"] == 1 and ordenes["COMUNICACION"] == 15


def test_perfil_general_sin_competencias_de_lider():
    desglose = _desglose([_ev("AMADO", "ANDREA", "AUTOEVALUACION", AUTOGESTION="8", EMPATIA="7")])
    r = parsear(_notas([_nota("AMADO", "ANDREA")]), desglose)
    assert r.evaluados[0].perfil == "general" and r.anomalias == []


def test_anomalia_perfil_competencia_de_lider_sin_tipo_de_lider():
    # Competencia de líder (PLANIFICACION) pero solo tipo PAR -> perfil lider + anomalía, no se corrige.
    desglose = _desglose([_ev("QUAGLIA", "CLARA", "PAR", PLANIFICACION="9")])
    r = parsear(_notas([_nota("QUAGLIA", "CLARA")]), desglose)
    assert r.evaluados[0].perfil == "lider"
    assert len(r.anomalias) == 1 and "ningún tipo de evaluador de líder" in r.anomalias[0]


def test_lider_sin_nota_final_no_es_error():
    # El evaluado no está en notas → nota_final None; eso NO es error ni anomalía a nivel evaluado.
    desglose = _desglose([_ev("BUSTAMANTE", "DARIO", "AUTOEVALUACION LIDER", ORGANIZACION="7")])
    r = parsear(_notas([_nota("OTRO", "PERSONA")]), desglose)
    assert r.problemas == []
    assert not any("líder" in a for a in r.anomalias)  # sin anomalía de perfil
    assert r.evaluados[0].nota_final is None and r.evaluados[0].perfil == "lider"


def test_anomalia_en_notas_sin_desglose():
    notas = _notas([{"APELLIDO EVALUADO": "FANTASMA", "NOMBRE EVALUADO": "JUAN", "NOTA FINAL": "6"}])
    r = parsear(notas, _desglose([]))
    assert r.evaluados == [] and r.problemas == []
    assert len(r.anomalias) == 1 and "FANTASMA JUAN" in r.anomalias[0]


def test_tipo_desconocido_es_problema_de_fila_no_aborta():
    desglose = _desglose([
        _ev("AMADO", "ANDREA", "PAR", AUTOGESTION="8"),
        _ev("AMADO", "ANDREA", "JEFE", AUTOGESTION="9"),  # tipo inválido -> fila 3
    ])
    r = parsear(_notas([]), desglose)
    assert len(r.evaluados) == 1  # la fila buena igual creó al evaluado
    assert len(r.problemas) == 1
    assert r.problemas[0].archivo == "desglose" and r.problemas[0].fila == 3


def test_celda_vacia_no_emite_resultado():
    desglose = _desglose([_ev("BAEZ", "NOELIA", "AUTOEVALUACION", AUTOGESTION="8", EMPATIA="")])
    r = parsear(_notas([]), desglose)
    comps = {x.competencia for x in r.evaluados[0].resultados}
    assert comps == {"AUTOGESTION"}  # EMPATIA vacía = no aplica


def test_sector_con_basura_se_conserva_crudo():
    desglose = _desglose([_ev("QUAGLIA", "CLARA", "AUTOEVALUACION", AUTOGESTION="8")
                          | {"SECTOR": "RECUPERO DEL GASTO HOSPITALARIO"}])
    r = parsear(_notas([]), desglose)
    assert r.evaluados[0].sector == "RECUPERO DEL GASTO HOSPITALARIO"


def test_nota_final_invalida_es_problema():
    notas = _notas([{"APELLIDO EVALUADO": "WHELAN", "NOMBRE EVALUADO": "NATALIA", "NOTA FINAL": "excelente"}])
    r = parsear(notas, _desglose([]))
    assert len(r.problemas) == 1 and r.problemas[0].archivo == "notas_finales" and r.problemas[0].fila == 2


def test_encoding_indeterminable_es_problema_de_archivo():
    basura = b"\xf1\xe9\xff;\xf0"  # sin BOM, inválido UTF-8
    r = parsear(basura, _desglose([_ev("KALAPIS", "ALEJO", "PAR", AUTOGESTION="7")]))
    assert any(p.archivo == "notas_finales" and p.fila == 0 for p in r.problemas)
    assert len(r.evaluados) == 1  # el desglose (válido) igual se parseó


def test_headers_faltantes_es_problema_de_archivo():
    malo = "\r\n".join(["ORGANISMO;NOTA FINAL", "x;5"]).encode("utf-8")
    r = parsear(malo, _desglose([]))
    assert any(p.archivo == "notas_finales" and p.fila == 0 and "Faltan columnas" in p.motivo for p in r.problemas)
