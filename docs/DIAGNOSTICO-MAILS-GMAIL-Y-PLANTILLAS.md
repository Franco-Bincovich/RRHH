# Diagnóstico READ-ONLY — envío de mails por Gmail con plantillas editables

> **2/8/2026 · Sesión de diagnóstico. NO se escribió una sola línea de código.**
> Verificado contra los archivos fuente, con `archivo:línea`.

---

## Resumen ejecutivo

1. **El OAuth de Google pide `gmail.readonly`. No alcanza para enviar.** Hay que sumar
   `gmail.send`, y eso **obliga a reconectar**: el refresh token guardado NO adquiere el scope
   nuevo. La integración de RRHH sigue leyendo, pero enviar le va a dar 403 hasta que reconecte.
2. 🔴 **`usuario_integraciones` es POR USUARIO y NO tiene `empresa_id`.** Confirmado en el
   catálogo. Los mails saldrían de la cuenta del humano que apretó el botón, y **un proceso sin
   humano no tiene de qué cuenta salir**. Es la decisión de producto que hay que cerrar antes de
   escribir una línea.
3. 🔴 **Bug preexistente en el refresh:** `gmail_service` renueva el access token y **no lo
   persiste**. Cada llamada después del vencimiento paga un round-trip extra a Google, y
   `token_expiry` queda desactualizado para siempre.
4. **`resend_api_key` es obligatoria sin default y nadie la importa.** Si falta, **no arranca la
   app** — ni siquiera `/health`. Es una env var que hoy solo puede romper.
5. **El molde del punto único ya existe y es exacto**: `services/export/` (paquete +
   `__init__` que expone la superficie + `engine.py` con dict de despacho). `services/mailer/`
   se calca de ahí.
6. **Nada de esto es verificable end-to-end hasta que Franco conecte su Gmail.** Lo que SÍ se
   puede probar sin cuenta es todo el motor de plantillas y variables — que es el 70% del trabajo.

---

# PARTE A — Gmail: qué hay y qué falta

## (a) El OAuth actual

**Scopes hoy** — `services/_google_oauth.py:31-35`:

```python
_GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
```

**Dónde se guardan los tokens** — tabla `usuario_integraciones`, vía
`IntegracionRepo.save_google_tokens` (`repositories/integracion_repo.py:25-44`), un `upsert` con
`on_conflict="user_id,tipo"`. Columnas relevantes (catálogo):

```
usuario_integraciones (id, user_id, tipo, access_token, refresh_token,
                       token_expiry, email_cuenta, api_key, activo, created_at, updated_at)
UNIQUE (user_id, tipo) · FK user_id → users(id) ON DELETE CASCADE
```

**Dos parámetros del flow que ya están bien puestos** (`_google_oauth.py:71-76`) y que conviene
no tocar:
- `access_type="offline"` → es lo que hace que Google devuelva `refresh_token`.
- `prompt="consent"` → fuerza la pantalla de consentimiento **en cada conexión**, y con eso
  garantiza que siempre venga un `refresh_token` nuevo. Sin esto, una reconexión suele devolver
  `refresh_token=None` y el upsert lo pisaría con NULL.
- `include_granted_scopes="true"` → autorización incremental: cuando el usuario reautorice con
  el scope de envío, el token resultante conserva también el de lectura. Importa para (b).

**Cómo se refresca** — `services/gmail_service.py:42-70`, `_get_access_token`:

```python
integracion = repo.get_by_user_and_tipo(user_id, "google")
if not integracion or not integracion.get("access_token"): → GMAIL_NOT_CONFIGURED (400)
expiry_str = integracion.get("token_expiry")
if expiry_str:
    try:
        expiry = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
        if expiry <= datetime.now(timezone.utc):
            refresh = integracion.get("refresh_token")
            if not refresh: → GMAIL_NOT_CONFIGURED (400)
            POST oauth2.googleapis.com/token (grant_type=refresh_token)
            return resp.json()["access_token"]        # ← NO SE PERSISTE
    except (ValueError, TypeError):
        pass                                          # ← camino silencioso
return integracion["access_token"]
```

### 🔴 Tres cosas que están mal y hay que arreglar de paso

1. **El token renovado NO se guarda.** `:64` devuelve el `access_token` nuevo y nunca llama al
   repo. Consecuencias: (a) cada request posterior al vencimiento vuelve a hacer el round-trip a
   Google —latencia de más en un camino que va a pasar a ser el de envío—; (b) `token_expiry` en
   la base queda **fijo en el pasado** para siempre, así que la condición `expiry <= now` da
   siempre True. Es un bug de eficiencia, no de corrección, pero al agregar envío empieza a
   pagarse en cada mail.
2. **`token_expiry` NULL saltea el refresh entero.** El `if expiry_str:` de `:48` es la única
   puerta al refresh. Si `credentials.expiry` vino None al conectar (`_google_oauth.py:126`
   guarda `None` en ese caso), el token vencido se devuelve tal cual → Gmail responde 401 → el
   caller lo envuelve en `GMAIL_ERROR` **502**, que dice "error al consultar Gmail" cuando lo que
   pasa es "tu sesión venció". Diagnóstico equivocado para el usuario.
3. **`except (ValueError, TypeError): pass` (`:68-69`) es un tragado silencioso.** Si el
   `token_expiry` guardado fuera naive (sin tz), la comparación con `datetime.now(timezone.utc)`
   levanta `TypeError`, se traga, y **se devuelve el token viejo sin intentar renovarlo**. Hoy no
   se dispara —`procesar_callback` guarda siempre con `tzinfo=utc`— pero es un camino vivo.

