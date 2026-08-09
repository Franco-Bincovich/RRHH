# Plan de trabajo — HR Karstec

> **5/8/2026. Supersede a `docs/Plan de trabajo`** (v2 del 27/7, sin extensión), que quedó
> desactualizado: sus bloques A, B y C están cerrados y su lectura del estado de datos es de
> cuando había 1 empresa y 19 empleados. **Ese archivo no se borró en esta sesión** — borrarlo es
> una acción de Franco.
>
> Todo lo de acá está verificado contra **el código** y **el catálogo vivo de producción**
> (`grmdiwxcvcjorlohpwji`) el 5/8/2026. No contra la documentación: **cinco cosas que las fuentes
> daban por ciertas ya no lo son**, y están marcadas 🆕 donde aparecen.

---

## 1. Cómo se usa

**Se sigue en orden.** Cada ítem tiene un id estable (`V1`, `F0.2`, `E3`…); una sesión toma UN id.

**Lo que aparezca en el camino y no esté acá se ANOTA en `docs/DEUDA-TECNICA.md` y se sigue.** No
se resuelve en el momento. Ese desvío es lo que este documento existe para cortar: las últimas
seis sesiones arrancaron con un objetivo y terminaron en otro. Salieron cosas buenas de ahí, pero
el saldo es trabajo construido y nunca ejercitado — el módulo de mails entero, por ejemplo.

**Leyenda.** 🖥️ = sesión de Claude Code · 👤 = acción de Franco fuera del código · 🔀 = las dos.
Esfuerzo: **S** ≤1 h · **M** 1-3 h · **L** >3 h. Gravedad: 🔴 rompe/expone · 🟠 va a romper ·
🟡 fricción · ⬜ cosmético.

---

## 2. El orden recomendado, y por qué

**Primero las verificaciones (§4), aunque no sean sesiones.** Son minutos cada una y ejercitan
semanas de código escrito a ciegas. Hoy hay **tres módulos completos que nunca corrieron contra
la realidad**: mails (0 mails enviados, 0 plantillas), CV screening por Gmail (0 vacantes, 0
candidatos) y saldos de vacaciones por período (0 solicitudes). Escribir la fase siguiente encima
de eso es apilar sobre algo que no se sabe si se sostiene.

**Después Google (Fase 0), porque es el cuello de botella de las dos fases que siguen.** Mails y
CV screening dependen los dos del mismo token. Y el orden dentro de Google no es libre: 🆕 **hoy
la cuenta está conectada pero NO hay forma de designarla como casilla del sistema** (§4, V2), así
que la Fase 1 no puede ni empezar hasta cerrar eso.

**Después mails (Fase 1) y recién ahí CV screening (Fase 2).** Los dos usan `_google_token`; si
el refresh está roto, se rompen los dos y conviene descubrirlo en el más barato. Mails es una
llamada por acción y un destinatario controlado; CV screening son N llamadas, un árbol MIME que
no se conoce y una dependencia de PDF sin decidir.

**Los fixes de auditoría (`E1`, `E2`) iban antes de que existiera la segunda empresa con
movimiento — ✅ los dos están HECHOS.** El razonamiento queda escrito porque sigue rigiendo para
lo que venga: hoy hay 2 empresas cargadas pero una sola opera, así que el desajuste
header-vs-entidad todavía no etiquetó mal casi nada. Cuando las dos operen, cada evento mal
etiquetado es un dato perdido en una tabla inmutable. **Lo que NO se cerró es la CLASE de bug:
ver `T11`.**

**Los cortes de archivo van cuando bloquean, no antes.** `routers/vacantes.py` está en 80/80 y la
Fase 2 le agrega endpoints: ese corte es parte de la Fase 2, no una tanda de limpieza. Los 35
archivos del front sobre 150 no bloquean nada y van al final.

---

## 3. Estado real de producción (5/8/2026) — la base de todo lo de abajo

| | | | |
|---|---|---|---|
| empresas | **2** 🆕 (era 1) | empleados | **31** 🆕 (era 19) |
| `manager_id` | **11/31** 🆕 (era 0/19) | `legajo` | **0/31** ❌ |
| `seniority` nulo | 28/31 | áreas | 12 (con 1 duplicada) |
| proyectos | 8 | asignaciones | 31, **las 31 con `valor_hora = 0`** |
| `costos_nomina` | **0** | `solicitudes_vacaciones` | **0** |
| `solicitudes_ausencia` | **0** | `vacaciones_pendientes` | **0** |
| `vacantes` | **0** | `candidatos` | **0** |
| `usuario_integraciones` | **1** 🆕 (era 0) | `es_remitente_sistema` | **false en la única** 🔴 |
| `plantillas_mail` | **0** | `mail_enviado` | **0** |
| `oauth_states` | 2 colgados | `evaluacion_lotes` | 1 (Bloque D sigue bloqueado) |
| `objetivos` | 1 fila | `auditoria` | 139 (10 con `empresa_id` NULL) |
| tablas | 58 | triggers no internos | **50** (39 `updated_at` + 11 `trg_emp_*`) |

**Migraciones: 089, 090, 091 y 092 están las cuatro CORRIDAS** (verificado por catálogo: índice
único en `solicitudes_ausencia` presente · `dias_vacaciones_asignados` nullable sin default ·
triggers de `usuario_integraciones` y `plantillas_mail` presentes · 0 filas con `'SIN DATOS'`).
**No queda ninguna pendiente. El próximo número libre es el 093.**
> 🔴 `CLAUDE.md` y `BITACORA-CAMBIOS.md` siguen diciendo que están pendientes. Ver `E7`.

