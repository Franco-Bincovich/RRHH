"""
Los valores de `empleados.estado` que el código necesita nombrar, en UN solo lugar.

Nace con el estado `preingreso` (migración 120), que es el primer valor del CHECK que **no es
`activo` y tampoco es `baja`**. Hasta él, "no está de baja" y "está en plantilla" eran la misma
pregunta escrita de dos formas y nadie podía notar la diferencia: con los 31 empleados de
producción en `activo`, los dos predicados devuelven la misma fila siempre.

═══════════════════════════════════════════════════════════════════════════════════════════
QUÉ PREGUNTA RESPONDE CADA CONSTANTE
═══════════════════════════════════════════════════════════════════════════════════════════

· `ESTADOS_EN_PLANTILLA` → **"¿esta persona forma parte de la dotación?"**
  Es el conjunto de estados de alguien que YA ENTRÓ y TODAVÍA NO SE FUE. Se usa donde la
  pregunta es de pertenencia y no de disponibilidad: el contador de empleados de un área, el
  padrón de candidatos de una posición.

· `ESTADO_PREINGRESO` → **"¿esta fila es una persona que todavía no entró?"**
  Se usa como COMPLEMENTO (`.neq(...)`) en los contadores que cuentan por FECHA y no miran
  `estado` en absoluto. Ver la sección del complemento, abajo: ahí el motivo de usar el
  complemento en vez de una enumeración es load-bearing.

🔴 NINGUNA DE LAS DOS REEMPLAZA A `= 'activo'`, Y NO HAY UNA TERCERA CONSTANTE PARA ESO.
Hay **15 lecturas** que preguntan `.eq("estado", "activo")` —el KPI de headcount, los dos
denominadores de ausentismo, la base de la tasa de rotación, los saldos de vacaciones, el
organigrama, el selector de superior, el gate del link público de horas— y **todas quedaron
correctas sin tocarlas**, porque un preingreso no es `activo`. Darles una constante propia
(`ESTADOS_ACTIVOS = ("activo",)`) sería una indirección que no agrupa nada y que invitaría a
"mantenerla" agregándole valores: el día que alguien sume `licencia` ahí adentro, el headcount
y los denominadores cambian de significado en silencio. **Ese literal se queda escrito donde
está, y que se lea `"activo"` en la query es la mejor documentación de qué cuenta.**

═══════════════════════════════════════════════════════════════════════════════════════════
POR QUÉ `licencia` ESTÁ EN PLANTILLA — decisión de producto, no filtro olvidado
═══════════════════════════════════════════════════════════════════════════════════════════

Alguien de licencia **sigue siendo dotación de su área**: ocupa la posición, cobra, y vuelve.
Un contador de área que lo excluyera diría que el área tiene menos gente de la que tiene, y el
día que vuelva de la licencia el número subiría solo, como si hubiera entrado alguien.

Esto ya estaba decidido y escrito antes de esta constante —`repositories/_area_row.py` lo
declaraba en su docstring y otra vez en un comentario inline— y **la constante no lo cambia: lo
CENTRALIZA**. Antes el criterio vivía como `.neq("estado", "baja")` en dos repos distintos, o
sea escrito por omisión: "todo lo que no sea baja". Escrito por omisión, cada valor nuevo del
CHECK entra al conjunto sin que nadie lo decida, que es exactamente lo que pasó con
`preingreso`. Ahora entra quien está en esta tupla y nadie más.

═══════════════════════════════════════════════════════════════════════════════════════════
POR QUÉ `suspendido` ESTÁ ACÁ AUNQUE HOY SEA UN VALOR MUERTO
═══════════════════════════════════════════════════════════════════════════════════════════

`suspendido` está en el CHECK de la base y **ningún código lo escribe ni lo lee** (verificado al
escribir la migración 120, sección "'suspendido' SIGUE SIENDO UN VALOR MUERTO"; cero filas en
producción, y `frontend/types/empleado.ts` ni siquiera lo declara en su unión).

Igual entra a `ESTADOS_EN_PLANTILLA`, y por dos motivos distintos:

1. **Porque es la traducción fiel del predicado que reemplaza.** `.neq("estado", "baja")` hoy
   incluye a un suspendido. Si la tupla lo dejara afuera, este cambio —que viene a sacar UN
   estado del conjunto— estaría sacando DOS, y el segundo sin que nadie lo pidiera. Un refactor
   que aprovecha para cambiar la semántica de paso es el que después nadie puede revisar.

2. **Porque angostar el conjunto es una decisión propia, no un efecto colateral de ésta.** La
   pregunta "¿un suspendido cuenta como dotación de su área?" tiene una respuesta de negocio
   —probablemente sí: sigue contratado— y la pregunta "¿este estado existe, o todavía no lo
   construimos?" tiene otra. Ninguna de las dos se contesta desde acá. El día que alguien las
   conteste, el cambio es sacar una palabra de esta tupla **en un commit que hable de eso**, y
   va a ser un diff de una línea con un test que lo cubra. Hoy sería un renglón invisible
   adentro de un commit sobre preingresos.

⚠️ Es el mismo criterio con el que la migración 120 dejó `suspendido` adentro del CHECK en vez
de aprovechar el DROP + CREATE para sacarlo. Dos capas, una sola decisión pendiente.

═══════════════════════════════════════════════════════════════════════════════════════════
🔴 EL COMPLEMENTO (`.neq(ESTADO_PREINGRESO)`) NO ES INTERCAMBIABLE CON LA ENUMERACIÓN
═══════════════════════════════════════════════════════════════════════════════════════════

Los contadores de ALTAS por `fecha_ingreso` usan `.neq("estado", ESTADO_PREINGRESO)` y **no**
`.in_("estado", ESTADOS_EN_PLANTILLA)`. Parece el mismo filtro escrito al revés y no lo es:

    alguien que entró en marzo y renunció en julio SIGUE SIENDO UN ALTA DE MARZO.

Con la enumeración, esa persona —hoy en `baja`— desaparecería del conteo de altas de marzo, y
el número de un mes cerrado cambiaría meses después: el mismo modo de falla que ya se corrigió
cuando esos contadores dejaron de contar por `updated_at`. `baja` **tiene que quedar del lado
que cuenta**, y el único estado que hay que excluir es el de quien todavía no entró.

Dicho de otra forma: los dos conjuntos responden preguntas distintas y sobre ejes distintos.
`ESTADOS_EN_PLANTILLA` es una foto de HOY ("¿quién está?"); el complemento es sobre un HECHO
del pasado ("¿esto ocurrió?"), y un hecho no se deshace porque la persona después se haya ido.

Por eso las dos constantes conviven en este módulo sin que una derive de la otra: no son
complementarias, no suman el universo, y **calcular una a partir de la otra las ataría**.

═══════════════════════════════════════════════════════════════════════════════════════════
LOS DOS TIPOS DE ESCRITURA VIVEN ACÁ, CON LAS CONSTANTES — Y NO EN `schemas/`
═══════════════════════════════════════════════════════════════════════════════════════════
`EstadoEmpleado` y `EstadoAlta` son el vocabulario de estados visto desde la ESCRITURA, igual
que las dos constantes de arriba lo son desde la LECTURA. Están en el mismo módulo por una
razón concreta: **`EstadoEmpleado` es el espejo del CHECK `empleados_estado_check`, y ese
espejo tiene que existir UNA sola vez.** Escrito en `schemas/empleado.py`, la lista de cinco
valores quedaría en un archivo y el porqué de cada uno en otro, y las dos podrían separarse sin
que nada falle — que es el modo de falla que este repo documenta una y otra vez.

Que un schema importe su vocabulario cerrado desde `utils/` ya es el patrón del repo:
`schemas/usuario.py` hace exactamente eso con `ROLES_VALIDOS` de `utils.permisos`. Y no hay
riesgo de ciclo: `utils/` no importa de `schemas/` en ningún archivo (verificado el 18/8/2026).
"""
from typing import Literal

