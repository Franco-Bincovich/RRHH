"""
EL MAPEO DE CAMPOS del puente candidato → empleado: de dónde sale cada campo del alta.

Extraído de `services/_candidato_contratar.py`, que quedó en 202/150. **El corte separa lo que
CAMBIA de lo que no**: este mapeo se toca cada vez que aparece una columna nueva en `empleados` o
en `vacantes`; el acto de contratar y sus guardas son estables y no se enteran.

📄 **EL ACTO vive en `services/_candidato_contratar.py`**: la orquestación y la doble comprobación
de empresa — candidato contra el header, vacante contra la empresa del candidato.
📄 **LAS GUARDAS viven en `services/_candidato_contratar_guardas.py`**: `CANDIDATO_SIN_VACANTE`,
`CANDIDATO_NO_ESTA_EN_OFERTA`, `CANDIDATO_NO_CONTRATABLE`, `FECHA_INGRESO_PASADA` y el 404 de la
barrera de empresa, cada una con su porqué — incluida la de fecha, que explica por qué contratar
exige `fecha_ingreso >= hoy` mientras `activar` exige lo contrario.

🔴 **ACÁ NO HAY NI UNA GUARDA, Y ES LA CONDICIÓN DEL CORTE.** `_payload` no contiene un solo
`raise`: cuando se lo llama, el acto ya decidió que la contratación procede. Si alguna vez algo
de acá tuviera que RECHAZAR, esa validación pertenece al acto y hay que moverla — armar el
payload es traducir datos ya validados, no volver a decidir. `tests/test_candidato_contratar.py`
lo fija con un test estructural sobre el AST, para que el corte no se erosione en silencio.

═══════════════════════════════════════════════════════════════════════════════════════════

    nombre, apellido    ← candidato
    email_personal      ← candidato.email      🔴 ver abajo
    telefono            ← candidato
    empresa_id          ← candidato            (NOT NULL, heredada de su vacante al crearlo)
    area_id             ← vacante
    modalidad_trabajo   ← vacante.modalidad    (mismo enum, verificado contra los dos CHECK)
    ubicacion           ← vacante
    email_corporativo   ← body
    roles               ← body
    fecha_ingreso       ← body
    estado              = 'preingreso'

🔴 `candidato.email` VA A `email_personal`, NUNCA A `email_corporativo`. El del candidato es su
mail personal —es por donde postuló— y `empleados.email_corporativo` es **UNIQUE GLOBAL en todo
el sistema**: escribirlo ahí quema ese mail para siempre, en todas las empresas, y encima deja al
legajo diciendo que el corporativo de esa persona es su Gmail. Por eso el corporativo viene del
body: no existe hasta que alguien abre la casilla.

🔴 `tipo_contrato` NO SE COPIA DE LA VACANTE, y es el error más fácil de cometer acá porque los
dos campos se llaman igual. Son vocabularios distintos: `vacantes.tipo_contrato` es un enum de
cuatro (`efectivo | plazo_fijo | contratado | pasantia`) y `empleados.tipo_contrato` es **TEXT
libre** desde la migración 065, con un padrón real que dice "Relación de dependencia". Copiarlo
mete un valor ajeno **sin ningún error** y ensucia todo reporte que agrupe por ese campo.
⚠️ Y ojo con el homónimo: el `'contratado'` del enum de la VACANTE es un tipo de contrato y **no
tiene ninguna relación** con `candidatos.estado = 'contratado'`, que es lo que este módulo
escribe. Un grep de "contratado" los mezcla; son dos ejes que no se tocan.

`modalidad_trabajo` sí se copia porque los dos CHECK son idénticos (`presencial | remoto |
hibrido`, verificado en `db/schema.sql`). Si la vacante no la tiene cargada **no se pasa**, para
que aplique el default de `EmpleadoCreate` en vez de escribir un `None` en una columna con CHECK.
"""
from uuid import UUID

from schemas.candidato import ContratarRequest
from schemas.empleado import EmpleadoCreate

# 🔴 EL ÚNICO CAMPO QUE EL PUENTE NO DERIVA NI RECIBE: LO PONE.
# `EmpleadoCreate.tipo_contrato` es REQUERIDO (no tiene default) y el puente no tiene de dónde
# sacarlo: no está en `candidatos`, y el de la vacante es de otro vocabulario (ver abajo). Sin
# esto, `EmpleadoCreate(**campos)` levanta un ValidationError que el handler global convierte en
# **500** — o sea el puente entero inutilizable.
#
# El valor es EL MISMO default que ya aplica el formulario de alta manual
# (`frontend/components/features/empleados/modal/_constants.ts`), y eso es lo que importa: si acá
# se pusiera otro, los empleados creados por el puente y los creados a mano quedarían en dos
# grupos distintos de cualquier reporte que agrupe por este campo, sin que nadie lo haya decidido.
#
# ⚠️ ES UN DEFECTO DE PRODUCTO, NO UN DATO VERIFICADO: nadie declaró que toda contratación que
# entre por acá sea en relación de dependencia. Se corrige por el PUT del legajo, como cualquier
# otro campo del alta. 🚩 Disparador para revisarlo: que RRHH contrate por este camino a alguien
# con otro tipo de contrato. La salida entonces NO es copiar el de la vacante —el enum de allá
# (`efectivo|plazo_fijo|contratado|pasantia`) no es este vocabulario— sino sumarlo al body.
TIPO_CONTRATO_POR_DEFECTO = "Relación de dependencia"


def payload(cand, vacante, data: ContratarRequest, empresa_id: UUID) -> EmpleadoCreate:
    """Arma el alta desde el candidato + su vacante + los tres del body. Ver EL MAPEO, arriba."""
    campos = {
        "nombre": cand.nombre, "apellido": cand.apellido,
        "email_personal": cand.email, "telefono": cand.telefono,
        "empresa_id": empresa_id, "area_id": vacante.area_id,
        "ubicacion": vacante.ubicacion,
        "email_corporativo": data.email_corporativo, "roles": data.roles,
        "fecha_ingreso": data.fecha_ingreso,
        "tipo_contrato": TIPO_CONTRATO_POR_DEFECTO,
        # El acuerdo todavía no ocurrió: la ficha nace SIN contar en ningún KPI. Pasa a `activo`
        # por `POST /api/empleados/{id}/activar`, que exige que la fecha ya haya ocurrido.
        "estado": "preingreso",
    }
    if vacante.modalidad:  # ver EL MAPEO: sin esto, un None pisaría el default del schema
        campos["modalidad_trabajo"] = vacante.modalidad
    return EmpleadoCreate(**campos)