---

## 4. Verificación — ejercitar lo construido (VAN PRIMERO)

No son sesiones de desarrollo. Son minutos cada una, y verifican semanas de código.

| id | Qué se verifica | Qué se mira y qué tiene que dar | Quién | Esf. |
|---|---|---|---|---|
| **V1** | 🆕 **Que el OAuth de Google funciona de punta a punta** | Ya está: `usuario_integraciones` tiene 1 fila del **3/8 19:24**, `activo=true`, con `access_token`, `refresh_token` y los 4 scopes (`gmail.readonly`, `gmail.send`, `userinfo.email`, `openid`). **El punto (1) de `DIAGNOSTICO-CV-SCREENING.md §s` está CERRADO.** Lo que falta verificar es el **refresh**: `token_expiry` quedó en `2026-08-03 20:24`, o sea vencido hace días y **`updated_at` == `created_at`**, así que el token nunca se renovó. Disparar cualquier lectura de Gmail y confirmar que `updated_at` avanza | 🔀 | S |
| **V2** | 🔴🆕 **Que se puede designar la casilla del sistema** | **NO SE PUEDE.** `IntegracionRemitenteRepo.set_remitente()` tiene **cero callers** en todo el backend: no hay endpoint, no hay service, y `IntegracionesSection.tsx` solo ofrece Conectar/Desconectar. Con `es_remitente_sistema=false`, **todo envío corta con `MAIL_SIN_REMITENTE` (400)**. Es el bloqueante de la Fase 1 entera y **no está en ninguna fuente** | 🖥️ | ver `F1.1` |
| **V3** | **Que un mail sale** | Depende de V2. Después: crear una plantilla en `/configuracion`, `POST /api/plantillas/preview` sin variables sin resolver, `POST /api/plantillas/enviar` a la propia casilla. Tiene que llegar el mail **y** aparecer 1 fila en `mail_enviado` con `estado='enviado'` **y** 1 evento en `auditoria` | 🔀 | S |
| **V4** | **Que la lectura de Gmail anda** | `GET /api/vacantes/{id}/emails-candidatos` sobre una vacante real. Requiere crear 1 vacante (hay 0). Tiene que devolver los mails que matcheen las palabras clave, sin 502 | 🔀 | S |
| **V5** | **El saldo de vacaciones por período** | Construido el 3/8 (`_vacaciones_cupos`, `_vacaciones_fifo`, R11) y **nunca ejercitado**: `solicitudes_vacaciones` y `vacaciones_pendientes` están en 0. Cargar 1 vacación a mano y confirmar que la pantalla y el reporte R11 dan **el mismo número** (es la divergencia que ese commit vino a cerrar) | 🔀 | S |
| **V6** | **El ownership cruzado de `mandos_medios`** | 🆕 Ya es verificable: `manager_id` está 11/31 y hay 2 empresas. Crear un usuario `mandos_medios`, confirmar que ve las vacaciones/ausencias de sus subordinados **incluidos los de la otra empresa**, y **nada más** | 🔀 | M |
| **V7** | **La sesión de 8 h y la baja blanda** | Construido el 3/8. `users.ultimo_acceso` está poblado en 3 de 4. Confirmar: dar de baja a un usuario de prueba → 403 `USUARIO_INACTIVO` en ≤60 s; y que revertir necesita **las dos** mitades (`activo=true` + `ban_duration:none`) | 🔀 | S |
| **V8** | **Los modales largos** | Construido el 3/8 sobre los 35 modales. Abrir `NominaModal` (287 líneas) y `VacanteModal` (251) en una pantalla chica: encabezado y pie fijos, scroll solo en el medio | 👤 | S |

---

## 5. Ejecutable ya — no depende de nadie

