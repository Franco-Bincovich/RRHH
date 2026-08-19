# Auditoría del backend — HR Karstec / Capital Humano

> Ejecutada el 19/8/2026 contra `VERIFICACION-BACKEND.md` (raíz del repo). Read-only: nada se
> arregló. Verificado contra el código y contra el catálogo vivo de Supabase
> (`grmdiwxcvcjorlohpwji`), no contra `docs/`.
>
> Método: 7 auditorías paralelas independientes (una por módulo/eje), cada una leyendo código y
> consultando el catálogo con SQL de solo lectura, más verificación directa de la suite de tests
> y unos pocos ítems de seguimiento hechos a mano para cerrar los `❓` que quedaron abiertos.

---

## 🔴 1. Sección 9 — reglas transversales en los 4 módulos nuevos (PRIORIDAD 1)

Esto es lo que el usuario pidió mirar primero. Resultado: **3 de 4 módulos pasan las 6 reglas
limpio. Objetivos falla dos reglas de lleno y una tercera parcialmente.**

| Regla | Perfiles de puesto | Recategorizaciones | Eventos de agenda | Objetivos |
|---|---|---|---|---|
| 1. Paginado desde el día uno | ✅ `.range()`+`count="exact"` (`perfil_puesto_repo.py:38-58`) | ✅ (`recategorizacion_repo.py:41-62`) | ✅ (`evento_agenda_repo.py:31-46`) | ❌ **`objetivo_repo.py:31-47` sin `.range()` ni page/page_size — trae el árbol entero.** Confesado en `schemas/objetivo.py:160-167`: *"HOY `total == len(items)` PORQUE EL TABLERO NO PAGINA"*. |
| 2. IDs `UUID` en Pydantic, nunca `str` | ✅ (`schemas/perfil_puesto.py:114-116`) | ✅ (`schemas/recategorizacion.py:85-87,100`) | ✅ (`schemas/evento_agenda.py:94-105`) | ❌ **Mixto.** `ObjetivoCreate`/`Update` sí usan `UUID`, pero `ObjetivoResponse.id/empresa_id/responsable_id/parent_id` y `ResponsableItem.id` son `str` (`schemas/objetivo.py:115-152`). Es literalmente "el error #1 del porteo a asyncpg" que la propia regla nombra. |
| 3. `model_dump(mode="json")` en save Y update | ✅ (`_perfil_puesto_write_repo.py:46,70`) | ✅ (`_recategorizacion_write_repo.py:58,82`) | ✅ (`_evento_agenda_write_repo.py:56,72`) | ⚠️ **Desvío ad-hoc.** `_objetivo_payload.py`: el alta arma el dict a mano (sin `model_dump`); la edición usa `model_dump(exclude_none=True)` **sin** `mode="json"`, compensando con un `str()` a mano sobre una lista fija de campos (`_A_TEXTO`). Funciona hoy; un `UUID`/`date` nuevo que alguien olvide sumar a esa lista sale sin castear. El grep de la Sección 11 **no lo detecta** porque busca el literal `model_dump()` sin argumentos, y acá siempre lleva `exclude_none=True`. |
| 4. Sin RLS | ✅ | ✅ | ✅ | ✅ — las 4 tablas tienen `relrowsecurity=true` (el toggle default de Supabase, igual que `empleados`/`clientes`), pero **cero políticas** en `pg_policies` para las 4. Nada que rompa el porteo. |
| 5. Permisos: sección en `Seccion` + espejo `permisos.ts` | ✅ `PERFILES_PUESTO` (`_secciones.py:92`) | ✅ `RECATEGORIZACIONES` (`_secciones.py:104`) | ✅ `EVENTOS` (`_secciones.py:117`) | ✅ `OBJETIVOS` (preexistente) — `test_espejo_permisos.py` verde en los 4. |
| 6. Auditoría de alta/edición/baja | ✅ 3/3 (`perfil_puesto_service.py:103,119,130`) | ✅ 2/2, sin baja porque no se borra (`_recategorizaciones_write.py:70,102`) | ✅ 4/4 — alta, edición, resolución, baja (`_eventos_write.py:56,66,82,92`) | ❌ **FALLA TOTAL.** `objetivo_service.py` (create/update/delete) y `_objetivos_write.py` (cambiar_estado/eliminar) no llaman a `AuditService.registrar` en ningún punto — solo `logger.info`, que no es auditoría. La única auditoría de objetivos existente es la del import masivo por Excel. Un alta/edición/borrado manual desde la pantalla no deja rastro en `/auditoria`. |
| 7. Export en `test_limite_export` con guarda subida | ✅ en `EXPORTS` | ✅ en `EXPORTS` | ✅ N/A — correctamente no tiene export | ✅ en `EXPORTS` |
| 8. Endpoints sin front en `test_callers_huerfanos` con disparador | ✅ disparador explícito | ✅ disparador explícito | ✅ (precedente: `/eventos/pendientes` ya salió de la lista cuando le llegó un caller) | ✅ disparador explícito |