## (b) 🔴 El scope de envío, y sí: obliga a reconectar

**Scope que falta:** `https://www.googleapis.com/auth/gmail.send`. Es el mínimo estricto —solo
permite enviar, no leer— y es preferible a `gmail.modify` o `mail.google.com`, que dan mucho más.
Queda `gmail.readonly` + `gmail.send`, dos scopes acotados en vez de uno amplio.

**¿Invalida el consentimiento existente?** **No lo invalida — lo deja corto, que a los efectos
prácticos es peor porque falla más tarde.** Concretamente:

- El `refresh_token` guardado **sigue siendo válido** y sigue sirviendo para leer el inbox.
- Pero el grant al que está atado **no incluye `gmail.send`**. Los access tokens que se deriven de
  él tampoco. Google **no** amplía un grant existente de forma retroactiva.
- ⇒ El primer intento de envío responde **403 `insufficientPermissions` / `ACCESS_TOKEN_SCOPE_INSUFFICIENT`**.
  No es un 401: el token es válido, lo que falta es el permiso.

**Qué significa en la práctica:** RRHH tiene una integración conectada hoy. Al deployar el scope
nuevo, **esa integración no se rompe** (sigue leyendo mails de candidatos, que es para lo que se
usa) **pero no va a poder enviar hasta que la persona reconecte**. Y el síntoma, sin trabajo
extra, sería un 403 críptico en medio de un envío.

**Recomendación — dos cosas, ninguna cara:**
1. **Guardar los scopes concedidos** al conectar (`credentials.scopes` está disponible en
   `procesar_callback`, hoy se descarta). Con eso se puede saber **antes de intentar** si esa
   cuenta puede enviar.
2. **Que la pantalla de integraciones lo diga**: "esta cuenta está conectada para lectura; para
   enviar mails hay que reconectar". Un cartel accionable en vez de un 403 en el momento peor.
   Como `prompt="consent"` ya está puesto, reconectar es un clic y devuelve refresh token nuevo.

⚠️ **Ojo con el orden de deploy:** si el scope se agrega y alguien reconecta ANTES de que exista
la pantalla que lo explica, no pasa nada malo (queda con los dos scopes). El riesgo es el inverso:
publicar el botón de "enviar" antes de que nadie haya reconectado.

## (c) 🔴 La integración es POR USUARIO — verificado, y es el problema de diseño de esta tanda

**Verificado en el catálogo:** `usuario_integraciones` **no tiene `empresa_id`**. Tiene
`user_id` con FK a `users` y `UNIQUE (user_id, tipo)`. `IntegracionRepo` scopea todo por
`user_id` (`get_by_user`, `get_by_user_and_tipo`, `save_google_tokens`, `delete`). Y
`GmailService._get_access_token(user_id)` recibe el user_id del request.

⇒ **Con el modelo actual, el mail sale de la casilla personal del usuario logueado que apretó el
botón.** No es un detalle técnico: el destinatario ve "de: fulana@gmail.com", no "de:
rrhh@karstec". Y si Fulana se va de la empresa y le borran el usuario, el `ON DELETE CASCADE`
se lleva la integración y **el envío deja de funcionar sin que nadie lo note hasta el próximo mail**.

### ¿De qué cuenta sale un mail que dispara un proceso y no una persona?

**Hoy: de ninguna. No hay respuesta posible.** Todos los caminos de `usuario_integraciones`
necesitan un `user_id`, y un proceso automático no tiene uno. Las opciones reales son tres:

| | Cómo | A favor | En contra |
|---|---|---|---|
| **1** | **Casilla del sistema**: una fila de integración con `user_id` = un usuario técnico dedicado, y el mailer la busca siempre a ella | Una sola cuenta remitente, estable, institucional. Un proceso automático tiene de dónde salir. Sobrevive a que se vaya cualquier persona | Requiere crear ese usuario y que alguien conecte su Gmail. Hay que decidir dónde se declara cuál es (env var vs tabla) |
| **2** | **Sale del usuario que disparó** | Cero trabajo nuevo | No cubre procesos automáticos, el remitente varía según quién apretó, y se rompe al dar de baja a esa persona |
| **3** | **Tabla nueva de casillas por empresa** | Cada empresa manda desde su dominio | Es la opción cara, y con 1 empresa en producción no se puede ni probar |

**Recomendación: opción 1, y decidirla ANTES de escribir código.** Es la que hace que el flujo de
prueba (la cuenta personal de Franco) y el flujo real (la casilla de RRHH) sean **idénticos** —
que es justo lo que pediste: cambia qué cuenta está conectada a ese usuario técnico, no cambia
una línea. Con la opción 2, probar con la cuenta personal y después mudar a la institucional son
dos circuitos distintos.

**Cómo declarar cuál es la casilla del sistema:** una env var `MAIL_REMITENTE_USER_ID` es lo más
barato, pero un UUID en una variable de entorno es opaco y se rompe en silencio si el usuario se
borra. Alternativa mejor y casi igual de barata: **una columna `es_remitente_sistema boolean` en
`usuario_integraciones`**, con un índice único parcial que garantice que haya **una sola**
(mismo patrón que el índice parcial de `parametros_empresa` en la migración 085). Así la elección
se ve en la base, se puede cambiar desde la UI, y no hay UUID escrito en Vercel.

