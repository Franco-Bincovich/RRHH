# Deuda técnica — relevamiento verificado

> **2/8/2026.** Todo verificado contra el **código** y el **catálogo vivo de producción**
> (`grmdiwxcvcjorlohpwji`), no contra la documentación.
>
> ✅ **ACTUALIZADO tras la tanda de limpieza del mismo día.** Lo cerrado quedó tachado en su
> lugar, con el motivo — **no se borró**: una lista que solo muestra lo pendiente pierde la única
> forma de saber si un ítem se cerró o se olvidó. Ver el resumen al final.
>
> Gravedad: 🔴 rompe o expone datos · 🟠 va a romper · 🟡 fricción · ⬜ cosmético
> Esfuerzo: S ≤1 h · M 1-3 h · L >3 h

---

## 1. Código muerto

| Qué | Dónde | Callers reales | Gravedad | Esf. |
|---|---|---|---|---|
| ✅ ~~`costo_repo.py` (135 líneas)~~ | — | **BORRADO 2/8.** Callers reverificados uno por uno antes de tocar nada | ✅ | — |
| ✅ ~~`assessment_repo.py` (131)~~ | — | **BORRADO 2/8.** Ídem | ✅ | — |
| ✅ ~~`EliminarLoteButton.tsx` (74)~~ | — | **BORRADO 2/8.** Ídem | ✅ | — |
| Tablas huérfanas: `configuracion_empresa`, `documentos_empleado`, `notificaciones`, `notificaciones_config`, `sucesion_posiciones`, `assessment_reportes` | `db/schema.sql` | **0 filas las 6** en producción | ⬜ | S |

### 🔴 Lo que NO está muerto, aunque se sospechaba

| Qué | Por qué NO se borra |
|---|---|
| **`ev_*` entero** (`ev_plantillas_repo` 129, `ev_instancias_repo` 146, `ev_ciclos`) | **Los 3 routers están MONTADOS** (`main.py:154-157`) y los repos tienen 3, 1 y varios callers. Las tablas están vacías en producción (0/0/0) pero **la API existe y responde**. Borrarlos rompe endpoints publicados |
| **Assessment** | El router se monta condicionalmente (`main.py:141`, `assessment_enabled=false`) — el módulo está apagado, **no muerto**. Los services, schemas y tests siguen vivos. Solo `assessment_repo` está huérfano |
| **Sucesión** | Apagado en el front por dos flags; **todo el backend intacto y montado** |

> ⚠️ **Regla que sale de esto:** "está oculto en la UI" ≠ "está muerto". De los 5 sospechosos,
> **3 estaban vivos**. Verificar callers uno por uno, siempre.

---

## 2. Fugas y oráculos pendientes

| # | Qué | Dónde | Gravedad | Esf. |
|---|---|---|---|---|
| a1 | ✅ ~~**`EMPRESA_MISMATCH` 422 vivo**~~ — **CERRADO 2/8.** Los dos pasan al 404 del módulo, con el filtro **en el WHERE** (Forma A), no comparando después. `tests/test_empresa_mismatch_cerrado.py` fija el contrato Y que la empresa viaje en la query; con el bug reinstalado caen 6 de 10 | ✅ | — |
| a2 | **7 comparaciones `empresa_id !=` post-lectura** (Forma B). Todas devuelven 404, así que **no hay oráculo**, pero traen la fila antes de decidir: más caro y más fácil de olvidar al copiar | `evaluacion_service.py:33` · `adjunto_service.py:64` · `cesion_service.py:42` · `periodo_service.py:49` · `tipos_ausencia_service.py:80` · `reporte_export_service.py:42` | 🟡 | L |
| b | **El import de costos no audita nada** — `batch_upsert_nomina` sin un solo evento, contra la regla propia de "un evento por lote". El Flujo 1 sí audita | `routers/importacion_nomina.py` (verificado: cero `audit` en el archivo) | 🟠 | S |
| c | **`_costos_write` audita con la empresa del HEADER**, no la de la entidad. Viola Vista vs Acción | `services/_costos_write.py:80` | 🟠 | S |
| c2 | **9 eventos con `empresa_id NULL` en producción.** 6 legítimos (`alta_usuario` ×3, `cambio_password` ×3 — los usuarios no cuelgan de empresa) y **3 mal etiquetados**: `alta_adjunto`, `baja_adjunto` (sobre una vacante, que sí tiene empresa) y `baja_candidato` | tabla `auditoria` | 🟡 | M |
| d | **Barrido de los endpoints nuevos (~15 sesiones): sin hallazgos.** `/plantillas` (4), `/plantillas/enviar`, `/superiores-pendientes` (2), `/asignaciones/area`, `/configuracion` (3) — **todos** con `require_permission` y barrera de empresa donde reciben un id | — | ✅ | — |

