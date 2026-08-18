"""
El PADRÓN del puente candidato → empleado: qué candidatos y qué vacantes existen, en dos empresas.

Helper, no test. Lo consume `tests/test_candidato_contratar.py`.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 POR QUÉ EL PADRÓN ES TRABAJO PREVIO Y NO UN EXTRA
═══════════════════════════════════════════════════════════════════════════════════════════
Antes de esta tanda, **`etapa='oferta'` y `estado='contratado'` tenían CERO fixtures en los 162
archivos de test del repo**. No es una casualidad: `oferta` es la etapa terminal del pipeline y
`contratado` el estado que nadie escribía (la columna estuvo muerta hasta A4.1). Sin estas filas,
las cuatro guardas del puente **no tienen contra qué fallar**: un `_validar` que rechazara todo,
o que aceptara todo, daría exactamente el mismo verde.

⚠️ **NO SE COPIÓ DE `test_exports_limpieza.py` NI DE `test_paginacion_candidatos_evaluados.py`**,
que son los fixtures de candidato que ya existían. Los dos usan etapas que **el CHECK rechazaría**
(`"entrevista"` y `"nuevo"`, que no están en `postulado|assessment|entrevista_rrhh|
entrevista_tecnica|oferta`). Pasan porque `CandidatoResponse.etapa_pipeline` es `str` sin validar,
así que Pydantic los acepta y la base nunca los ve. Heredarlos habría metido en un test nuevo un
valor que producción no admite. Está anotado en `docs/DEUDA-TECNICA.md`.

Las etapas y estados de acá salen del CHECK de `db/schema.sql`, escritos como literales: si se
importaran del `Literal` del schema, el padrón afirmaría que el schema coincide consigo mismo.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 DOS EMPRESAS, Y LA BARRERA TIENE QUE PODER FALLAR
═══════════════════════════════════════════════════════════════════════════════════════════
`EMPRESA_A` y `EMPRESA_B` con un candidato en oferta cada una. Los repos falsos **honran
`empresa_id` y devuelven `None` cuando no coincide** — un fake que lo aceptara e ignorara daría
verde sin validar nada, que es el caso #1 de la regla transversal del repo.

Y el caso que sólo dos empresas pueden desmentir: en modo **consolidado** (`empresa_id=None`) el
header no restringe, así que el candidato de B ES alcanzable. Lo que tiene que seguir cerrado ahí
es que su vacante y su alta salgan con la empresa **del candidato** y no con la del header.

📄 **LOS FAKES viven en `tests/_contratar_fakes.py`** (qué responde cada colaborador, y por qué
los cuatro honran `empresa_id`) y **EL ARNÉS HTTP en `tests/_contratar_arnes.py`** (el app mínimo
con el router real y el cliente). Salieron de acá cuando este archivo llegó a 226/200 y después a
215/200, y el corte responde tres preguntas distintas: **qué filas existen** · **qué responde
cada colaborador** · **cómo se le pega al endpoint**. Sólo la primera crece con cada caso nuevo.
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

from datetime import date, datetime, timedelta, timezone  # noqa: E402
from typing import Optional  # noqa: E402
from uuid import NAMESPACE_DNS, uuid4, uuid5  # noqa: E402

from schemas.candidato import CandidatoResponse  # noqa: E402
from schemas.vacante import VacanteResponse  # noqa: E402

EMPRESA_A = str(uuid4())
EMPRESA_B = str(uuid4())
AREA_A = str(uuid4())
AREA_B = str(uuid4())
USUARIO = str(uuid4())

AHORA = datetime.now(timezone.utc)
HOY = date.today()
MANANA = HOY + timedelta(days=1)
AYER = HOY - timedelta(days=1)

# Literales del CHECK `candidatos_etapa_check` y `candidatos_estado_check`. Escritos a mano y NO
# importados del schema: ver el encabezado.
ETAPA_OFERTA = "oferta"
ETAPA_TECNICA = "entrevista_tecnica"
ESTADO_ACTIVO = "activo"
ESTADO_CONTRATADO = "contratado"

# ids del padrón. 🔴 SON UUID DE VERDAD Y TIENEN QUE SERLO: el endpoint declara `id: UUID`, así
# que un id legible tipo "c-oferta-a" no llega nunca al service — FastAPI lo corta con un 422 en
# la frontera y TODOS los tests de guardas pasarían por el motivo equivocado (rechazo por forma
# del id, no por la guarda). Pasó al escribir este padrón: 20 de 26 tests en 422.
#
# Se derivan del nombre legible con `uuid5`, no con `uuid4`: son deterministas y **reversibles**
# —dado un UUID de un mensaje de fallo se puede recalcular cuál es— así que el nombre parlante no
# se pierde. `NOMBRE_DE(uuid)` lo resuelve para los mensajes de aserción.
_SEMILLAS = {
    "c-oferta-a": "el camino feliz",
    "c-oferta-b": "mismo caso en la OTRA empresa: la barrera puede fallar",
    "c-sin-vacante": "huérfano (vacante borrada → FK SET NULL, migración 071)",
    "c-en-tecnica": "todavía no llegó a oferta",
    "c-contratado": "🔴 el único `contratado` del padrón de todo el repo",
    "v-a": "la vacante de la empresa A",
    "v-b": "la vacante de la empresa B",
    "c-fantasma": "un id válido que NO existe: el contraste del 404 de otra empresa",
}
_ID = {nombre: str(uuid5(NAMESPACE_DNS, nombre)) for nombre in _SEMILLAS}
NOMBRE_DE = {v: k for k, v in _ID.items()}

C_OFERTA_A = _ID["c-oferta-a"]
C_OFERTA_B = _ID["c-oferta-b"]
C_SIN_VACANTE = _ID["c-sin-vacante"]
C_EN_TECNICA = _ID["c-en-tecnica"]
C_YA_CONTRATADO = _ID["c-contratado"]
C_FANTASMA = _ID["c-fantasma"]
VAC_A = _ID["v-a"]
VAC_B = _ID["v-b"]


def candidato(cid: str, *, empresa: str = EMPRESA_A, vacante: Optional[str] = VAC_A,
              etapa: str = ETAPA_OFERTA, estado: str = ESTADO_ACTIVO) -> CandidatoResponse:
    """Un candidato del padrón. Los defaults son el CAMINO FELIZ; cada test cambia UNA cosa.

    Que el default sea contratable es deliberado: así el test que verifica una guarda declara en
    su llamada exactamente qué la dispara, y no hay que leer el fixture para saber qué se rompió.
    """
    return CandidatoResponse(
        id=cid, vacante_id=vacante, empresa_id=empresa, nombre="Ana", apellido="Pérez",
        email="ana.perez@gmail.com", telefono="11-5555-0000", etapa_pipeline=etapa,
        estado=estado, created_at=AHORA)


def vacante(vid: str, *, empresa: str = EMPRESA_A, area: str = AREA_A,
            modalidad: Optional[str] = "remoto", ubicacion: Optional[str] = "Mar del Plata",
            estado: str = "con_candidatos") -> VacanteResponse:
    """Una vacante del padrón. `tipo_contrato` va cargado A PROPÓSITO con un valor del enum de
    vacantes (`efectivo`), que NO es del vocabulario de `empleados.tipo_contrato`: así el test
    que verifica que no se copia tiene algo concreto que detectar. Sin eso, "no se copió" y "la
    vacante no lo tenía" serían indistinguibles."""
    return VacanteResponse(
        id=vid, codigo=f"VAC-{vid}", empresa_id=empresa, titulo="Analista SSR", area_id=area,
        tipo_contrato="efectivo", estado=estado, modalidad=modalidad, ubicacion=ubicacion,
        created_at=AHORA)


_PADRON = {
    C_OFERTA_A: candidato(C_OFERTA_A),
    C_OFERTA_B: candidato(C_OFERTA_B, empresa=EMPRESA_B, vacante=VAC_B),
    C_SIN_VACANTE: candidato(C_SIN_VACANTE, vacante=None),
    C_EN_TECNICA: candidato(C_EN_TECNICA, etapa=ETAPA_TECNICA),
    C_YA_CONTRATADO: candidato(C_YA_CONTRATADO, estado=ESTADO_CONTRATADO),
}
_VACANTES = {VAC_A: vacante(VAC_A), VAC_B: vacante(VAC_B, empresa=EMPRESA_B, area=AREA_B)}