> 🚩 **Es una decisión de producto, no técnica.** Si RRHH quiere que los mails salgan a nombre de
> quien los manda (p. ej. un mail de bienvenida firmado por la persona de RRHH), la opción 1
> igual sirve: el remitente es la casilla institucional y el nombre va en el cuerpo.

## (d) Token vencido o revocado al momento de enviar

| Situación | Qué pasa hoy | ¿Ruidoso? |
|---|---|---|
| Access token vencido, refresh válido | Se renueva y sigue (pero no se persiste, ver (a)) | — funciona |
| Refresh token **revocado** (el usuario sacó el permiso en su cuenta de Google) | Google responde 400 `invalid_grant` → `raise_for_status()` → `AppError("No se pudo renovar el token de Google", "GMAIL_TOKEN_EXPIRED", 401)` (`gmail_service.py:67`) | ✅ **Ruidoso y correcto** |
| Integración borrada / sin `access_token` | `GMAIL_NOT_CONFIGURED` (400) | ✅ ruidoso |
| Sin `refresh_token` guardado | `GMAIL_NOT_CONFIGURED` (400) | ✅ ruidoso, aunque el mensaje miente un poco: sí está configurado, le falta el refresh |
| **`token_expiry` NULL** | Salta el refresh, manda con token vencido → Gmail 401 → se envuelve en `GMAIL_ERROR` **502** | ⚠️ ruidoso pero **con el diagnóstico equivocado** |
| **`token_expiry` naive** | `TypeError` → `except: pass` → manda con el token viejo | 🔴 **SILENCIOSO** (hoy inalcanzable, pero el camino existe) |

**Para el envío hay que agregar un caso que hoy no existe: el 403 por scope insuficiente** (ver
(b)). Sin tratarlo aparte, va a caer en el `except Exception` genérico y salir como
`GMAIL_ERROR 502` — "error al enviar" cuando el problema es "reconectá tu cuenta". Es el error
que más veces va a pasar en las primeras semanas, así que merece su propio código.

## (e) `gmail_service.py`: 150/150 — está EN EL LÍMITE EXACTO

**Qué hace hoy:** solo lectura, y solo para reclutamiento. Tres piezas:
- `_parse_from_header` (`:18-29`) y `_is_cv_email` (`:32-34`) — helpers puros de parseo.
- `_get_access_token` (`:42-70`) — el token, con el refresh.
- `get_emails_candidatos` (`:72-117`) y `crear_candidato_desde_email` (`:119-150`) — el caso de uso.

🔴 **150/150 significa que el próximo cambio EXIGE dividir primero** (regla 2 del repo). No hay
lugar ni para una línea de envío.

### El corte propuesto en CLAUDE.md (`_gmail_parseo.py`) YA NO es el correcto

Ese corte apunta a las ~17 líneas de parseo de headers (`_parse_from_header` + `_is_cv_email`).
Servía cuando el archivo solo leía. Con envío encima, **corta por el lado equivocado**: deja en
el mismo archivo dos casos de uso sin relación (leer postulaciones · enviar mails) y saca lo
único que ya era independiente.

**Corte que propongo, por responsabilidad:**

| Módulo | Qué se lleva | Por qué |
|---|---|---|
| **`services/_google_token.py`** (nuevo) | `_get_access_token` + el refresh + **la persistencia que hoy falta** + la lectura de scopes concedidos | 🔴 **Es lo que van a compartir lectura y envío.** Si el envío se copia su propia versión, el arreglo del refresh queda hecho en un lado solo. Es la pieza crítica del corte |
| **`services/_gmail_parseo.py`** | `_parse_from_header`, `_is_cv_email` | El corte ya identificado. Sigue siendo válido, solo deja de ser el principal |
| **`gmail_service.py`** | los dos casos de uso de reclutamiento | Queda en ~100 y con margen |
| **`services/mailer/_gmail.py`** | el envío (ver Parte C) | El envío NO va en `gmail_service`: ese archivo es de reclutamiento. Va detrás del punto único |

---

# PARTE B — El modelo de plantillas

## (f) 🔴 Dónde guardarlas

Hoy **no hay tabla**. Ninguna de las existentes sirve: `onboarding_templates` es de checklists de
onboarding, y `notificaciones`/`notificaciones_config` son huérfanas (0 callers, marcadas para
limpieza post-AWS) y modelan notificaciones in-app, no mails.

### ¿Por empresa o globales? → **Por empresa, con fallback global**

El repo ya tiene los dos precedentes y **no se contradicen: responden a preguntas distintas**.

- `tipos_ausencia` terminó **global** porque un tipo de ausencia es una categoría del mundo
  ("licencia por maternidad" es lo mismo en cualquier empresa). La migración 085 igual le agregó
  `empresa_id` nullable para permitir excepciones.
- `onboarding_templates` es **por empresa** (`empresa_id uuid NOT NULL`) porque el contenido es de
  la empresa.

**Una plantilla de mail es contenido, no categoría**: lleva el nombre de la empresa, su tono, su
firma. ⇒ **por empresa**.

**Pero con `empresa_id` NULLABLE = plantilla global**, exactamente el patrón de la migración 085
(`empresa_id NULL` = fila global, lectura por `COALESCE(mi empresa, global)`), con su **índice
único parcial** — porque en SQL `NULL <> NULL` y un `UNIQUE` común no impediría dos globales.
Motivo concreto: se pueden sembrar las plantillas base una sola vez y cada empresa las pisa solo
si quiere. Con `NOT NULL` habría que duplicarlas por empresa desde el día uno, y con 1 empresa en
producción eso se ve gratis y deja de serlo con la segunda.