> ✅ **a1 era el único 🔴 de la sección y está cerrado.** Lo que queda (b, c, c2) son **fixes de
> comportamiento, no limpieza**, y van en sesión propia: hoy no rompieron nada porque hay UNA
> empresa, y se vuelven visibles el día que exista la segunda.

---

## 3. Límites de líneas

### ✅ Sobre el límite — CERRADO 2/8: **el backend quedó en CERO archivos over-limit**

| Archivo | Antes | Ahora | Qué se hizo |
|---|---:|---:|---|
| `repositories/_onboarding_templates_row.py` | 159 | **87** | Partido en tres: `_row` (SELECT+mappers), `_filtros` (empresa y visibilidad), `_write` (payloads) |
| `services/_audit_payloads.py` | 167 | **119** | `_audit_payloads_offboarding.py`, siguiendo la instrucción que el propio archivo dejaba escrita |
| `repositories/ev_instancias_repo.py` | 146 | **98** | Satélite `_ev_instancias_row.py` |
| `repositories/ev_plantillas_repo.py` | 129 | **93** | Satélite `_ev_plantillas_row.py` |
| `services/reporte_anual.py` | 154 | **112** | `_reporte_anual_metricas.py` |
| `repositories/costo_repo.py` · `assessment_repo.py` | 135 · 131 | — | **Borrados**, no divididos |
| `services/usuario_service.py` | 149 | **77** | `_usuario_alta.py`. **Desbloquea la guarda de la casilla de correo** (sección 8) |
| `services/ev_instancias_service.py` | 149 | **113** | `_ev_instancia_crear.py`, forzado por el fix de a1 |

> 🔴 **EL APRENDIZAJE, que vale más que los ocho cortes:** dos satélites tenían escrito en su
> docstring *"acá el límite es 200"*, y por eso uno llegó a **159 sin que nadie lo notara**. Un
> `_*.py` dentro de `repositories/` **es un repositorio y su límite es 100**. Partir un archivo
> para respetar un límite es correcto; **redefinir el límite del archivo nuevo, no**.

### En el techo exacto — el próximo cambio EXIGE dividir primero (remedido 2/8)

**Services 150/150:** `assessment_service.py`. **A 149:** `vacante_service` · `offboarding_service` · `adjunto_service` · `_nomina_lote`.
**Repos 100/100:** `planes_carrera_repo` · `inventario_asignaciones_repo` · `evaluacion_repo`. **A 98-99:** `objetivo_repo` · `vacante_repo` · `onboarding_templates_repo` · `nomina_repo` · `inventario_items_repo` · `ev_instancias_repo` · `empresa_repo` · `capacitacion_repo`.
**Routers 80/80:** `vacantes.py` · `adjuntos.py`. **A 79:** `vacaciones.py` · `objetivos.py` · `inventario_items.py` · `asignaciones_capacitacion.py`.

### Frontend

| Archivo | Líneas | Corte | Esf. |
|---|---:|---|---|
| `app/(dashboard)/costos/page.tsx` | **624** | El peor del repo. Molde: `components/features/sucesion/` (855→85) | L |
| `app/(dashboard)/vacantes/[id]/page.tsx` | **577** | Ídem | L |
| `app/(dashboard)/onboarding/page.tsx` | **410** | Tabs a componentes | M |
| `components/features/costos/ImportarNominaCSVModal.tsx` | **377** | Hook + pasos | M |
| `app/(dashboard)/offboarding/page.tsx` | 307 · `NominaModal` 287 · `areas/page` 261 · `evaluacion/[token]` 258 · `VacanteModal` 251 · `AIPanel` 249 · +18 más sobre 150 | — | L |
| **Hooks sobre 80** | `useFiltrosVacaciones.ts` **95** · `useFiltrosAsignacionesCap.ts` **89** | Molde ya aplicado: `useOpcionesAusencias` (partir carga de opciones vs. estado del filtro) | S |