# El estado de quien tiene la ficha creada y la fecha de ingreso acordada, pero todavía no
# entró. Único valor que la migración 120 agregó al CHECK.
ESTADO_PREINGRESO = "preingreso"

# Los estados de alguien que YA ENTRÓ y TODAVÍA NO SE FUE. Deja afuera a `baja` (se fue) y a
# `preingreso` (no entró). Ver el encabezado para por qué `licencia` y `suspendido` están.
ESTADOS_EN_PLANTILLA = ("activo", "licencia", "suspendido")

# ── Tipos de escritura ──────────────────────────────────────────────────────────────────────

# 🔴 EL ESPEJO DEL CHECK. Lo consume `EmpleadoUpdate.estado`, que hasta el 18/8/2026 era un
# `Optional[str]` SIN VALIDAR: un `estado` cualquiera del body viajaba entero hasta Postgres,
# chocaba contra `empleados_estado_check` y volvía como un error **23514 que NINGÚN `except` de
# la cadena mapea** — o sea un 500 con un mensaje de driver para lo que es un error del que
# manda el request. Tipado, Pydantic lo corta en la frontera y sale un **422** por el camino
# normal, con el contrato {error, message, code} que el front ya entiende.
#
# POR QUÉ `Literal` Y NO UN `Enum` NI UN `field_validator`:
#   · Un Enum agregaría un tipo nuevo que después hay que convertir a str para el payload de
#     PostgREST (`model_dump()` devolvería el miembro, no el valor), a cambio de nada: no hay
#     comportamiento que colgarle, es una lista de cinco strings.
#   · Un validator movería la regla al cuerpo de una función, fuera del schema, y no saldría en
#     el OpenAPI. Con el Literal, los valores válidos quedan publicados en /docs.
#
# 🔴 `suspendido` ENTRA AUNQUE HOY SEA UN VALOR MUERTO (nadie lo escribe ni lo lee; ver la
# sección de arriba y la migración 120). Esta lista ES el CHECK, y sacarlo de acá ANGOSTA el
# conjunto de lo aceptado: es una decisión propia sobre si ese estado existe o todavía no se
# construyó, no un efecto colateral de tipar el campo. El día que se decida, se saca de los dos
# lados —CHECK y Literal— en un commit que hable de eso.
EstadoEmpleado = Literal["activo", "baja", "licencia", "suspendido", "preingreso"]

