# DIAGNÓSTICO FASE 1 — las cinco features nuevas, los transversales y el lote de DDL

> **Fecha:** 12/8/2026 · **Alcance:** read-only. No se editó código, no se creó ninguna migración,
> no se tocó git.
>
> **Fuentes, en este orden:** (1) el **catálogo vivo** de producción (Supabase
> `grmdiwxcvcjorlohpwji`, "HR Karstec") vía MCP; (2) el **código** del repo. `docs/` **no** se usó
> como fuente — se lo contrasta y, donde difiere, se dice. Cada cifra de datos sale de un `SELECT`
> corrido hoy; cada afirmación de código lleva `archivo:línea`.
>
> **Este documento consolida las dos partes del diagnóstico** (features nuevas + transversales y
> DDL). El intermedio `DIAGNOSTICO-FASE-1A.md` **no se creó**: las dos partes se pidieron en la
> misma sesión y dejar dos archivos tracked con la misma prosa es exactamente el modo de falla que
> `CLAUDE.md` documenta ("si tenés que elegir entre dos copias, ya es tarde"). Todo el contenido de
> la parte A está integrado abajo, en las secciones 1 a 6.

---

## 0. La foto de datos con la que se lee todo lo demás

Verificado contra el catálogo el **12/8/2026**. Casi todas las features nuevas se apoyan en
columnas que hoy están vacías; esto no cambia el diseño, pero sí cambia **qué se puede probar**.

| Tabla | Filas | Tabla | Filas |
|---|---|---|---|
| `empresas` | **2** | `objetivos` | **1** |
| `empleados` | **31** | `objetivo_responsables` | 1 |
| `areas` | 12 | `vacantes` | **1** |
| `auditoria` | 156 | `candidatos` | 3 |
| `proyectos` | 8 | `adjuntos` | **1** |
| `plantillas_mail` | 2 | `onboarding_instancias` | 1 |
| `onboarding_templates` | 1 | `onboarding_tareas` | 2 |
| `onboarding_progreso` | 2 | `parametros_empresa` | **1** |
| `capacitaciones` | **0** | `empleado_capacitacion` | **0** |
| `offboarding_instancias` | **0** | `offboarding_activos` | **0** |
| `costos_nomina` | **0** | `planes_carrera` | **0** |
| `solicitudes_vacaciones` | **0** | `solicitudes_ausencia` | **0** |

Las dos empresas: **KARSTEC - IT NET \| DATOS** (12 empleados, 3 áreas) y **SERVICIOS Y CONSULTORIA
SA KARSTEC SA - UT - DOSUBA** (19 empleados, 9 áreas).

**Triggers no internos en producción: 43** = 35 `set_updated_at` + 8 `fn_misma_empresa`
(`trg_emp_areas`, `trg_emp_ass_campanas`, `trg_emp_ass_links`, `trg_emp_ass_resultados`,
`trg_emp_empleados`, `trg_emp_onb_templates`, `trg_emp_planes_carrera`, `trg_emp_vacantes`).
Coincide con lo que dice `CLAUDE.md`. `trg_emp_sucesion` ya no existe.

---

## 1. PERFILES DE PUESTO

### 1.1 Estructura completa de `vacantes` (32 columnas, catálogo vivo)

Separadas por lo que la feature pide separar: **lo que describe el puesto** (candidato a viajar al
perfil) vs. **lo que describe el proceso de búsqueda** (nunca puede estar en una plantilla).

**DESCRIPTIVAS del puesto — 13 columnas.** Son las que una plantilla copiaría:

| Columna | Tipo | Null | Nota |
|---|---|---|---|
| `titulo` | varchar | NO | |
| `descripcion` | text | SÍ | |
| `requisitos` | text | SÍ | |
| `funciones` | text | SÍ | |
| `formacion` | text | SÍ | |
| `experiencia` | text | SÍ | |
| `conocimientos_tecnicos` | text | SÍ | |
| `modalidad` | varchar | SÍ | CHECK `presencial\|remoto\|hibrido` |
| `tipo_contrato` | varchar | SÍ | CHECK `efectivo\|plazo_fijo\|contratado\|pasantia` |
| `nivel` | varchar | SÍ | CHECK `junior\|semi_senior\|senior\|lider\|manager\|director\|c_level` |
| `jornada` | text | SÍ | libre |
| `ubicacion` | text | SÍ | libre |
| `area_id` | uuid | SÍ | 🔴 FK a `areas` — ver 1.2 |

Las cinco del medio (`funciones`, `requisitos`, `formacion`, `experiencia`,
`conocimientos_tecnicos`) ya están agrupadas y editadas juntas en el front:
`frontend/components/features/vacantes/InformacionPuestoSection.tsx:19-25` las declara en un array
`CAMPOS` con label y placeholder, y las guarda de una sola vez con `updateVacante`
(`:45-51`). **Ese componente de 93 líneas es literalmente el formulario de un perfil de puesto.**

**DE PROCESO — 12 columnas.** Nunca van a una plantilla:
`codigo` (NOT NULL, default `'VAC-' || lpad(nextval('vacantes_codigo_seq'),4,'0')`, CHECK
`^VAC-[0-9]{4,}$`, único por `upper(codigo)`), `estado` (CHECK
`nueva|en_proceso|con_candidatos|cerrada`), `prioridad` (CHECK `baja|media|alta|urgente`),
`cantidad_puestos` (smallint NOT NULL default 1, CHECK > 0), `fecha_apertura`, `fecha_cierre`,
`responsable_id` (FK `users`), `empresa_id` (**NOT NULL**), `created_at`, `updated_at`, `id`,
y `rango_salarial_min`/`max` + `moneda` (que son un caso intermedio: describen el puesto pero se
negocian por búsqueda; hoy tienen 3 CHECKs propios, incluido `chk_rango_salarial`).

**DE PUBLICACIÓN — 5 columnas**, tampoco de plantilla: `linkedin_post_id`, `linkedin_url`,
`copy_publicacion`, `hashtags`, `email_contacto`.

### 1.2 ¿`vacantes` tiene FK a `areas`? Sí — y es el nudo de la feature

```
vacantes_area_id_fkey  FOREIGN KEY (area_id) REFERENCES areas(id) ON DELETE RESTRICT
```

Y hay una segunda defensa, a nivel base:

```
trg_emp_vacantes BEFORE INSERT OR UPDATE ON vacantes
  EXECUTE FUNCTION fn_misma_empresa('area_id','areas')
```

O sea: **la base rechaza una vacante cuyo `area_id` sea de otra empresa que su `empresa_id`.**
`areas.empresa_id` es NOT NULL y hay 12 áreas repartidas 3/9 entre las dos empresas.

**Consecuencia directa: un perfil de puesto del GRUPO no puede llevar `area_id`.** Si lo llevara,
el perfil quedaría atado a una empresa por transitividad y sería usable en una sola — que es
justo lo contrario de lo pedido.

**Cómo se resuelve al copiar hacia la vacante:** el área **no se copia, se elige**. El perfil
aporta los 12 campos descriptivos; `area_id`, `empresa_id`, `responsable_id` y las de proceso las
pone el formulario de alta de vacante, como ya lo hacen hoy. El `trg_emp_vacantes` sigue siendo la
red: si el usuario elige un área de otra empresa, la base rechaza el INSERT antes de que el
service tenga que enterarse.

> ⚠️ El caso simétrico ya está resuelto en el repo y sirve de molde: `onboarding_templates` **sí**
> tiene `area_id` y **sí** tiene su `trg_emp_onb_templates`, porque las plantillas de onboarding
> son POR EMPRESA (`onboarding_templates.empresa_id` NOT NULL). Los perfiles de puesto no lo son —
> es la diferencia que decide el modelo.

### 1.3 Precedentes de "plantilla" en el repo: hay dos, y **los dos REFERENCIAN, no copian**

**a. `onboarding_templates` → `onboarding_instancias`.** `repositories/onboarding_repo.py:46-62`:
al iniciar un onboarding se inserta la instancia con `template_id` y **una fila de
`onboarding_progreso` por cada `onboarding_tareas.id` del template** — guardando el `tarea_id`,
no el texto de la tarea. Editar el nombre de una tarea del template **cambia lo que ven todos los
onboardings en curso**. Es referencia pura.

**b. `plantillas_mail` → `mail_enviado`.** El render resuelve las variables contra el catálogo
allowlist de `services/mailer/_variables.py:49-67` en el momento del envío. Lo que queda
persistido es el mail ya renderizado; la plantilla sigue viva y editable.

**c. Visibilidad — precedente adicional que conviene mirar.** `onboarding_templates.es_publica`
(boolean NOT NULL default `true`) ya existe en producción, con su filtro `with_visibilidad`
reusado desde dos lugares (`repositories/onboarding_repo.py:77-81`). **Es el mecanismo que C6
("plantillas públicas/privadas", declarado NO HECHO en `CLAUDE.md`) pedía, ya construido para
onboarding.** Si perfiles de puesto necesita lo mismo, hay molde exacto.

> 🔴 **Pero el precedente NO aplica a esta feature, y hay que decirlo explícito.** El requisito
> dice: *"se elige un perfil, los campos **se copian** y se editan solo para esa vacante"*. Eso es
> COPIA, no referencia — y es la decisión correcta: una vacante publicada no puede cambiar de
> requisitos porque alguien editó la plantilla seis meses después. **El repo no tiene ningún
> precedente de copia**, así que este sería el primero. Lo que sí se puede seguir del precedente
> es la mecánica de resolución (`ensure_template_accesible` /
> `services/_template_scope.py`) y la de visibilidad.

### 1.4 Qué del front de vacantes se reusa

13 componentes en `frontend/components/features/vacantes/`. Reusables sin tocar o casi:

| Componente | Líneas | Reuso |
|---|---|---|
| `InformacionPuestoSection.tsx` | 93 | 🟢 **El formulario del perfil, tal cual.** Su array `CAMPOS` (`:19-25`) son 5 de los 12 campos descriptivos. Hay que parametrizar el `updateVacante` de `:45` por un callback. |
| `VacantesTable.tsx` | 82 | 🟢 Molde del listado (ordenamiento, estados vacíos). |
| `EliminarVacanteButton.tsx` | — | 🟢 **Patrón canónico de borrado con confirmación** del repo (así lo declara `CLAUDE.md`). Copiar de acá. |
| `VacanteModal.tsx` | **251** | 🟡 Es el alta/edición de vacante, y es donde se agrega el selector de perfil. **Ya está 101 líneas sobre el límite de 150** — ver §11. |
| `PublicacionSection.tsx` | 143 | 🔴 No aplica (LinkedIn). |
| `CandidatoModal`, `CandidatoCard`, `CvField`, `MailsPendientes`, `RevisarCasillaButton`, `CodigoPostulacion`, `VacanteImagenes`, `ImagenCard` | — | 🔴 No aplican. |

Backend reusable: `services/_vacantes_export.py` (67) como molde de export,
`services/_vacante_write.py` (100) como molde de write+auditoría.

---

## 2. OBJETIVOS

### 2.1 Estructura actual (catálogo vivo)

`objetivos` — 11 columnas: `id`, `empresa_id` (NOT NULL, FK), `responsable_id` (**NOT NULL, FK a
`users`**), `titulo` (NOT NULL), `descripcion`, `prioridad` (NOT NULL default `'media'`, CHECK
`baja|media|alta`), `estado` (NOT NULL default `'por_hacer'`, CHECK
`por_hacer|haciendo|terminado`), **`fecha_entrega` (date, NULLABLE)**, `created_at`, `updated_at`,
`parent_id` (FK self, ON DELETE CASCADE).

`objetivo_responsables` — 3 columnas: `objetivo_id` + `user_id` (PK compuesta, las dos FK con ON
DELETE CASCADE) + `created_at`. Sin `empresa_id`: se alcanza por el objetivo.

Índices: `idx_obj_empresa`, `idx_obj_estado`, `idx_obj_parent`, `idx_obj_responsable`,
`ux_objetivo_responsable_titulo`, `objetivos_pkey`. En la puente: `idx_obj_resp_user` +
la PK.

**¿Hay algún campo de período hoy? NO.** Lo más cercano es `fecha_entrega`, que es un vencimiento
puntual y **nullable**. No hay `anio`, ni `periodo`, ni `trimestre`, ni recurrencia. Confirmado
contra el catálogo, no contra docs.

**Y no hay `area_id`** — correcto, y es decisión cerrada (`responsable_id → users`, los objetivos
son tablero del equipo de RRHH).

### 2.2 El filtro de texto libre con desplegable de valores usados: **existe, y SÍ está atado a `empleados`**

- `services/empleado_catalogos_service.py:15-18` — `CAMPOS_AUTOCOMPLETABLES`, **9 campos**:
  `gerencia`, `sector`, `seniority`, `tipo_contrato`, `perfil`, `categoria`, `ubicacion`,
  `organismo`, `tipo_documento`.
- `services/empleado_catalogos_service.py:29-37` — valida el campo contra la whitelist y delega.
- `repositories/empleado_roles_repo.py:10` — **`_TABLE = "empleados"` es una constante de módulo**,
  y `get_valores_conocidos` (`:28-41`) hace `supabase_admin.table(_TABLE).select(campo)` y
  deduplica en Python.

**Veredicto: el mecanismo es reusable, la implementación no.** El repo está hardcodeado a
`empleados` en tres puntos (la constante, el select, y el hecho de que **no filtra por empresa a
propósito** — es un pool compartido entre empresas, documentado en el docstring de `:15-19`).

Además hay un detalle que lo hace más caro de lo que parece: ese repo tiene una **excepción
declarada** en el barrido de selects — `tests/test_selects_repos.py:99` lo declara con
`(1, "select(campo): UNA columna de la whitelist CAMPOS_AUTOCOMPLETABLES")`. Si se generaliza a dos
tablas, esa excepción **deja de decir la verdad** y hay que actualizarla (el barrido verifica el
conteo por archivo, así que un segundo select dinámico en el mismo archivo lo rojea).

Y del otro lado: `frontend/components/features/objetivos/ObjetivosFiltros.tsx` **no usa
`FiltersBar` ni `useFiltros<Modulo>`** — son 4 `<select>` escritos a mano, y su encabezado
(`:14-16`) declara explícitamente que no se migraron porque "eso es un rediseño del filtro, no una
división". Agregar dos filtros nuevos ahí es el momento de migrarlo, o de escribir dos controles
más a mano.

### 2.3 🔴 El índice único: sí colisiona con periodicidad, y ya lo resolvió una vez

```sql
CREATE UNIQUE INDEX ux_objetivo_responsable_titulo
    ON public.objetivos USING btree (empresa_id, responsable_id, lower(titulo));
```

`backend/migrations/111_objetivos_dedup.sql:20-53` explica el criterio con precisión, y ese texto
**es la respuesta a la pregunta**:

- La clave natural es **lo que identifica una fila de la planilla**, y eso son las dos columnas que
  el import declara REQUERIDAS (`_objetivos_import_transforms.py:46`): `Titulo` y `Responsable`.
- **`fecha_entrega` se dejó afuera a propósito, por dos motivos** (`111:37-44`): (1) es editable —
  resubir con la fecha corregida crearía un duplicado; (2) **es NULLABLE, y en Postgres los NULL no
  colisionan entre sí**, así que el índice dejaría de deduplicar en silencio para todo objetivo sin
  fecha.

Con `periodicidad`, "Cerrar el trimestre" anual y mensual del mismo responsable **colisionan hoy**:
el segundo rebota con 23505. Las tres salidas, y por qué dos son trampa:

| Opción | Qué pasa |
|---|---|
| **A. Agregar `periodicidad` a la clave, tal cual** | 🔴 **Reproduce exactamente la trampa que la 111 documentó.** Si `periodicidad` es NULLABLE, los NULL no colisionan y el índice **deja de deduplicar** para todo objetivo sin periodicidad — que hoy son los 1 que existen y probablemente la mayoría de los que se importen. |
| **B. `periodicidad` NOT NULL con default (p. ej. `'unica'`)** + agregarla a la clave | 🟢 Sin NULLs no hay agujero. Requiere backfill de la única fila existente (trivial: 1 fila) y decidir el vocabulario ANTES. |
| **C. `coalesce(periodicidad,'')` en el índice** | 🟢 Equivalente a B sin tocar la nulabilidad. Sigue siendo índice por expresión, o sea que sigue **sin servir como target de `on_conflict`** — lo cual no importa: el import de objetivos busca que el INSERT REBOTE, no un upsert (`111:48-49`). |

**Recomendación: B.** Es la que deja el dato legible en la tabla (todo objetivo dice qué
periodicidad tiene) en vez de esconder la decisión dentro de una expresión de índice. El costo es
un `UPDATE objetivos SET periodicidad='unica'` sobre **1 fila**.

DDL resultante (destructivo en el sentido de que **dropea un índice único vigente**):
```sql
ALTER TABLE objetivos ADD COLUMN periodicidad text NOT NULL DEFAULT 'unica'
    CHECK (periodicidad IN (...));               -- vocabulario a definir
DROP INDEX ux_objetivo_responsable_titulo;
CREATE UNIQUE INDEX ux_objetivo_responsable_titulo
    ON objetivos (empresa_id, responsable_id, lower(titulo), periodicidad);
```

> ⚠️ **El nombre del índice se conserva a propósito.** `services/objetivo_service.py` no lo nombra,
> pero el mensaje de error del import y la verificación de la 111 sí. Cambiarlo obliga a tocar los
> dos.

### 2.4 El import por Excel: qué columnas espera y qué cambia

`services/_objetivos_import_transforms.py:39-47`:

