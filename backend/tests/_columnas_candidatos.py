"""
Inventario declarativo de las columnas de `candidatos`: qué se expone, qué se renombra y qué
NO viaja al front, con la razón de cada una.

Helper, no test. Lo consume `tests/test_columnas_candidatos.py`, donde está el barrido y el
encabezado que explica por qué hizo falta. Molde del corte: `_barrido_escrituras_estado.py`
separándose de `_barrido_estado.py`.

🔴 EL CORTE CAE DONDE EL ARCHIVO CRECE. `_NO_EXPUESTAS` suma una entrada por cada columna nueva
que se decida no publicar, para siempre; los seis tests del otro archivo son estables. Juntos
pasaban de 200 líneas y el próximo agregado los volvía a pasar.

🔴 LA RAZÓN DE CADA COLUMNA ES EL CONTENIDO DE ESTE ARCHIVO, NO UN CAMPO A COMPLETAR. Sin el
porqué, la próxima persona borra una entrada porque "no se usa" y revive exactamente el bug que
el barrido existe para impedir: `candidatos.estado` estuvo doce meses del lado equivocado de la
distinción entre "se decidió no exponerla" y "se olvidaron", y nadie podía notarlo porque no
había un solo lugar donde esa diferencia estuviera escrita.
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

from typing import Dict, Set  # noqa: E402

from schemas.candidato import CandidatoResponse  # noqa: E402
from tests._postgrest_schema import cargar_schema  # noqa: E402

TABLA = "candidatos"

# Guardas contra el falso verde del barrido. Hoy son 30 columnas y 19 campos; los mínimos van
# holgados para que no sean ruido cada vez que alguien agrega o saca uno.
MINIMO_COLUMNAS = 25
MINIMO_CAMPOS = 15

# ── Columna de la tabla → campo del schema, cuando el nombre NO coincide ──────
# Es UN renombre y viene de lejos: la columna se llama `etapa` y el schema la publica como
# `etapa_pipeline`. No se "arregla" unificando los nombres — el front entero lee
# `etapa_pipeline` (`types/vacantes.ts`, `CandidatoCard.tsx`) y la columna la nombran el CHECK y
# las tres migraciones del pipeline. Se declara, que es lo que hace que el barrido no lo lea
# como una columna sin exponer.
RENOMBRADAS: Dict[str, str] = {"etapa": "etapa_pipeline"}

# ── Columnas que a propósito NO viajan al front, cada una con su razón ────────
NO_EXPUESTAS: Dict[str, str] = {
    "cv_texto":
        "entrada del clasificador, puede pesar 20 KB por fila y engordaría todos los listados "
        "sin que nadie lo mire en pantalla. Está escrito en schemas/candidato.py y hay un test "
        "en test_cv_texto que fija que NO esté.",
    "cv_sha256":
        "clave de idempotencia del import por mail (mig 098). Es maquinaria del dedup, no un "
        "dato del candidato: la pantalla no tiene nada que hacer con un hash.",
    "gmail_message_id":
        "ídem cv_sha256 — la otra mitad de la clave de idempotencia de la ingesta.",
    "updated_at":
        "metadato de fila que mantiene un trigger. Ningún response del repo lo publica; quién "
        "tocó qué y cuándo se lee en /auditoria, que es el registro que sí lo responde.",
    "cv_url":
        "columna LEGACY, anterior al bucket privado. El CV vivo se sirve por "
        "`cv_storage_path` + `GET /{id}/cv-url` (signed URL). Sigue en CandidatoCreate y no se "
        "borra acá: sacarla de la tabla es DDL y esta tanda no toca DDL.",
    "linkedin_url":
        "se declaró con la tabla y nunca se cargó ni se mostró. No se expone hasta que exista "
        "la decisión de producto de qué hace la pantalla con ella.",
    "fuente":
        "de dónde vino la postulación. Sin escritura hoy: la ingesta por mail no la setea. "
        "Exponerla mostraría una columna vacía para todos.",
    "notas":
        "texto libre de reclutamiento, sin UI que lo edite ni lo muestre.",
    "puntuacion":
        "puntuación MANUAL del entrevistador, distinta de `score_ia` (que sí se expone). Sin "
        "camino de escritura hoy.",
    "entrevistador_id":
        "quién entrevista. Cero referencias en repositories/, services/ y schemas/ "
        "(verificado el 18/8/2026): la columna existe y el módulo nunca la usó.",
    "fecha_postulacion":
        "tiene DEFAULT CURRENT_DATE y hoy es redundante con `created_at`, que es el que la "
        "pantalla ordena y muestra. Exponer las dos invita a que se separen.",
}


def columnas() -> Set[str]:
    """Las columnas reales de `candidatos`, del catálogo de reconstrucción (`db/schema.sql`)."""
    return cargar_schema().columnas[TABLA]


def campos() -> Set[str]:
    """Los campos que `CandidatoResponse` declara.

    Es la clase BASE a propósito: `CandidatoGrupoResponse` agrega `grupo_nombre` y
    `busqueda_activa`, que son derivados resueltos por el service y no columnas de la tabla.
    """
    return set(CandidatoResponse.model_fields)