### ¿Texto plano o HTML?

**Recomendación: cuerpo en TEXTO PLANO con Markdown mínimo (negrita, itálica, listas, links),
renderizado a HTML EN EL SERVIDOR al enviar.** RRHH escribe texto; el sistema genera el HTML.

Por qué, y no por comodidad:
- **HTML editable por el usuario es una superficie de inyección.** El destinatario recibe lo que
  RRHH escribió sin que nadie lo revise. El repo hoy **no tiene ninguna dependencia de
  sanitización** (verificado: cero `bleach`, cero `dangerouslySetInnerHTML` en todo el front), así
  que habría que sumar una y mantenerla. Sanitizar HTML bien es notoriamente difícil.
- Con Markdown, el conjunto de HTML posible lo genera **nuestro código**, no el usuario. La
  superficie desaparece en vez de acotarse.
- Es lo que RRHH necesita de verdad: negrita, una lista, un link. No una tabla anidada.

**Regla no negociable, venga como venga:** las variables se interpolan **después** de renderizar
el Markdown y **siempre escapadas**. Un empleado que se llame `Ana <script>` no puede convertirse
en markup — y ese es el vector real, porque el valor sale de la base, no de la plantilla.

### ¿Versionar?

**No versionar la plantilla. Guardar el mail RENDERIZADO en el log de envíos** (ver (i)).

El razonamiento: la pregunta que se va a hacer alguien es *"¿qué le llegó a Fulano?"*, no *"¿cómo
era la plantilla en marzo?"*. Versionar la plantilla responde la segunda y, para responder la
primera, obliga a reconstruir el render con los valores de aquel momento — que ya no existen
(el empleado cambió de área desde entonces). **Guardar el asunto y el cuerpo ya renderizados
responde la pregunta real, exactamente y sin reconstruir nada.**

Y es más barato: una columna de texto en una tabla que ya hay que crear, contra una tabla de
versiones + FK + resolución de "qué versión regía".

## (g) 🔴 Las variables

### La sintaxis: `{{nombre_empleado}}`

Doble llave, `snake_case`, sin espacios adentro.

- **Inconfundible dentro de un texto normal.** Un `{{` no aparece en castellano por accidente.
  `{simple}` sí puede aparecer, y `$var` o `%var%` también.
- **RRHH ya la vio** (es la de Google Docs, Notion, Mailchimp). No hay que enseñarla.
- **Un `{{` sin cerrar es detectable** y se puede señalar al guardar.

⚠️ **No usar la interpolación de Python** (`str.format` o f-strings) para resolverlas. `format`
sobre texto del usuario permite `{empleado.__class__.__init__.__globals__}` — un camino conocido
a los internals del proceso. La resolución tiene que ser un **reemplazo literal por regex sobre un
diccionario de valores ya calculados**, sin evaluar nada.

### 🔴 De dónde salen los valores: cada plantilla DECLARA SU CONTEXTO

Es la parte central del diseño, y sí: **cada plantilla declara de qué contexto habla**.

```
plantilla_mail (
    id, empresa_id NULL,
    clave           text NOT NULL,      -- 'bienvenida_empleado', 'aviso_vacaciones'...
    contexto        text NOT NULL,      -- 'empleado' | 'vacacion' | 'ausencia' | 'ninguno'
    asunto          text NOT NULL,
    cuerpo          text NOT NULL,
    activa          boolean NOT NULL DEFAULT true,
    ...
)
UNIQUE parcial (empresa_id, clave) + UNIQUE parcial (clave) WHERE empresa_id IS NULL
```

El `contexto` es lo que hace verificable todo lo demás:

- **Un CATÁLOGO en código** —no en la base— mapea cada contexto a sus variables y a cómo se
  resuelven. Molde exacto: `services/reportes/reporte_generators.py`, que es un dispatcher de
  `clave → generador`, y `_RENDERERS` de `services/export/engine.py`.
- La UI **ofrece solo las variables de ese contexto** (un desplegable que las inserta), así RRHH
  no las escribe a mano y no puede inventar una.
- El validador de guardado **rechaza** una variable que el contexto no declara.

Ejemplo de catálogo (código, no datos):

```
"empleado" → nombre_empleado · apellido_empleado · nombre_completo · email_empleado
             empresa_nombre · area_nombre · fecha_ingreso · modalidad_contratacion
             superior_nombre · fecha_hoy · hora_ahora
"vacacion" → todo lo de "empleado" + fecha_desde · fecha_hasta · dias · tipo
"ninguno"  → fecha_hoy · hora_ahora · empresa_nombre
```

⚠️ **`superior_nombre` depende de `manager_id`, que hoy está 0/19** (lo arregla el import de la
sesión anterior, pero hasta que RRHH re-importe sale vacío). Una plantilla que lo use va a mandar
un mail con un hueco. Es un argumento fuerte para el "valor por defecto" de abajo.

### ¿Qué pasa si una plantilla usa una variable que el contexto no provee?

**Las tres cosas, en tres momentos distintos — y ninguna sobra:**

1. **Al GUARDAR: se rechaza.** Es la barrera principal. Una variable fuera del catálogo del
   contexto declarado → 422 con la lista de las válidas. Es el único momento en que hay un humano
   mirando la pantalla y puede corregirlo.