> ⬜ `dropdown-menu.tsx` (268) y `dialog.tsx` (160) son primitivos generados de shadcn/ui: **no cuentan**.

---

## 4. Espejos y duplicaciones

| Qué | Estado verificado | Gravedad | Esf. |
|---|---|---|---|
| **`permisos.ts` ↔ `permisos.py`** | ✅ **CERRADO 2/8** — `tests/test_espejo_permisos.py` compara secciones, acciones, roles y el fail-closed, con guarda de mínimo por extracción. Nació en verde (era el momento más barato: no había nada que arreglar primero) | ✅ | — |
| **`MANDOS_MEDIOS_SECCIONES` duplicado** | ✅ **CUBIERTO por el mismo test**: sigue habiendo dos declaraciones, pero ya no pueden separarse en silencio | ✅ | — |
| **`_subset` duplicado** en los 6 `_audit_payloads*` | Es deliberado y está documentado (a diferencia de `sin_derivados`, que se importa) | ⬜ | — |
| **Filtro `empresa` duplicado 8× entre repos** | `_with_empresa` existe pero no todos lo usan | 🟡 | M |
| **Presupuesto de tiempo duplicado** | `_nomina_lote.py:65-105` y `_lote_mails.py:55-85`. Fue decisión consciente con 2 casos; con un 3º entrando (import de novedades) deja de serlo | 🟡 | M |

> 🔑 Con esto son **cinco** los barridos estructurales del repo (paridad list↔export, límite de
> export, selects de repos, espejo de permisos, nav↔permisos), **todos con guarda de mínimo**.

---

## 5. Tests que no prueban

| Qué | Dónde | Mutación que sobreviviría | Gravedad |
|---|---|---|---|
| Fake que **acepta `empresa_id` y lo ignora** | `test_empleado_service.py:128` · `test_audit_instrumentacion_rrhh.py:81` · `test_domicilio_desglosado.py:119` | Borrar el `_with_empresa` del repo real | 🟡 (declarado) |
| Ídem, devolviendo constante | `test_empleado_area_empresa.py:71` (`return _resp(EMPLEADO, EMPRESA_A)`) | Ídem | 🟡 (declarado) |
| Fake de asignaciones sin empresa | `test_mail_envio.py:79` | El mailer no valida empresa (por diseño) | ⬜ |

**Hallazgo honesto:** el barrido **no encontró aserciones vacuas nuevas**. Los ~10 fakes permisivos
que aparecen están **todos declarados en su docstring** (`"acepta empresa_id y lo ignora"`,
`"permisivo"`) y tienen un archivo hermano que sí la honra — que es exactamente el patrón que
CLAUDE.md manda. La disciplina se sostuvo.

⚠️ **Lo que sí falta es cobertura, no calidad:**

| Hueco | Gravedad | Esf. |
|---|---|---|
| **Ningún test del alta/edición de plantillas de mail** (`plantillas_service.guardar/borrar`) — solo del render y los permisos | 🟠 | M |
| **Ningún test de `_asignaciones_bulk.asignar_bulk`** en su camino manual con proyecto inexistente | 🟡 | S |
| **`mail_enviado_repo` sin tests** (idempotencia probada solo con fake) | 🟡 | S |

---

## 6. Documentación que miente

**`CLAUDE.md`** — desactualizado en **10 números verificables**:

| Afirma | Real | |
|---|---|---|
| "975 passed" | **1539** | tests backend |
| "61 archivos `test_*.py`" | **87** | |
| "backend va por **081**" | **089** | y 086-089: las 4 primeras corridas, la 089 pendiente |
| "hoy son **54**" repos | **67** | regla 14 (asyncpg) |
| "143 tests" front | **214** | |
| "52 tablas" | **58** | schema.sql |
| "113 archivos" services | **124** | |
| "79 archivos SQL" | **87** | migraciones |
| "180 gates" | **240** | `require_permission` |
| "48 endpoints" routers | 52 archivos de router | |

Además: la sección **"Líneas — REMEDIDO 28/7/2026"** está entera obsoleta (no incluye
`_onboarding_templates_row` 159, ni los hooks sobre 80); dice que `AusenciaModal` está en 149
(hoy 103) y `useFiltrosAusencias` en 93 (hoy 59).