| id | Qué | Qué destraba | Quién | Esf. | Grav. |
|---|---|---|---|---|---|
| ~~**E1**~~ | ✅ **HECHO — Auditar el import de costos.** `batch_upsert_nomina` ya no corre sin evento: emite **uno por lote** (`importacion_costos`) desde `services/nomina_import_service.py`, el service nuevo que le faltaba al `confirmar` (era el único de los 3 imports sin capa de service) | ⚠️ **El molde que decía esta fila era el equivocado.** `payload_carga_nomina` es de **UNA FILA** (recibe un `NominaResponse` y difea contra el `prior`): habría dado un evento **por fila**, justo lo que la regla prohíbe. El molde real es **`payload_importacion_nomina`** en `_audit_payloads_import.py` — mismo problema resuelto (`registro_id` = uuid4 de EVENTO, porque `costos_nomina` no persiste un lote con id propio) | 🖥️ | S | ✅ |
| **E2** | **`_costos_write.py:80` audita con la empresa del HEADER**, no la de la entidad. Viola Vista vs Acción | Con 2 empresas cargadas, el desajuste pasa a ser real. Junto: los 3 eventos ya mal etiquetados (`alta_adjunto`, `baja_adjunto`, `baja_candidato`) | 🖥️ | S | 🟠 |
| ~~**E3**~~ | ✅ **HECHO — Guarda de baja del usuario que sostiene la casilla del sistema (409 `USUARIO_ES_REMITENTE_SISTEMA`).** Corre ANTES de tocar al usuario. Vive en `services/_usuario_remitente.py` (satélite: con el razonamiento adentro, `usuario_service` se iba a 171/150) | Es guarda del `activo=false`, no del CASCADE — que **no se tocó**: la baja blanda ya no lo dispara, pero igual apaga el envío porque la integración queda colgando de un usuario inactivo. ⚠️ **Es FAIL-OPEN**: si no se puede leer la casilla, la baja sigue (dar de baja es acción de seguridad; no puede bloquearla un subsistema caído) | 🖥️ | S | ✅ |
| **E4** | **Migrar `objetivos.responsable_id`** de FK a `users` → FK a `empleados` | Desbloquea el filtro por área y el import de objetivos. 🆕 **Hay 1 sola fila: la migración sigue siendo trivial.** Con datos, es cara | 🖥️ | M | 🟠 |
| **E5** | **Los 2 hooks del front sobre 80** (`useFiltrosVacaciones` 95, `useFiltrosAsignacionesCap` 89) | Molde ya aplicado: `useOpcionesAusencias` | 🖥️ | S | 🟡 |
| **E6** | **Dividir `objetivos.py` e `inventario_items.py` (79/80)** y agregarles `shared_limit("30/hour", scope="export")` | Son 2 de los 3 exports que corren bajo el baseline de 300/min. Hay un test que lo recuerda | 🖥️ | S | 🟡 |
| **E7** | **Poner `CLAUDE.md`, `DEPLOY.md`, `BITACORA-CAMBIOS.md` y `DEUDA-TECNICA.md` al día** | Los cuatro mienten hoy: migraciones 089-092 pendientes (están corridas) · `resend_api_key` como obligatoria en `CLAUDE.md` (se sacó, y cargarla en el `.env` **impide colectar los tests**) · 36 triggers vs 50 reales · `manager_id 0/19` vs 11/31 · 19 empleados vs 31 · 1 empresa vs 2 · tests 1551/214 vs 1599/298 | 🖥️ | M | 🟠 |
| **E8** | **Purgar los 2 `oauth_states` colgados** 🆕 | La purga corre solo en el camino que CREA states, así que si nadie vuelve a conectar quedan ahí. Es higiene, no corrección — la verificación ya descarta por `expires_at`. Se limpian solos en la próxima conexión | 👤 | S | ⬜ |
| **E9** | **Los 35 archivos del front sobre 150 + 2 hooks.** `costos/page.tsx` 624 · `vacantes/[id]/page.tsx` 577 · `onboarding/page.tsx` 410 · `ImportarNominaCSVModal` 377 · `offboarding/page.tsx` 307 · `NominaModal` 287 | Molde: `components/features/sucesion/` (855 → 85). 🆕 `dialog.tsx` pasó de 160 a **221** con el fix del 3/8, pero es primitivo de shadcn: no cuenta | 🖥️ | L | 🟡 |
| **E10** | **7 comparaciones `empresa_id !=` post-lectura (Forma B)** en `evaluacion_service` · `adjunto_service` · `cesion_service` · `periodo_service` · `tipos_ausencia_service` · `reporte_export_service` | **No hay oráculo** (todas devuelven 404): es elegancia y costo, no seguridad. Toca 6 services vivos por cero cambio observable | 🖥️ | L | 🟡 |

---

## 6. Bloqueado por RRHH — con el dato exacto que falta

| id | Qué falta | Qué destraba | Estado hoy |
|---|---|---|---|
| **R1** | **El archivo real de vacaciones y ausencias**, con **DNI** (o `legajo` en la nómina mensual) | Es lo ÚNICO que queda del playbook: los filtros ya están. Sin ancla, el import no puede matchear a nadie | `legajo` **0/31**. `solicitudes_vacaciones` y `solicitudes_ausencia` en **0** |
| **R2** | **Cargar `costos_nomina`** | El **historial salarial (C1)** está entero y sale vacío para todos: la serie de esa tabla ES el historial. También la masa salarial y el reporte de presupuesto | **0 filas** |
| **R3** | **Deduplicar `GESTION DE DEUDA` / `GD - GESTION DE DEUDA`** | Con áreas duplicadas, "asignar el área entera" asigna a la mitad de la gente | **2 filas** en `areas`, sigue igual |
| **R4** | **Decidir si `valor_hora = 0` es cero o "no sabemos"** | El reporte de costos lo suma como cero. Son indistinguibles hoy | **31 de 31** asignaciones en 0 |
| **R5** | **Un segundo lote de evaluaciones** | Bloquea el **Bloque D** entero (estadísticas cross-lote): con un solo lote no son verificables | **1 lote** |
| **R6** | **`seniority`** | El reporte de distribución sale casi todo en "Sin especificar" | **28/31 nulo** |
| **R7** | **Resolver el 1 superior pendiente** y decidir si se reimporta | 🆕 `manager_id` ya está 11/31 (RRHH reimportó): `mandos_medios` ya es probable. Queda 1 fila en `empleado_superior_pendiente` | 1 pendiente |
| **R8** | **Sus tipos de ausencia propios** | Recién ahí se desactiva **"Otro"**, que es un anti-tipo: la información se pierde ahí adentro | 3 tipos activos |
| **R9** | **Qué manda de verdad en el asunto de un mail de postulación** | Decide si el formato `[AAA-NNNN]` del matcher sirve. Es una suposición hasta ver el primer mail | Sin datos |
| **R10** | **Si pueden exportar DNI o legajo en evaluaciones** · los 2 líderes sin nota final · qué es "Kolektur" | Pendientes viejos, sin respuesta | — |

---

## 7. Bloqueado por una definición