| Columna | Estado |
|---|---|
| `Titulo` | **REQUERIDA** |
| `Responsable` | **REQUERIDA** (se resuelve contra `users`, no contra `empleados` — `objetivos_import_service.py:9-14`) |
| `Prioridad` | opcional; valor fuera del enum cae a `"media"` sin rechazar la fila (`:79-83`) |
| `Fecha entrega` | opcional, `d/m/Y` → ISO; ilegible = `None`, no tumba la fila (`:109-127`) |
| `Descripcion` | opcional |
| `Responsables` | opcional, separados por `;` o `,` (`:90-100`) |

Y hay una **lista de rechazo**: `COLUMNAS_JERARQUIA = ["Objetivo padre", "Padre", "Subobjetivo de"]`
(`:50`). Si el archivo trae cualquiera de esas, **el import rechaza el archivo entero** con
`MENSAJE_JERARQUIA` (`:52-56`).

**¿Cambia?** Sí, dos cosas y ninguna es opcional:

1. **`Periodicidad` como columna opcional.** Si no se agrega, todo lo importado nace con el default
   y el índice nuevo deduplica igual que hoy (no rompe). Si se agrega, hay que decidir si un valor
   inválido cae al default (como hace `Prioridad`) o rechaza la fila. **Recomendación: caer al
   default**, por simetría con `Prioridad` y porque el dato importante sigue siendo título +
   responsable.
2. **`Areas involucradas` como columna opcional**, texto libre. Sin normalización: es texto libre
   filtrable, no un catálogo.

El resto del pipeline (`objetivos_import_preview.py`, 129 líneas · `objetivos_import_service.py`,
108) no cambia de forma: `confirmar` va por `ObjetivoService.create`, así que hereda las
validaciones nuevas gratis (`objetivos_import_service.py:53-57`).

---

## 3. RECATEGORIZACIONES

### 3.1 Valores reales en producción (catálogo, 12/8/2026)

| Campo | Valores | Cobertura |
|---|---|---|
| **`cargo`** | *(todos NULL)* | **0 / 31** |
| **`seniority`** | `SENIOR` (1), `TRAINEE` (1), `EXPERT` (1) | **3 / 31** |
| **`categoria`** | `"3"` (2) | **2 / 31** |
| `perfil` | *(todos NULL)* | 0 / 31 |
| `estado` | `activo` (31) | 31 / 31 |

🔴 **Tres cosas que importan de esta tabla:**

1. **`cargo` está 100 % vacío.** Es la columna que la feature pone en el centro ("nuevo cargo") y
   **está deprecada por decisión de producto**: `schemas/empleado_out.py:40` la marca
   `# DEPRECADO (se dropea en S6)`, y `_dashboard_alertas_catalogo.py:73` la excluyó de las alertas
   con la razón *"deprecado por decisión de producto, se resuelve con `roles[0]`"*. El cargo real
   hoy vive en **`empleados.roles` (array, NOT NULL, CHECK `array_length >= 1`)**.
   **Esto hay que decidirlo antes de escribir una línea** — ver §(b) del cierre.
2. **`seniority` viene en MAYÚSCULAS** y sin catálogo: es texto libre alimentado por el import de
   nómina. Si la recategorización va a ofrecer un desplegable, sale de
   `/api/empleados/valores-conocidos?campo=seniority`, que devuelve exactamente esos 3 valores.
3. **`categoria` tiene un solo valor y es `"3"`** — un número guardado como texto. No hay catálogo
   ni CHECK.

### 3.2 🔴 ¿La auditoría YA registra el diff de un update de empleado? **SÍ, y con más cobertura de la que uno esperaría**

Esta es la pregunta que decide si la tabla nueva sobra. La respuesta honesta tiene tres capas.

**Capa 1 — sí, se registra, y es un diff real.** `services/_empleados_write.py:108` llama a
`payload_update_empleado(prior, empleado, usuario_id, empleado.empresa_id)` en **todo** update.
`services/_audit_payloads_rrhh.py:60-67` arma el diff con
`AuditService._diff(sin_derivados(prior, _DERIVADOS_EMPLEADO), sin_derivados(nuevo, ...))`.

**Capa 2 — el diff EXCLUYE, no enumera**, así que `cargo`, `seniority` y `categoria` entran solos.
`_DERIVADOS_EMPLEADO = {"area_nombre", "empresa_nombre", "manager_nombre"}`
(`_audit_payloads_rrhh.py:31`) son las **únicas tres** exclusiones. Todo lo demás que esté en
`EmpleadoResponse` se auditá. Y los tres campos de la feature están en
`schemas/empleado_out.py:40` (`cargo`), `:64` (`seniority`), `:66` (`categoria`).

**En producción hay 95 eventos `update_empleado`** (de 156 filas de `auditoria`). El mecanismo está
vivo, no es teórico.

**Capa 3 — el límite real, que nadie escribió hasta ahora.** El diff se arma sobre
`EmpleadoResponse`, **no sobre las 56 columnas de la tabla**. Lo que la tabla tiene y el Response
no, queda **fuera de la auditoría en silencio**:

> `fecha_egreso` · `motivo_baja` · `equipo` · `liderazgo` · `co_sourcing` · `product_owner` ·
> `fecha_ingreso_reconocida` · `potencial` · `desempeno` · `foto_url` · `user_id` · `updated_at`

No es un problema para esta feature (los tres campos que importan sí están), pero **es un hallazgo
que corresponde anotar**: el comentario de `_audit_payloads_rrhh.py:55-59` dice que excluir en vez
de enumerar hace que "una columna nueva quede auditada sola", y eso es cierto **solo si la columna
nueva también se agrega a `EmpleadoResponse`**.

### 3.3 Entonces: ¿la tabla nueva sobra?

**No, pero por menos motivos de los que parecía.** Lo que la auditoría **ya cubre**: qué cambió, de
qué valor a qué valor, quién lo hizo, cuándo, en qué empresa, sobre qué empleado
(`registro_id = empleado.id`). Es consultable: `/auditoria` ya filtra por entidad, evento, usuario,
registro y rango de fechas (`repositories/audit_repo.py`).

Lo que la auditoría **NO** puede dar, y no por un ajuste:

| Falta | Por qué no se puede meter en `auditoria` |
|---|---|
| **`motivo`** | La auditoría registra un hecho técnico ("este campo pasó de X a Y"). El motivo es un dato de negocio que el usuario escribe. Meterlo en el JSONB del diff sería inventar un campo que no cambió. |
| **`impacto_salarial`** | Es un dato de otra tabla (`costos_nomina`, hoy en 0 filas) y de otra sección de permisos (`Seccion.COSTOS`). Un evento de auditoría de `empleado` que lleve un sueldo adentro **saltea el gate de costos** — el mismo argumento por el que `services/mailer/_variables.py:34-36` excluye el sueldo de las variables de mail. |
| **`fecha_efectiva`** | La auditoría fecha **cuándo se cargó**, no **desde cuándo rige**. Una recategorización cargada el 12/8 con efecto desde el 1/7 es indistinguible. |
| **Escritura por parte de RRHH** | `auditoria` es **inmutable por diseño**. Una recategorización mal cargada no se puede corregir. |
| **"RRHH carga lo mínimo, el sistema completa el resto"** | El requisito describe un **formulario propio**, con sus valores anteriores precargados. Eso necesita una fila que se pueda leer antes de escribir. |

**Conclusión:** la tabla nueva se justifica por `motivo` + `fecha_efectiva` + `impacto_salarial` +
mutabilidad. **Pero el diff de la auditoría no se duplica**: la recategorización escribe en
`empleados` por el mismo `EmpleadoService.update_empleado` y la auditoría emite su
`update_empleado` como siempre. La tabla nueva es el **registro de negocio**, la auditoría sigue
siendo el **registro técnico**. Los dos, y ninguno reemplaza al otro.

### 3.4 Qué otras tablas guardan histórico por empleado, y qué patrón usan

| Tabla | Patrón | Sirve de molde |
|---|---|---|
| **`costos_nomina`** | Serie temporal con `UNIQUE (empleado_id, anio, mes)` — **una fila por mes**. `CLAUDE.md` lo llama "la serie ES el historial" (C1, historial salarial). | 🟡 Molde de **serie**, no de **evento**. Una recategorización no ocurre todos los meses. |
| **`cesiones`** (7 col) | Hija de empleado, sin estado, se lista en la ficha. Auditada (`_audit_payloads_cesion.py`, 10 eventos `alta_cesion` en producción). | 🟢 **El molde más cercano**: hecho puntual, hijo de empleado, visible en la ficha, con auditoría propia. |
| **`planes_carrera`** (13 col) | `cargo_objetivo` (NOT NULL), `fecha_inicio`, `fecha_objetivo`, `progreso`, `estado`. Trigger `trg_emp_planes_carrera` valida `responsable_id`↔empresa. **0 filas.** | 🔴 Es **plan a futuro**, no hecho consumado. No se reusa. |
| **`empleado_superior_pendiente`** (6 col) | Cola de revisión humana del import (mig 086). | 🔴 No aplica. |
| **`evaluacion_evaluados`** | Cuelga del lote, no del empleado. | 🔴 No aplica. |
| **`auditoria`** | Ver 3.2/3.3. | 🟡 Complementa, no reemplaza. |

### 3.5 Si actualiza al empleado, ¿qué triggers se disparan?

**Dos, verificados contra el catálogo:**

1. **`trg_empleados_updated_at`** `BEFORE UPDATE ... EXECUTE FUNCTION set_updated_at()`.
   Consecuencia no obvia: **el KPI de bajas del mes usa `updated_at`, no una fecha de baja**.
   `services/dashboard_service.py:75-82` cuenta `estado='baja'` con
   `.gte("updated_at", ini).lte("updated_at", fin)`. **Una recategorización sobre un empleado ya de
   baja lo re-cuenta como baja del mes en curso.** Con `fecha_egreso` en 0/31 hoy nadie lo ve, pero
   es un bug latente que esta feature puede activar.

2. **`trg_emp_empleados`** `BEFORE INSERT OR UPDATE ... fn_misma_empresa('area_id','areas','manager_id','empleados')`.
   Si la recategorización toca `area_id`, la base valida que el área sea de la misma empresa. Es una
   red gratis; el service ya lo valida antes (`_empleados_write.py:99`).

Y en la migración a AWS, los dos hay que tenerlos presentes: `set_updated_at` lo recrea la 077;
`fn_misma_empresa` lo recrea la **094**, que hoy **está rota** — declara 9 triggers y el noveno es
sobre `sucesion_posiciones`, tabla que la 112 dropeó. Ver §10.

---

## 4. PRÓXIMOS INGRESOS / BAJAS

### 4.1 CHECK completo de `empleados.estado` y su distribución

```sql
empleados_estado_check
  CHECK (estado::text = ANY (ARRAY['activo','baja','licencia','suspendido']::text[]))
```
Default: `'activo'`.

| Valor | Filas |
|---|---|
| `activo` | **31** |
| `baja` | 0 |
| `licencia` | 0 |
| `suspendido` | 0 |

**Los 4 valores existen; solo uno se usa.** `licencia` y `suspendido` están declarados y muertos.

### 4.2 Campos de fecha de `empleados`

| Columna | Tipo | Null | Cobertura hoy |
|---|---|---|---|
| `fecha_ingreso` | date | **NO** | 31/31 · min `2018-02-01`, max `2026-07-21`, **0 futuras** |
| `fecha_egreso` | date | SÍ | **0/31** |
| `fecha_nacimiento` | date | SÍ | 31/31 |
| `fecha_ingreso_reconocida` | date | SÍ | 10/31 |
| `created_at` / `updated_at` | timestamptz | NO | 31/31 |

**Solo 5 fechas, y ninguna es "prevista".** `fecha_ingreso` es NOT NULL, o sea que **un preingreso
tiene que llevar una fecha de ingreso ya cargada** — que es exactamente lo que la vuelve indistinguible
de un ingreso consumado.

⚠️ Además: **ni `fecha_egreso` ni `motivo_baja` están en `EmpleadoUpdate`** (`schemas/empleado.py:107-151`).
La única forma de escribir `fecha_egreso` es `dar_de_baja` (`repositories/_empleado_write_repo.py:76-97`),
que la escribe **junto con `estado='baja'` en un solo UPDATE**.

### 4.3 🔴 ¿El sistema distingue "trabaja acá" de "el legajo está activo"? **NO. Y hay un bug latente ya en producción**

`services/_offboarding_iniciar.py:74-83`:

```python
fecha_egreso = data.fecha_ultimo_dia or (date.today() + timedelta(days=30))
...
empleado_repo.dar_de_baja(str(data.empleado_id), fecha_egreso, empresa_uuid)
```

**Se pone `estado='baja'` en el instante en que se inicia el trámite, con la fecha del último día
en el futuro.** O sea: hoy, si RRHH abre un offboarding el 1/8 con último día el 31/8, **el
empleado desaparece del headcount, de los reportes, del organigrama y del KPI de dotación el 1/8**,
aunque siga trabajando 30 días. Y aparece como "baja del mes" de agosto por `updated_at`.

Con `offboarding_instancias` en **0 filas** nadie lo vio todavía. **La feature 4 no es solo una
mejora: es el arreglo de esto.**

Del otro lado, el ingreso: `repositories/_empleado_write_repo.py:36` hace `payload["estado"] = "activo"`
**incondicionalmente en el alta**. Un empleado dado de alta el 1/1 con `fecha_ingreso` el 15/1 **ya
cuenta como activo el 1/1**: aparece en el listado, en el headcount y en el organigrama.

**Respuesta concreta a "si un empleado tiene ingreso futuro, ¿aparece?":**

| Superficie | ¿Aparece? |
|---|---|
| Listado `/empleados` | **SÍ** — `empleado_repo.find_all` (`:48-49`) solo filtra `estado` si viene, y el front no lo manda por default. |
| Headcount / KPI `empleados_activos` | **SÍ** — `dashboard_service.py:65` cuenta `estado='activo'`. |
| Todos los reportes de dotación | **SÍ** |
| Organigrama | **SÍ** — `organigrama_service.py:49` |
| KPI `ingresos_mes` | **SÍ, pero por `fecha_ingreso`** (`dashboard_service.py:67-73`) — este es el único que ya usa la fecha y no el estado, así que **ya se comporta bien**. |

### 4.4 Todos los lugares que cuentan/filtran empleados activos

Barrido por grep sobre `backend/` excluyendo `tests/`. **17 sitios de producción**, en tres grupos.

**Grupo A — `.eq("estado","activo")`: cuentan de MENOS si aparece un estado nuevo.** Un preingreso o
una baja-en-trámite simplemente no se contaría, que es en general lo correcto para "headcount hoy",
pero hay que revisarlos uno por uno:

| Archivo:línea | Qué |
|---|---|
| `services/dashboard_service.py:65` | KPI `empleados_activos` |
| `services/_dashboard_headcount.py:28` | headcount por área |
| `services/_dashboard_kpis.py:57` | base del % de ausentismo |
| `services/_dashboard_kpis.py:66` | cumpleaños y aniversarios del mes |
| `services/_dashboard_alertas.py:78` | alertas de campo vacío (+ el `href_listado` `?estado=activo`) |
| `services/reportes/_reporte_dotacion.py:23` | headcount por área |
| `services/reportes/_reporte_dotacion.py:82` | total de activos |
| `services/reportes/_reporte_distribucion.py:54` | distribución seniority/modalidad/turno |
| `services/reportes/_reporte_ausentismo.py:64` | base del ausentismo por área |
| `services/reportes/_reporte_saldos.py:54` | saldos de vacaciones |
| `services/_reporte_anual_metricas.py:47` | métricas del reporte anual |
| `services/reporte_adhoc.py:38` | conteo del prompt de IA |
| `services/organigrama_service.py:49` | el árbol |
| `repositories/empleado_roles_repo.py:51` | `get_seleccionables` (poblar selects) |
| `repositories/sucesion_repo.py:82` | módulo apagado |

**Grupo B — `.neq("estado","baja")`: cuentan de MÁS.** Estos **sí se rompen** con un estado nuevo,
porque un preingreso pasaría a contar como headcount:

| Archivo:línea | Qué | Comentario en el código |
|---|---|---|
| `repositories/area_repo.py:17` | empleados por área en `/areas` | `# Excluye 'baja': licencia sigue siendo headcount del área` |
| `repositories/sucesion_repo.py:88` | candidatos por área (módulo apagado) | |

🔴 **El comentario de `area_repo.py:16` es el resumen del problema:** la regla escrita es "todo lo
que no es baja es headcount". Con `preingreso` en el CHECK, esa regla pasa a ser falsa **sin que el
código cambie ni falle**.

**Grupo C — gates de estado, no conteos:**

| Archivo:línea | Qué |
|---|---|
| `services/_identificacion_resolver.py:59` | `if empleado.get("estado") != "activo"` → **rechaza el link público de horas**. Un preingreso no podría cargar horas (correcto), pero un empleado en trámite de baja **tampoco** (probablemente incorrecto: sigue trabajando). |
| `services/asignaciones_service.py:85-87` | `EMPLEADO_INACTIVO` (422) al asignar a un proyecto |
| `repositories/_empleado_write_repo.py:36` | fuerza `'activo'` en el alta |
| `repositories/_empleado_write_repo.py:70-97` | `baja_logica` y `dar_de_baja` |

**Balance: 15 cuentan de menos (revisables), 2 cuentan de más (rompen), 4 son gates que hay que
decidir.** El CHECK de `estado` es el objeto más caro de todo el lote de DDL.

### 4.5 ¿`onboarding`/`offboarding` ya manejan fechas previstas? Sí — y se solapan parcialmente

