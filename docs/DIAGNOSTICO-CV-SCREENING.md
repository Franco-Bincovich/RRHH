# Diagnóstico — CV screening (Gmail → matcher → clasificador)

> **READ-ONLY, 3/8/2026.** Nada de esto está implementado. Verificado contra el código y contra
> el catálogo vivo de producción (`grmdiwxcvcjorlohpwji`).

## 🔴 La regla que tiene que quedar escrita donde se implemente

**El clasificador es un FILTRO DE DESCARTE, no una decisión.** No rankea, no elige y no
recomienda a nadie: separa lo que claramente no aplica de lo que hay que mirar. La decisión es
de RRHH y **un humano revisa siempre**, incluido lo que el agente marcó `no_relevante`. Esto va
en el docstring del módulo del clasificador y en la pantalla, no solo acá.

Consecuencias de diseño que salen de esa regla y no son negociables:

- Las tres clases son `relevante | dudoso | no_relevante`. **Ninguna es "descartado"**: el
  descarte lo hace una persona, y tiene que ser una acción distinta y registrada.
- Un `no_relevante` **no se borra ni se esconde**: se muestra en una pestaña aparte.
- El resultado del agente se guarda **junto a su justificación**. Una etiqueta sin motivo no se
  puede auditar ni discutir, y es exactamente lo que RRHH va a querer discutir.

---

# PARTE A — Lo que ya existe

## a) `gmail_service.py` (122/150) — qué hace hoy

Dos métodos, los dos **por vacante y disparados a mano** desde la ficha de la vacante:

| Método | Qué hace |
|---|---|
| `get_emails_candidatos(vacante_id, user_id, empresa_id)` | `GET /messages?maxResults=50`, se queda con los **primeros 20**, pide cada uno con `format=metadata` (solo `From`, `Subject`, `Date`) y filtra por palabras clave con `_is_cv_email(subject, snippet)`. Devuelve `EmailCandidatoResponse` (id, remitente, asunto, fecha, preview). |
| `crear_candidato_desde_email(vacante_id, email_id, user_id, empresa_id)` | Relee el mail, parsea `From` con `_parse_from_header` y crea el candidato. |

**Qué le falta para bajar adjuntos — cuatro cosas concretas:**

1. **`format=metadata` no trae el cuerpo ni la estructura MIME.** Hay que pedir `format=full`
   para que venga `payload.parts[]` con los `filename` y los `body.attachmentId`.
2. **No recorre `parts[]`.** Un mail con adjunto es un árbol MIME (`multipart/mixed` →
   `multipart/alternative` + la parte del archivo), y las partes anidan. Hace falta un recorrido
   recursivo que junte las hojas con `filename` no vacío.
3. **No llama al endpoint de adjuntos.** Es una llamada aparte:
   `GET /messages/{id}/attachments/{attachmentId}` → devuelve `{size, data}` con el contenido en
   **base64url** (no base64 estándar: `-` y `_` en vez de `+` y `/`; usar `base64.urlsafe_b64decode`
   con el padding repuesto).
4. **No filtra por tipo ni por tamaño.** `cv_service.validar()` ya tiene ese criterio para la
   subida manual — hay que reusarlo, no escribir otro.

**El filtro por palabras clave (`_is_cv_email`) sobra en el flujo nuevo** y conviene no
arrastrarlo: el criterio pasa a ser el código de vacante en el asunto, que es explícito. Dejar
los dos activos a la vez descarta en silencio mails que sí traen código.

## b) Scopes — alcanzan, no hace falta ninguno nuevo

`services/_google_scopes.py`:

```python
SCOPE_LECTURA = "https://www.googleapis.com/auth/gmail.readonly"
SCOPE_ENVIO   = "https://www.googleapis.com/auth/gmail.send"
SCOPES_PEDIDOS = [SCOPE_LECTURA, SCOPE_ENVIO, ".../userinfo.email", "openid"]
```

**`gmail.readonly` cubre `messages.attachments.get`.** No hace falta `gmail.modify` ni
`mail.google.com` — los dos dan el buzón entero para la misma tarea.