| id | Qué | Qué depende de esto | Falta para empezar |
|---|---|---|---|
| **D1** | **Link público de carga de horas** (E4 del plan viejo) | Mockup HTML aprobado. **Es una ruta PÚBLICA nueva** — hoy hay exactamente 4, y agregar una toca el middleware, `PUBLIC_ROUTES`, el rate limit y las reglas de WAF del día del cutover | La reunión de definición. Sin ella no se sabe qué autentica el link (¿token por proyecto? ¿por empleado? ¿vencimiento?) |
| **D2** | **Ventana temporal del filtro por proyecto** | Hoy no hay ninguna: las 31 asignaciones tienen `fecha_desde`/`fecha_hasta` en NULL, así que la regla con ventana daría lo mismo y nadie podría probarla | Disparador escrito: **que empiecen a cargarse esas fechas** |
| **D3** | **Plantillas de mail base del sistema** | La 087 no siembra ninguna y hay **0** en producción: el mecanismo de plantilla global (`empresa_id` NULL) está entero y **sin usar** | Qué plantillas trae el sistema de fábrica |
| **D4** | **Borrado de plantillas en la UI** | `DELETE /api/plantillas/{id}` y `borrarPlantilla()` existen y **nadie los llama** | Si el borrado tiene que existir. Es su tanda |
| **D5** | **Un candidato por mail o por adjunto** | Cambia la constraint de idempotencia: `(empresa_id, gmail_message_id)` vs `(…, attachment_id)` | Definirlo **antes** de escribir la migración de la Fase 2 |
| **D6** | **Extractor de PDF** | El formato más común de CV es PDF y **el backend no tiene ninguna dependencia de PDF** (hay `openpyxl` y `python-docx`, nada más). También decide qué significa `ilegible` | Elegir librería, y si hace falta OCR. Antes de la fase 3 del CV screening |
| **D7** | **C6 — plantillas de onboarding públicas/privadas** | Único ítem del Bloque C sin cerrar | Sigue sin alcance definido (§4.3 del plan viejo) |
| **D8** | **Qué es un "equipo"** | `empleados.equipo` es texto libre y está sin poblar; sin definirlo, "asignar por equipo" no existe | Definir si un equipo es distinto de un área |
| **D9** | **`adjuntos` con `entidad_tipo="evaluacion"`** | Está mapeado a una Sección, **no tiene repo resolver** y tiene 0 callers. Hoy es fail-closed con `ENTIDAD_INVALIDA` (400) | A qué apunta exactamente |

---

## 8. Bloqueado por AWS

| id | Qué | Nota |
|---|---|---|
| **A1** | **Porteo de los 69 repos a asyncpg** | Molde: `migracionAWS/empleado_repo_NEW`. Cada repo nuevo suma uno |
| **A2** | **`RATE_LIMIT_STORAGE_URI` → Redis/ElastiCache** | Con `memory://` el límite efectivo es N× el configurado. El enchufe está puesto y probado; **falta la instancia** |
| **A3** | **Recalibrar `TRUSTED_PROXY_HOPS`** | `1` con ALB solo, `2` con CloudFront adelante. 🔴 Un valor de más deja al equipo entero afuera con 429 |
| **A4** | **Re-medir los 4 techos** (`MAX_SIZE_SUBIDA`, `LIMITE_FILAS_EXPORT`, los 2 presupuestos) | Están calibrados contra Vercel. Si el ALB queda en 60 s, el import de 280 s muere antes de poder cortar ordenadamente |
| **A5** | **El equivalente del `ban_duration`** | En AWS no existe: hay que revocar `refresh_tokens` (mig 076). La mitad que corta de verdad (`users.activo`) es columna nuestra y sobrevive |
| **A6** | **Recrear los triggers `updated_at`** | 🆕 **La mig 077 crea 41, y en producción hay 39 + 11 `trg_emp_*` = 50.** `CLAUDE.md` y `DEPLOY.md` dicen 36/45: los dos números están mal |
| **A7** | **Parametrizar `_BUCKET`** (hoy `"documentos"` hardcodeado) + **E2E real de adjuntos**, que nunca corrió | El E2E apunta a producción; por eso nunca se ejecutó |
| **A8** | **Dropear la FK `users.id → auth.users(id)`** + `DEFAULT gen_random_uuid()` | Sin esto no se puede insertar un usuario del otro lado |
| **A9** | **Limpiar las 6 tablas huérfanas y las `ev_*`** | Las 6 huérfanas están en 0 filas. `ev_*` **no se borra antes**: sus 3 routers están montados y responden |
| **A10** | **Storage: ¿Supabase o S3?** | 🔴 Decidir **antes** de la Entrega 2 de evaluaciones (guardar los CSV originales), o se hace dos veces |

---

## 9. Deuda anotada sin prioridad — postergada a propósito