> ✅ **La limpieza de `docs/` se hizo el 2/8/2026** (28 → 17 archivos). `MODELO_DATOS.md` se
> **borró** —describía 13 tablas inexistentes y se declaraba fuente de verdad del schema—, junto
> con las dos auditorías del 29/5, la extracción de Nexio, `INVESTIGACION_ROLES.md`, `CHANGELOG.md`
> y los 7 diagnósticos de sesión (fusionados en `DECISIONES.md`). `ESTADO-VS-COMPROMISO.md` y
> `MATRIZ-FILTROS.md` quedaron actualizados, y se sumaron `DEPLOY.md` y `DECISIONES.md`.
>
> **Lo único que sigue mintiendo es `CLAUDE.md`**, con los 10 números de arriba.

---

## 7. Datos inconsistentes en producción

| Qué | Evidencia | Gravedad | Esf. |
|---|---|---|---|
| **`GESTION DE DEUDA` y `GD - GESTION DE DEUDA`** — la misma área duplicada por el import (una por grafía del CSV). Con áreas duplicadas, "asignar el área" asigna a la mitad | tabla `areas`, 9 filas | 🟠 | S (RRHH) |
| 🔴 **`manager_id` sigue 0/19** — el import ya lo escribe (sesión del 2/8) pero **RRHH no reimportó**. Sin esto, `mandos_medios` no ve nada y el ownership cruzado no se puede probar | `empleados` | 🔴 | — (RRHH) |
| 🔴 **`legajo` 0/19** — bloquea el import de vacaciones pendientes, que solo trae legajo como ancla | `empleados` | 🔴 | — (RRHH) |
| **`valor_hora = 0` en las 19 asignaciones** — indistinguible de "no lo sabemos", y el reporte de costos lo suma | `proyecto_asignaciones` | 🟠 | S |
| **`seniority` 15/19 vacío** | `empleados` | 🟡 | — (RRHH) |
| **1 adjunto con `empresa_id` NULL** (fila legacy) — bloqueado en TODOS los modos por diseño, o sea inaccesible | `adjuntos` | 🟡 | S |
| **1 proyecto sin nadie asignado** — no aparece bajo ninguna área (es la definición, no un bug) | `proyectos` | ⬜ | — |
| **`costos_nomina` 0 filas** → el historial salarial (C1) sale vacío para todos. Feature entera, dato inexistente | | 🟠 | — (RRHH) |
| **`tipos_ausencia`: 3 activos** (Injustificada desactivada por la 088 ✅, "Otro" sigue activo a la espera del catálogo real) | | ⬜ | — |

---

## 7-bis. `db/schema.sql` — dos trampas de mantenimiento

Verificado el 7/8/2026 contra el catálogo vivo: el archivo está **exacto** (0 diferencias en
tablas, columnas, FKs, CHECKs e índices, en las dos direcciones). No es deuda de contenido. Lo
que sigue es deuda de **proceso**, y las dos muerden recién el día que alguien lo regenere.

### 🔴 Regenerarlo con `pg_dump` rompe el barrido de selects — y el rojo miente

`tests/_postgrest_schema.py` no parsea SQL: lo lee con dos regex hechos a medida del formato
actual del archivo.

| Regex | Qué exige hoy | Qué emite `pg_dump` |
|---|---|---|
| `_RE_TABLA` | que el `CREATE TABLE` cierre con `\n);` | formato propio, con tipos calificados por esquema |
| `_RE_FK` | `ALTER TABLE [public.]tabla ADD CONSTRAINT … FOREIGN KEY …` | **`ALTER TABLE ONLY public.tabla …`** |

**`_RE_FK` no contempla el `ONLY`.** Con un dump, las **153 FKs dejarían de parsearse**: `entre()`
devolvería siempre vacío, los embeds con FK nombrada tirarían `SelectInvalidoError` y
`test_selects_repos.py` caería en masa sobre sus 238 selects.

**Lo peligroso no es el rojo, es cómo se lee:** parece "el schema está mal" cuando el problema es
el formato. **Si alguna vez se regenera con otra herramienta, los dos regex se adaptan en la MISMA
tanda**, o se pierde medio día persiguiendo un bug que no existe.

### No hay script generador, ni procedimiento escrito

`schema.sql` se generó **a mano**, leyendo el catálogo. En `backend/scripts/` solo hay smoke
tests. `docs/DEPLOY.md` dice *"hay que regenerarlo desde el catálogo"* sin decir **con qué**, y
`backend/db/README.md` tampoco. O sea: el artefacto más crítico del rebuild no tiene forma
reproducible de rehacerse, y el próximo que lo intente va a improvisar un `pg_dump` — que es
exactamente lo que dispara la trampa de arriba.