| Tabla | Columna | Semántica | Cobertura |
|---|---|---|---|
| `onboarding_instancias` | `fecha_inicio` (NOT NULL, default `CURRENT_DATE`) | cuándo arrancó el proceso | 1/1 |
| | `fecha_fin_esperada` | **prevista**, se setea a `hoy+30` en `onboarding_repo.py:51` | 1/1 |
| | `fecha_completada` | efectiva | 0/1 |
| `offboarding_instancias` | **`fecha_notificacion`** (nullable) | 🟢 **cuándo se notificó la baja** — el arranque del trámite | 0 filas |
| | **`fecha_ultimo_dia`** (**NOT NULL**) | 🟢 **el último día real de trabajo** | 0 filas |
| | `estado` | `iniciado\|en_proceso\|completado\|cancelado` | |

🔴 **`offboarding_instancias` YA TIENE la separación efectiva/burocrática que la feature pide, para
el lado de la baja.** `fecha_notificacion` (trámite) + `fecha_ultimo_dia` (efectiva) + `estado`
(cierre del trámite). Lo que falta **no es el dato: es que `empleados.estado` lo respete.** Hoy
`_offboarding_iniciar.py:76` lo ignora y baja al empleado en el acto.

Del lado del ingreso **no hay nada equivalente**: el onboarding se inicia *después* de que el
empleado existe (`_onboarding_iniciar.py:65` exige `ensure_empleado_de_empresa`), así que
`onboarding_instancias.fecha_inicio` no puede ser la fecha del trámite de alta — el trámite empieza
antes de que haya legajo.

**Solapamiento real:** si se agrega `fecha_baja_prevista` a `empleados`, duplica
`offboarding_instancias.fecha_ultimo_dia`. **Recomendación: no duplicar.** El estado de `empleados`
se deriva de la instancia de offboarding, y en `empleados` solo hace falta el estado nuevo.

### 4.6 ¿Los candidatos tienen fecha de ingreso hoy? **NO**

`candidatos` (30 columnas) tiene `fecha_postulacion` (date NOT NULL, default `CURRENT_DATE`),
`created_at` y `updated_at`. **Ninguna fecha de ingreso, ni prevista ni acordada.** El CHECK de
`etapa` llega hasta `oferta` (`postulado|assessment|entrevista_rrhh|entrevista_tecnica|oferta`) y el
de `estado` incluye `contratado` — o sea que el modelo sabe que alguien fue contratado, pero **no
cuándo entra**.

Producción: 3 candidatos, 2 en `postulado` y 1 en `assessment`, los 3 `estado='activo'`. Ninguno
contratado.

**Consecuencia:** "próximos ingresos" no se puede alimentar desde candidatos sin agregar una fecha
ahí, o sin crear el empleado en preingreso. **La segunda es más barata y es la que el modelo
sugiere** (el candidato contratado se convierte en empleado; el empleado nace en `preingreso`).

---

## 5. DASHBOARD, ALERTAS Y EVENTOS

### 5.1 Los KPIs actuales y el patrón `_safe`

Son **11 cálculos** en dos capas (`CLAUDE.md` dice "9 KPIs"; el conteo real de bloques `_safe` es
6 + 5):

**Capa 1 — `KPIResponse`, 6 KPIs** (`services/dashboard_service.py:48-104`):
`empleados_activos` (`:65`) · `ingresos_mes` (`:67-73`, por `fecha_ingreso`) · `bajas_mes`
(`:75-82`, 🔴 **por `updated_at`**) · `costo_nomina` (`:84-88`) · `onboardings_activos` (`:90`) ·
`vacantes_activas` (`:92-95`).

**Capa 2 — `KPIsExtraResponse`, 5 bloques** (`services/_dashboard_kpis.py:96-131`):
ausencias activas hoy (`:29-36`) · % ausentismo del mes + su nota (`:39-60`) · masa salarial
actual/anterior/variación (`:80-86`) · distribución seniority/modalidad (`:89-93`) ·
cumpleaños/aniversarios del mes (`:63-77`).

**El patrón `_safe`, dos niveles distintos:**

- **Por SECCIÓN** (`dashboard_service.py:22-28`): envuelve `kpis`, `headcount` y `alertas`. Si una
  falla, devuelve el default y loguea `dashboard_seccion_fallo`. Los 6 KPIs de la capa 1 caen
  juntos (comparten un solo `_safe`).
- **Por KPI** (`_dashboard_kpis.py:103-109`): cada uno de los 5 extras tiene el suyo, y el que falla
  se anota en `KPIsExtraResponse.errores` — que **viaja al front**.

🚨 Regla que hay que respetar al agregar cualquier KPI nuevo: **un `_safe` propio**. Y hay un
detalle no obvio en `_dashboard_kpis.py:111-114`: la tasa de ausentismo y su nota salen del **mismo**
`_safe` a propósito, porque calculadas por separado podrían mostrar una tasa dividida por 22 con un
texto que dice 20.

### 5.2 `_dashboard_alertas_catalogo.BLOQUEOS`: qué hay y cuánto daría hoy

**5 bloqueos** (`services/_dashboard_alertas_catalogo.py:31-52`), cada uno = "esta tabla está vacía
para esta empresa, y eso deja un módulo sin usar". La query es de EXISTENCIA (`limit 1`), no de
conteo (`_dashboard_alertas.py:60-67`).

| Tipo | Tabla | Nivel | Filas hoy | ¿Dispara? |
|---|---|---|---|---|
| `sin_costos_nomina` | `costos_nomina` | warning | **0** | 🔴 **SÍ**, en las dos empresas |
| `sin_items_inventario` | `inventario_items` | warning | 0 | 🔴 **SÍ** |
| `sin_capacitaciones` | `capacitaciones` | warning | **0** | 🔴 **SÍ** |
| `sin_presupuesto` | `presupuesto_areas` | warning | 0 | 🔴 **SÍ** |
| `sin_vacantes` | `vacantes` | info | **1** (empresa DOSUBA) | 🟡 SÍ en KARSTEC, NO en DOSUBA |

Más **2 campos vacíos** (`:78-86`) y **2 derivadas de KPIs** (`_dashboard_alertas.py:98-107`):

| Tipo | Regla | Hoy |
|---|---|---|
| `empleados_sin_manager` | `manager_id IS NULL AND estado='activo'` | **20 de 31** → sale AGREGADA (umbral nominal = 5, `_dashboard_alertas.py:40`) con link a `/empleados?estado=activo&sin_manager=true` |
| `empleado_sin_email` | `email_corporativo IS NULL AND estado='activo'` | 0 → no dispara |
| `vacantes` (info) | `kpis.vacantes_activas > 0` | 1 en DOSUBA → dispara ahí |
| `onboarding` (info) | `kpis.onboardings_activos > 0` | 1 → dispara |

**Total hoy: ~7 alertas en modo consolidado.** El panel no está vacío, pero **6 de las 7 dicen "no
cargaste datos"** — que es la foto correcta del proyecto.

### 5.3 🔴 Las 4 alertas del mockup, una por una

#### a) Evaluaciones vencidas — 🔴 **el dato NO existe**

`evaluacion_lotes` tiene **5 columnas**: `id`, `empresa_id`, `periodo` (text), `importado_por`,
`created_at`. **No hay fecha de vencimiento, ni fecha objetivo, ni estado.** `evaluacion_evaluados`
y `evaluacion_resultados` tampoco.