| id | Qué | Por qué se posterga |
|---|---|---|
| **P1** | **Filtro `empresa` duplicado 8× entre repos** | `_with_empresa` existe pero no todos lo usan. Sin efecto observable |
| **P2** | **Presupuesto de tiempo duplicado** (`_nomina_lote` y `_lote_mails`) | Fue decisión consciente con 2 casos. **Con el 3º entrando (CV screening) deja de serlo** — se extrae cuando llegue esa fase, no antes |
| **P3** | **`permisos.ts` ↔ `permisos.py`** sigue siendo espejo manual | Ya tiene test (`test_espejo_permisos.py`). Lo que no tiene es una sola fuente |
| **P4** | **40 mensajes de backend llegan crudos al front** (37 archivos) | No todos son bug: algunos son el mensaje más útil del formulario. No hay forma de distinguir un `AppError` redactado de jerga interna. Es una tanda propia |
| **P5** | **`_postgrest_schema` no cubre queries fuera de los generadores barridos** | Toda query con `select` anidado fuera del barrido sigue siendo punto ciego: verificar en producción tras el deploy |
| **P6** | **Índice normalizado para el matcheo por nombre** | Hoy es una lectura full-table de `empleados`. Disparador: que el padrón pase de unos miles (hoy 31) |
| **P7** | **Un nieto de tipo de ausencia se puede crear por SQL directo** | El CHECK no puede consultar otra fila; la guarda vive en el service. Por la UI no pasa |
| **P8** | **1 adjunto con `empresa_id` NULL** (legacy) | Bloqueado en todos los modos por diseño, o sea inaccesible. Borrarlo o etiquetarlo |
| **P9** | **Filtro por provincia/localidad** | Las 6 columnas existen (mig 081) y `provincia` ya es lista cerrada por endpoint. Barato, pero no hay domicilios cargados |
| **P10** | **Aplicar `ruff format` al repo** | Reflowea archivos enteros (`ausencias_service` 149→253 en la prueba) y **exige re-medir todos los límites**. Tarea propia, nunca dentro de una sesión de feature |
| **P11** | **`ev_*` y las 6 tablas huérfanas** | Se limpian en el cutover (`A9`). No ahora |

---

## 10. Tests y calidad

**Estado real medido hoy** (no lo que dice `CLAUDE.md`):

| | Archivos | Casos |
|---|---|---|
| Backend | **93** `test_*.py` (+ 2 helpers: `_postgrest_schema.py`, `_selects_descubiertos.py`) | **1226** funciones `def test_` → ~1599 ejecutados con `parametrize` |
| Frontend | **26** `*.test.ts(x)` | **262** declaraciones → ~298 ejecutados con `.each` |

> `CLAUDE.md` dice 89/1551 y 16/214. Los dos están dos sesiones atrás. Va en `E7`.

### 10.1 🔴 Cobertura cero en lo que más se usó de excusa para no probar

Verificado por grep de cada símbolo contra `tests/`:

| id | Módulo sin ningún test | Líneas | Por qué importa |
|---|---|---|---|
| **T1** | **`integracion_remitente_repo`** (y `set_remitente`) | 75 | Es la casilla del sistema. **Ningún test, y ningún caller** (§4 V2). El único test que la toca es el del mailer, con un fake |
| **T2** | **`plantillas_service`** (`guardar` / `borrar`) | 133 | `test_plantillas_permisos.py` prueba los **gates**, no el alta ni la edición. `test_mail_variables.py` prueba el **render** |
| **T3** | **`mail_enviado_repo`** | — | La idempotencia del log está probada **solo con un fake**. Es lo que evita reenviar un lote entero tras un timeout |
| **T4** | **`vacante_service`** | **149** | Cero tests, y es donde aterriza el código de vacante de la Fase 2 |
| **T5** | **`candidato_service`** | 97 | Cero tests |
| **T6** | **`gmail_service`** | 122 | Solo aparece en `test_assessment_vacantes_scope.py` (barrera de empresa). **Ningún test funcional del parseo de headers ni del filtro por palabras clave** |
| **T7** | **`_google_oauth.procesar_callback`** — la persistencia de tokens y scopes | 134 | `test_oauth_state` cubre el nonce y `test_google_token` el refresh. Que los **scopes concedidos se guarden** —de lo que depende `puede_enviar()`— no lo prueba nadie |

### 10.2 Tests frágiles o que no pueden fallar