**Tests corridos, no inferidos:** `pytest tests/test_espejo_permisos.py tests/test_callers_huerfanos.py tests/test_limite_export.py -q` → **78 passed**.

**Contexto importante para no leer esto como una regresión de la tanda 6-septiembre:** `objetivo_service.py` viene del commit `347afb3` ("multiempresa, módulos vacaciones/ausencias/capacitaciones/evaluaciones/inventario/objetivos/proyectos"), muy anterior a este bloque. La migración 119 (de esta tanda) solo agregó `tipo`/`areas_involucradas`/`periodicidad` — no tocó paginación ni auditoría. Y la falta de auditoría ya está **auto-declarada** en `tests/test_auditoria_coherente.py`, que excluye a objetivos "a propósito" de su barrido con una nota de que falta "la definición de producto" (no está exento por ser correcto, está exento porque nadie decidió todavía qué auditar ahí). O sea: es deuda vieja y conocida, no algo que este checklist debería haber declarado como "hecho" — pero el checklist tampoco advierte que objetivos no cumple estas reglas, y como es uno de los 4 módulos que la Sección 9 pide verificar explícitamente, correspondía decirlo.

**Veredicto:** esto es exactamente lo que el usuario pidió que se marcara como lo peor si aparecía. Perfiles/Recategorizaciones/Eventos están limpios. Objetivos no — y como objetivos ya tiene 68 filas hoy y va a crecer, el `.range()` faltante y el `model_dump()` sin `mode="json"` sí son riesgo real de cara al porteo a asyncpg, aunque sean viejos.

---

## 🔴 2. Lo que está en el repo y no está en el documento (PRIORIDAD 2)

### a) `LIMITE_FILAS_EXPORT` es 20.000, no 5.000
`backend/services/_limite_export.py:68` — cambiado el **13/8/2026** (antes de la fecha del
checklist), con justificación medida por escala proyectada (~1.005 colaboradores, ~16.000
eventos/trimestre) y documentado en el propio archivo (líneas 36-40, que además ya avisa que
20.000 **tampoco** cubre un año completo de auditoría — ~64.000 eventos proyectados). El test
`test_limite_export.py:75` fija el literal `20000`. Ni `VERIFICACION-BACKEND.md` (Sección 8) ni
`CLAUDE.md` (varios lugares) reflejan este número — los dos siguen diciendo 5.000. Ligado a
esto: la lista `EXPORTS` creció a **20 entradas** (antes 18) y el conjunto de módulos que
paginan/chequean el límite creció a 8, incluyendo capacitaciones/asignaciones, inventario
(ítems y asignaciones) y proyectos — **hoy solo objetivos queda sin paginar**, no "tres módulos"
como dice `CLAUDE.md`.

### b) `Inventario` está en el menú — el checklist (Sección 10) dice que no debería
`frontend/components/layout/nav-config.ts:76` — `{ label: "Inventario", href: "/inventario", ... }`
sin ningún flag condicional (a diferencia de `SUCESION_ACTIVA` en la línea de al lado). `git log`
confirma que este ítem viene de commits viejos, no se agregó en esta tanda. `Seccion.INVENTARIO`
existe en `utils/_secciones.py:47` con permisos normales, sin gate especial. **La Sección 10 del
checklist dice "Inventario — Fuera del menú hasta nuevo aviso" y eso no es lo que hay hoy en el
repo**: está visible y navegable para cualquier rol con permiso de lectura sobre esa sección. O
el ítem de la Sección 10 está desactualizado, o hay una decisión de producto de volver a mostrarlo
que no quedó escrita en ningún lado.

