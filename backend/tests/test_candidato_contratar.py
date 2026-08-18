"""
El puente candidato → empleado, por HTTP: `POST /api/candidatos/{id}/contratar`.

📄 **LAS GUARDAS están en `tests/test_candidato_contratar_guardas.py`** — el corte es el mismo
seam que el del service: acá lo que el puente HACE, allá lo que RECHAZA.
📄 El PADRÓN está en `tests/_contratar_padron.py`, los FAKES en `tests/_contratar_fakes.py`, el
ARNÉS HTTP en `tests/_contratar_arnes.py` y el CONTEXTO compartido en
`tests/_contratar_contexto.py`.

═══════════════════════════════════════════════════════════════════════════════════════════
🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
═══════════════════════════════════════════════════════════════════════════════════════════
**Que el padrón no tuviera un candidato en `oferta`.** Antes de esta tanda no lo había en ningún
archivo del repo, así que las cuatro guardas de estado no tenían contra qué fallar: un `_validar`
que aceptara todo y uno que rechazara todo daban el mismo verde.

Por eso **cada guarda va con su CONTRASTE**: el caso que la dispara y el caso que NO. Sin el
segundo, un `raise` incondicional pasa los dos. El contraste del conjunto es
`test_el_camino_feliz_crea_el_empleado`, que es el único que llega a escribir.

Y por eso los fakes **honran `empresa_id`** y `FakeVacanteRepo` registra CON QUÉ empresa se lo
consultó: la mitad no obvia de la barrera —que la vacante se busque con la empresa del CANDIDATO
y no con la del header— sólo se puede afirmar mirando eso, porque en modo consolidado el header
es `None` y "no restringió" es indistinguible de "restringió con None".
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

from datetime import date  # noqa: E402

import pytest  # noqa: E402

from services._candidato_contratar_mapeo import TIPO_CONTRATO_POR_DEFECTO  # noqa: E402
from tests._contratar_arnes import body  # noqa: E402
from tests._contratar_contexto import _Contexto, _contratar  # noqa: E402
from tests._contratar_padron import (  # noqa: E402
    AREA_A, C_OFERTA_A, C_OFERTA_B, EMPRESA_B, MANANA, VAC_A,
)
from utils.errors import AppError  # noqa: E402


# ── (a) el camino feliz + el mapeo ────────────────────────────────────────────

async def test_el_camino_feliz_crea_el_empleado() -> None:
    """(a) 201 y el empleado nace en `preingreso`. CONTRASTE de todas las guardas de abajo."""
    ctx = _Contexto()
    r = await _contratar(ctx)
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "preingreso"


async def test_los_campos_se_mapean_donde_corresponde() -> None:
    """(a) El mapeo completo, sobre lo que el service MANDÓ al alta, no sobre la respuesta."""
    ctx = _Contexto()
    await _contratar(ctx)
    enviado = ctx.empleados_repo.guardados[0]
    assert enviado.nombre == "Ana" and enviado.apellido == "Pérez"
    assert enviado.email_personal == "ana.perez@gmail.com"      # del candidato
    assert enviado.email_corporativo == "ana.perez@karstec.com"  # del body
    assert enviado.telefono == "11-5555-0000"
    assert str(enviado.area_id) == AREA_A                        # de la VACANTE
    assert enviado.modalidad_trabajo == "remoto"                 # de la VACANTE
    assert enviado.ubicacion == "Mar del Plata"                  # de la VACANTE
    assert enviado.roles == ["Analista"] and enviado.fecha_ingreso == MANANA
    assert enviado.estado == "preingreso"


async def test_el_email_del_candidato_no_va_al_corporativo() -> None:
    """🔴 `email_corporativo` es UNIQUE GLOBAL: meter ahí el mail personal lo quema para siempre.

    ¿Qué tendría que ser distinto para que falle? Que el mapeo cruzara los dos campos — que es el
    error natural, porque el candidato tiene UN email y el empleado tiene DOS.
    """
    ctx = _Contexto()
    await _contratar(ctx)
    enviado = ctx.empleados_repo.guardados[0]
    assert enviado.email_corporativo != "ana.perez@gmail.com"


async def test_el_tipo_contrato_no_se_copia_de_la_vacante() -> None:
    """🔴 La vacante trae `tipo_contrato='efectivo'` (SU enum) y el empleado NO debe heredarlo.

    Son dos vocabularios: el de vacantes es un enum de cuatro y el de empleados es TEXT libre,
    con un padrón real que dice "Relación de dependencia". Copiarlo metería un valor ajeno **sin
    ningún error** y ensuciaría todo reporte que agrupe por ese campo.

    ⚠️ El puente SÍ escribe el campo —`EmpleadoCreate.tipo_contrato` es requerido y no hay de
    dónde derivarlo— pero con el default del formulario de alta, no con el de la vacante. Lo que
    este test fija es exactamente esa diferencia.

    ¿Qué tendría que ser distinto para que falle? Que la vacante del padrón no tuviera cargado
    `tipo_contrato`: ahí "no se copió" y "no había nada que copiar" serían indistinguibles.
    """
    ctx = _Contexto()
    assert ctx.vacantes.filas[VAC_A].tipo_contrato == "efectivo", "el padrón tiene qué copiar"
    await _contratar(ctx)
    enviado = ctx.empleados_repo.guardados[0]
    assert enviado.tipo_contrato != "efectivo"
    assert enviado.tipo_contrato == TIPO_CONTRATO_POR_DEFECTO


# ── (b) y (k) el círculo con A3.1: preingreso no cuenta, activo sí ────────────

async def test_el_empleado_nuevo_no_cuenta_como_alta_del_mes() -> None:
    """(b) Nace en `preingreso`, y los contadores de altas excluyen ese estado (A3.1).

    Se verifica sobre el estado que VIAJÓ al alta, que es lo que este puente controla. Que
    `preingreso` quede fuera de los contadores lo prueba `test_estado_preingreso_lecturas`; acá
    lo que se cierra es que el puente no cree la ficha directamente en `activo`.
    """
    ctx = _Contexto()
    await _contratar(ctx)
    assert ctx.empleados_repo.guardados[0].estado == "preingreso"
    assert ctx.empleados_repo.guardados[0].estado != "activo"


async def test_el_ciclo_completo_contratar_y_despues_activar() -> None:
    """(k) 🔴 EL CÍRCULO ENTERO. Contratar deja la ficha fuera de los contadores; activar la mete.

    Se contrata con fecha de HOY —el único valor que las dos mitades aceptan— y después se activa.
    Las dos mitades viven en módulos distintos y **se exigen lo contrario**: contratar pide
    `fecha_ingreso >= hoy` y activar pide que ya haya ocurrido. Hoy es la bisagra.

    ¿Qué tendría que ser distinto para que falle? Que `FakeEmpleadoRepo.update` devolviera la fila
    sin aplicar el patch: ahí "activó" y "no hizo nada" serían indistinguibles. Por eso ese fake
    muta de verdad, y por eso no se reusó el de `_empleado_duplicado_fakes`.
    """
    ctx = _Contexto()
    r = await _contratar(ctx, fecha=date.today())
    empleado_id = r.json()["id"]
    assert ctx.empleados_repo.filas[empleado_id].estado == "preingreso"

    activado = ctx.empleados.activar_empleado(empleado_id, None, "user-1")

    assert activado.estado == "activo"
    assert ctx.empleados_repo.filas[empleado_id].estado == "activo"


async def test_activar_antes_de_la_fecha_no_se_puede() -> None:
    """CONTRASTE del ciclo: con fecha futura, activar RECHAZA. Es la guarda que hace que el
    preingreso signifique algo — sin ella se podría activar a alguien que todavía no entró, y
    aparecería en el headcount y en los denominadores de ausentismo antes de trabajar un día."""
    ctx = _Contexto()
    r = await _contratar(ctx, fecha=MANANA)
    with pytest.raises(AppError) as exc:
        ctx.empleados.activar_empleado(r.json()["id"], None, "user-1")
    assert exc.value.code == "INGRESO_AUN_NO_OCURRIO"


# ── (c) y (d) los dos efectos laterales ──────────────────────────────────────

async def test_el_candidato_queda_contratado_y_la_etapa_sigue_en_oferta() -> None:
    """(c) `estado` cambia, `etapa` NO. Son dos ejes: dónde llegó y cómo terminó."""
    ctx = _Contexto()
    await _contratar(ctx)
    assert [(c, e) for c, e, _ in ctx.candidatos.estados_escritos] == [(C_OFERTA_A, "contratado")]
    assert ctx.candidatos.filas[C_OFERTA_A].estado == "contratado"
    assert ctx.candidatos.filas[C_OFERTA_A].etapa_pipeline == "oferta"


async def test_la_vacante_no_cambia_de_estado() -> None:
    """(d) `cantidad_puestos` puede ser >1: cerrar la búsqueda es decisión de RRHH.

    ¿Qué tendría que ser distinto para que falle? Que el service escribiera la vacante. El fake
    de vacantes NO expone un método de escritura, así que un intento sería un AttributeError —
    y esta aserción documenta por qué el fake es así.
    """
    ctx = _Contexto()
    antes = ctx.vacantes.filas[VAC_A].estado
    await _contratar(ctx)
    assert ctx.vacantes.filas[VAC_A].estado == antes == "con_candidatos"


# ── la auditoría del acto ────────────────────────────────────────────────────

async def test_audita_con_la_empresa_del_candidato() -> None:
    """Vista vs Acción: la empresa del evento sale de la ENTIDAD, nunca del header.

    Se corre en CONSOLIDADO justamente porque ahí el header es `None`: con el header, el evento
    quedaría sin empresa y se caería del filtro por empresa de `/auditoria`.
    """
    ctx = _Contexto(empresa=None)
    async with ctx.cliente() as c:
        await c.post(f"/api/candidatos/{C_OFERTA_B}/contratar", json=body())
    ev = ctx.audit.eventos[0]
    assert ev["evento"] == "contratacion_candidato"
    assert ev["empresa_id"] == EMPRESA_B
    assert ev["datos_anteriores"] == {"estado": "activo"}
    assert ev["datos_nuevos"]["estado"] == "contratado"