| id | Qué | Mutación que sobreviviría |
|---|---|---|
| **T8** | **Fakes que aceptan `empresa_id` y lo ignoran**: `test_empleado_service.py:128` · `test_audit_instrumentacion_rrhh.py:81` · `test_domicilio_desglosado.py:119` · `test_empleado_area_empresa.py:71` | Borrar `_with_empresa` del repo real. **Están declarados en su docstring y tienen archivo hermano que sí la honra** — es el patrón que `CLAUDE.md` manda, no un descuido. Se anota, no se arregla |
| **T9** | **`loadingSeApaga.test.ts` verifica FORMA, no comportamiento** | Un `finally` que apague el loading equivocado pasa igual. Cubre "alguien borró el apagado", que es lo que tumbó `/proyectos`. Aceptable, pero **no confundirlo con cobertura** |
| **T10** | **vitest corre sin jsdom**: los tests de componente usan `renderToStaticMarkup` y **no ejecutan `useEffect`** | Un guard de permisos borrado dentro de un `useEffect` pasa en verde (caso #4 de la regla transversal). **Cualquier lógica en efectos es invisible para la suite del front** |

### 10.3 Barridos estructurales que faltan

| id | Qué | Qué clase de bug cerraría |
|---|---|---|
| **T11** | **Barrido de "todo repo con método de escritura tiene su evento de auditoría"** | 🆕 **Sigue abierto aunque `E1` ya esté hecho, y por eso mismo:** se arregló LA INSTANCIA (el import de costos), no LA CLASE. El próximo import nace igual de mudo y nadie se entera hasta que alguien mira `/auditoria` y no encuentra nada |
| **T12** | **Barrido de "todo `_*.py` público tiene al menos un caller"** | 🆕 Habría detectado `set_remitente` con cero callers, que es el bloqueante de la Fase 1 entera. Y habría detectado los 3 muertos que se borraron a mano el 2/8 |
| **T13** | **Test que compare `aplicar_filtro_estado` con `derive_estado`** | Son espejo declarado y no hay nada que los ate |

> Con T11-T13 serían **nueve** barridos estructurales. Los seis actuales: paridad list↔export ·
> límite de export · selects de repos · espejo de permisos · nav↔permisos · loading se apaga.
> **Todos llevan guarda de mínimo, y el nuevo también tiene que llevarla.**

---

## 11. Fase 0 — Google operativo

> **Objetivo:** que exista una casilla institucional que lee y manda, y que el token se renueve
> solo. Sin esto las fases 1 y 2 no arrancan.

### F0.1 👤 Consola de Google — lo que no vive en el repo

Nada de esto se puede verificar desde el código. Hay que mirarlo en
`console.cloud.google.com`, proyecto del OAuth client:

1. **Gmail API habilitada** (APIs & Services → Library → Gmail API → Enable). Si no lo está, la
   lectura devuelve 403 y el backend lo envuelve en `GMAIL_ERROR` **502**, que dice otra cosa.
2. **OAuth consent screen**: si está en **Testing**, solo entran las cuentas listadas en *Test
   users* y **el refresh token vence a los 7 días**. Es la explicación más probable de que
   `token_expiry` esté en el 3/8 y `updated_at` no se haya movido. Para producción hay que
   publicarla (**In production**) o mantener la casilla en la lista de test users a sabiendas.
3. **Authorized redirect URIs**: tiene que estar **exactamente**
   `https://sofia-backend-pi.vercel.app/api/integraciones/google/callback`, sin barra final. Un
   solo carácter de diferencia da `redirect_uri_mismatch` en la pantalla de Google, antes de
   llegar a nuestro código.
4. **Scopes en la pantalla de consentimiento**: `gmail.readonly`, `gmail.send`, `userinfo.email`,
   `openid`. Si falta uno, el usuario no lo puede conceder aunque lo pidamos.

> 🔴 **El client secret que apareció en el chat de esta sesión hay que rotarlo** (Credentials →
> el OAuth client → Reset Secret) y actualizar `GOOGLE_CLIENT_SECRET` en Vercel. Rotarlo **no**
> invalida los refresh tokens ya emitidos.

### F0.2 👤 Vercel (`sofia-backend`) — las cuatro variables

Las cuatro tienen default, así que **su ausencia no rompe el arranque: rompe el flujo en
silencio**, con `GOOGLE_NOT_CONFIGURED` (503).

| Variable | Valor de producción |
|---|---|
| `GOOGLE_CLIENT_ID` | el del OAuth client |
| `GOOGLE_CLIENT_SECRET` | 🔴 el **rotado** |
| `GOOGLE_REDIRECT_URI` | `https://sofia-backend-pi.vercel.app/api/integraciones/google/callback` |
| `FRONTEND_URL` | `https://www.hrkarstec.site` — es a donde redirige el callback (`?oauth=google` / `?oauth=error`) |

Después: **redeploy** (son build-time para el proceso) y `curl -i .../health` → 200.

### F0.3 🖥️ Sesión — dar de alta la casilla del sistema

**Es el bloqueante real, y no está en ninguna fuente.** `set_remitente()` existe, está
documentado, respeta el orden desmarcar→marcar que exige el índice único parcial de la 087… y
**nadie lo llama**.

- `POST /api/integraciones/google/remitente` — gate `Seccion.INTEGRACIONES + WRITE`.
- Toggle en `IntegracionesSection.tsx`, visible solo si `google.connected`.
- 🔴 **Rechazar marcar una cuenta sin `gmail.send`**: marcarla deja el sistema en un estado que
  *parece* configurado y falla con 403 en el primer envío. El dato ya está (`puede_enviar`).
- El `IntegracionResponse` ya expone `es_remitente_sistema` — el front solo tiene que pintarlo.
- **Tests:** que marcar desmarque la anterior (idempotencia), y que una cuenta sin `gmail.send`
  no se pueda marcar. Cierra `T1`.

> ⚠️ Mientras tanto se puede desbloquear con un `UPDATE usuario_integraciones SET
> es_remitente_sistema = true WHERE tipo='google'`. **No es la solución**: sin endpoint, el día
> que RRHH cambie de casilla hay que volver a entrar a la base.

### F0.4 🔀 Verificar (V1)

Disparar una lectura de Gmail y confirmar en el catálogo que `usuario_integraciones.updated_at`
avanzó y `token_expiry` quedó en el futuro. **Si no avanza, el refresh está roto** y hay que
mirarlo antes de seguir — los tres bugs que `_google_token.py` arregló vivían justo ahí.

---

## 12. Fase 1 — Mails, ejercitado de punta a punta

> **Objetivo:** que salga el primer mail. Hoy hay 0 plantillas y 0 mails enviados: el módulo
> entero (engine, proveedor, log, auditoría, variables, presupuesto) **nunca corrió**.

| Paso | Qué | Quién |
|---|---|---|
| **F1.1** | `F0.3` completo — sin casilla no hay nada que probar | 🖥️ |
| **F1.2** | Crear **la primera plantilla** desde `/configuracion`. Define `D3` de hecho: la que se escriba primero es la plantilla base | 👤 |
| **F1.3** | **Preview** (`POST /api/plantillas/preview`) contra un empleado real. Tiene que resolver todas las variables de la allowlist y **no dejar ninguna sin resolver**. Con el sidebar en "Todas las empresas" el botón Guardar está deshabilitado a propósito — Previsualizar sigue habilitado | 👤 |
| **F1.4** | **Enviar a la propia casilla.** Verificar las tres cosas: llega el mail · 1 fila en `mail_enviado` con `estado='enviado'` y el texto renderizado · 1 evento en `auditoria` | 🔀 |
| **F1.5** | **Probar el camino de FALLO**: mandar a una dirección inválida. Tiene que quedar 1 fila con `estado='fallido'` y el motivo, **y después** propagar el error. Sin esa fila, "no me llegó" no tiene respuesta | 🔀 |
| **F1.6** | 🖥️ **Tests de `plantillas_service.guardar/borrar` y de `mail_enviado_repo`** (`T2`, `T3`) | 🖥️ |
| **F1.7** | 🖥️ **`E3`** — guarda de baja del usuario que sostiene la casilla | 🖥️ |

> **Lo que NO entra en la Fase 1:** envío masivo real. El presupuesto de tiempo
> (`MAIL_PRESUPUESTO_SEGUNDOS=120`) está construido y probado con fake; ejercitarlo pide un lote
> real, y eso depende de `R2`/`R1`.

---

## 13. Fase 2 — CV screening, fase 1 de 3 (bajar CVs de Gmail)

> **Alcance de esta fase: bajar el adjunto y crear el candidato.** El matcher y el clasificador
> son las fases 2 y 3. **La regla que gobierna todo el módulo:** el clasificador es un **filtro de
> descarte, no una decisión** — no rankea, no elige, y un humano revisa siempre, incluido lo que
> el agente marque `no_relevante`. Va en el docstring del módulo y en la pantalla.

### F2.0 🔀 Armar el escenario ANTES de escribir código

Hay **0 vacantes y 0 candidatos**: no hay nada contra qué probar. Crear 1 vacante con los cinco
campos de requisitos poblados, y mandarle desde otra cuenta un mail con un PDF adjunto. **Esto es
lo primero, no lo último** — sin un mail real no se conoce la forma del árbol MIME, que anida
distinto según el cliente que lo mandó.

### F2.1 🖥️ Las tres divisiones obligatorias — remedidas hoy, **ninguna cambió**

Cada una en su commit, **antes** de escribir nada del módulo:

| Archivo | Hoy | Límite | Corte |
|---|---:|---:|---|
| `routers/vacantes.py` | **80** | 80 | Los 3 endpoints de candidatos/gmail a un router propio |
| `services/vacante_service.py` | **149** | 150 | `_vacante_codigo.py`, función libre. Molde `_vacaciones_write` |
| `services/gmail_service.py` | **122** | 150 | `_gmail_adjuntos.py`: recorrido MIME + descarga + decode. **Sin nada de vacantes ni candidatos** |
| `repositories/vacante_repo.py` | **98** | 100 | Probablemente también, al sumar el lookup por código |

### F2.2 🖥️ Mover la lectura a la casilla del sistema

**Verificado hoy: sigue usando la del usuario** — `gmail_service.py:54` y `:99` llaman a
`access_token_valido(self._integracion_repo, user_id)`. Pasa a `get_remitente()`. Sin esto: los
CVs entran o no según quién apretó el botón, y un proceso automático no puede leer.

> El nombre `integracion_remitente_repo` / `es_remitente_sistema` queda corto: pasa a ser también
> la casilla de **recepción**. **No renombrar la columna** (migración + código por un nombre);
> aclararlo en el docstring.

### F2.3 🖥️ Bajar el adjunto — las cuatro cosas que faltan

1. `format=full` en vez de `format=metadata` (metadata no trae ni cuerpo ni estructura MIME).
2. **Recorrido recursivo de `payload.parts[]`**, juntando las hojas con `filename` no vacío.
3. `GET /messages/{id}/attachments/{attachmentId}` — es una llamada aparte.
4. **`base64.urlsafe_b64decode` con el padding repuesto** — Gmail devuelve base64url (`-`/`_`),
   no base64 estándar.

**Reusar `cv_service.validar()`** para tipo y tamaño; ya tiene el criterio de la subida manual.
**El CV no es un adjunto polimórfico**: es `candidatos.cv_storage_path`, bucket `cvs`, y ya existe
todo el camino de Storage. Meterlo en `adjuntos` daría dos lugares desde donde borrar un CV.

### F2.4 ✅ Idempotencia — RESUELTO, y distinto de como se planteó acá

**Esta entrada describía un bug de `crear_candidato_desde_email`. Esa función ya no existe**: la
sesión del matcher la borró junto con `get_emails_candidatos`, sus dos endpoints, `EmailsSection`
y `EmailCandidatoRow`. No conviven dos criterios de alta desde un mail. Lo que sigue es cómo
quedó, para que nadie implemente de nuevo lo que está abajo.

**La migración salió como 098, no como 093**, y la clave es **`(empresa_id, gmail_message_id,
cv_sha256)`**, no `(empresa_id, gmail_message_id)`. La diferencia es la respuesta a `D5`, que
efectivamente había que resolver primero: **la unidad es el CV, no el mail**. Un mismo mensaje
puede traer dos adjuntos y crear dos candidatos, así que una clave por mensaje habría rechazado
el segundo CV en silencio.

🔴 **Y el hash es del CONTENIDO, no el `attachmentId` de Gmail** —que era la otra opción que esta
entrada contemplaba—: ese id **no es estable entre lecturas del mismo mensaje**, así que como
clave de idempotencia habría dejado entrar duplicados en cada relectura de la casilla. Está
verificado contra la documentación de Google, y escrito en el encabezado de la 098.

⚠️ El índice es **PARCIAL** (`WHERE gmail_message_id IS NOT NULL AND cv_sha256 IS NOT NULL`): los
candidatos cargados a mano no tienen ninguna de las dos columnas y no deben caer bajo la
restricción.

⚠️ **Lo que la idempotencia NO cubre, y sigue abierto:** dedupea por MENSAJE, no por persona. La
misma persona mandando el mismo CV a la misma búsqueda en **dos mails distintos** crea dos
candidatos — `candidatos.email` tiene índice pero no es UNIQUE. Nadie decidió todavía si eso es
un problema.

### F2.5 🖥️ Mails sin match — visibles, nunca en silencio

**Candidato con `vacante_id = NULL`** (la columna ya es nullable), no una tabla nueva. Es el mismo
criterio que ya rige en tres lugares del repo: lo que no resuelve **no es un error, es una fila
para que un humano mire**. El único agregado es un filtro "sin vacante asignada" en el listado —
que por la invariante list↔export tiene que ir **también** en el export, o el test estructural
falla solo.

### F2.6 🖥️ El botón, no un cron

`POST /api/vacantes/revisar-casilla`, gate `Seccion.VACANTES + WRITE`. Vercel no corre nada
periódico, y un proceso automático que corre mientras el matcher no existe no sirve de nada.
**Diseñarlo como función libre que recibe sus colaboradores** (molde `_vacaciones_write`,
`_onboarding_iniciar`): el día que se automatice en AWS, es el mismo service llamado desde otro
lado y no hay que reescribir nada.

**Presupuesto de tiempo obligatorio**: son **dos** llamadas externas por CV (bajar + más adelante
clasificar) y 20 CVs pueden ser minutos. Acá es donde `P2` deja de ser postergable: hay que
**extraer el presupuesto genérico** de `_lote_mails.py` a un módulo propio y que los dos lo usen.

### F2.7 🖥️ Tests

Cierra `T4`, `T5` y `T6`. Como mínimo: el recorrido MIME contra un árbol real capturado en `F2.0`
(anidado, no plano), el decode base64url con padding faltante, y que un segundo llamado con el
mismo `gmail_message_id` **no** cree un segundo candidato.

---

## 14. Fuera de alcance por ahora — nombrado para que no vuelva como novedad

| Qué | Por qué |
|---|---|
| **Fase 2 y 3 del CV screening** (matcher por código, clasificador con Claude) | La fase 1 tiene que estar corriendo con CVs reales primero. El código `[AAA-NNNN]` y `VACANTE_SIN_REQUISITOS` están diseñados en `DIAGNOSTICO-CV-SCREENING.md`, no hace falta rediseñarlos |
| **Bloque D — evaluaciones cross-lote** | 1 solo lote. No es cuestión de esfuerzo: es que las estadísticas no son verificables |
| **Entrega 2 de evaluaciones** (descargar los CSV originales) | 🔴 Depende de `A10` (Supabase o S3), o se hace dos veces. Y es **solo hacia adelante**: el lote de Julio ya existe sin archivos |
| **S6 / DROP de `cargo` y `rol`** | Decisión de producto: no se borra nada. Los fallbacks `roles[0] ?? cargo` quedan |
| **"Compatibilidad con una posición"** (sucesión) | Feature nunca construida — **no es deuda técnica**. Cuando RRHH la reclame, definir qué significa compatibilidad antes de improvisar |
| **Reactivar assessment o sucesión** | Apagados por decisión. Assessment: una env var. Sucesión: dos líneas, una por archivo. **Hacen falta las dos** |
| **Reactivar el reporte adhoc con IA** | Oculto del catálogo, no borrado. Reactivable en una línea |
| **Base de import genérica (`ImportGenerico<T>`)** | Se descartó con fundamento: de las 7 piezas que parecían compartidas solo 3 lo estaban. Ya está en `DECISIONES.md` |
| **Tabla `equipos`** | `D8`. Entregaría una pantalla vacía |
| **RLS a nivel DB para ownership** | En AWS no va: queda app-level definitivo |
| **Renombrar los proyectos de Vercel** a `rrhh-*` | Cambiaría las URLs `*.vercel.app` y rompería `NEXT_PUBLIC_API_URL`. Divergen del nombre del repo **a propósito** |

---

## 15. Lo que este plan agrega y no estaba en ninguna fuente

Marcado 🆕 arriba. Resumido, por si se lee solo esto:

1. 🔴 **`set_remitente()` no tiene callers ni endpoint ni UI** → la casilla del sistema no se
   puede designar → **el módulo de mails entero es inalcanzable hoy** (`V2`, `F0.3`).
2. ✅ **El OAuth de Google SÍ se completó en producción** (1 integración, 3/8, con los dos
   scopes). `DIAGNOSTICO-CV-SCREENING.md §s(1)` y §p están desactualizados.
3. ⚠️ **El token nunca se renovó** (`updated_at == created_at`, `token_expiry` vencido el 3/8) —
   compatible con una consent screen en *Testing*, donde el refresh token vence a los 7 días.
4. ✅ **`manager_id` pasó de 0/19 a 11/31 y hay 2 empresas**: `mandos_medios` y el ownership
   cruzado **ya son verificables con datos reales**. `DEUDA-TECNICA.md §7` dice lo contrario.
5. 🔴 **Cinco módulos con cero tests**, incluidos `vacante_service` (149 líneas) y la casilla del
   sistema. `DEUDA-TECNICA.md §5` listaba tres huecos; son más.
6. **Los triggers en producción son 50** (39 `updated_at` + 11 `trg_emp_*`), no 36 ni 45.
7. **Las migraciones 089-092 están las cuatro corridas**; dos documentos las dan por pendientes.