---

## 8. Anotado y nunca hecho

| Pendiente | Dónde | Gravedad | Esf. |
|---|---|---|---|
| 🔴 **Guarda de baja del usuario que es la casilla de correo** — bloquear con 409. **No se hizo porque `usuario_service.py` está en 149/150** | `repositories/integracion_remitente_repo.py` 🚩 | 🟠 | M (exige dividir primero) |
| **Mapeo de columnas del archivo de novedades** — a la espera del archivo real de RRHH | `services/_import_csv.py` 🚩 | 🟡 | — |
| **Índice normalizado para el matcheo por nombre** — cuando el padrón pase de unos miles (hoy 19) | `repositories/_empleado_lookup_repo.py` 🚩 | ⬜ | — |
| **Un nieto de tipo de ausencia se puede crear por SQL directo** — el CHECK no puede consultar otra fila; la guarda vive en el service | `services/_tipos_jerarquia.py` 🚩 | ⬜ | — |
| **`objetivos.responsable_id` es FK a `users`, no a `empleados`** — bloquea filtro por área e import. **Con 1 fila la migración es trivial; con datos, cara** | CLAUDE.md, verificado en catálogo | 🟠 | M |
| **Filtro por provincia/localidad** — las 6 columnas existen (mig 081), sin domicilios cargados | | ⬜ | — |
| **`objetivos.py` / `inventario_items.py` (79 líneas)**: al dividirlos, agregarles `shared_limit("30/hour", scope="export")` | hay un test que lo recuerda | 🟡 | S |
| **Los 2 hooks del front sobre 80** (`useFiltrosVacaciones` 95, `useFiltrosAsignacionesCap` 89) — quedaron fuera de la tanda de límites del 2/8, que fue de backend | molde: `useOpcionesAusencias` | 🟡 | S |
| **E2E real de adjuntos nunca ejecutado** (`_BUCKET` hardcodeado a prod) | | 🟡 | — (cutover AWS) |
| **Reactivar `/configuracion` → desactivar "Otro"** cuando RRHH cargue sus tipos | mig 088 🚩 | ⬜ | — (RRHH) |

---

## Orden recomendado de ataque

**✅ Tandas 1 a 5 — HECHAS el 2/8/2026**, salvo lo que se separó a propósito:
1. ✅ `EMPRESA_MISMATCH` ×2 · ✅ borrado de los 3 muertos · ✅ `CLAUDE.md`,
   `ESTADO-VS-COMPROMISO.md` y `MATRIZ-FILTROS.md` al día · ✅ los 7 over-limit (5 partidos,
   2 borrados) + `usuario_service` · ✅ el test del espejo de permisos.
2. 🚩 **Queda de la tanda 1:** auditoría del import de costos (2b), `_costos_write` con la empresa
   de la entidad (2c) y los 3 eventos mal etiquetados (2c2). **Se separaron a propósito: son fixes
   de COMPORTAMIENTO, no limpieza**, y merecen su propia sesión con tests de auditoría.
3. 🚩 **Queda de la tanda 4:** los **2 hooks del front sobre 80** (`useFiltrosVacaciones` 95,
   `useFiltrosAsignacionesCap` 89) y los 33 archivos del front sobre 150, con
   `costos/page.tsx` (624) y `vacantes/[id]/page.tsx` (577) a la cabeza.

**Fuera de código — pedidos a RRHH (bloqueantes reales).**
9. **Reimportar la nómina** para poblar `manager_id` (hoy 0/19): sin eso, `mandos_medios` no ve
   nada y todo el ownership cruzado que se construyó está sin ejercitar.
10. **Definir el ancla del import de vacaciones** (legajo en la nómina, o DNI en el archivo).
11. **Deduplicar `GESTION DE DEUDA`**.
12. Definir si `valor_hora = 0` es cero o "no sabemos".

> **Lo que NO recomiendo tocar en esta limpieza:** los 7 `empresa_id !=` de Forma B (2a2) — son
> correctos, solo menos elegantes, y migrarlos toca 6 services vivos por cero cambio observable.
> Y las 6 tablas huérfanas: se limpian en el cutover a AWS, como ya está decidido.