2. **Al RENDERIZAR: no se rompe.** Una variable declarada pero sin valor (el empleado no tiene
   área cargada, `manager_id` vacío) **no puede tumbar el envío**: es un dato faltante, no un
   error de programa. Se reemplaza por un texto neutro configurable por variable
   (`""` o `"—"`), y **se loguea a WARNING**.
3. **Al PREVISUALIZAR: se avisa.** El preview marca en amarillo las variables que quedaron vacías
   con los datos elegidos. Es donde RRHH se entera antes de mandar.

> 🔴 **Por qué (1) no alcanza sola:** el catálogo puede cambiar. Si se saca una variable, las
> plantillas guardadas la siguen teniendo, y sin (2) el primer envío revienta con 500. Y por qué
> (2) no alcanza sola: sin (1), un typo (`{{nombre_emplado}}`) llega al destinatario como texto
> literal, y eso ya pasó — es el mismo modo de falla del `_seen_legajo` del import.

### ⚠️ Qué campos NO deberían estar disponibles

**El catálogo es una allowlist, nunca "todos los campos del empleado menos algunos".** Con
`SELECT *` o exposición automática, **cada columna nueva de `empleados` se vuelve variable de mail
sin que nadie lo decida.** Es exactamente el argumento inverso al de `sin_derivados` en auditoría,
y por el mismo motivo: ahí la pregunta es "¿qué cambió?" y enumerar miente por omisión; acá es
"¿qué se puede mandar por mail?" y enumerar es la única respuesta segura.

**Fuera del catálogo, con motivo:**

| Campo | Por qué no |
|---|---|
| **Todo `costos_nomina`** (`salario_bruto`, `cargas_sociales`, `bonos`, `otros_costos`, `total`) | Sueldo. Un mail se reenvía, se imprime y queda en el buzón del destinatario para siempre. Y hoy `Seccion.COSTOS` está gateada aparte justamente para que no cualquiera lo vea: una variable de plantilla saltearía ese gate |
| `dni`, `cuil` | Documento. No hace falta en ningún mail que RRHH mande y su filtración es cara |
| `fecha_nacimiento` | Dato personal. Un mail de cumpleaños necesita el NOMBRE, no la fecha |
| `domicilio*` (los 6 de la mig 081) | Domicilio particular |
| `telefono`, `telefono_alternativo`, `email_personal` | Contacto personal. `email_corporativo` sí |
| `potencial`, `desempeno` | 🔴 **El peor de todos.** Evaluación interna, nunca comunicada. Un mail con `{{desempeno}}` sería un incidente laboral |
| `motivo_baja`, `entrevista_salida`, `notas_entrevista` | Sensible y sobre un vínculo que terminó |
| `manager_id`, `area_id`, `empresa_id`, y todo id | UUIDs. Un mail con un UUID es un bug visible. Va el nombre resuelto |

**Regla que hay que dejar escrita en el catálogo:** *agregar una variable es una decisión, no una
consecuencia de agregar una columna.*

## (h) Previsualización

**Con datos reales de un empleado que RRHH elige, y con datos de ejemplo como fallback.**

- **Datos reales**, porque es lo único que responde la pregunta que RRHH realmente tiene: *"¿cómo
  le llega esto a Fulano?"*. Con datos de ejemplo, los huecos reales (área sin cargar, superior
  vacío) **no se ven** — y ese es justo el problema que hoy existe.
- El preview **no manda nada**: renderiza y devuelve asunto + cuerpo. Endpoint propio,
  `POST .../preview` con `{plantilla, empleado_id}`, gate de lectura.
- **Datos de ejemplo** para el contexto `ninguno` y para cuando todavía no hay empleados cargados.
- El preview usa **exactamente el mismo renderer** que el envío. Si fueran dos, divergen — es la
  lección de los filtros duplicados front/back.

> ⚠️ **El preview con datos reales lee datos del empleado**, así que va gateado por lectura de
> `EMPLEADOS` además de por la sección de plantillas. Un usuario que puede editar plantillas pero
> no ver empleados no debería sacar datos por esta puerta.

## (i) Registrar qué se envió: **sí, y no es opcional**

Las tres razones que planteás son tres cosas distintas y las tres pesan:

1. **"No me llegó"** — sin log, la respuesta es un encogimiento de hombros. Con log: se sabe si
   salió, a qué dirección exacta, cuándo, y qué respondió Gmail.
2. **No mandar dos veces** — un reintento tras un timeout (ver (l)) puede duplicar. Con una clave
   de idempotencia (`plantilla + entidad + día`) se detecta antes de mandar.
3. **Auditoría** — mandar un mail a nombre de la empresa **es una acción**, y el repo ya tiene la
   regla: toda acción se audita. Sin esto, es la única escritura hacia afuera sin rastro.

**Propuesta:**

```
mail_enviado (
    id, empresa_id, plantilla_clave, contexto, entidad_id,
    destinatario, remitente,
    asunto_render, cuerpo_render,        -- lo que REALMENTE se mandó (reemplaza al versionado)
    estado,                               -- 'enviado' | 'fallido'
    error, gmail_message_id,
    enviado_por, created_at
)
```

**El costo, sin maquillar:**
- **Una tabla más y un repo más** → +1 a portar a asyncpg (hoy 55, regla 14).
- **`cuerpo_render` crece.** Un mail son ~2 KB; 1.000 mails son ~2 MB. Irrelevante hoy, y con
  volumen la salida es una política de retención (borrar el cuerpo a los N meses, conservar el
  resto), no dejar de guardarlo.
- 🔴 **Contiene datos personales por definición** (nombre, mail, y el cuerpo entero). Hereda las
  mismas restricciones que el resto: gateado, y **nunca exportable a Excel sin pensarlo**.