Y el motivo es de diseño, no un olvido: **el sistema no evalúa, importa resultados calculados
afuera** (`CLAUDE.md`, y `services/procesos_service.py:17-22` lo dice explícito al explicar por qué
evaluaciones no está en el panel de Procesos: *"un lote importado no tiene el eje que este panel
muestra: no hay abierto/cerrado ni iniciada/finalizada que contar — un lote existe o no existe"*).

**Cuánto da hoy: 0, y daría 0 siempre.** Qué falta: definir **qué es una evaluación vencida** cuando
el sistema no las programa. Las dos lecturas posibles son features distintas:
- "hace más de N meses que no se importa un lote para esta empresa" → derivable de
  `max(created_at)`, **cero DDL**, y probablemente lo que se quiere;
- "hay una evaluación programada que pasó su fecha" → **exige el módulo de programación entero**,
  que no existe.

🔑 **Lo más cercano que SÍ existe es `empleado_capacitacion.fecha_limite`** (date, nullable). Una
alerta de *capacitaciones* vencidas es gratis hoy — solo que la tabla tiene 0 filas.

#### b) Onboarding con tareas pendientes — 🟢 **el dato EXISTE, completo**

`onboarding_progreso`: `estado` (CHECK `pendiente|en_progreso|completado|omitido`), `instancia_id`,
`tarea_id`, `empresa_id`. Y `onboarding_tareas.dias_limite` (smallint NOT NULL, default 1, CHECK > 0)
+ `onboarding_instancias.fecha_inicio` permiten calcular **vencida**, no solo pendiente.

**Cuánto da hoy: 2 tareas pendientes**, en la única instancia (`en_progreso`).

Qué falta: nada de DDL. Una query de conteo y una entrada en el catálogo de alertas — que es
literalmente agregar una tupla (`_dashboard_alertas_catalogo.py:5-6`: *"agregar una alerta es
agregar una tupla acá"*). ⚠️ Pero **no encaja en `BLOQUEOS`** (que es "tabla vacía") ni en
`CAMPOS_VACIOS` (que es "columna de `empleados` en null"): es una **familia nueva** — un conteo con
umbral. Es la primera de las cuatro que obliga a extender el catálogo, no solo a poblarlo.

#### c) Documentos próximos a vencer — 🔴 **NO hay fecha de vencimiento. Esta es la que preocupaba, y con razón**

`adjuntos`, 15 columnas verificadas en el catálogo:
`id`, `entidad`, `entidad_id`, `empresa_id`, `bucket`, `storage_path`, `nombre_archivo`,
`mime_type`, `tamano_bytes`, `categoria`, `descripcion`, `estado`, `subido_por`, `created_at`,
`es_principal`.

**No existe `fecha_vencimiento` ni ninguna fecha que no sea `created_at`.** `categoria` es text
nullable y libre — y de **1 adjunto en producción, su `categoria` es NULL**.

Y hay un segundo problema, más caro que la columna: **la alerta necesita saber qué documentos DEBERÍA
tener cada empleado**, no solo cuáles vencen. Hoy no hay catálogo de tipos de documento
(`categoria` es texto libre sin CHECK ni tabla). Sin eso, "documentos próximos a vencer" solo puede
avisar de los que alguien cargó con fecha — nunca de los que faltan.

**Cuánto da hoy: 0** (1 adjunto, sin categoría, sin fecha). Qué falta: **DDL** (`fecha_vencimiento`
+ índice parcial) **y una decisión de producto** sobre si hay catálogo de tipos.

#### d) Candidatos nuevos por revisar — 🟢 **el dato EXISTE, y hay dos definiciones posibles**

`candidatos.etapa` (CHECK, default `'postulado'`), `candidatos.estado` (default `'activo'`),
`candidatos.clasificacion_ia` (CHECK `relevante|dudoso|no_relevante`, nullable) y
`clasificacion_origen` (`modelo|humano`).

**Cuánto da hoy, según la definición:**

| Definición | Hoy |
|---|---|
| `etapa='postulado' AND estado='activo'` | **2** |
| `clasificacion_ia IS NULL` (sin clasificar) | **1** |
| `clasificacion_ia='relevante' AND etapa='postulado'` | **1** |

Qué falta: **elegir la definición**. Cero DDL. La tercera es la más útil (lo que la IA marcó como
relevante y nadie movió todavía), y es la que aprovecha el bloque F.

### 5.4 🔴 Los 4 eventos del mockup

#### a) Ingreso — 🟢 **existe**

`empleados.fecha_ingreso`, NOT NULL, 31/31. **0 futuras hoy**, así que la lista de "próximos
ingresos" saldría **vacía** hasta que se cargue el primer preingreso. El KPI `ingresos_mes` ya lee
esta columna correctamente (`dashboard_service.py:67-73`).

#### b) Fin de período de prueba — 🔴 **no existe, y `parametros_empresa` NO tiene la regla**

`parametros_empresa`, **11 columnas verificadas** (1 fila en producción):

| Columna | Default | Qué configura |
|---|---|---|
| `base_dias_habiles` | 22 | denominador del ausentismo |
| `corte_antiguedad_mes` | 10 | escala de vacaciones |
| `periodo_vacacional_desde_mes` | 10 | ventana vacacional |
| `periodo_vacacional_hasta_mes` | 4 | ventana vacacional |
| `primer_anio_mes_corte` | 7 | primer año |
| `primer_anio_dias` | 5 | primer año |
| `vencimiento_anios` | 4 | vencimiento de vacaciones |

**Las 7 son de vacaciones y ausentismo. Ninguna es un período de prueba.** No hay nada en ninguna
tabla que dé esa regla: ni en `empleados`, ni en `empresas` (11 col), ni en `tipos_ausencia`.

Qué falta: **una columna en `parametros_empresa`** (`periodo_prueba_dias smallint NOT NULL DEFAULT 90`)
y el cálculo `fecha_ingreso + periodo_prueba_dias`. 🔑 La tabla ya es el lugar correcto: es
por-empresa, tiene su repo con `upsert(on_conflict="empresa_id")`
(`repositories/configuracion_repo.py:36-39`) y su pantalla (`/configuracion`, 81 líneas). ⚠️ Pero el
PUT de esa pantalla **manda el juego completo de parámetros** (nota en
`migrations/100_cv_screening_clasificacion.sql:25`), así que agregar una columna toca el schema de
entrada, el repo, el service y el form. No es solo una columna.

#### c) Inicio de vacaciones — 🟢 **existe** (y la tabla está vacía)

`solicitudes_vacaciones.fecha_desde`. **0 filas.** El KPI de ausencias activas ya usa el mismo tipo
de query (`_dashboard_kpis.py:29-36`). Cuánto da hoy: **0**.

⚠️ Y hay una regla del repo que aplica: el rango se evalúa con **semántica de solapamiento**
(`repositories/_rango_fechas.py`), no de contención. Un evento "próximos 7 días" tiene que usar la
misma o va a divergir del listado.

#### d) Evaluación programada — 🔴 **no existe** (mismo caso que 5.3.a)

Ninguna tabla programa evaluaciones. Cuánto da hoy: 0, y daría 0 siempre.

### 5.5 Eventos manuales (nombre + fecha): ninguna tabla sirve

Se evaluaron las 52 tablas del catálogo. Las tres candidatas y por qué ninguna alcanza:

| Candidata | Por qué no |
|---|---|
| `objetivos` | Tiene `titulo` + `fecha_entrega`, pero `responsable_id` es **NOT NULL** (FK a `users`) y arrastra `estado`, `prioridad`, `parent_id` y el índice único de dedup. Un feriado no tiene responsable. Y contaminaría el tablero de objetivos y el Panel de Procesos (`procesos_service.py:28`). |
| `periodos_cerrados` | Es un bloqueo de escritura por módulo (`modulo`, `desde`, `hasta`, `estado`, `cerrado_por`). Semántica opuesta. |
| `onboarding_tareas` | Cuelga de un template y de una instancia. No es una agenda. |

**Es tabla nueva.** Es la más barata del lote: sin FKs más allá de `empresas`, sin estado, sin
jerarquía.

### 5.6 El aviso "una semana antes": ¿hay algo configurable parecido?

Sí, **dos precedentes con formas distintas**:

1. **`parametros_empresa`** — 7 parámetros numéricos por empresa, editables desde `/configuracion`,
   con su repo y su upsert. 🟢 **Es el molde**, si el aviso es una política de la empresa.
2. **Constantes de módulo** — `services/_limite_export.py::LIMITE_FILAS_EXPORT = 5000` y
   `services/_dashboard_alertas.py:40::_UMBRAL_NOMINAL = 5`. El repo tiene una regla escrita para
   elegir: `LIMITE_FILAS_EXPORT` es constante y **no** variable de entorno *"porque subirlo exige
   revisar los techos de tiempo, y eso es una decisión, no configuración"* (`CLAUDE.md`).

**Aplicando esa misma regla al aviso:** 7 días **no** tiene una restricción técnica detrás, es una
preferencia de RRHH → va configurable. **Dónde**: si el aviso es igual para todos los eventos,
`parametros_empresa.dias_aviso_evento`; si cada evento manual quiere el suyo,
`eventos_agenda.dias_aviso` con default 7. **Recomendación: las dos** — el parámetro de empresa como
default y la columna por evento como override, que es exactamente el patrón ya usado en
`empleados.dias_vacaciones_asignados` (`schemas/empleado_out.py:43-50`: *"NULL = se aplica la regla
por antigüedad · un entero = override permanente de esa persona, que gana sobre la regla"*).

---

## 6. FORMACIÓN vs CAPACITACIONES

> 🔒 El Excel de formación no llegó. Todo lo de abajo es lo que se puede afirmar del código y del
> catálogo.

### 6.1 Estructura y filas

**`capacitaciones` — el catálogo, 10 columnas, 0 filas:**
`id`, `empresa_id` (NOT NULL, FK), `nombre` (NOT NULL), `descripcion`, `categoria` (text libre),
`duracion_horas` (**numeric, nullable**), `obligatoria` (bool NOT NULL default false), `activo`
(bool NOT NULL default true), `created_at`, `updated_at`.
Índices: `capacitaciones_pkey`, **`capacitaciones_id_empresa_id_key` (id, empresa_id)** —
existe para sostener la FK compuesta de abajo — e `idx_cap_empresa_id`.

**`empleado_capacitacion` — las asignaciones, 11 columnas, 0 filas:**
`id`, `empresa_id` (NOT NULL), `capacitacion_id` (NOT NULL), `empleado_id` (NOT NULL), `estado`
(CHECK `pendiente|en_curso|completado`), `fecha_asignacion`, `fecha_limite`, `fecha_completado`,
**`certificado_url`**, `created_at`, `updated_at`.
🔑 **Dos FKs COMPUESTAS**: `ec_capacitacion_empresa_fk (capacitacion_id, empresa_id) → capacitaciones(id, empresa_id)`
y `ec_empleado_empresa_fk (empleado_id, empresa_id) → empleados(id, empresa_id)`. Es de las 22 FKs
compuestas del modelo: **la base impide asignar un curso de una empresa a un empleado de otra.**
Unicidad: `(capacitacion_id, empleado_id)`.

### 6.2 Qué se puede hacer HOY

- **Catálogo por empresa** con ABM (`services/capacitacion_service.py`, 98 líneas) y **baja
  inteligente**: soft-delete si tiene asignaciones, hard-delete si no (`:84-98`).
- **Asignar** un curso a un empleado (`services/asignacion_service.py`, 127 líneas), con la empresa
  heredada del empleado (`:61`) y el curso validado contra esa empresa (`:64`).
- **Estados** con auto-completado de `fecha_completado` al pasar a `completado` (`:87-88`).
- **Certificado por asignación**: upload al bucket privado `documentos` (`:104-118`) y descarga por
  URL firmada de 3600 s (`:120-127`). Tipos permitidos: PDF, JPG, PNG, WEBP (`:23`).
- **Dos exports**, con filtros distintos: el del catálogo (`solo_activos`) y el de asignaciones
  (`area · capacitación · empleado · estado`).
- **Panel de Procesos** cuenta `empleado_capacitacion` por estado (`procesos_service.py:27`).
- **Reporte** de capacitación por área (`services/reportes/_reporte_capacitacion.py`, 58 líneas).
- **Alerta** de catálogo vacío (`_dashboard_alertas_catalogo.py:40-43`).

### 6.3 Qué NO se puede hacer, y que un Excel de formación probablemente pida

| Necesidad | ¿Existe? | Qué falta |
|---|---|---|
| **Historial por persona** | 🟡 **Parcial, y el límite es duro.** `UNIQUE (capacitacion_id, empleado_id)` significa **una fila por par**: si alguien hace el mismo curso dos veces (recertificación anual), **no se puede registrar**. Se pisa. | Agregar `anio`/`edicion` a la clave única, o una tabla de ediciones. |
| **Horas** | 🟡 `capacitaciones.duracion_horas` existe, **pero es del CURSO, no de lo que la persona cursó**. Si alguien hizo 6 de 8 horas, no hay dónde. | `empleado_capacitacion.horas_cursadas numeric`. |
| **Certificados** | 🟢 **Existe y funciona** (`certificado_url` + Storage + URL firmada). | Nada. ⚠️ Pero **no tiene fecha de emisión ni de vencimiento** — mismo hueco que `adjuntos` (§5.3.c). |
| **Proveedores / instituciones** | 🔴 **No existe.** `categoria` es texto libre y no es eso. | Columna o catálogo. |
| **Costos** | 🔴 **No existe.** Ni en el curso ni en la asignación. Y `presupuesto_areas` no tiene tipo de costo "capacitación" declarado. | Columna + decisión de si entra al presupuesto por área. |
| **Nota / aprobación** | 🔴 No existe. `estado` llega hasta `completado`. | |
| **Modalidad (presencial/online), fechas de dictado** | 🔴 No existe. | |
| **Obligatoriedad por área o por rol** | 🟡 `obligatoria` es un bool **global del curso**. | |
| **Formación externa autogestionada** | 🔴 No existe: toda fila necesita un `capacitacion_id` del catálogo. Un posgrado que la persona hizo por su cuenta **no se puede cargar sin inventar una entrada de catálogo**. | Es el hueco conceptual más grande. |

### 6.4 Mi lectura: es Capacitaciones ampliado, **no otra cosa** — con una salvedad

**El argumento a favor (contra el código, no contra el nombre):** el modelo actual ya tiene las tres
piezas estructurales de un módulo de formación —**catálogo × asignación × evidencia
(certificado)**— con las FKs compuestas correctas, la barrera de empresa en la base, dos exports,
un reporte y una entrada en el Panel de Procesos. **Ninguna de esas piezas habría que construirla de
nuevo.** Lo que falta son **atributos** (horas cursadas, proveedor, costo, nota, fechas de dictado):
columnas sobre tablas que existen, no un modelo distinto.

**La salvedad, y es la que puede darlo vuelta:** hay **dos** cosas que no son atributos y sí son
modelo:

1. **La unicidad `(capacitacion_id, empleado_id)`.** Si el Excel trae la misma persona haciendo el
   mismo curso en dos años, el modelo actual **no puede representarlo**. Eso no se arregla con una
   columna: se arregla cambiando la clave única, que es DDL destructivo sobre un índice.
2. **La formación externa sin catálogo.** Si el Excel es "qué estudió cada uno" (posgrados, cursos
   externos, idiomas) en vez de "qué cursos internos asignamos", el eje es la PERSONA y no el
   CURSO, y `capacitaciones.empresa_id` NOT NULL no tiene sentido para un título universitario.

**Veredicto: 70/30 a favor de ampliar Capacitaciones.** Pero **las dos preguntas de arriba se
responden con el Excel en la mano y no antes**, y la segunda cambiaría el lote de DDL. Ver §10 y el
cierre (d).

> ⚠️ Nota de dato, no de modelo: `empleados.estudios` (text, nullable) ya existe y es el único lugar
> donde hoy podría estar la formación externa. Está en `EmpleadoResponse:57` y en el import de
> nómina. No se midió su cobertura porque no entra en la whitelist de autocompletado; conviene
> mirarlo antes de decidir.

---

## 7. NAVEGACIÓN Y RENOMBRE

### 7.1 Dónde se define la navegación

**Tres archivos, y los tres hay que tocarlos juntos:**

1. **`frontend/components/layout/nav-config.ts`** (104 líneas) — `NAV_GROUPS`
   (`:55-104`): 6 grupos, 25 ítems visibles + `DASHBOARD_ITEM` fijo fuera del acordeón (`:31-33`) +
   `SUCESION_ITEM` oculto por flag (`:48-52`).
2. **`frontend/services/permisos.ts`** — `RUTA_SECCION` (`:54-86`, 25 entradas) decide **a qué se
   entra**, y `RUTAS_ORDENADAS` (`:100-124`, 23 entradas) decide **el redirect** cuando el rol no
   puede ver la ruta actual.
3. **`frontend/components/layout/Sidebar.tsx`** (144 líneas) — el render.

Y sí, **hay barrido**: `frontend/components/layout/nav-config.test.ts` (41 líneas) compara
`NAV_GROUPS` entero contra `seccionDeRuta` de `permisos.ts`, con guarda de mínimo
`ITEMS.length >= 20` (`:21`). Un ítem nuevo sin su mapeo de ruta lo rojea (`:36-40`). Ver §9.

### 7.2 Las pantallas actuales mapeadas contra los 6 grupos nuevos

**40 páginas** en `frontend/app/` (36 en `(dashboard)`, 4 fuera). Los grupos actuales son 6:
**Personas · Incorporación · Operación · Desempeño · Análisis · Administración**. Los nuevos:
**Personas · Reclutamiento · Incorporación · Talento y Desarrollo · Gestión · Egresos** +
Administración.

| Pantalla (ruta) | Grupo HOY | Grupo NUEVO | Nota |
|---|---|---|---|
| `/empleados` | Personas | **Personas** | + renombre (§7.3) |
| `/organigrama` | Personas | **Personas** | |
| `/equipo` ("Mi equipo") | Personas | **Personas** | `soloRol: ["mandos_medios"]` |
| `/vacaciones` | Personas | **Personas** | |
| `/ausencias` | Personas | **Personas** | |
| `/vacantes` | Incorporación | **Reclutamiento** | |
| `/candidatos` | Incorporación | **Reclutamiento** | |
| `/onboarding` | Incorporación | **Incorporación** | |
| `/onboarding/templates` (+ `/[id]`) | — (sin ítem propio) | **Incorporación** | 🔴 hoy NO está en el sidebar |
| `/offboarding` | Incorporación | **Egresos** | 🔴 mudanza de grupo |
| `/capacitaciones` | Desempeño | **Talento y Desarrollo** | |
| `/evaluaciones` | Desempeño | **Talento y Desarrollo** | |
| `/objetivos` | Desempeño | **Talento y Desarrollo** | |
| `/sucesion` | Incorporación (oculta) | **Talento y Desarrollo** | flag `SUCESION_ACTIVA=false` |
| `/procesos` | Operación | **Gestión** | |
| `/proyectos` (+ `/[id]`) | Operación | **Gestión** | |
| `/inventario` | Operación | **Gestión** | |
| `/horas-por-cliente` | Operación | **Gestión** | |
| `/comunicacion` | Operación | **Gestión** | 🟢 mudanza pedida explícitamente |
| `/costos` | Análisis | 🔴 **no encaja** | ver abajo |
| `/reportes` | Análisis | 🔴 **no encaja** | |
| `/auditoria` | Análisis | 🔴 **no encaja** | |
| `/empresas` (+ `/[id]`) | Administración | **Administración** | |
| `/areas` | Administración | **Administración** | |
| `/clientes` | Administración | **Administración** | |
| `/usuarios` | Administración | **Administración** | |
| `/periodos` | Administración | **Administración** | |
| `/configuracion` | Administración | **Administración** | `seccion: null` |
| `/dashboard` | fijo arriba | fijo arriba | |
| `/assessment` (+ `/[id]`) | — | — | módulo apagado, sin ítem |
| `/login`, `/cambiar-password`, `/horas`, `/evaluacion/[token]` | fuera del dashboard | idem | |

**🔴 Las que NO encajan — el grupo "Análisis" desaparece y sus 3 pantallas quedan sin casa:**

- **`/costos`** — no es Personas, no es Reclutamiento, no es Incorporación, no es Talento, no es
  Egresos. Cabe en **Gestión** o en **Administración**. Argumento por Gestión: es operación
  recurrente (importar nómina todos los meses), y es el mismo argumento con el que Comunicación se
  movió a Gestión (`nav-config.ts:78-81`: *"desde ahí ahora se MANDAN mails, y eso es operación
  recurrente, no configuración"*).
- **`/reportes`** — transversal a los 6 grupos por definición (14 reportes que cruzan dotación,
  vacaciones, costos, capacitación y auditoría). Ponerlo en cualquier grupo miente sobre su
  alcance. **Recomendación: ítem fijo arriba, junto a Dashboard** — es el otro que ya está fuera del
  acordeón (`nav-config.ts:31-33`) y por la misma razón.
- **`/auditoria`** — es administración de sistema, no de RRHH. **Recomendación: Administración.**

Y una cuarta que no está en la lista pero es una decisión: **`/onboarding/templates` no tiene ítem
en el sidebar hoy** (solo se llega desde `/onboarding`). Si el rediseño de nav lo agrega,
`permisos.ts::RUTA_SECCION` ya lo cubre por el primer segmento (`onboarding`), así que el barrido
`nav-config.test.ts` pasa sin tocar nada.

### 7.3 🔴 "Empleados" → "Colaboradores": el conteo por categoría

Método: `Select-String -CaseSensitive` con lookarounds sobre el token aislado
`(?<![A-Za-z0-9_])[Ee]mpleados?(?![A-Za-z0-9_])`, excluyendo `node_modules`, `.next`, `venv`,
`__pycache__` y `*.test.*`. Los identificadores compuestos (`EmpleadoModal`, `empleado_id`,
`fetchEmpleados`) **no** matchean ese patrón, que es lo que hace el conteo utilizable.

**Volumen bruto, para calibrar:** `mpleado` aparece **1.700 veces en 205 archivos** del front y
**8.126 veces en 464 archivos** del backend. Ese es el número que asusta y **no es el número que
importa**.

#### Categoría 1 — ETIQUETAS DE INTERFAZ (cambian): **≈ 67 strings**

| Dónde | Cantidad | Detalle |
|---|---|---|
| `.tsx` — token capitalizado aislado | **59 apariciones**, de las cuales **29 son visibles** | Las otras 30 son anotaciones de tipo (`import type { Empleado }`, `Empleado[]`, `useState<Empleado>`) y 3 comentarios. Las 29 visibles: 9 `<TableHead>Empleado(s)`, 6 `<Label>Empleado`, 2 `PageHeader title="Empleados"`, "Volver a Empleados", "Empleados a cargo", "Empleados que cargaron", "Empleados del sistema", "Empleado / Asignación", 2 "Empleado vinculado", 1 `aria-label="Empleados"`, y 5 encabezados de tabla más. |
| `.ts` — token capitalizado aislado | **38 apariciones**, de las cuales **≈12 visibles en 8 sitios** | `nav-config.ts:57` (el ítem del menú) · `dashboardAdminData.ts:40` ("Empleados activos") · **4 hooks de filtro** (`useFiltrosVacaciones:71`, `useFiltrosAusencias:34`, `useFiltrosAsignacionesCap:71`, `useFiltrosAsignacionesInv:54`) que aportan 2 strings cada uno (`label: "Empleado"` + `opcionTodos: "Todos los empleados"`) · `auditLabels.ts:7` y `:103`. |
| `.tsx`/`.ts` — frases en minúscula entre comillas | **28 matches**, ≈26 visibles | "No hay empleados que coincidan con los filtros aplicados.", "No se pudieron cargar los empleados.", "Seleccioná un empleado.", "El empleado es requerido", "Solo se listan empleados marcados como líderes.", "¿Qué empleados están en onboarding?", 3 descripciones del catálogo de reportes, etc. |

**Subtotal front visible: ≈ 67.** Es el número real del renombre en la UI.

🔴 **Uno de esos 67 es una trampa: `auditLabels.ts:7` (`empleado: "Empleado"`).** Es la traducción
del valor `entidad` de la auditoría a texto de pantalla. **Ahí el label SÍ cambia y el valor NO** —
justamente esa línea es la que permite renombrar la etiqueta sin tocar el histórico. Es la pieza que
hace que la categoría 3 sea gratis.

#### Categoría 2 — TABLAS, COLUMNAS Y ENDPOINTS (**NO cambian**)

| Qué | Cantidad exacta |
|---|---|
| Tabla `empleados` | **1** |
| Columna `empleado_id` | **20 tablas** (`assessment_links`, `assessment_resultados`, `cesiones`, `costos_nomina`, `empleado_capacitacion`, `empleado_superior_pendiente`, `evaluacion_equivalencias`, `evaluacion_evaluados`, `horas_proyecto`, `intentos_identificacion`, `inventario_asignaciones`, `mail_enviado`, `offboarding_instancias`, `onboarding_instancias`, `planes_carrera`, `proyecto_asignaciones`, `sesiones_horas`, `solicitudes_ausencia`, `solicitudes_vacaciones`, `vacaciones_pendientes`) |
| Columna `empleado_empresa_id` | **2 tablas** (`horas_proyecto`, `proyecto_asignaciones`) |
| Tabla `empleado_capacitacion` | 1 |
| Tabla `empleado_superior_pendiente` | 1 |
| Referencias a `empleado_id` en código | **699 en `.py`** (sin tests) + **147 en `.ts`/`.tsx`** |
| Prefijo de ruta `/api/empleados` + rutas con `{empleado_id}` | prefijo + **6 rutas** (`costos.py:63`, `onboarding.py:43` y `:53`, `vacaciones_empleado.py:25` y `:31`, `vacaciones_pendientes.py:58`) |
| Índices/constraints con el nombre | `empleados_pkey`, `empleados_empresa_dni_uq`, `empleados_id_empresa_uq`, `empleados_legajo_empresa_key`, `empleados_email_corporativo_key`, `empleados_estado_check`, `empleados_roles_no_vacio`, `empleados_area_id_fkey`, `ec_empleado_empresa_fk`, `idx_empleados_*` (×8), `trg_empleados_updated_at`, `trg_emp_empleados` |

**Subtotal: ~880 referencias de código + 24 columnas + 3 tablas + 7 rutas. Ninguna se toca.**

#### Categoría 3 — El valor `entidad` de la auditoría (**NO cambia**)

`services/_audit_payloads_rrhh.py:43`, `:64`, `:73` escriben `"entidad": "empleado"`. En producción
hay **115 filas** con `entidad='empleado'` (95 `update_empleado` + 19 `alta_empleado` + 1
`importacion_nomina`), sobre 156 totales — **el 74 % de la auditoría**. Y `auditoria.tabla` es
espejo 1:1 de `entidad`, así que serían 230 valores.

**Cambiarlo parte el histórico en dos**: el filtro por entidad de `/auditoria` dejaría de traer lo
viejo, y `auditoria` es **inmutable por diseño** (no se puede backfillear). El label de pantalla ya
sale de `auditLabels.ts:7`, así que **cambiar la etiqueta y dejar el valor es una línea**.

#### Categoría 4 — Exports, mensajes de error y mails: **¿cambian? Sí, y hay que decidir uno por uno**

| Subcategoría | Cantidad exacta | Recomendación |
|---|---|---|
| **Encabezados de export** | **13 sitios**: `_ausencias_export.py:25`, `_capacitaciones_export.py:29`, `_horas_cliente_export.py:34`, `_inventario_export.py:23`, `_nomina_export.py:21`, `_offboarding_export.py:56`, `_onboarding_export.py:36`, `_vacaciones_export.py:25`, `_vacaciones_pendientes_export.py:33` (columna `"Empleado"`), `_areas_export.py:38` (`"Empleados"`), `_evaluaciones_resultados_export.py:20` (`"Empleado asignado"`), `reporte_anual.py:79` (`"Empleados activos"`), `empleado_service.py:89` (`nombre="Empleados"` + hoja `"Empleados"`) | 🟢 **SÍ cambian.** El archivo lo abre alguien de RRHH; si la pantalla dice "Colaboradores" y el Excel dice "Empleado", el renombre se ve a medias. Sin riesgo técnico: son keys de dict que el motor de export capitaliza, no columnas de base. ⚠️ Salvo que RRHH tenga tableros de Excel que referencien el nombre de la columna. |
| **Mensajes de error (`AppError`)** | **20 líneas**, de las cuales **11 son el literal canónico `"Empleado no encontrado"`** (`nomina_repo.py:54`, `asignaciones_service.py:85`, `asignacion_service.py:63`, `cesion_service.py:36`, `_ausencias_write.py:42`, `_empleados_utils.py:31`, `_empleados_write.py:134`, `_empleado_scope.py:83`, `_vacaciones_saldo.py:114`, `_vacaciones_write.py:82`, `errors.py:17`) + 9 propios | 🟡 **Decisión.** Cambiarlos es correcto para el usuario. 🔴 **Pero `CLAUDE.md` dice que ese literal "no lo dupliques, delegá, así el mensaje no puede divergir" — y en el código hay ONCE copias.** Es un hallazgo aparte: el renombre las tocaría todas y sería el momento de unificarlas, o de dejarlas y aceptar 11 sitios. El `code` (`EMPLEADO_NOT_FOUND`) **NO se toca**: es contrato de API. |
| **Mails** | **0 strings visibles.** Lo que hay es el nombre de **6 variables de plantilla** en `services/mailer/_variables.py:53-61`: `nombre_empleado`, `apellido_empleado`, `email_empleado` (y `nombre_completo`, `area_nombre`, `superior_nombre` que no lo nombran) | 🔴 **NO cambiar.** Son claves que **RRHH ya escribió dentro de las 2 plantillas guardadas en producción**. Renombrarlas rompe las plantillas existentes en silencio: `valores()` (`:97-123`) devuelve `""` para una variable que no existe, o sea que el mail sale con un hueco y **nadie se entera** (el propio docstring `:100-103` lo declara: *"una variable declarada pero SIN VALOR devuelve `""` — no revienta"*). |

#### Resumen del renombre

| Categoría | Cantidad | Cambia |
|---|---|---|
| 1 · Etiquetas de interfaz | **≈ 67** | 🟢 SÍ |
| 2 · Tablas, columnas, endpoints, identificadores | **~880 refs + 24 col + 3 tablas + 7 rutas** | 🔴 NO |
| 3 · Valor `entidad` de auditoría | **115 filas · 3 sitios de código** | 🔴 NO |
| 4a · Encabezados de export | **13 sitios** | 🟢 SÍ (recomendado) |
| 4b · Mensajes de error | **20 líneas (11 duplicadas)** | 🟡 decisión |
| 4c · Variables de mail | **6 nombres** | 🔴 NO |

**El renombre real es de ~80 a ~100 strings, no de 200 lugares — y ninguno de ellos es riesgoso
salvo los tres que NO hay que tocar.** El riesgo del cambio no está en el volumen: está en que un
search-and-replace de "Empleado" toque las categorías 2, 3 y 4c.

---

## 8. TRANSVERSALES — lo que más se olvida

Para cada sección nueva (**perfiles de puesto · recategorizaciones · eventos** — y **formación** si
sale del ampliado):

### 8.1 PERMISOS

**Cómo se agrega una sección** — 4 pasos, y el orden importa:

1. `backend/utils/permisos.py` → un valor al enum `Seccion` (hoy **28 valores**, `:39-92`).
2. `frontend/services/permisos.ts` → el **mismo string** en la unión `Seccion` (`:13-19`) **y** en
   `RUTA_SECCION` (`:54-86`) si tiene ruta propia, **y** en `RUTAS_ORDENADAS` (`:100-124`).
3. `frontend/components/layout/nav-config.ts` → el ítem con su `seccion`.
4. El router: `dependencies=[Depends(require_permission(SECCION, Accion.READ|WRITE))]` por endpoint.
   Hoy hay **204 gates en 61 routers**.

**¿Qué rol ve qué?** Se decide solo (`utils/permisos.py:130-136`): `admin_rrhh` todo ·
`gerencia_lectura` solo READ · `mandos_medios` **solo si la sección está en
`MANDOS_MEDIOS_SECCIONES`** (hoy `{VACACIONES, AUSENCIAS}`) · rol desconocido → False.

🔑 **Para las 3 (o 4) secciones nuevas la respuesta es la misma: `admin_rrhh` escribe,
`gerencia_lectura` lee, `mandos_medios` nada.** No hay que escribir lógica: `puede()` es genérica.

🔴 **Y hay una decisión previa: ¿sección nueva o reuso?** El enum lleva escrita la regla en su
propio comentario (`permisos.py:70-92`), y es la mejor guía que tiene el repo:
- **Comunicación NO creó sección** y reusa `configuracion`, porque era una ruta de front sobre
  endpoints que ya existían y ya estaban gateados.
- **Clientes SÍ creó sección**, porque *"la invariante declarada de este enum es una por módulo con
  router real registrado en `main.py`"*.

Aplicado: **perfiles de puesto, recategorizaciones y eventos son módulos nuevos con routers
propios → sección propia cada uno** (28 → 31 valores). **Formación**, si es Capacitaciones ampliado,
**reusa `CAPACITACIONES`** — no crea nada.

**¿`test_espejo_permisos` rojea si falta algo? SÍ, y en las dos direcciones.**
`tests/test_espejo_permisos.py:87-94` compara `==` de conjuntos (no `<=`) entre la unión de
TypeScript y el enum de Python, con guarda `>= 20` que corre **antes** (`:82-85`). Agregar una
sección en `permisos.py` y olvidarse de `permisos.ts` **rojea al instante**, con el mensaje que dice
de qué lado falta.

### 8.2 AUDITORÍA

🔴 **La regla del repo NO es "todo lo que escribe audita". Es: un módulo que audita ALGO tiene que
auditarlo TODO.** `tests/test_auditoria_coherente.py:1-17`:

> *"Solo se miran los módulos que YA emiten al menos un evento. Los 44 métodos de escritura en
> módulos sin ninguna auditoría —objetivos, áreas, capacitaciones, proyectos, inventario,
> onboarding_templates, horas, asignaciones, tipos_ausencia, configuración, plantillas— quedan
> FUERA POR CONSTRUCCIÓN, no por estar exentos."*

**Traducción operativa para las secciones nuevas: es todo o nada, y hay que elegir por adelantado.**

| Sección nueva | ¿Debería auditar? | Consecuencia |
|---|---|---|
| **Recategorizaciones** | 🟢 **SÍ, obligatorio.** Es un cambio de categoría de una persona; el update de empleado que la acompaña ya emite `update_empleado`. | El módulo entra al barrido: **alta, edición y baja de la recategorización tienen que emitir evento**. Si se audita solo el alta, `test_auditoria_coherente::test_ningun_modulo_audita_a_medias` rojea. |
| **Perfiles de puesto** | 🟡 Decisión. Es master data como `clientes` — y **`clientes` SÍ audita** (4 eventos `alta_cliente` en producción). | Si audita, los 3 métodos (alta/edición/baja lógica). Si no audita, queda con los otros 44 fuera de alcance y el barrido no dice nada. **Recomendación: SÍ**, por simetría con clientes y áreas. |
| **Eventos manuales** | 🔴 **NO.** Es una agenda: crear un feriado no es un hecho auditable. | Módulo fuera de alcance. Coherente con `objetivos`, que tampoco audita sus escrituras (solo el import). |
| **Formación (ampliado)** | 🔴 **NO cambia nada**: `capacitaciones` y `empleado_capacitacion` hoy **no auditan ninguna escritura** y están entre los 44. Agregarles auditoría los mete al barrido de golpe con ~8 métodos. | Si se decide auditar, es una tanda propia. |

⚠️ **Si un módulo nuevo audita, ojo con las tres guardas de mínimo** del barrido
(`test_auditoria_coherente.py:78-80`): `_MINIMO_MODULOS_QUE_AUDITAN = 18`,
`_MINIMO_METODOS_DE_ESCRITURA = 93`, `_MINIMO_ESCRITURAS_EN_ALCANCE = 37`. **Suben solas** (más
módulos, más métodos) — no hay que tocarlas al agregar; sí habría que tocarlas si se borrara algo.

Y el molde del payload: `services/_audit_payloads*.py`. **Regla no negociable: un diff de UPDATE usa
`sin_derivados(obj, DERIVADOS)`, nunca una lista curada** (`_audit_payloads.py:41-46`), y **un
import audita UN evento por lote, nunca fila por fila**.

### 8.3 EXPORT

**¿Una sección nueva DEBE tener export? El código no lo obliga, pero los dos barridos lo hacen casi
inevitable — y el requisito de fondo del bloque B lo pide** (*"que RRHH llegue a cualquier corte de
información sin pedirle nada a desarrollo"*).

**Qué rojea, exactamente:**

| Barrido | Qué exige | Qué rojea si la sección nueva tiene export |
|---|---|---|
| `tests/test_paridad_list_export.py` | Descubre las rutas por **introspección de `app.routes`** (`:62-68`), así que **un export nuevo entra solo, sin tocar el test**. | 🔴 Si el listado filtra por algo que el export no acepta (`:123-134`). 🔴 Si el export tiene un filtro propio que el listado no tiene (`:135-145`). 🔴 Si el export no acepta `formato` (`:147-148`). 🔴 Si el export acepta `page`/`page_size` (`:150-152`). 🔴 Si el path del export no deriva del listado sacándole `/exportar` o `/export` (`:71-76`) → hay que declararlo en `_EXPORTS_SIN_LISTADO` **con razón**. |
| `tests/test_limite_export.py::TestTodosLosExportsChequean` | Que el service **importe Y llame** `verificar_limite_export` (verificado con `inspect.getsource`, `:139-147`). | ⚠️ **La lista `EXPORTS` (`:89-108`) es A MANO — hoy 18 entradas, guarda `>= 18` (`:129`).** Un export nuevo **no entra solo**: hay que agregarlo. **Y si no se agrega, el barrido NO lo detecta** — pasa en verde con el export sin control. Es el ítem K2 pendiente. |

🔑 **La conclusión práctica: si la sección nueva tiene export, hay que tocar `test_limite_export.py`
a mano y NO hay que tocar `test_paridad_list_export.py`.** Y el nombre de la ruta tiene que ser
`<listado>/exportar`, o se paga una excepción declarada.

**Además, el rate limit:** todo export lleva `@limiter.shared_limit("30/hour", scope="export")`
(36 sitios hoy). 🟢 **Nota de corrección a `CLAUDE.md`: la deuda declarada ahí ("`objetivos.py` e
`inventario_items.py` quedaron fuera de la franja, 79 líneas cada uno") YA ESTÁ RESUELTA** — los dos
se partieron (`objetivos.py` 47 + `objetivos_escrituras.py` 68; `inventario_items.py` 60 +
`inventario_items_escrituras.py` 60) y los dos exports tienen su decorador (`objetivos.py:39`,
`inventario_items.py:40`). **Hoy no queda ningún export bajo el baseline.**

### 8.4 FILTROS

**`FiltersBar` se reusa — pero no todas las pantallas lo usan hoy, y ahí está el trabajo.**

`frontend/components/ui/FiltersBar.tsx` (128 líneas) es presentacional puro: sin estado, sin fetch,
sin debounce (`:1-5`). **5 tipos**: `select`, `search`, `date`, `daterange` (emite un objeto),
`multiselect` (checkboxes, y `:15-18` explica por qué no es `<select multiple>`).

El molde del hook está en `frontend/components/features/shared/filtros.ts` (115 líneas), con tres
helpers listos: `etiquetaArea` (`:70-78`, sufija con la empresa en modo consolidado),
`setFiltro` (`:96-104`, normaliza `""` y `[]` a `undefined` en **un** lugar) y `filtrosActivos`
(`:110-114`).

**Hooks vivos hoy: 7** (`useFiltrosEmpleados`, `useFiltrosVacaciones`, `useFiltrosAusencias`,
`useFiltrosProyectos`, `useFiltrosAsignacionesCap`, `useFiltrosAsignacionesInv`,
`useFiltrosEvaluadosResultados`).

🔴 **Objetivos NO usa ninguno de los dos.** `ObjetivosFiltros.tsx` son 4 `<select>` a mano, y su
encabezado (`:14-16`) declara que el movimiento fue puro y que migrarlo *"es un rediseño del filtro,
no una división"*. **La feature 2 agrega 2 filtros ahí, así que la decisión llega ahora**: migrar a
`FiltersBar` + `useFiltrosObjetivos` (más trabajo, alinea con el resto y deja el módulo cubierto por
las 4 invariantes del bloque B) o escribir dos `<select>` más a mano (más barato, deja la deuda).

**Las 4 invariantes que valen para todo filtro nuevo** (`filtros.ts:5-23`, y son regla, no
sugerencia): (1) si afecta al export, **server-side, una sola implementación**; (2) todo filtro que
acote empleados entra por `_ownership_filter`, nunca por un `.eq()` nuevo; (3) la composición con
ownership es por **intersección**; (4) `page` se resetea a 1 al cambiar cualquier filtro, y el hook
**no conoce `page`** — recibe `onFiltroChange`.

---

## 9. 🔴 LOS 15 BARRIDOS: cuál rojea al agregar una tabla, un repo, un router o una pantalla

**Leer esto antes de empezar es la diferencia entre "agregar una feature" y "agregar una feature y
arreglar cuatro barridos en el medio".**

| # | Barrido | Descubrimiento | ¿Rojea? | Qué hay que actualizar |
|---|---|---|---|---|
| **1** | `tests/test_paridad_list_export.py` (152) | **Automático** — `app.routes` (`:62-68`) | 🟡 **Solo si el export está mal.** Un export nuevo entra solo. | **Nada**, si el export acepta los mismos Query que el listado, acepta `formato`, no acepta `page`/`page_size`, y su path es `<listado>/exportar`. Si no: `_EXPORTS_SIN_LISTADO` **con razón** (`:50-54`). |
| **2** | `tests/test_limite_export.py` (203) | 🔴 **LISTA A MANO** `EXPORTS` (`:89-108`), guarda `>= 18` (`:129`) | 🔴 **NO rojea — y ese es el problema.** Un export nuevo no entra solo. | **Agregar la tupla `(módulo, clase, "exportar")`.** Y el service tiene que **importar Y llamar** `verificar_limite_export` en el cuerpo de `exportar`. |
| **3** | `tests/test_selects_repos.py` (249) | **Automático** — AST sobre 8 directorios (`:59-60`) | 🔴 **SÍ**, si el `select` nombra una columna o un embed que `db/schema.sql` no tiene. | **Actualizar `db/schema.sql`** con las tablas/columnas nuevas **antes** de escribir el repo. 🔴 Si el select es dinámico (tabla o columnas por parámetro), declararlo en `SIN_RESOLVER_DECLARADOS` (`:91-118`) **con conteo por archivo** — el conteo es parte de la clave. Guardas: `>=150` selects, `>=40` embeds, `>=178` resueltos, `>=60` archivos. |
| **4** | `tests/test_espejo_permisos.py` (140) | Regex sobre `permisos.ts` | 🔴 **SÍ**, garantizado, si se agrega una `Seccion` de un solo lado. Compara `==`, no `<=` (`:87-94`). | Agregar el valor en **`utils/permisos.py` Y `frontend/services/permisos.ts`**, en la misma tanda. |
| **5** | `tests/test_callers_huerfanos.py` (202) | **Automático** — AST + `app.routes` + literales de path del front | 🔴 **SÍ**, si un símbolo público de `services/`+`repositories/` no tiene caller, o si un endpoint montado no aparece escrito en el front. **Y también el bucket 2: símbolos cuyo único caller está en `tests/`.** | Conectar la punta, o declarar en `_SIMBOLOS_SIN_CALLER` / `_ENDPOINTS_SIN_FRONT` **con razón ≥20 chars** (`:198-202`). ⚠️ Guardas: `>=700` símbolos, `>=180` rutas, `>=140` paths del front — **suben solas**. ⚠️ **No citar rutas del backend entre backticks en comentarios del front**: el escáner no distingue comentario de template literal y taparía el endpoint. |
| **6** | `tests/test_mappers_ejercitados.py` (186) | **Automático** — AST sobre `repositories/` (`:60`) | 🔴 **SÍ**, si el repo nuevo tiene un mapper que abre con `if not rows: return []`. Guarda `_MINIMO_MAPPERS = 18` (`:67`). | Declarar el mapper con el módulo de test que lo ejercita **con elementos**, o con el disparador que lo volvería urgente. El molde obligatorio es un `test_la_lista_vacia_no_prueba_nada` en el test del mapper. |
| **7** | `tests/test_contrato_repos.py` (233) | **Automático** — resuelve `self._x = x or XRepo()` del `__init__` (`:19-23`) | 🔴 **SÍ**, si el service llama un método que la clase colaboradora no declara. Guardas `_MINIMO_LLAMADAS=150`, `_MINIMO_ARCHIVOS=25` (`:59-60`). | **Nada, si el código está bien.** Solo mira receptores `self.<attr>` atados a un constructor; los satélites `_*_write.py` que reciben el repo por parámetro quedan fuera a propósito (`:29-33`). |
| **8** | `tests/test_auditoria_coherente.py` (131) | **Automático** — AST + grafo de llamadas | 🔴 **SÍ**, si el módulo nuevo audita **algunas** escrituras y no todas. | O auditar todas, o **no auditar ninguna**, o declarar en `_SIN_EVENTO_DECLARADAS` **con razón**. Ver §8.2. Guardas 18/93/37 — suben solas. |
| **9** | `tests/test_nombres_definidos.py` (134) | **Automático** — `ruff --select F821,F822,F823` sobre todo el backend | 🔴 **SÍ**, ante cualquier nombre usado y no definido. Guarda `_MINIMO_ARCHIVOS = 400` (`:82`). | **Nada** — salvo que ruff no esté instalado, y ahí **falla, no se saltea** (`:98-109`). Con ~4 archivos nuevos el mínimo sigue holgado. |
| **10** | `tests/test_triggers_updated_at.py` (105) | **Automático** — deriva del `CREATE TABLE` de `schema.sql` | 🔴 **SÍ**, y es de los más fáciles de olvidar: **toda tabla nueva con `updated_at` exige su bloque en `migracionAWS/.../077`**. Igualdad estricta en las dos direcciones (`:75-105`). | **Por cada tabla nueva con `updated_at`: (a) el trigger en su propia migración de `backend/migrations/`, (b) el bloque `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER` en la 077, (c) el `CREATE TABLE` en `schema.sql`.** ⚠️ Los mínimos `_MIN_TABLAS`/`_MIN_TRIGGERS = 34` (`:52-53`) suben solos; **no bajarlos nunca** salvo que se borre código, y el archivo explica por qué (`:42-51`). |
| **11** | `frontend/components/layout/nav-config.test.ts` (41) | **Automático** — `NAV_GROUPS.flatMap` | 🔴 **SÍ**, si el ítem nuevo del sidebar no tiene su mapeo en `RUTA_SECCION`, o si el `href` tiene un typo (`:36-40`). Guarda `>= 20` (`:21`). | Agregar la ruta en `permisos.ts::RUTA_SECCION`. ⚠️ El rediseño de nav de §7 **lo toca entero**: renombrar grupos no rompe (compara ítems, no grupos), pero **mover un ítem sí, si su `seccion` cambia**. |
| **12** | `frontend/services/barridoFront.test.ts` (274) | **Automático** — árbol de `app/`, `components/`, `hooks/`, `services/` | 🔴 **SÍ**, si `services/` exporta una función que ninguna pantalla importa. **Y el bucket 2**: solo importada por tests. Guardas 200/330/600 (`:118-120`). | Conectar la punta o declarar en `SIN_CALLER` **con razón**. 🔑 **Es el barrido que caza el wrapper `fetchX` por id que nadie usa** — si el service nuevo lo tiene, va a rojear. ⚠️ Los paths se normalizan a `/` en `archivosDe` (`:141-152`): un barrido nuevo que compare un tramo de path contra `/` literal muere en Windows. |
| **13** | `frontend/app/contrasteTokens.test.ts` | Parsea `globals.css` | 🟢 **NO**, salvo que se toque la paleta. | Nada. |
| **14** | `tests/test_storage_punto_unico.py` (143) | **Automático** — AST sobre `services/` + `repositories/` (`:50-59`) | 🔴 **SÍ**, si el módulo nuevo nombra un bucket (`"documentos"`, `"cvs"`, `"avatars"`) en **código** o llama `<algo>.storage.<...>`. Guarda `>= 150` archivos. | Usar `integrations/storage.py` (`storage.DOCUMENTOS` / `subir` / `url_firmada` / `url_publica` / `borrar`). 🔑 **Los docstrings NO cuentan** — hay un quinto test (`:129-143`) que lo fija, para que nadie "arregle" un falso positivo borrando documentación. **Aplica si perfiles/formación suben archivos.** |
| **15** | `tests/test_acceso_a_datos.py` (164) | **Automático** — AST sobre `services/`, `routers/`, `utils/`, `middleware/`, `scripts/`, `config/`, `schemas/` | 🔴 **SÍ**, si el service nuevo llama `.table()` o `.rpc()` y su path no contiene `reporte`, `dashboard`, `organigrama` o `procesos`. Guardas: `>=250` archivos escaneados, `>=60` repos que sí consultan (`:130`). | **El acceso a datos va en un repo. Punto.** 🔴 **Y hay un techo duro: `test_no_hay_mas_de_cinco_familias` (`:160-164`) — hoy hay 4.** Si una feature nueva pidiera una quinta familia, quedaría **una sola** disponible para siempre. En la práctica: no se declara ninguna familia nueva. |

### 9.1 El resumen accionable

**Al agregar una tabla nueva:** rojean **#3** (si no está en `schema.sql`) y **#10** (si tiene
`updated_at` y falta en la 077). Los dos son "actualizá dos archivos", no diseño.

**Al agregar un repo:** rojean **#3** (selects contra el schema), **#6** (mapper con early return)
y potencialmente **#5** (símbolo sin caller, si se escribe antes que el service).

**Al agregar un service + router:** rojean **#5** (endpoint sin front, hasta que exista la pantalla),
**#8** (si audita a medias), **#15** (si consulta la base directo) y **#2 no rojea pero hay que
tocarlo a mano** si hay export.

**Al agregar una pantalla:** rojean **#11** (ítem sin mapeo de ruta), **#12** (service export sin
importador), **#4** (si hay sección nueva de un solo lado).

**El peor orden posible** es escribir el repo primero y el front al final: durante toda la tanda,
**#5 y #12 están en rojo** por símbolos y endpoints todavía sin punta. **El orden que evita eso:
schema.sql → migración → repo + su test de mapper → service → router → pantalla, todo en la misma
sesión por módulo** (que es la regla 12 de `CLAUDE.md`: cortar sub-tareas por módulo).

---

## 10. EL LOTE DE DDL

> 🔴 **Esta sección congela el schema.** Después de este lote, cada cambio de DDL es una
> coordinación con el dev de infra en medio de su migración.

### 10.0 Lo que se evaluó reusar antes de proponer nada

**La restricción es real: cada tabla nueva es un repo y un service más a portear a asyncpg** (hoy
**85 archivos** en `repositories/`). Lo que se evaluó, tabla por tabla:

| Necesidad | Tablas existentes evaluadas | Por qué no alcanzaron |
|---|---|---|
| **Perfiles de puesto** | **`vacantes`** con una bandera `es_plantilla` | 🔴 `empresa_id` es **NOT NULL** (un perfil es del grupo) · `codigo` es NOT NULL con secuencia `VAC-####` y CHECK de formato · `area_id` tiene FK a `areas` **y** el trigger `trg_emp_vacantes` que valida area↔empresa · `estado`, `prioridad`, `cantidad_puestos`, `fecha_apertura/cierre` no significan nada en una plantilla. Y sobre todo: **el KPI `vacantes_activas` cuenta `.neq("estado","cerrada")`** (`dashboard_service.py:92`), el Panel de Procesos cuenta `vacantes` por estado (`procesos_service.py:26`) y la alerta `sin_vacantes` pregunta por existencia — **las plantillas se contarían como vacantes abiertas en tres lugares**. |
| | **`onboarding_templates`** | 🔴 `empresa_id` NOT NULL + `trg_emp_onb_templates`. Es POR EMPRESA por diseño. Sí sirve de molde de código (`es_publica`, `with_visibilidad`), no de tabla. |
| **Recategorizaciones** | **`auditoria`** | 🟡 Cubre el diff (95 eventos `update_empleado` en producción, y `sin_derivados` incluye `cargo`/`seniority`/`categoria`), pero **no tiene `motivo`, ni `fecha_efectiva`, ni `impacto_salarial`, y es inmutable**. Ver §3.3. |
| | **`costos_nomina`** | 🔴 Serie mensual (`UNIQUE empleado_id, anio, mes`). Una recategorización no es mensual. Y está tras `Seccion.COSTOS`. |
| | **`planes_carrera`** (0 filas) | 🔴 Es plan a **futuro** (`cargo_objetivo`, `fecha_objetivo`, `progreso`), no hecho consumado. |
| | **`cesiones`** | 🟡 Molde estructural correcto (hija de empleado, hecho puntual, auditada) pero semántica distinta. Se copia el patrón, no la tabla. |
| **Próximos ingresos/bajas** | **`offboarding_instancias`** | 🟢 **SE REUSA.** Ya tiene `fecha_notificacion` (trámite) + `fecha_ultimo_dia` (efectiva) + `estado`. **Cero DDL del lado de la baja.** |
| | **`empleados`** para el ingreso | 🟡 Se reusa con **columnas nuevas**, no tabla nueva. |
| | **`candidatos`** | 🔴 No tiene fecha de ingreso y su `etapa` llega hasta `oferta`. |
| **Eventos manuales** | `objetivos` · `periodos_cerrados` · `onboarding_tareas` | 🔴 Ver §5.5. Ninguna sirve. |
| **Alerta de documentos** | **`adjuntos`** | 🟢 **SE REUSA** con una columna nueva. No hace falta tabla. |
| **Fin de período de prueba** | **`parametros_empresa`** | 🟢 **SE REUSA** con una columna nueva. |
| **Formación** | **`capacitaciones` + `empleado_capacitacion`** | 🟢 **SE REUSAN** (70/30, ver §6.4). Pendiente del Excel. |

**Resultado: 3 tablas nuevas propuestas** (perfiles de puesto, recategorizaciones, eventos), no 6.
Y **una de las tres es discutible** (recategorizaciones — ver la decisión (c) del cierre).

### 10.1 Tablas nuevas

> Convenciones obligatorias del porteo, aplicadas a las tres: **IDs `uuid`**, **sin RLS**,
> `created_at`/`updated_at` `timestamptz NOT NULL DEFAULT now()`, y **si tiene `updated_at`, su
> trigger va en su propia migración Y en la 077** (barrido #10).

#### T1 · `perfiles_puesto` — catálogo GLOBAL del grupo

```
id                      uuid PK DEFAULT gen_random_uuid()
nombre                  text NOT NULL
descripcion             text NULL
funciones               text NULL
requisitos              text NULL
formacion               text NULL
experiencia             text NULL
conocimientos_tecnicos  text NULL
modalidad               varchar NULL  CHECK (presencial|remoto|hibrido)   -- mismo CHECK que vacantes
tipo_contrato           varchar NULL  CHECK (efectivo|plazo_fijo|contratado|pasantia)
nivel                   varchar NULL  CHECK (junior|semi_senior|senior|lider|manager|director|c_level)
jornada                 text NULL
activo                  boolean NOT NULL DEFAULT true
created_by              uuid NULL REFERENCES users(id) ON DELETE SET NULL
created_at              timestamptz NOT NULL DEFAULT now()
updated_at              timestamptz NOT NULL DEFAULT now()
```
- **SIN `empresa_id` y SIN `area_id`.** Es la decisión de fondo (§1.2). Molde: `clientes`
  (migraciones 108/109), que es el único catálogo global del repo.
- **Índice único:** `ux_perfiles_puesto_nombre_global ON perfiles_puesto (lower(nombre))`.
  Criterio: el nombre lo escribe RRHH a mano, "Analista SSR" y "analista ssr" son el mismo perfil.
  Molde y motivo idénticos a `ux_clientes_nombre_global`. ⚠️ Índice por expresión → **no sirve como
  target de `on_conflict`**; no importa, no se upsertea.
- **Índice de listado:** `idx_perfiles_puesto_activo ON perfiles_puesto (activo) WHERE activo`.
- **Baja LÓGICA** (`activo=false`), como `clientes` y como `capacitaciones`.
- **Trigger `updated_at`** → migración propia **+ bloque en la 077**.
- **NO mueve datos. NO es destructiva.**

#### T2 · `recategorizaciones` — histórico de cambios de puesto

```
id                    uuid PK DEFAULT gen_random_uuid()
empresa_id            uuid NOT NULL REFERENCES empresas(id)
empleado_id           uuid NOT NULL
fecha_efectiva        date NOT NULL
cargo_anterior        text NULL
cargo_nuevo           text NULL
seniority_anterior    text NULL
seniority_nueva       text NULL
categoria_anterior    text NULL
categoria_nueva       text NULL
motivo                text NOT NULL
impacto_salarial      numeric NULL
registrado_por        uuid NULL REFERENCES users(id) ON DELETE SET NULL
created_at            timestamptz NOT NULL DEFAULT now()
updated_at            timestamptz NOT NULL DEFAULT now()
```
- 🔑 **FK COMPUESTA, no simple:**
  `FOREIGN KEY (empleado_id, empresa_id) REFERENCES empleados(id, empresa_id)`. El índice
  `empleados_id_empresa_uq` ya existe para sostenerla, y es el patrón que usan las 22 FKs compuestas
  del modelo (p. ej. `ec_empleado_empresa_fk`). **La base impide colgar una recategorización de un
  empleado de otra empresa** — que es la barrera de empresa a nivel base que `fn_misma_empresa` da
  para los otros casos.
- **Índice:** `idx_recat_empleado ON recategorizaciones (empleado_id, fecha_efectiva DESC)` — es la
  query del historial en la ficha.
- **SIN índice único.** A propósito: dos recategorizaciones el mismo día del mismo empleado son
  legítimas (corrección de una carga). No hay import de esta entidad, así que no hay idempotencia que
  sostener. ⚠️ Si mañana se importa por Excel, **hace falta una clave** — y ese es el problema que
  la 111 documentó para objetivos.
- **Trigger `updated_at`** → migración propia **+ la 077**.
- **NO mueve datos. NO es destructiva.**

#### T3 · `eventos_agenda` — eventos manuales del calendario

```
id            uuid PK DEFAULT gen_random_uuid()
empresa_id    uuid NULL REFERENCES empresas(id)     -- NULL = evento del grupo (feriado nacional)
nombre        text NOT NULL
fecha         date NOT NULL
descripcion   text NULL
dias_aviso    smallint NOT NULL DEFAULT 7 CHECK (dias_aviso BETWEEN 0 AND 365)
created_by    uuid NULL REFERENCES users(id) ON DELETE SET NULL
created_at    timestamptz NOT NULL DEFAULT now()
updated_at    timestamptz NOT NULL DEFAULT now()
```
- **`empresa_id` NULLABLE a propósito**, y hay que decidirlo (ver cierre (e)): NULL = evento del
  grupo. Precedente: `plantillas_mail.empresa_id` es nullable con la misma semántica, y
  `parametros_empresa.empresa_id` también. ⚠️ Si se elige NULLABLE, **el filtro por empresa NO puede
  ser `.eq("empresa_id", id)`** — tiene que ser `.or_("empresa_id.is.null,empresa_id.eq.<id>")`, y
  eso es distinto a todo lo demás del repo. Es el costo de la decisión.
- **Índice:** `idx_eventos_agenda_fecha ON eventos_agenda (fecha)`.
- **Sin índice único** — dos eventos el mismo día con el mismo nombre son raros pero no imposibles.
- **Trigger `updated_at`** → migración propia **+ la 077**.
- **NO mueve datos. NO es destructiva.**

### 10.2 Columnas nuevas en tablas existentes

| # | Tabla | Columna | Tipo | Mueve datos | Destructiva |
|---|---|---|---|---|---|
| C1 | `objetivos` | `periodicidad` | `text NOT NULL DEFAULT 'unica' CHECK (...)` | 🟡 **SÍ** — backfill del default sobre **1 fila** | NO |
| C2 | `objetivos` | `areas_involucradas` | `text NULL` | NO | NO |
| C3 | `empleados` | `fecha_ingreso_prevista` | `date NULL` | NO | NO |
| C4 | `empleados` | `fecha_baja_prevista` | `date NULL` | NO | NO |
| C5 | `adjuntos` | `fecha_vencimiento` | `date NULL` | NO | NO |
| C6 | `parametros_empresa` | `periodo_prueba_dias` | `smallint NOT NULL DEFAULT 90` | 🟡 backfill del default sobre **1 fila** | NO |
| C7 | `parametros_empresa` | `dias_aviso_evento` | `smallint NOT NULL DEFAULT 7` | 🟡 idem, **1 fila** | NO |
| C8 | `vacantes` | `perfil_puesto_id` | `uuid NULL REFERENCES perfiles_puesto(id) ON DELETE SET NULL` | NO | NO |

**Notas por columna:**

- **C1/C2** — ver §2.3/§2.4. `periodicidad` **debe** existir antes del índice nuevo (I1).
- **C3/C4** — 🔴 **Son la alternativa a tocar el CHECK de `estado`, y hay que elegir UNA. No las
  dos.** Ver la decisión (a) del cierre y §10.3.
- **C5** — `adjuntos` **no tiene `updated_at`**, así que no toca la 077 ni el barrido #10. Requiere
  índice parcial (I3).
- **C6/C7** — ⚠️ El PUT de `/configuracion` manda el juego completo de parámetros, así que estas dos
  tocan `schemas/`, `configuracion_repo.py`, el service y el form. **No es "una columna".**
- **C8** — **opcional**, solo trazabilidad ("esta vacante salió del perfil X"). 🔴 Si se agrega,
  crea una FK de `vacantes` (que tiene `empresa_id` NOT NULL) hacia una tabla global — lo cual es
  legal y correcto (misma dirección que `horas_proyecto.cliente_id → clientes`), pero **agrega una
  segunda relación entre `vacantes` y otra tabla**, y hay que verificar que ningún embed de
  `select` quede ambiguo (PGRST201). El barrido #3 lo detecta.

### 10.3 🔴 CHECKs a modificar — el objeto más caro del lote

#### K1 · `empleados_estado_check` — **solo si se elige la opción "estados nuevos"**

```sql
-- HOY
CHECK (estado IN ('activo','baja','licencia','suspendido'))
-- PROPUESTO
CHECK (estado IN ('activo','baja','licencia','suspendido','preingreso','egreso_en_tramite'))
```

- **No mueve datos** (los 31 siguen en `activo`) y **no es destructiva** en el sentido de perder
  filas. Pero **es el cambio de mayor radio de todo el lote**: §4.4 lista **17 sitios** que dependen
  del vocabulario de esta columna, de los cuales **2 cuentan de más** (`area_repo.py:17` y
  `sucesion_repo.py:88`, los dos `.neq("estado","baja")`) y **4 son gates de comportamiento**.
- ⚠️ Mecánica: `ALTER TABLE ... DROP CONSTRAINT` + `ADD CONSTRAINT`. Con 31 filas el `VALIDATE` es
  instantáneo.

#### K2 · `objetivos.periodicidad` — CHECK nuevo, viene con C1

```sql
CHECK (periodicidad IN ('unica','mensual','trimestral','semestral','anual'))  -- vocabulario a definir
```
🔴 **El vocabulario hay que cerrarlo antes de escribir la migración**, porque después del 21/8
cambiarlo es otro DDL. Alternativa sin CHECK: dejarlo texto libre con un catálogo en el front — más
flexible, y consistente con `seniority`/`categoria`, que ya son texto libre.

#### K3 · CHECKs de las tablas nuevas
`perfiles_puesto`: 3 CHECKs (`modalidad`, `tipo_contrato`, `nivel`) — **copiar literalmente los de
`vacantes`**, no reescribirlos, o divergen. `eventos_agenda`: 1 (`dias_aviso`).

### 10.4 Índices de unicidad, con su criterio

| # | Índice | Criterio | Destructivo |
|---|---|---|---|
| **I1** | `ux_objetivo_responsable_titulo` → `(empresa_id, responsable_id, lower(titulo), periodicidad)` | 🔴 **DROP + CREATE del índice vigente.** El criterio es el de la 111 (`:20-49`): la clave es lo que identifica una fila de la planilla. Con periodicidad, dos objetivos del mismo responsable con el mismo título y distinta cadencia son legítimos. **`periodicidad` NOT NULL con default es lo que impide el agujero de NULL** que la 111 documentó para `fecha_entrega`. | 🔴 **SÍ — dropea un índice único vigente.** Verificar antes: `SELECT empresa_id, responsable_id, lower(titulo), periodicidad, count(*) ... HAVING count(*)>1` → hoy **0 filas** (solo hay 1 objetivo). |
| **I2** | `ux_perfiles_puesto_nombre_global ON perfiles_puesto (lower(nombre))` | Nombre único en TODO el sistema (es catálogo global). `lower()` porque lo escribe una persona. Molde: `ux_clientes_nombre_global`. ⚠️ Índice por expresión → no sirve para `on_conflict`. | NO |
| **I3** | `idx_adjuntos_vencimiento ON adjuntos (fecha_vencimiento) WHERE fecha_vencimiento IS NOT NULL` | **Parcial**, porque la enorme mayoría de los adjuntos no vencen. Molde: `idx_empleados_domicilio_provincia`, que ya usa `WHERE ... IS NOT NULL` por el mismo motivo. **No es único.** | NO |
| **I4** | `idx_recat_empleado ON recategorizaciones (empleado_id, fecha_efectiva DESC)` | La query del historial en la ficha. **No es único** — ver T2. | NO |
| **I5** | `idx_eventos_agenda_fecha ON eventos_agenda (fecha)` | La query "próximos N días". **No es único.** | NO |
| **I6** | `idx_perfiles_puesto_activo ON perfiles_puesto (activo) WHERE activo` | Listado por defecto. | NO |
| **I7** | `idx_empleados_fecha_ingreso_prevista` / `_baja_prevista`, parciales `WHERE ... IS NOT NULL` | Solo si se elige la opción C3/C4 (fechas previstas) en vez de K1. | NO |

### 10.5 🔴 Un arreglo que este lote NO puede saltear: la migración 094

`migrations/094_recrear_triggers_empresa.sql` declara **9** triggers `trg_emp_*`; el noveno es
`trg_emp_sucesion` sobre `sucesion_posiciones`, **tabla que la migración 112 dropeó**. Producción
tiene **8** (contado hoy). Un replay de `schema.sql` seguido de la 094 **aborta**:
`DROP TRIGGER IF EXISTS x ON tabla` falla igual si la que no existe es la TABLA.

**Esto no es opcional en un lote que congela el schema**, porque `fn_misma_empresa()` es la **única**
defensa a nivel base contra el cruce de empresas por referencia, y **no está en `schema.sql`** (que
no trae funciones ni triggers). Si el rebuild en RDS aborta en la 094, las 8 protecciones no se
crean y nadie lo nota hasta que alguien cuelga un área de otra empresa.

**Corrección: sacar las líneas 82-85 y el comentario que dice "debe devolver 9".** Es una edición de
archivo, no un DDL nuevo, y no mueve datos.

### 10.6 El orden, y qué va antes y qué después del deploy

**Regla que gobierna el orden** (la que dejó escrita la migración 090 en `empleado_out.py:43-49`):
**una columna que se vuelve nullable, o un valor nuevo en un CHECK, exige que el CÓDIGO QUE LO
TOLERA esté desplegado ANTES de correr el DDL.** Al revés, la base devuelve un valor que Pydantic
rechaza → `ValidationError` → 500 del handler global, y no en un endpoint sino en **toda lectura**
de esa entidad.

**Antes del deploy del código (DDL puramente aditivo, invisible para el código viejo):**

| Orden | Objeto | Por qué acá |
|---|---|---|
| 1 | **Fix de la 094** (sacar `trg_emp_sucesion`) | No es DDL de producción, es reparar el rebuild. Independiente de todo. |
| 2 | **T1 `perfiles_puesto`** + I2 + I6 + trigger | Tabla nueva: nadie la lee. |
| 3 | **T2 `recategorizaciones`** + I4 + trigger | Idem. |
| 4 | **T3 `eventos_agenda`** + I5 + trigger | Idem. |
| 5 | **C5** `adjuntos.fecha_vencimiento` + **I3** | Columna nullable nueva: el `AdjuntoResponse` viejo la ignora. |
| 6 | **C3/C4** `empleados.fecha_*_prevista` (si se elige esa opción) | Nullable nuevas. |
| 7 | **C8** `vacantes.perfil_puesto_id` (si se decide) | Nullable + FK a T1, que ya existe por el paso 2. |

**🔴 Junto con el deploy — el código va PRIMERO, el DDL DESPUÉS:**

| Orden | Objeto | Por qué |
|---|---|---|
| 8 | **C6/C7** `parametros_empresa.periodo_prueba_dias` / `dias_aviso_evento` | `NOT NULL DEFAULT` es seguro para el código viejo (no las lee), **pero el PUT de `/configuracion` manda el juego completo** — el schema nuevo tiene que estar desplegado o el PUT viejo pisaría con los defaults. |
| 9 | **K1** ampliar `empleados_estado_check` (si se elige esa opción) | 🔴 **Este es el que no se puede invertir.** El código que entiende `preingreso`/`egreso_en_tramite` —los 17 sitios de §4.4— tiene que estar desplegado ANTES. Si el CHECK se amplía primero y alguien crea un preingreso, **`area_repo.py:17` lo cuenta como headcount y nadie se entera**. |
| 10 | **C1 + K2** `objetivos.periodicidad` | `NOT NULL DEFAULT 'unica'` backfillea la única fila sin bloqueo. El código nuevo tiene que estar arriba para que `ObjetivoResponse` la exponga. |
| 11 | **I1** DROP + CREATE del índice único de objetivos | 🔴 **Después de C1, obligatoriamente**: el índice referencia la columna. Y **después del deploy**, porque entre el DROP y el CREATE la tabla queda **sin protección de duplicados**. Con 1 fila la ventana es irrelevante; escribirlo igual. |
| 12 | **C2** `objetivos.areas_involucradas` | Nullable; podría ir antes, va acá por coherencia de módulo. |

**Después del deploy:** nada. **El lote entero es una sola migración numerada** (la próxima libre es
la **113**), o a lo sumo dos: una aditiva pura (pasos 1-7) y una dependiente del código (8-12). 🔑
**Recomendación: DOS archivos**, `113_*` y `114_*`, porque el orden respecto del deploy es distinto y
mezclarlos obliga a correr la mitad y esperar.

### 10.7 Lo que este lote NO incluye, y el riesgo que eso deja

🔴 **FORMACIÓN NO ESTÁ EN EL LOTE**, porque el Excel no llegó y §6.3 muestra que **al menos dos de
las columnas candidatas dependen de qué traiga** (y una de ellas, la unicidad
`(capacitacion_id, empleado_id)`, es un **DROP + CREATE de índice**, no una columna).

**El riesgo, dicho explícito: si el Excel llega después del 21/8, formación exige un segundo lote de
DDL en medio de la migración de infra.** Las salidas son tres y hay que elegir ahora:
1. Conseguir el Excel antes del 21/8 (es un pedido a RRHH, no trabajo de desarrollo).
2. Incluir **preventivamente** las columnas de bajo riesgo que casi seguro van a hacer falta
   (`capacitaciones.proveedor text`, `capacitaciones.costo numeric`, `capacitaciones.moneda char(3)`,
   `empleado_capacitacion.horas_cursadas numeric`, `empleado_capacitacion.nota text`,
   `empleado_capacitacion.fecha_vencimiento_certificado date`) y **cambiar el índice único a
   `(capacitacion_id, empleado_id, coalesce(anio, 0))`**. Son columnas nullable: si sobran, quedan
   vacías y no molestan. 🔴 **Va contra la regla del repo de no construir lo que no se pidió**, y hay
   que decirlo así.
3. Aceptar el segundo lote y coordinarlo.

**Recomendación: (1), y (2) como plan B solo para las columnas nullable — nunca para el índice
único**, que es el único objeto destructivo del grupo.

---

## 11. SUPERFICIE DE PORTEO Y LÍNEAS

### 11.1 Cuántos repos, services y routers nuevos

Base actual medida hoy: **67 routers · 219 services · 85 repositories · 160 archivos de test**.

| Feature | Repos | Services | Routers | Schemas | Front (pantalla/comp.) |
|---|---|---|---|---|---|
| **1 · Perfiles de puesto** | **1** (`perfil_puesto_repo.py`) | **2** (`perfil_puesto_service.py` + `_perfiles_export.py`) | **1-2** (`perfiles_puesto.py`, + `_escrituras.py` si pasa de 80) | 1 | 1 pantalla + ~4 componentes |
| **2 · Objetivos (ampliar)** | **0** | **0** nuevos | **0** | 0 | 0-1 |
| **3 · Recategorizaciones** | **1** | **1-2** (`recategorizacion_service.py` + `_audit_payloads_recategorizacion.py`) | **1** | 1 | ~2 componentes (sección de ficha + modal) |
| **4 · Ingresos/bajas** | **0** | **0** nuevos | **0** | 0 | 1-2 componentes de dashboard |
| **5 · Eventos y alertas** | **1** (`evento_agenda_repo.py`) | **1-2** (`evento_agenda_service.py` + extensión del catálogo de alertas) | **1** | 1 | ~2 componentes |
| **6 · Formación** | 0 (amplía los existentes) | 0 nuevos | 0 | — | — |
| **7 · Navegación/renombre** | 0 | 0 | 0 | 0 | toca ~3 archivos + ~80 strings |
| **TOTAL** | **+3 repos** | **+4 a 6 services** | **+3 a 4 routers** | **+3** | |

**Superficie de porteo a asyncpg: 3 repos nuevos** (85 → 88, +3,5 %). Es el número que le importa al
dev de infra. Los 3 se moldean sobre `migracionAWS/empleado_repo_NEW` (regla 14 de `CLAUDE.md`).

Más: **+3 valores en el enum `Seccion`** (28 → 31, en los dos lados) · **~10-14 gates
`require_permission`** (204 → ~218) · **+3 entradas en `EXPORTS`** de `test_limite_export.py`
(18 → 21) · **+3 bloques de trigger en la 077** (35 → 38).

### 11.2 Archivos a tocar, con líneas actuales contra su límite

🔴 **AL FILO — el próximo cambio EXIGE dividir primero:**

| Archivo | Líneas | Límite | Feature que lo toca |
|---|---|---|---|
| **`services/objetivo_service.py`** | **143** | 150 | 🔴 **Feature 2.** Sumar `periodicidad` y `areas_involucradas` toca `get_all`, `exportar`, `create` y `update`: son ~8 líneas de firma. **No entra.** |
| **`repositories/objetivo_repo.py`** | **100** | 100 | 🔴 **Feature 2.** Los dos filtros nuevos van al `find_all`. **Ya está EN el límite: no entra ni una línea.** |
| **`services/_vacaciones_write.py`** | **150** | 150 | 🟡 Feature 4, solo si el estado nuevo cambia la validación de solicitudes. |
| **`services/assessment_service.py`** | 150 | 150 | 🟢 No lo toca nada. |
| **`services/_clasificador_prompt.py`** | 150 | 150 | 🟢 No lo toca nada. |
| **`repositories/vacante_repo.py`** | **100** | 100 | 🔴 **Feature 1**, si `vacantes` recibe `perfil_puesto_id` (C8). |
| **`repositories/area_repo.py`** | **100** | 100 | 🔴 **Feature 4** — `_counts_by_area` (`:15-22`) es uno de los 2 sitios que cuentan de más. |
| **`repositories/candidato_repo.py`** | 100 | 100 | 🟡 Feature 4, si el preingreso arranca desde un candidato. |
| **`routers/candidatos.py`** · **`routers/adjuntos.py`** | **80** | 80 | 🔴 **`adjuntos.py` lo toca la feature 5** (C5, `fecha_vencimiento`). |
| **`services/adjunto_service.py`** | 144 | 150 | 🟡 Feature 5. Entran ~6 líneas, no más. |

🟡 **Con margen ajustado (entre 6 y 20 líneas libres):**
`services/_empleados_write.py` **138**/150 (feature 3 y 4) ·
`services/costo_service.py` **141**/150 (feature 3, si el impacto salarial se cruza con el historial) ·
`services/audit_service.py` **140**/150 ·
`repositories/empleado_repo.py` **96**/100 (feature 4: filtro por estado nuevo) ·
`repositories/_empleado_write_repo.py` **97**/100 (feature 4: el `payload["estado"]="activo"` de `:36`) ·
`routers/empleados.py` **74**/80 ·
`services/_dashboard_kpis.py` **131**/150 (feature 5) ·
`services/_dashboard_alertas.py` **107**/150 y `_dashboard_alertas_catalogo.py` **86**/150 (feature 5: la familia nueva de alertas) ·
`services/dashboard_service.py` **111**/150 (feature 4: el KPI de bajas por `updated_at`).

🟢 **Con margen sobrado:** `services/vacante_service.py` 112/150 · `services/capacitacion_service.py`
98/150 · `services/asignacion_service.py` 127/150 · `routers/vacantes.py` 59/80 ·
`routers/objetivos.py` 47/80 · `routers/objetivos_escrituras.py` 68/80.

**FRONT — sobre el límite de 150 (componentes) / 80 (hooks):**

| Archivo | Líneas | Límite | Feature |
|---|---|---|---|
| **`components/features/vacantes/VacanteModal.tsx`** | **251** | 150 | 🔴 **Feature 1** — es donde va el selector de perfil. Ya está 101 sobre. |
| `app/(dashboard)/vacantes/[id]/page.tsx` | **451** | 150 | 🟡 Feature 1 |
| `app/(dashboard)/costos/page.tsx` | **624** | 150 | 🟡 Feature 3, si el impacto salarial se muestra ahí |
| `components/features/objetivos/ObjetivoModal.tsx` | **137** | 150 | 🔴 **Feature 2** — los 2 campos nuevos lo pasan |
| `components/features/objetivos/ObjetivoFormFields.tsx` | **125** | 150 | 🔴 **Feature 2** — idem |
| `app/(dashboard)/objetivos/page.tsx` | **148** | 150 | 🔴 **Feature 2** — **2 líneas libres** |
| `components/features/objetivos/ObjetivosFiltros.tsx` | 68 | 150 | 🟢 Feature 2 |
| `components/features/objetivos/ImportarObjetivosModal.tsx` | 148 | 150 | 🟡 Feature 2 — 2 líneas libres |
| `components/layout/nav-config.ts` | 104 | 200 | 🟢 Feature 7 |
| `components/layout/Sidebar.tsx` | 144 | 150 | 🟡 Feature 7 — 6 líneas libres |
| `app/(dashboard)/empleados/page.tsx` | 144 | 150 | 🟡 Feature 4 — 6 líneas libres |

> ⚠️ **Corrección a `CLAUDE.md`:** dice que `vacantes/[id]/page.tsx` está en **577** en un lugar y
> en **451** en otro. **Medido hoy con `-LiteralPath`: 451.** El 577 es stale.

### 11.3 🔴 Qué divisiones hay que hacer ANTES de empezar a construir

**Obligatorias (el archivo no admite una línea más):**

| # | Archivo | Corte propuesto |
|---|---|---|
| **D1** | `repositories/objetivo_repo.py` **100/100** | Sacar el armado del `find_all` (filtros + orden) a `repositories/_objetivo_filtros.py`. Molde exacto: `repositories/_scope_filtros.py` (93) y `_rango_fechas.py`. |
| **D2** | `services/objetivo_service.py` **143/150** | Sacar `exportar` a `services/_objetivos_export_service.py` o mover las validaciones (`_validate_responsable`, `:136-143`) a `services/_objetivos_validaciones.py`. Molde: `_objetivos_jerarquia.py`, que ya salió de ahí. |
| **D3** | `components/features/objetivos/ObjetivoFormFields.tsx` **125/150** + `ObjetivoModal.tsx` **137/150** | Los dos campos nuevos no entran en ninguno. Cortar `ObjetivoFormFields` en dos bloques (datos / clasificación). |
| **D4** | `app/(dashboard)/objetivos/page.tsx` **148/150** | **2 líneas libres.** Extraer el bloque de acciones o el de vistas. |
| **D5** | `components/features/vacantes/VacanteModal.tsx` **251/150** | Ya está 101 sobre el límite **antes** de la feature. Cortar en `VacanteDatosSection` + `VacanteRangoSection` + el modal orquestador. Molde: el corte de `components/features/sucesion/` (855 → 85). |
| **D6** | `repositories/vacante_repo.py` **100/100** | Solo si se decide C8. Sacar el mapper de fila a `_vacante_row.py`, molde `_empleado_row.py`. |
| **D7** | `repositories/area_repo.py` **100/100** | Solo si la feature 4 cambia `_counts_by_area`. Sacar los mappers a `_area_row.py`. |
| **D8** | `routers/adjuntos.py` **80/80** | Solo si `fecha_vencimiento` agrega un Query al listado. Molde: los 8 pares `*_escrituras.py` que ya existen. |

**Recomendadas (margen < 12 líneas y la feature los toca):**
`repositories/_empleado_write_repo.py` 97/100 · `repositories/empleado_repo.py` 96/100 ·
`services/_empleados_write.py` 138/150 · `components/layout/Sidebar.tsx` 144/150 ·
`app/(dashboard)/empleados/page.tsx` 144/150.

🔑 **La regla del repo aplica textual y conviene recordarla acá: un satélite `_*.py` NO hereda un
límite más alto. Dentro de `repositories/` es un repositorio y su límite es 100; dentro de
`services/`, 150.** Ya pasó dos veces en este repo, con un archivo llegando a 159.

**Y la regla 12 de `CLAUDE.md`: cortar sub-tareas por módulo cuando hay división de archivos de por
medio.** O sea: **D1+D2 son una sesión propia antes de tocar objetivos; D5 es una sesión propia
antes de tocar vacantes.** No se hacen "de paso".

---

# CIERRE

## (a) El lote de DDL consolidado

**3 tablas nuevas · 8 columnas nuevas · 2 CHECKs · 7 índices · 1 archivo de migración a reparar.**

| Tipo | Objeto | Mueve datos | Destructivo | Antes/después del deploy |
|---|---|---|---|---|
| **fix** | `migrations/094` — sacar `trg_emp_sucesion` | NO | NO | independiente |
| **tabla** | `perfiles_puesto` + I2 + I6 + trigger | NO | NO | **antes** |
| **tabla** | `recategorizaciones` + I4 + trigger | NO | NO | **antes** |
| **tabla** | `eventos_agenda` + I5 + trigger | NO | NO | **antes** |
| **columna** | `adjuntos.fecha_vencimiento` + I3 | NO | NO | **antes** |
| **columna** | `empleados.fecha_ingreso_prevista`, `.fecha_baja_prevista` *(opción B de la decisión (a))* | NO | NO | **antes** |
| **columna** | `vacantes.perfil_puesto_id` *(opcional)* | NO | NO | **antes** |
| **columna** | `parametros_empresa.periodo_prueba_dias`, `.dias_aviso_evento` | 🟡 1 fila | NO | **después** |
| **CHECK** | `empleados_estado_check` +2 valores *(opción A de la decisión (a))* | NO | NO | 🔴 **después** |
| **columna+CHECK** | `objetivos.periodicidad` | 🟡 1 fila | NO | **después** |
| **índice** | `ux_objetivo_responsable_titulo` (DROP + CREATE) | NO | 🔴 **SÍ** | **después**, y **después de la columna** |
| **columna** | `objetivos.areas_involucradas` | NO | NO | después |

**Un solo objeto destructivo en todo el lote: I1.** Verificado hoy que entra sin deduplicar nada
(1 objetivo, 0 colisiones).

**Formato: dos archivos, `113_*` (aditivo puro) y `114_*` (dependiente del deploy).** Y de cada tabla
nueva con `updated_at`: su trigger en la migración **y** su bloque en `migracionAWS/.../077`, o el
barrido #10 rojea y el `updated_at` queda congelado en RDS.

## (b) Las decisiones que necesitás tomar, ordenadas por cuánto bloquean

| # | Decisión | Bloquea | Por qué no la puedo tomar yo |
|---|---|---|---|
| **1** | 🔴 **Preingresos/bajas: ¿estados nuevos en el CHECK, o fechas previstas sin tocar el estado?** | **Toda la feature 4, y el orden del deploy.** Es el único objeto del lote que **no se puede correr antes del código**. | **A (estados):** semánticamente correcto, pero toca **17 sitios** y **2 de ellos cuentan de más en silencio** (§4.4). **B (fechas):** cero riesgo sobre el código existente, pero deja el bug de `_offboarding_iniciar.py:76` intacto (el empleado sigue bajando en el acto) y obliga a que cada consumidor decida qué hacer con la fecha. **Es un tradeoff funcional real, no una elección técnica.** |
| **2** | 🔴 **Recategorizaciones: ¿el "cargo" es `empleados.cargo` (0/31, deprecado) o `empleados.roles[0]`?** | La tabla T2 entera y su formulario. | `cargo` está declarado **DEPRECADO, se dropea en S6** (`empleado_out.py:40`) y el repo ya lo resuelve con `roles[0]`. Construir la feature sobre una columna que se va a borrar es deuda inmediata; construirla sobre `roles` (array NOT NULL) cambia el modelo de T2 (`roles_anteriores text[]` en vez de `cargo_anterior text`). **Producto tiene que decir cuál es el cargo real.** |
| **3** | 🟡 **¿La tabla `recategorizaciones` existe, o alcanza con una vista sobre `auditoria` + un campo `motivo`?** | La tabla T2, 1 repo y 1 service de porteo. | La auditoría **ya guarda el diff completo** (§3.2). Lo que falta es `motivo`, `fecha_efectiva`, `impacto_salarial` y mutabilidad. Si RRHH acepta cargar el motivo como texto libre en la edición del empleado y renunciar a la fecha efectiva, **la tabla se evita entera** (−1 repo de porteo). Es una decisión de producto sobre cuánto vale la fecha efectiva. |
| **4** | 🟡 **Objetivos: vocabulario de `periodicidad` — ¿CHECK cerrado o texto libre?** | C1, K2 e I1, o sea el índice único. | Un CHECK cerrado es más seguro pero **después del 21/8 cambiarlo es otro DDL**. Texto libre es consistente con `seniority` y `categoria` (que ya son libres) y con el autocompletado. **Y hay que decidir el default**, porque de eso depende que I1 no reintroduzca el agujero de NULL. |
| **5** | 🟡 **`eventos_agenda.empresa_id`: ¿NULLABLE (eventos del grupo) o NOT NULL?** | T3 y el filtro por empresa. | NULLABLE permite feriados nacionales, pero **el filtro deja de ser `.eq()` y pasa a ser un `.or_()`** — distinto a todo el resto del repo, y un lugar más donde equivocarse. NOT NULL obliga a cargar cada feriado dos veces (una por empresa) hoy, y N veces cuando haya 5. |
| **6** | 🟡 **Renombre: ¿cambian los encabezados de export (13) y los mensajes de error (20)?** | El alcance del renombre. | Los exports: recomiendo **sí** (el archivo lo abre RRHH), salvo que tengan tableros de Excel que referencien el nombre de la columna. Los errores: recomiendo **sí**, y aprovechar para **unificar las 11 copias del literal canónico** que `CLAUDE.md` dice que no deberían existir. Los mails: **no**, y no es negociable (rompe las 2 plantillas cargadas en silencio). |
| **7** | 🟡 **Navegación: dónde van `/costos`, `/reportes` y `/auditoria`** — los 3 huérfanos del grupo "Análisis". | El rediseño de nav. | Mi recomendación: `/costos` → **Gestión** (mismo argumento que Comunicación) · `/reportes` → **ítem fijo arriba junto a Dashboard** (es transversal a los 6 grupos) · `/auditoria` → **Administración**. Pero es una decisión de producto sobre cómo lee RRHH el menú. |
| **8** | 🟡 **Objetivos: ¿se migra a `FiltersBar` + `useFiltrosObjetivos`, o se agregan 2 `<select>` a mano?** | El tamaño de la feature 2 en el front. | Migrar alinea el módulo con los otros 7 y lo deja cubierto por las 4 invariantes del bloque B; no migrar es más barato hoy y deja la deuda declarada en `ObjetivosFiltros.tsx:14-16`. |
| **9** | 🟡 **Formación: ¿se espera el Excel, se agregan columnas preventivas, o se acepta un segundo lote de DDL?** | El congelamiento del schema. | Ver §10.7. Recomiendo pedir el Excel antes del 21/8. |
| **10** | 🟢 **¿`vacantes.perfil_puesto_id` (C8) se agrega?** | Nada crítico. | Solo trazabilidad. Sin ella, no se puede responder "¿cuántas vacantes salieron de este perfil?". |
| **11** | 🟢 **¿Perfiles de puesto lleva visibilidad pública/privada?** | Nada crítico. | El molde ya existe (`onboarding_templates.es_publica` + `with_visibilidad`), y es lo que C6 pedía. Si se agrega, es una columna más en T1. |

## (c) Sesiones estimadas por feature

Contando **una tarea atómica por sesión** (regla 7) y **las divisiones como sesiones propias**
(regla 12):

| Feature | Divisiones previas | Backend | Frontend | Total |
|---|---|---|---|---|
| **0 · El lote de DDL** (2 migraciones + fix 094 + `schema.sql` + los 3 bloques de la 077) | — | **1** | — | **1** |
| **1 · Perfiles de puesto** | **1** (D5: `VacanteModal` 251→<150) | **2** (repo+service+router+export · integración con el alta de vacante) | **2** (pantalla ABM · selector + copia en `VacanteModal`) | **5** |
| **2 · Objetivos** | **2** (D1+D2 backend · D3+D4 front) | **1** (columnas, filtros, import, índice) | **1** (2 controles + las 2 vistas) | **4** |
| **3 · Recategorizaciones** | — | **2** (repo+service+router+auditoría · el update de empleado y su historial) | **1** (sección de ficha + modal) | **3** |
| **4 · Próximos ingresos/bajas** | **1** (D7 `area_repo` si va la opción A) | **2** (el estado/fechas + los 17 sitios de §4.4 · el arreglo de `_offboarding_iniciar`) | **1** (bloque de dashboard) | **4** |
| **5 · Dashboard, alertas y eventos** | — | **2** (`eventos_agenda` + la familia nueva de alertas · los 4 eventos y el aviso configurable) | **1** | **3** |
| **6 · Formación** | — | **1-3** *(no estimable sin el Excel)* | 1-2 | **2-5** |
| **7 · Navegación + renombre** | — | **1** (los 13 exports + los 20 errores, si se deciden) | **2** (nav 6 grupos + los ~67 strings) | **3** |
| **TOTAL** | **4** | **12-14** | **9-10** | **~25-29** |

⚠️ **Dos advertencias sobre esta estimación:**
1. **No incluye el arreglo de los barridos.** §9 muestra que cada módulo nuevo toca entre 2 y 5 de
   los 15. En la práctica eso es ~20 % más por sesión, no una sesión aparte.
2. **La feature 4 es la más subestimada.** "2 sesiones de backend" asume que los 17 sitios se
   revisan en bloque. Si aparece un decimoctavo, es otra sesión.

## (d) Los huecos, y a quién preguntarle cada uno

| # | Hueco | A quién | Por qué bloquea |
|---|---|---|---|
| **1** | 🔴 **El Excel de formación.** | **RRHH** | §6.4 muestra que **dos decisiones de modelo** dependen de él (recertificación → índice único; formación externa → si el eje es la persona o el curso). Y §10.7: si llega después del 21/8, **es un segundo lote de DDL en medio de la migración de infra**. |
| **2** | 🔴 **El mockup de las 4 alertas y los 4 eventos: ¿de dónde salió?** | **Quien lo diseñó** | **3 de los 8 elementos no tienen dato en el sistema y dos de ellos no lo van a tener** ("evaluaciones vencidas" y "evaluación programada" — §5.3.a y §5.4.d: el sistema **no evalúa**, importa resultados). Si el mockup se muestra tal cual, dos tarjetas van a estar permanentemente en cero. Hay que decidir si se sacan, se reemplazan (p. ej. "capacitaciones vencidas", que sí es gratis) o se construye la programación. |
| **3** | 🟡 **¿Qué es un "documento próximo a vencer" para RRHH?** | **RRHH** | Además de la columna (C5), hace falta saber **si hay un catálogo de tipos de documento**. Hoy `adjuntos.categoria` es texto libre y el único adjunto cargado la tiene en NULL. Sin catálogo, la alerta solo puede avisar de lo que alguien cargó con fecha, nunca de lo que falta. |
| **4** | 🟡 **El vocabulario de `periodicidad`.** | **RRHH / producto** | Decisión (4). |
| **5** | 🟡 **¿El período de prueba es el mismo para las dos empresas y para todos los contratos?** | **RRHH** | C6 lo modela como un parámetro **por empresa**. Si varía por tipo de contrato (`efectivo` vs `pasantia`), el modelo es otro y la columna no alcanza. |
| **6** | 🟡 **¿RRHH tiene tableros de Excel que referencien los encabezados de export?** | **RRHH** | Decide la categoría 4a del renombre (13 sitios). |
| **7** | 🟡 **"Áreas involucradas" en objetivos: ¿es realmente texto libre?** | **Producto** | Si en la práctica siempre se van a escribir nombres de las 12 áreas cargadas, un texto libre va a acumular variantes ("Sistemas", "sistemas", "SISTEMAS") y el desplegable de valores usados va a mostrar las tres. `lower()` en el filtro lo mitiga, no lo resuelve. |
| **8** | 🟢 **`empleados.estudios` — ¿qué tiene cargado?** | verificable, no se midió acá | Es el único lugar donde hoy podría estar la formación externa (§6.4). Conviene mirarlo antes de decidir el modelo de formación. |

---

## Anexo · Correcciones a `CLAUDE.md` detectadas en este diagnóstico

Todas verificadas hoy contra el código o el catálogo. **No se corrigieron** (esta sesión es
read-only); se listan para que se apliquen en la sesión que corresponda.

1. 🟢 **"`objetivos.py` e `inventario_items.py` (79 líneas) quedaron fuera de la franja de rate
   limit del export" — YA NO ES CIERTO.** Los dos se partieron (`objetivos.py` **47** +
   `objetivos_escrituras.py` 68; `inventario_items.py` **60** +
   `inventario_items_escrituras.py` 60) y los dos exports tienen su
   `@limiter.shared_limit("30/hour", scope="export")` (`objetivos.py:39`, `inventario_items.py:40`).
   **Hoy no queda ningún export bajo el baseline.**
2. **`repositories/nomina_repo.py` figura en "99/100". Medido hoy: 80.**
3. **`vacantes/[id]/page.tsx` figura en 451 en un lugar y en 577 en otro. Medido hoy: 451.**
4. **Backend: 67 routers (no 66), 219 services, 85 repositories, 160 archivos `test_*.py`.**
5. **`services/objetivo_service.py` está en 143/150 y `repositories/objetivo_repo.py` en 100/100** —
   ninguno de los dos figura en la lista de "al filo" del documento, y los dos los toca la feature 2.
6. 🔴 **Hallazgo nuevo, no documentado en ningún lado:** `services/procesos_service.py:44-46`
   declara para `vacantes` los estados `nueva | en_revision | cerrada`, pero el CHECK real es
   `nueva | en_proceso | con_candidatos | cerrada`. **El Panel de Procesos muestra "En revisión"
   siempre en 0 y nunca cuenta las vacantes en `en_proceso` ni en `con_candidatos`.** Con 1 vacante
   (`nueva`) no se nota. Es un bug vivo, independiente de todo lo de este diagnóstico.
7. 🔴 **Hallazgo nuevo:** el literal canónico `"Empleado no encontrado"` está **duplicado en 11
   archivos** (§7.3, categoría 4b), cuando `CLAUDE.md` dice explícitamente *"no lo dupliques,
   delegá, así el mensaje no puede divergir"*. `services/_empleados_utils.py::empleado_or_404` es el
   canónico y `utils/errors.py:17` es otro.
8. 🔴 **Hallazgo nuevo:** el diff de auditoría de empleado se arma sobre `EmpleadoResponse`, no sobre
   la tabla, así que **12 columnas de `empleados` quedan fuera de la auditoría en silencio**
   (`fecha_egreso`, `motivo_baja`, `equipo`, `liderazgo`, `co_sourcing`, `product_owner`,
   `fecha_ingreso_reconocida`, `potencial`, `desempeno`, `foto_url`, `user_id`, `updated_at`). El
   comentario de `_audit_payloads_rrhh.py:55-59` dice que "una columna nueva queda auditada sola", y
   eso es cierto **solo si también se agrega al Response**.
9. 🔴 **Hallazgo nuevo, latente:** el KPI `bajas_mes` cuenta por `updated_at`
   (`dashboard_service.py:75-82`), así que **cualquier edición de un empleado ya dado de baja lo
   vuelve a contar como baja del mes en curso**. Hoy invisible (`fecha_egreso` 0/31); la feature 3
   lo activa.