### c) `documentos próximos a vencer` tiene DDL construido, no "nada"
La migración 113 agregó `adjuntos.fecha_vencimiento date` + índice parcial
`idx_adjuntos_vencimiento` (confirmado en catálogo y en `schema.sql:210,1819`), con un comentario
explícito de que es "para la alerta 'documentos próximos a vencer' del dashboard". Pero es DDL
puro: cero referencias a `fecha_vencimiento` en `schemas/`, `services/`, `routers/` ni en todo el
frontend. Ningún form la expone, ninguna alerta la lee. Es la misma clase de hallazgo que la
trazabilidad candidato→empleado (que si está bien declarada como DDL-sin-wiring en el propio
código) — acá no hay ninguna nota que avise que la columna ya existe.

### d) `/api/eventos/pendientes` ya NO existe — no es "vive sin caller"
La Sección 12 del checklist (deuda conocida) dice que esta ruta "existe y no tiene caller". Es
incorrecto a la fecha del checklist mismo: se **borró el 19/8/2026** (sesión A6,
`routers/eventos_agenda.py:46-51` documenta el porqué) porque `GET /api/dashboard/atencion` pasó
a consumir `EventoAgendaService.pendientes` directamente. La lógica sigue viva, la ruta HTTP no.
Es una corrección a favor: el problema que la Sección 12 señalaba ya se resolvió, solo falta
actualizar el texto.

### e) "Plan de desarrollo — se muestra como Próximamente" (Sección 10) no se encontró
Grep de `"Plan de desarrollo"`, `plan_desarrollo`, `roadmap` en todo `frontend/` → cero matches.
El único `"(Próximamente)"` real es el tab "proyectos" de `empresas/[id]/page.tsx:143`, sin
relación. O el nombre cambió y el checklist quedó con el nombre viejo, o es un ítem que nunca se
llegó a construir ni como placeholder — no se pudo confirmar cuál de los dos.

### f) `objetivos` — falta `GET /{id}`
`registro_routers.py:180-183` tiene un comentario propio diciendo que `ObjetivoService.get_by_id`
está escrito "esperando" esa ruta, que todavía no existe (`objetivos.py` solo expone `""` y
`/exportar`). Es una pieza a medio construir que ningún ítem de la Sección 5 menciona — no es
grave, pero es alcance parcial no declarado.

### g) Corrección al Ítem del puente candidato→empleado (Sección 6)
"4 de los 5 campos que faltan salen de la vacante (área, rol, modalidad, tipo de contrato)" es
**inexacto**. Leyendo `_candidato_contratar_mapeo.py:78-94`: solo **2 campos** salen realmente de
la vacante (`area_id`, `modalidad_trabajo`). `roles` sale del **body** de la request, no de la
vacante. `tipo_contrato` es un **default hardcodeado** (`TIPO_CONTRATO_POR_DEFECTO`,
"Relación de dependencia") — y el propio archivo dedica un comentario a explicar por qué
*no* se copia de la vacante (vocabularios distintos: `vacantes.tipo_contrato` es un enum de 4
valores, `empleados.tipo_contrato` es texto libre — copiarlo sería "el error más fácil de
cometer acá", dice el código). El código está bien y está documentado; el checklist describe mal
de dónde sale el prellenado. Además el mapeo escribe `email_personal` ← `candidato.email` y
`ubicacion` ← vacante, dos campos que la Sección 6 no menciona.

Sobre este mismo punto: "un candidato sin vacante también puede pasar a preingreso, pidiendo todo
a mano" es cierto, pero **no es una rama del mismo endpoint puente** — el puente
(`POST /candidatos/{id}/contratar`) exige `vacante_id` y rechaza con 409 `CANDIDATO_SIN_VACANTE`
si no la tiene. Lo que existe es un camino separado: el alta manual normal
(`POST /api/empleados`) acepta `estado: Literal["activo","preingreso"]`. El checklist no distingue
esto y puede leerse como si el puente soportara ambos casos.

---

## 3. Resto del checklist, por sección

### Sección 1 — Migraciones: **todas ✅**, verificadas por objeto contra el catálogo vivo (no por
conteo de tablas). Las 9 migraciones (113-120) confirmadas con SQL directo contra
`information_schema`/`pg_catalog`, incluido `pg_get_constraintdef` de los CHECK. `db/schema.sql`
refleja 113-121 (72 referencias encontradas) y su encabezado efectivamente ya no lista qué
migraciones están corridas — hay un bloque explícito en las líneas 35-40 que lo dice.

### Sección 2 — Perfiles de puesto: **todos ✅**, sin excepciones. CHECKs de modalidad/nivel/
tipo_contrato comparados carácter por carácter contra `vacantes` — idénticos. Router de
catálogos se registra antes que el CRUD (`registro_routers.py:109-110`).