**Además, un evento en `auditoria`** por envío — pero **de lote cuando sea lote**, siguiendo la
regla propia del repo ("al auditar una importación, un evento por lote"). Un envío masivo a 50
personas es UN evento con el conteo, no 50.

---

# PARTE C — El punto de salida único

## (j) 🔴 La forma: `services/mailer/`, calcado de `services/export/`

El molde existe y es exacto. `services/export/` (verificado):

```
services/export/__init__.py      5 líneas — expone SOLO build_export y Descarga
services/export/engine.py       48 — _RENDERERS: Dict[str, Callable] + build_export
services/export/_pdf.py         96 · _excel.py 107 · _csv.py 67 · _word.py 78
```

Las tres propiedades que lo hacen el molde correcto acá:
1. **El `__init__` es el contrato.** Los 11 services que exportan importan `build_export` y nada
   más. Ninguno sabe que existe `_pdf.py`.
2. **El dispatch es un dict**, no una cadena de `if`. Sumar un formato es una entrada.
3. **Es agnóstico de dominio** (lo dice su encabezado): no sabe qué son los datos.

**Traducción:**

```
services/mailer/__init__.py     → expone enviar_mail(...) y nada más
services/mailer/engine.py       → _PROVEEDORES = {"gmail": enviar_gmail}; valida, loguea, audita
services/mailer/_gmail.py       → el único que sabe de Gmail API y de tokens
services/mailer/_render.py      → plantilla + contexto → (asunto, cuerpo). Sin red
```

**Lo que compra concretamente:** cambiar de proveedor es agregar `_ses.py` (o `_resend.py`) y una
entrada en `_PROVEEDORES`. Cero cambios en los callers. Y en la migración a AWS —donde Gmail
puede pasar a SES— eso es un archivo, no un barrido.

**Dos invariantes que hay que fijar el día uno, o el punto único se erosiona:**
- **Nadie llama a `_gmail.py` directo.** Es el equivalente de "todo export pasa por
  `build_export`", que hoy sostiene un test estructural (`test_limite_export.py` barre los 11
  services). **Merece el mismo barrido**: un test que verifique que ningún módulo fuera de
  `services/mailer/` importa `_gmail`, con guarda de mínimo.
- **El log y la auditoría viven en `engine.py`, no en `_gmail.py`.** Si viven en el proveedor, el
  próximo proveedor nace sin log — es exactamente el caso de `verificar_limite_export`.

**Y un helper hermano, molde `_limite_export.py`:** un tope de destinatarios por envío
(constante de módulo, no env var) para que un envío masivo mal armado no se coma el rate limit de
Gmail ni los 300s de Vercel.

## (k) `resend_api_key`: hay que sacarla — hoy solo puede romper

**Verificado:**
- `config/settings.py:57` — `resend_api_key: str`, **sin default**.
- `Settings(BaseSettings)` se instancia en import (`settings = Settings()`).
- **Ningún service la importa.** Los únicos usos en todo el backend son `settings.py` y dos
  asserts en `tests/test_critical_flows.py:135,140`.

**Qué pasa hoy si falta:** pydantic-settings levanta `ValidationError` en el import de
`config.settings` → **el módulo no carga** → no carga `main.py` → **la app no arranca, ni
`/health` responde**. Un 500 de plataforma, sin log útil.

⇒ Es una variable que **no habilita nada y puede tumbar el deploy entero**. Con la decisión de
usar Gmail, sacarla es limpieza, no riesgo.

**Cómo sacarla, en orden:**
1. Borrar `resend_api_key` y `resend_from_email` de `settings.py`.
2. Borrar los dos asserts de `test_critical_flows.py` (son los únicos callers).
3. **Sacar las variables de Vercel `sofia-backend` DESPUÉS de deployar**, no antes: mientras el
   código viejo esté vivo, sacarlas tumba la app.
4. Declararlo en la bitácora — el dev de AWS puede tenerlas en su lista.

> ⚠️ `resend_from_email` (`"noreply@hrkarstec.com"`) SÍ tiene default, así que no rompe nada, pero
> se va con la misma barrida. Ojo: **el dominio ahí es `.com` y el sitio es `.site`** — otra señal
> de que nunca se usó.

## (l) El envío bloquea el request. Cómo resolverlo sin inventar infraestructura

**El escenario, con números:** `backend/vercel.json` declara `maxDuration: 300`. Un envío por
Gmail API es ~1-3 s por mail (más el refresh de token si venció). Un envío individual no es
problema; **50 mails en un request sí**: 50-150 s de un usuario mirando un spinner, y con más
volumen el corte a 300 s con la mitad mandada y sin reporte.

**No hay procesos de fondo:** verificado, cero `BackgroundTasks`, cero `asyncio.create_task`,
cero threading en todo el backend. Y en serverless un thread post-respuesta se muere con la
función.

**Recomendación — el patrón YA está resuelto en este repo, con el import de nómina.** No hay que
inventar nada:

1. **Envío individual: síncrono.** Un mail son 1-3 s. Meterlo en una cola sería infraestructura
   nueva para resolver un problema que no existe.