# 🔴 SOLO DOS DE LOS CINCO, y la lista corta es el punto. Lo consume `EmpleadoCreate.estado`.
# `baja` y `licencia` describen algo que le PASÓ a alguien que ya estaba: nadie se da de alta
# como dado de baja, y una licencia es un tramo dentro de una relación laboral que empezó antes.
# Aceptarlos en el alta permitiría crear una ficha en un estado al que no se puede llegar por
# ningún camino real, y los contadores de altas/bajas —que cuentan por FECHA— la tomarían como
# un movimiento del mes. `suspendido` queda afuera por lo mismo, y además está muerto.
#
# 🔴 EL DEFAULT DEL ALTA VIVÍA EN EL REPO Y AHORA VIVE EN EL SCHEMA (`EmpleadoCreate.estado =
# "activo"`). Hasta el 18/8/2026 `_empleado_write_repo.guardar` hacía `payload["estado"] =
# "activo"` hardcodeado DESPUÉS de armar el payload, así que pisaba cualquier cosa que viniera
# del schema. Se borró esa línea. Queda escrito porque es exactamente la clase de dato que
# después nadie encuentra: el que busque por qué un alta nace en `activo` va a mirar el schema,
# no el armado del payload.
EstadoAlta = Literal["activo", "preingreso"]