### Sección 3 — Recategorizaciones: **todos ✅**, sin excepciones. El "solo la fila más reciente
actualiza al empleado" tiene hasta un test de empate (`test_el_EMPATE_de_fecha_actualiza`).

### Sección 4 — Eventos de agenda: **todos ✅**. Nota: usa el mismo literal
`ROL_VE_PRIVADAS_AJENAS` que `onboarding_templates`, con un test de identidad
(`assert ROL_VE_PRIVADAS_AJENAS is ROL_VE_TODO`) — no es una copia que pueda divergir.

### Sección 5 — Objetivos: **todos ✅** (funcionalmente — ver Sección 9 arriba para las fallas
transversales). Confirmado con seguimiento directo: `.contains()` usa un helper
`literal_array()` que sí comilla (`_objetivo_area.py:40`, con el porqué en el docstring);
`_reporte_anual_metricas.py:88` tiene el comentario 🔴 declarando explícitamente que suma
anuales+operativos a propósito; `areas_involucradas` es `text[]` (`udt_name=_text`) confirmado
contra el catálogo.

### Sección 6 — Preingresos y bajas: **todos ✅ salvo la corrección del puente candidato→empleado
(ver arriba, punto 2g)**. El bug del offboarding está realmente arreglado
(`_offboarding_iniciar.py` no toca al empleado; `_offboarding_efectivizar.py:116` es el único que
llama a `dar_de_baja`). El CHECK de estado en catálogo vivo tiene los 5 valores confirmados. Los
5 contadores que excluyen preingreso existen los 5, aunque las líneas citadas en el checklist
migraron (dashboard_service.py ahora en :80/:95, no :67; `_reporte_dotacion.py` en :37/:51/:106,
no :31/:89; `_reporte_movimientos.py` en :41/:62, no :32/:44 — mismo contenido, distinta
ubicación). Los 2 whitelist (`_area_row.py`, `sucesion_repo.py`) usan una constante compartida
`ESTADOS_EN_PLANTILLA`, mejor que lo descrito. El conteo de "15 sitios con `= 'activo'`" en
realidad da 21 ocurrencias en 17 archivos — el número del checklist está desactualizado, pero el
espíritu del ítem (no se tocaron, siguen correctos) se sostiene. El ❌ de "no hay trazabilidad
candidato→empleado" es correcto y está confirmado verbatim en el propio código
(`_candidato_contratar.py:19-20`: *"No crea ninguna referencia... es DDL y está fuera de alcance
por decisión tomada"*).

### Sección 7 — Formación: **todos ✅, incluido el ❓ que más dudaba el usuario.** El import del
Excel real **está construido y probado**, no es un placeholder: `routers/importacion_formacion.py`
(preview+confirmar, rate limit 10/hora), servicios de matcheo/traducción/duplicados completos, y
`tests/test_formacion_import.py` (482 líneas) cubre preview-no-escribe, matcheo por los dos
órdenes de nombre, pares parecidos, reimport sin duplicar, auditoría y revalidación. El Excel
real con nombres reales no está en el repo (correcto, por privacidad), pero el fixture sintético
reproduce las anomalías reales documentadas (13 headers, nombres invertidos, apellido solo,
estado fuera de diccionario). Única precisión menor: el guard que evita `None` en el `.in_()`
vive en `repositories/_asignacion_row.py:38`, no en `asignacion_repo.py` como dice el checklist
— mismo comportamiento, archivo distinto.

### Sección 8 — Escala y paginación: **todos ✅**, incluido el patrón de `nomina_repo` con 3
callers que agregan (confirmado que no se tocó al paginar el resto).

### Sección 11 — Los cuatro greps:
1. `uuid.*==` → 9 matches, todos `uuid4()` como argumento de test, ningún caso real. **No aplica.**
2. `supabase_admin.auth` → 5 matches reales, todo código de auth preexistente (no de los 4
   módulos nuevos). **Deuda de porteo ya declarada, sin novedad.**
3. `model_dump()` sin `mode=` → ~55 matches. La mayoría son `_audit_payloads*.py` (van a JSONB,
   patrón consistente en todo el sistema) y repos preexistentes no relacionados a los módulos
   nuevos. La excepción real es `_objetivo_payload.py`, ya cubierta arriba en la Sección 9 — y el
   grep textual **no la detecta** porque el código usa `model_dump(exclude_none=True)`, no
   `model_dump()` a secas.
4. `": str"` en `schemas/*_id` → **el checklist subestima el alcance.** Los 3 casos que declara
   bien (`message_id`, `post_id`, `email_id` — Gmail/LinkedIn/Zernio) están correctos. Pero hay
   ~30 campos más `_id: str` sin excusar en `ausencias.py`, `cesion.py`, `adjunto.py`,
   `capacitacion.py`, `inventario.py`, `costo.py`, `vacaciones.py`, `dashboard.py`, etc. —
   mayormente `*Response` de salida, no de escritura, así que el riesgo es menor que un INSERT
   mal tipado, pero no están declarados como excepción. Ninguno pertenece a los 4 módulos
   nuevos (son deuda general preexistente), salvo `ObjetivoResponse` que sí es parte de la falla
   de la Sección 9 ya reportada arriba.

### Sección 12 — Deuda conocida: confirmada vigente ítem por ítem, salvo:
- `/api/eventos/pendientes` — **resuelto, no vigente** (ver punto 2d arriba).
- `TestElPisoDeTiempo` — vigente, y "tres apariciones" se refiere a 3 test methods dentro de una
  clase en un único archivo (`tests/test_identificacion_publica.py:370`), no 3 archivos.
- `proyecto_asignaciones` — 31 filas confirmado contra catálogo vivo hoy mismo.
- `'suspendido'` — confirmado muerto: 0 de 31 empleados en ese estado, CHECK lo sigue admitiendo.
- `.gitattributes` — confirmado que sigue sin existir.
- `test_limite_export` con lista a mano — confirmado (`EXPORTS`, ahora 20 entradas, sigue siendo
  literal, no introspección).

---

## 4. Lo que no se pudo determinar leyendo

- **Sección 10 / Inventario**: no se re-auditó el módulo de Inventario en sí (competencias,
  estructura de datos) porque no forma parte de los 4 módulos nuevos del checklist ni de sus
  reglas transversales — solo se verificó su presencia en el menú (punto 2b arriba). Si hace
  falta un veredicto completo sobre Inventario, es una tanda propia.
- **"Plan de desarrollo — Próximamente"**: no se encontró en el código actual (punto 2e). No se
  puede determinar si el ítem cambió de nombre, se movió, o nunca se construyó ni como
  placeholder, sin preguntarle a alguien que sepa el estado real de esa pantalla.
- **`proyecto_asignaciones` — "la ficha no las muestra"**: se re-confirmó el conteo (31 filas)
  contra el catálogo, pero no se re-verificó el lado de UI (que la ficha efectivamente no las
  liste) en esta pasada — quedó dado por bueno del checklist original sin re-chequeo de código.

---

## 5. Estado real de la suite (a la fecha de esta auditoría)

- **Backend: 4004 passed**, 0 fallos, corrido completo (`pytest -q` desde `backend/`, venv). 3
  warnings de deprecación (gotrue, Pydantic config, reportlab), ninguno relevante. **Coincide
  exacto con lo que dice `CLAUDE.md`.**
- **Frontend (`npm test` / vitest): 740 tests en 62 archivos**, todos verdes. **Coincide exacto
  con `CLAUDE.md`.**
- **`node_modules/.bin/tsc --noEmit`: limpio**, exit 0, sin output.
- **Barridos estructurales relevantes a esta auditoría, corridos y verdes**: `test_espejo_permisos.py`
  + `test_callers_huerfanos.py` + `test_limite_export.py` → 78 passed (una corrida) / 68 passed
  (otra corrida parcial de las mismas dos últimas). Sin rojos en ninguna combinación.

---

## 6. Resumen para decidir qué hacer después

**Bloqueante real de cara al porteo:** Objetivos no cumple paginado, auditoría, ni el patrón
`model_dump(mode="json")` — es deuda vieja (preexiste a esta tanda) pero es exactamente la clase
de cosa que "no explota en septiembre" depende de cerrar, porque objetivos va a crecer con uso
real y hoy trae el árbol entero sin límite.

**Para reconciliar documentación (no bloqueante, pero deja el checklist desalineado):**
`LIMITE_FILAS_EXPORT`=20.000 (no 5.000) en `CLAUDE.md` y en la Sección 8 del checklist · el ítem
"Inventario fuera del menú" de la Sección 10 no refleja el código actual · "documentos próximos a
vencer" tiene DDL sin wiring, no "nada" · `/api/eventos/pendientes` ya se resolvió, sacar de la
Sección 12 · corregir la descripción del prellenado del puente candidato→empleado (Sección 6).

**Nada arreglado.** Esto es una auditoría.