2. **Envío masivo: presupuesto de tiempo + reporte parcial**, calcado de `LoteNomina`
   (`services/_nomina_lote.py`) y `settings.import_presupuesto_segundos = 280`:
   - Se manda **de a uno, chequeando el margen ANTES de cada mail** (`hay_margen()`), nunca en el
     medio.
   - Al agotarse, se para y se devuelve el reporte de **lo que se mandó y lo que quedó**, con
     `parcial=True`.
   - **La idempotencia hace el resto**: el log de (i) permite reintentar el mismo envío y saltear
     los ya mandados — igual que el dedup por DNI hace continuable el import.
   - 🔴 **Es lo que evita el peor caso**, que no es "tarda": es **mandar 30 mails, morir en el
     timeout, y que el usuario reintente y mande esos 30 de nuevo**.
3. **Rate limit propio.** Franja `scope="mail"`, molde `scope="import"` (10/hora). Un endpoint que
   manda mails a nombre de la empresa no puede correr bajo el baseline de 300/min.

> ⚠️ El presupuesto de mails tiene que ser **más chico que el del import** (280 s), porque acá
> cada unidad es una llamada de red externa con su propio timeout. ~120 s es un punto de partida
> razonable, y el log de (i) da los datos para calibrarlo con la realidad en vez de a ojo.

---

# TRANSVERSAL

## (m) Permisos y dónde vive la pantalla

**Permisos: `Seccion.CONFIGURACION`, mismo criterio que las reglas.** Verificado en
`utils/permisos.py:107-113`: `admin_rrhh` puede todo, `gerencia_lectura` solo READ,
`mandos_medios` solo VACACIONES/AUSENCIAS. ⇒ **crear y editar plantillas queda en admin_rrhh**, y
gerencia_lectura puede leerlas — que es correcto y deseable: quien lee todos los reportes debería
poder ver con qué texto se comunica la empresa.

**No crear una `Seccion` nueva.** El criterio del router de configuración
(`routers/configuracion.py:8-11`) aplica igual acá: una plantilla de mail es una **regla de cómo
opera la empresa**, del mismo tipo que la escala de vacaciones.

**Dónde: sección nueva del panel de configuración, NO pantalla propia.** Cuatro razones:
1. **La conexión de Gmail YA vive ahí** (`IntegracionesSection.tsx` en el acordeón de
   `/configuracion`). Plantillas y la cuenta desde la que salen, en la misma pantalla.
2. Es el mismo dueño y la misma sección de permisos.
3. El gate por bloque ya está resuelto ahí, con los dos criterios distintos ya pensados
   (ocultar vs. solo-lectura) documentados en la propia página.
4. Una pantalla propia pide entrada en el sidebar → `NAV_GROUPS` → y arrastra el test estructural
   `nav-config.test.ts`. Todo eso para algo que se toca dos veces al año.

> ⚠️ **Con una salvedad de UX que no es menor:** editar el cuerpo de un mail necesita más espacio
> que un input de "22 días hábiles". `/configuracion` está en `max-w-2xl`. Lo natural es que la
> **sección** liste las plantillas y **cada edición abra un modal ancho**, molde de los modales
> que ya existen. Si el editor termina pidiendo más, ahí sí conviene su pantalla — pero es una
> decisión que se toma con el editor a la vista, no antes.

## (n) Líneas contra límites

**Lo que se toca (estado HOY):**

| Archivo | Hoy | Límite | Estado |
|---|---:|---:|---|
| 🔴 `services/gmail_service.py` | **150** | 150 | **EN EL LÍMITE — hay que dividir ANTES de tocarlo.** Ver (e) |
| `services/_google_oauth.py` | 136 | 150 | ✅ 14 de margen: el scope nuevo es 1 línea; guardar los scopes concedidos, ~3 |
| `services/integracion_service.py` | 110 | 150 | ✅ |
| `repositories/integracion_repo.py` | 85 | 100 | ⚠️ 15 de margen — alcanza para persistir el token renovado; si además entra `es_remitente_sistema`, queda al filo |
| `services/configuracion_service.py` | 116 | 150 | ⚠️ **no meter plantillas acá** (ver abajo) |
| `routers/configuracion.py` | 55 | 80 | ⚠️ 25 de margen: 4 endpoints nuevos no entran cómodos |
| `config/settings.py` | — | 200 | ✅ (sacar Resend RESTA líneas) |
| `frontend/app/(dashboard)/configuracion/page.tsx` | 79 | 150 | ✅ +1 línea por la sección nueva |

**Archivos nuevos y su presupuesto estimado:**
`services/mailer/{__init__,engine,_gmail,_render}.py` · `services/_google_token.py` ·
`services/_gmail_parseo.py` · `services/plantillas_service.py` ·
`repositories/{plantilla_mail_repo,mail_enviado_repo}.py` · `routers/plantillas.py` ·
`schemas/plantillas.py` + front: `PlantillasSection.tsx`, `PlantillaModal.tsx`,
`usePlantillas.ts` (hook, límite **80**), `services/plantillas.ts`.

🔴 **Dos avisos de arquitectura, no de conteo:**
- **Plantillas NO va dentro de `configuracion_service.py`** (116/150). Comparte la sección de
  permisos, no el service: aquel resuelve escalares y escalas; esto es CRUD de contenido + render
  + envío. Router propio (`routers/plantillas.py`) montado bajo `/api/plantillas`, con
  `SECCION = Seccion.CONFIGURACION`.
- **+2 repos → 57 a portar a asyncpg** (regla 14). Moldearlos sobre `migracionAWS/empleado_repo_NEW`.

## (o) Próximo número de migración libre: **087**

Verificado en las dos carpetas:
- `backend/migrations/` → llega a **086** (`086_create_empleado_superior_pendiente.sql`, de la
  sesión anterior, **todavía sin correr en producción**).