> ⚠️ **Pero SÍ hace falta reconectar si aparece un scope nuevo más adelante.** Está documentado
> en ese archivo: Google **no amplía retroactivamente un grant ya otorgado**, así que un scope
> agregado después devuelve **403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`** (no 401) hasta que el
> usuario vuelva a autorizar. Por eso se persisten los scopes concedidos y existe
> `puede_enviar()`. **Si el CV screening llegara a necesitar un scope nuevo, hace falta el mismo
> par: persistir + una función `puede_leer_adjuntos()` que avise ANTES.**

## c) 🔴 De qué casilla lee — ACÁ ESTÁ EL PROBLEMA MÁS GRAVE DE LA PARTE A

**La lectura usa la casilla del usuario, NO la del sistema.** `gmail_service` llama a
`access_token_valido(self._integracion_repo, user_id)`, o sea `IntegracionRepo` scopeado por
`user_id` — la cuenta de Google de quien apretó el botón.

La casilla institucional existe pero **solo la usa el envío**:
`repositories/integracion_remitente_repo.py::get_remitente()` busca
`.eq("tipo","google").eq("es_remitente_sistema", True)` **sin filtrar por usuario**, justamente
porque la pregunta es cuál es la casilla institucional sin importar quién pregunta.

**Para el CV screening hay que mover la lectura a `get_remitente()`.** Sin eso:

- los CVs entran o no según quién apretó el botón y qué casilla tenga conectada;
- un proceso automático no tiene `user_id` que aportar, así que directamente no puede leer;
- el circuito de prueba y el real serían distintos — que es el argumento textual por el que se
  creó la casilla del sistema para el envío.

> El nombre `integracion_remitente_repo` / `es_remitente_sistema` va a quedar corto: pasa a ser
> también la casilla de RECEPCIÓN. **No renombrar la columna** (migración + código por un
> nombre); sí aclararlo en el docstring del repo.

> 🚩 Ya está anotado ahí un pendiente que ahora pesa más: **no hay guarda que impida dar de baja
> al usuario que sostiene la casilla del sistema.** Con el envío eso rompe los mails; con la
> recepción, además, deja de entrar cualquier CV. Sigue sin implementarse.

## d) Vacantes y candidatos — el modelo

**`vacantes`** (28 columnas): `titulo`, `descripcion`, `requisitos`, `funciones`, `formacion`,
`experiencia`, `conocimientos_tecnicos`, `email_contacto`, `estado`, `prioridad`, `area_id`,
`responsable_id`, rango salarial, LinkedIn… **NO hay columna `codigo`.** Hay que agregarla.

**`candidatos`** (23 columnas) — ya trae casi todo lo que el flujo necesita:

| Columna | Nulo | Sirve para |
|---|---|---|
| `vacante_id` | **SÍ** | un candidato puede existir sin vacante → los mails sin match caben acá |
| `cv_storage_path`, `cv_url` | SÍ | el CV bajado |
| `score_ia` | SÍ | **existe y no lo escribe nadie hoy** |
| `estado`, `etapa` | NO | pipeline actual |
| `fuente` | SÍ | de dónde salió (`gmail`) |
| `notas` | SÍ | texto libre |

**Endpoints hoy:** `vacantes` tiene 9 rutas (CRUD + `/candidatos` + `/publicar-linkedin` +
`/emails-candidatos` + `/candidatos-desde-email`); `candidatos` tiene 4 (listar, `cv-url`,
delete, `etapa`).

> ⚠️ **`score_ia` es un número y el clasificador devuelve una CLASE.** No lo reuses: un score
> numérico invita a ordenar por él, que es exactamente lo que la regla del encabezado prohíbe.
> Va una columna `clasificacion_ia` (texto, 3 valores) + `clasificacion_motivo` (texto).

## e) Adjuntos — `candidato` NO es una entidad válida

`services/_adjunto_padres.py::RESOLVERS` tiene **5**: `empleado`, `vacacion`, `ausencia`,
`vacante`, `offboarding`. Una entidad sin resolver corta con `ENTIDAD_INVALIDA` (400), fail-closed.

**Pero no hace falta agregar `candidato`.** El CV **no es un adjunto polimórfico**: es un campo
del candidato (`cv_storage_path`), con su propio bucket y su propio service. Meterlo en
`adjuntos` duplicaría el concepto y dejaría dos lugares desde donde borrar un CV. **Se reusa
`cv_service`, no `adjunto_service`.**

## f) Storage — el bucket ya existe

Cuatro buckets en producción: **`avatars` (público)** · **`cvs` (privado)** ·
**`documentos` (privado)** · **`reportes` (privado)**.

`cv_service.py` (63/150) ya sube al bucket `cvs` con `_BUCKET = "cvs"`, valida tipo y tamaño, y
`candidato_service.py` genera `create_signed_url(..., expires_in=3600)` para descargar.
**El camino de storage está entero: la fase 1 solo tiene que llamar a `cv_service.subir()` con
los bytes que baje de Gmail en vez de con los de un upload del navegador.**

---

# PARTE B — El matcher

## g) 🔴 El código de vacante — lo genera el sistema

**Recomendación: generado, no escrito por RRHH.** Un código tipeado a mano se repite, se escribe
con typos y nadie garantiza que sea único; y como es lo que decide a qué vacante va un CV, un
duplicado manda postulaciones a la búsqueda equivocada sin ningún error.

Formato propuesto: **`[AAA-NNNN]`** — 3 letras + 4 dígitos, ej. `[ECO-2026]`.

- **Corto**, entra en un asunto sin comerlo.
- **Legible y dictable por teléfono** (nada de UUIDs ni base64).
- **Los corchetes son parte del código**, no decoración: acotan la búsqueda en el asunto y
  evitan que `ECO` matchee dentro de una palabra cualquiera.
- Las 3 letras salen del área o del título; los 4 dígitos, de un contador por empresa.

**Dónde vive:** columna nueva `vacantes.codigo TEXT`, con
**`UNIQUE (empresa_id, codigo)`** — no `UNIQUE(codigo)` global: dos empresas del grupo pueden
tener cada una su `[ADM-0001]`, y el flujo ya sabe de qué empresa es la casilla.

> 🔴 **La unicidad va en la BASE, no en el service.** Un chequeo "¿ya existe?" seguido de un
> INSERT deja la ventana abierta entre las dos operaciones; la constraint no.

> ⚠️ **Nullable, y las 0 vacantes de hoy ayudan:** la columna nace vacía y se completa al crear.
> Si algún día hay vacantes viejas sin código, quedan fuera del matcheo — que es correcto, no
> son búsquedas que reciban CVs por esta vía.

## h) El matcheo — comparación simple, no hay nada reusable

Es `codigo.upper() in asunto.upper()`, sobre los códigos activos de la empresa.

**No hay nada que reusar y está bien que no lo haya.** Los normalizadores que existen resuelven
otro problema: `_nomina_parsers._norm` hace `casefold` + colapsa espacios para *deduplicar
nombres*, y `ResolutorIdentidad` de evaluaciones desempata personas por apellido y superior. Acá
la comparación es contra un token generado por nosotros, sin acentos ni ambigüedad.

**Lo que sí hay que decidir de entrada:** qué pasa si un asunto trae **DOS** códigos
(reenvío, cadena de mails). Recomendación: **no elegir** — tratarlo como sin match y mandarlo a
revisión manual. Elegir el primero es una decisión invisible sobre la carrera de alguien.

## i) Mails sin match — visibles, nunca en silencio

**Es el mismo criterio que ya rige en tres lugares del repo** (`sin_candidato` del matcheo de
evaluaciones, `empleado_superior_pendiente` del import de nómina, y los 3 grupos de
`asignados/ya_asignados/errores` de proyectos): lo que no resuelve **no es un error, es una
fila para que un humano mire**.

Dos opciones, y la segunda es mejor:

| Opción | Problema |
|---|---|
| Tabla nueva `cv_sin_match` | Otra tabla, otro repo, otra pantalla, y el CV queda fuera del pipeline |
| **Candidato con `vacante_id = NULL`** | **Ninguno: la columna YA es nullable.** El CV se baja igual, el candidato existe, y RRHH le asigna la vacante desde la UI que ya sabe listar candidatos |

**Recomiendo la segunda.** El único agregado es un filtro "sin vacante asignada" en el listado.

## j) Idempotencia — el `id` de Gmail alcanza, pero hay que persistirlo

El `messages.id` de Gmail es **estable e inmutable por buzón**. Alcanza como clave.

**Lo que falta es dónde guardarlo.** Hoy nada persiste qué mail se procesó:
`crear_candidato_desde_email` recibe el `email_id` del front y crea el candidato sin registrarlo,
así que **llamarlo dos veces con el mismo mail crea dos candidatos**. Ya es un bug hoy, con el
botón manual.

Propuesta: columna `candidatos.gmail_message_id TEXT` + **`UNIQUE (empresa_id, gmail_message_id)`**.
La constraint hace la idempotencia atómica y sirve para el `on_conflict` de PostgREST — es el
mismo razonamiento de la migración 089 para el import de ausencias.

> ⚠️ Un mail puede traer **varios** adjuntos (CV + carta). Si se decide un candidato por adjunto,
> la clave pasa a ser `(empresa_id, gmail_message_id, attachment_id)`. **Definirlo antes de
> escribir la migración**, porque cambia la constraint.

---

# PARTE C — El clasificador

## k) Contra qué compara — hay más estructura de la que parecía

`vacantes` no tiene un solo campo de requisitos: tiene **cinco campos separados**, todos texto
libre y todos nullable — `requisitos`, `funciones`, `formacion`, `experiencia`,
`conocimientos_tecnicos` (+ `descripcion`).

**No están estructurados** (no hay lista de skills, ni años mínimos, ni nada tipado), pero
separados en cinco campos son bastante mejor que un solo blob: permiten armar el prompt por
secciones y decir en la justificación *cuál* requisito no se cumple.

> 🔴 **Los cinco son nullable y hoy hay 0 vacantes.** Una vacante con los cinco vacíos hace que
> el clasificador no tenga contra qué comparar. **Eso no puede terminar en "todo es relevante":
> tiene que cortar antes con un error propio** (`VACANTE_SIN_REQUISITOS`) y no llamar a Claude.

## l) Anthropic — hay molde, con reservas

Cuatro archivos tocan Anthropic: `integrations/anthropic_client.py` (el cliente),
`services/reporte_adhoc.py` (el único uso real), `integracion_service.py` (guardar la API key) y
`_google_oauth.py` (nada que ver, es el import de settings).

**`reporte_adhoc.py` es el molde**: `anthropic_client.messages.create(model="claude-sonnet-4-6",
max_tokens=1500, ...)`, con el contexto armado antes y el resultado parseado después. Su router
lleva **rate limit propio de 20/hora** porque cada request cuesta plata.

**Dos diferencias que hacen que NO se pueda copiar tal cual:**

1. **`reporte_adhoc` está OCULTO del catálogo** (patrón AIPanel) y nunca corrió en producción
   con carga real. Es molde de *forma*, no evidencia de que funcione a escala.
2. Es **una** llamada por request; el clasificador son **N**. Ver (o).

**El modelo se escribe sin fecha** (`claude-sonnet-4-6`): los strings con fecha se retiran y
dan 404. Está en CLAUDE.md y en la lista de minas de AWS.

## m) 🔴 CV que no se puede procesar — se marca, no se descarta

Un PDF escaneado (imagen sin capa de texto), un `.docx` corrupto o un formato raro **no pueden
terminar en `no_relevante`**: eso es afirmar que la persona no aplica cuando lo que pasó es que
no pudimos leer el archivo. Son dos cosas distintas y tienen que verse distinto.

**Hace falta un cuarto estado: `ilegible`**, fuera de las tres clases. Y con él:

- El CV **se guarda igual** en el bucket — es el único ejemplar que existe.
- El candidato se crea igual, con `clasificacion_ia = 'ilegible'` y el motivo técnico.
- La UI lo muestra en la misma pestaña de revisión manual que los sin-vacante.
- **No se reintenta solo.** Un reintento automático contra un PDF escaneado gasta plata y da lo
  mismo.

> ⚠️ **No hay extractor de PDF en el backend.** El repo tiene `openpyxl` (Excel) y `python-docx`
> (Word, export) pero **ninguna dependencia de PDF** — no hay PyMuPDF ni pdfplumber. Y el
> formato más común de CV es PDF. **Es una dependencia nueva y hay que decidirla antes de la
> fase 3**; también es lo que decide qué significa "ilegible" (sin capa de texto ≠ archivo roto).

---

# PARTE D — Operación

## n) 🔴 Botón, no proceso automático — y mi lectura de por qué

**Vercel no corre nada periódico**, y montar un scheduler externo (GitHub Actions, cron de AWS,
Supabase pg_cron) para un módulo que todavía no existe es infraestructura antes que producto.

**Recomiendo un botón "Revisar casilla"**, y no solo por la limitación:

- **Es la fase 1 de tres.** Un proceso automático que corre solo mientras el matcher y el
  clasificador no existen no sirve de nada, y hay que desarmarlo después.
- **Con 0 vacantes y 0 candidatos**, nadie puede saber todavía cuál es la cadencia correcta.
  Un botón la revela: si RRHH lo aprieta 8 veces por día, ahí está el dato para automatizarlo.
- **Un botón tiene dueño.** Un cron que falla a las 3am no lo mira nadie.

**Quién y cada cuánto:** RRHH (`admin_rrhh`, gate `Seccion.VACANTES + WRITE`), **una o dos veces
por día durante una búsqueda activa**. Los CVs no son urgentes en minutos.

> El día que se automatice, el enganche natural es el **cutover a AWS** (ahí sí hay dónde correr
> un job), y el botón se queda igual: es el mismo service llamado desde otro lado. Diseñarlo
> como función libre que recibe sus colaboradores —el molde de `_vacaciones_write` y
> `_onboarding_iniciar`— es lo que hace que ese día no haya que reescribir nada.

## o) Presupuesto de tiempo — el molde de `_lote_mails` aplica, y hace falta

`services/_lote_mails.py` (96/150) ya tiene la pieza: constructor con `presupuesto` y un reloj
inyectable (`time.monotonic`), `hay_margen()`, `destinatarios_con_margen()`, y contadores de
`registrar_envio/omitido/fallo` + `resumen()`.

**Aplica, y con más razón que en los mails**, porque acá son **dos** llamadas externas por CV
(bajar el adjunto + clasificar) y la de Claude tarda segundos, no milisegundos. 20 CVs pueden ser
minutos.

**Los techos que mandan** (los mismos de `_limite_export`): **30 s** del timeout httpx de
Supabase y el límite de la función de Vercel. Un lote sin presupuesto muere por timeout **sin
decir cuántos alcanzó a procesar** — que es el modo de falla que `_lote_mails` vino a evitar.

> ⚠️ **`_lote_mails` está acoplado al vocabulario de mails** (`destinatarios_con_margen`,
> `registrar_envio`). Reusarlo pide **extraer el presupuesto genérico a un módulo propio** y que
> los dos lo usen. Ya está anotado como duplicación pendiente en el Bloque G de CLAUDE.md — esta
> es la segunda ocasión, y la que lo justifica.

## p) Datos en producción — CERO, y peor de lo esperado

| Tabla | Filas |
|---|---|
| `vacantes` | **0** |
| `candidatos` | **0** |
| `usuario_integraciones` | **0** |
| `adjuntos` | 1 |

🔴 **`usuario_integraciones` en 0 significa que NO hay ninguna cuenta de Google conectada.** No
es solo que falten datos de prueba: **el flujo de OAuth nunca se completó en producción**. Antes
de escribir una línea de la fase 1 hay que conectar una casilla y verificar que el token se
persiste y renueva — es la única forma de saber que la base sobre la que se apoya todo esto
funciona.

Se construye a ciegas, igual que el módulo de mails. La diferencia es que acá **sí se puede
armar el escenario**: crear una vacante con código, mandarle un mail con un PDF adjunto desde
otra cuenta, y correr el botón. **Eso es lo primero que hay que hacer, no lo último.**

---

# TRANSVERSAL

## q) Líneas — dónde hay margen y dónde no

| Archivo | Hoy | Límite | Margen |
|---|---|---|---|
| `services/gmail_service.py` | 122 | 150 | 28 — **no alcanza** para el árbol MIME + descarga + decode |
| `services/_google_token.py` | 140 | 150 | 10 |
| `services/_google_scopes.py` | 54 | 150 | 96 |
| `services/cv_service.py` | 63 | 150 | 87 |
| `services/candidato_service.py` | 97 | 150 | 53 |
| `services/vacante_service.py` | **149** | 150 | **1 — el código de vacante NO entra** |
| `services/_adjunto_padres.py` | 95 | 150 | (no se toca) |
| `services/_lote_mails.py` | 96 | 150 | 54 |
| `routers/vacantes.py` | **80** | 80 | **0 — al límite exacto** |
| `routers/candidatos.py` | 53 | 80 | 27 |
| `repositories/vacante_repo.py` | 98 | 100 | 2 |
| `repositories/candidato_repo.py` | 91 | 100 | 9 |

🔴 **Tres divisiones OBLIGATORIAS antes de escribir nada, cada una en su commit:**

1. **`routers/vacantes.py` (80/80)** — cualquier endpoint nuevo lo pasa. Corte natural: los 4 de
   candidatos/gmail (`/{id}/candidatos`, `/candidatos-desde-email`, `/emails-candidatos`) a un
   router propio.
2. **`services/vacante_service.py` (149/150)** — la generación del código no entra. Corte:
   `_vacante_codigo.py`, función libre, molde `_vacaciones_write`.
3. **`services/gmail_service.py` (122/150)** — ya se dividió una vez (el token se fue a
   `_google_token.py`). La bajada de adjuntos es un módulo aparte: **`_gmail_adjuntos.py`**
   (recorrido MIME + descarga + decode base64url), sin nada de vacantes ni candidatos.
4. `repositories/vacante_repo.py` (98/100) — con 2 líneas de margen, agregar el lookup por código
   probablemente también pida cortar.

## r) Migraciones — 🚩 CORREGIDO: las cuatro pendientes YA SE CORRIERON

**Verificado contra el catálogo (3/8/2026), no contra la doc:**

| Mig | Estado | Evidencia |
|---|---|---|
| **089** ausencias unicidad | ✅ **CORRIDA** | índice UNIQUE sobre `solicitudes_ausencia` presente |
| **090** dias_vacaciones nullable | ✅ **CORRIDA** | `dias_vacaciones_asignados.is_nullable = YES` |
| **091** triggers faltantes | ✅ **CORRIDA** | `usuario_integraciones` y `plantillas_mail` ya tienen trigger |
| **092** seniority SIN DATOS | ✅ **CORRIDA** | 0 filas con el literal |

**No queda ninguna migración pendiente. El próximo número libre es el 093.**

> Hay que actualizar CLAUDE.md y la bitácora: las dos dicen que 089–092 están pendientes.

**Migraciones que este módulo va a necesitar (2, o 1 si se juntan):**

- `vacantes.codigo TEXT` + `UNIQUE (empresa_id, codigo)`
- `candidatos.gmail_message_id TEXT` + `UNIQUE (empresa_id, gmail_message_id)` +
  `clasificacion_ia TEXT` + `clasificacion_motivo TEXT`

## s) Lo que NO se puede verificar hasta que haya casilla y CV real

1. **Que el OAuth funcione en producción.** `usuario_integraciones` está en 0: el flujo nunca se
   completó. Ver el (2) del punto n de la sección anterior sobre el `redirect_uri`.
2. **La forma real del árbol MIME.** Gmail anida distinto según el cliente que mandó el mail
   (Outlook, iPhone, webmail). El recorrido recursivo solo se valida contra mails de verdad.
3. **Qué manda RRHH de verdad en el asunto.** Que el código llegue entero y con los corchetes es
   una suposición hasta que se vea el primer mail.
4. **Qué proporción de CVs es PDF escaneado**, que es lo que decide si el extractor de texto
   alcanza o hace falta OCR (otra dependencia, otro costo).
5. **Cuánto tarda una clasificación** con un CV real, que es lo que fija el presupuesto de
   tiempo y el tamaño del lote.
6. **Si el rate limit de Gmail aprieta.** Bajar 20 adjuntos son 40+ llamadas; los cuotas por
   usuario de la API no se conocen hasta ejercitarlas.