- `migracionAWS/backend/migrations/` → **075, 076, 077**.

⇒ Máximo global **086**, sin huecos reusables. **Próximo libre: 087.**

> 🚩 **La 086 todavía no se corrió.** Si esto avanza antes de deployar aquella, van dos migraciones
> pendientes y el orden importa (086 antes que 087). Declararlo en la bitácora.

Se necesitarían **hasta 3**: plantillas, log de envíos, y —si se toma la opción 1 de (c)— la
columna `es_remitente_sistema`. **Pueden ir en una sola 087**: son del mismo cambio funcional y
partirlas obliga a coordinar tres pasos de deploy en vez de uno.

## (p) 🔴 Qué NO se puede verificar sin una cuenta conectada

### Se puede probar HOY, sin Gmail — y es la mayor parte del trabajo

| Qué | Cómo |
|---|---|
| **El render entero**: sintaxis, sustitución, escapado, variables faltantes | Tests puros. `_render.py` no toca red ni base. **Acá vive el grueso del riesgo lógico** |
| **La validación al guardar** (variable fuera del contexto → 422) | Test de service con fakes |
| **El catálogo de contextos** — que ninguna variable prohibida esté declarada | 🔴 **Test estructural**, molde de los tres barridos que ya existen: barrer el catálogo y afirmar que ninguna clave sale de `costos_nomina`/`potencial`/`desempeno`/`dni`/domicilio, **con guarda de mínimo**. Es lo que impide que la próxima variable se cuele |
| **El punto único** — que nadie importe `_gmail` fuera de `services/mailer/` | Test estructural con guarda de mínimo, molde `test_limite_export.py` |
| **El presupuesto de tiempo y el corte parcial** | Con reloj inyectado, molde exacto de `test_nomina_presupuesto.py` (que ya lo hace y explica por qué no usa `sleep`) |
| **La idempotencia** (no mandar dos veces) | Fake del repo de log |
| **El 403 por scope insuficiente → mensaje accionable** | Fake del cliente HTTP devolviendo 403 |
| **CRUD de plantillas, permisos, preview** | Tests de service + router con fakes |
| **Que sacar Resend no rompe nada** | La suite entera |

### NO se puede probar hasta que Franco conecte su Gmail

| Qué | Por qué |
|---|---|
| 🔴 **Que el mail LLEGUE** | Es lo único que importa de verdad y no hay forma de simularlo |
| 🔴 **Que `gmail.send` sea el scope suficiente** | La pantalla de consentimiento y la respuesta real de Google. Si faltara algo, se descubre acá |
| **El formato como lo ve el destinatario** | Que el HTML renderice bien en Gmail/Outlook. Ningún test lo dice |
| **El flujo de reconsentimiento** (b) | Que reconectar sume el scope sin perder el refresh token |
| **El refresh real contra Google** | Los tests faltean el HTTP; que el `invalid_grant` llegue como se espera, no |
| **El 403 real por scope** | Se puede simular la respuesta, no provocarla |
| **La latencia real por mail** | De ahí sale el número del presupuesto de tiempo. Hasta entonces es una estimación |
| **Límites de envío de Gmail** | Una cuenta personal tiene cuotas distintas a una de Workspace: **el número que se mida con la cuenta de prueba NO es el de la casilla real** |

### Mínimo para desbloquear

**Una cuenta de Gmail conectada** —la personal alcanza— **y un empleado con `email_corporativo`
cargado.** Con eso se prueba el circuito entero de punta a punta.

🔴 **Y la condición para que "el flujo sea idéntico" cuando se mude a la casilla real: cerrar la
decisión de (c) ANTES de escribir código.** Si el remitente sale del usuario logueado, probar con
la cuenta personal y después mudar a la institucional son **dos circuitos distintos** y el
segundo queda sin probar. Con la casilla del sistema, mudarse es reconectar otra cuenta al mismo
usuario técnico: cero código, y lo probado es lo que va a producción.

---

## Apéndice — inventario, para no re-diagnosticar

**Gmail/OAuth:** `services/_google_oauth.py:31-35` (scopes) · `:71-76` (flow) · `:120-129`
(persistencia) · `services/gmail_service.py:42-70` (token+refresh, **los 3 bugs**) · `:150/150` ·
`repositories/integracion_repo.py` (85) · catálogo `usuario_integraciones` (**sin `empresa_id`**).

**Plantillas:** sin tabla · precedente global-con-fallback `migrations/085` (índice único
parcial) · precedente por-empresa `onboarding_templates` · huérfanas `notificaciones`,
`notificaciones_config` (**no reusar**) · campos sensibles en `empleados` y `costos_nomina`.

**Punto único:** `services/export/__init__.py` (5) · `engine.py:16-20` (`_RENDERERS`) ·
`services/_limite_export.py` (68) · `tests/test_limite_export.py` (barrido con guarda).

**Config/permisos:** `utils/permisos.py:69` (`CONFIGURACION`) · `:107-113` (matriz de roles) ·
`routers/configuracion.py` (55) · `services/configuracion_service.py` (116) ·
`frontend/app/(dashboard)/configuracion/page.tsx` (79) · `components/features/configuracion/`
(22 archivos, `IntegracionesSection.tsx` incluido).

**Infra:** `backend/vercel.json` (`maxDuration: 300`) · `config/settings.py:57-58` (Resend) ·
`services/_nomina_lote.py` (molde de presupuesto) · `utils/rate_limit.py` (franjas).
