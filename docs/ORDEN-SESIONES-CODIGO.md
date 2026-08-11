# Orden de sesiones — camino a producción

> **Estado al cierre del commit del 422.** Objetivo: que RRHH empiece a usar el sistema, y que el
> dev de infra pueda unificar repos y subir a AWS sin esperarnos.
>
> Dificultad: **1** trivial · **2** acotada · **3** requiere diseño · **4** toca muchos archivos
> 📄 = comprometido con el directorio · 🔒 = bloqueado por dato o decisión · 🌐 = prueba en navegador

---

## Las cuatro reglas de este plan

1. **Nada de AWS.** Ni Dockerfile, ni CI/CD, ni IaC, ni porteo a asyncpg. Es del otro dev. Lo nuestro es que el repo esté en un estado que él pueda tomar.
2. **Solo lo expuesto en el front.** Lo que existe solo en backend queda como está. Eso saca del alcance a assessment, sucesión, las vistas apagadas del organigrama, el reporte adhoc con IA y los módulos `ev_*`.
3. **Se cierran los frentes abiertos antes de abrir nuevos.** Un módulo construido y no ejercitado es trabajo sin cobrar.
4. **El sistema se prueba en el navegador, no solo en la suite.** Los tests estaban en verde mientras 6 de los 11 reportes no funcionaban en producción.

---

## Lo hecho

| Bloque | Qué se cerró |
|---|---|
| **A** ✅ | Casilla del sistema designable · `es_lider` derivado del import · contrato en el organigrama · filtro por área en inventario |
| **B** ❌ | **Cancelado.** Objetivos es tablero del equipo de RRHH, no de los 31 empleados: `responsable_id → users` es el modelo correcto |
| **C** ✅ | El import de costos audita · la empresa del evento sale de la entidad · guarda de baja del usuario que sostiene la casilla |
| **D** ✅ | Cuatro barridos estructurales nuevos + los 8 eventos de auditoría que faltaban + la migración que rescata los triggers de cruce de empresa |
| **E** ✅ | Sección Comunicación · envío de plantillas · destinatario libre · historial de mails · **el sistema mandó su primer mail** |
| **H** ✅ | Export de 12 a 25 módulos · subobjetivos con múltiples responsables · import de objetivos por Excel con su pantalla |
| **F** ✅ | CV screening completo: código de vacante, matcher, adjunto, extracción de texto, clasificador con criterio configurable |
| **G** ✅ | Link público de carga de horas (`/horas`) · pantalla de clientes · vista de horas por cliente |
| **422** ✅ | Bug de producción en el alta de clientes + handler de `RequestValidationError`. Las 27 pantallas dejan de mostrar "Error del servidor" ante un 422 |

**Suite:** 3280 backend · 647 front en 53 archivos · **trece** barridos estructurales · `tsc` limpio.
*(Remedido el 11/8/2026. La lista de los trece vive en `CLAUDE.md` → Tests; acá solo el número.)*
**Migraciones:** hasta la 107, todas corridas. `schema.sql` verificado exacto contra el catálogo.

---

## Bloque L — Clientes como catálogo global

**Es lo que sigue, y va antes de J** porque cambia `schema.sql`, que es el archivo del handoff.

**Decisión tomada:** un cliente no pertenece a ninguna empresa. Se ve, se crea y se elimina con
el sidebar en cualquier modo, y cualquier empleado imputa horas contra cualquier cliente.
Revierte lo que declara `migrations/102_clientes.sql`.

**Verificado en el catálogo vivo (10/8):** `clientes` 0 filas · `horas_proyecto` 0 filas ·
los tres índices de `clientes` idénticos a `schema.sql`, sin drift · `auditoria.empresa_id` es
nullable.

**El hallazgo que despeja el cambio:** `horas_proyecto.empresa_id` no sale del cliente por
ningún camino. En el link público sale del empleado; en el camino interno, del proyecto.

| # | Sesión | Dif. | |
|---|---|:---:|---|
| **L1** | Dividir `identificacion_service.py` (150/150) y `ClienteModal.tsx` (147/150) | 2 | Refactor puro, commit propio. La suite tiene que quedar idéntica: 3247 / 636 |
| **L2** | Backend: schemas, `cliente_repo`, `cliente_service`, auditoría | 3 | Unidad indivisible. Partirla deja el módulo en 500 |
| **L3** | 🔴 Migración **108** — `DROP NOT NULL` + `ux_clientes_nombre UNIQUE (lower(nombre))` | 1 | No destructiva. Va **antes** del deploy de L2 |
| **L4** | Link público: `clientes_disponibles`, `_verificar_cliente`, `hay_clientes_activos` | 3 | El gate `sin_clientes` se queda: pasa a ser "¿hay algún cliente activo en el sistema?" |
| **L5** | Front: `types/cliente.ts`, `guardarCliente.ts`, sacar el `<select>` de empresas | 2 | |
| **L6** | 🔴 Migración **109** — drop del índice viejo, la FK, `idx_clientes_empresa` y la columna | 1 | Destructiva. Va **después** de que L2–L5 estén en producción |
| **L7** | Reemplazar los ~13 tests de aislamiento que pierden objeto | 3 | No se borran: se reemplazan. Ver las cuatro invariantes abajo |

### Las decisiones de L, para no rediscutirlas

- **Unicidad:** `UNIQUE (lower(nombre))` global. "ACME" existe una sola vez en el sistema.
- **Orden de migraciones:** 108 antes del código, 109 después. Nunca hay un estado donde el alta falle.
- **Auditoría:** el evento de cliente lleva `empresa_id` NULL. Una entidad global no tiene empresa;
  etiquetarla con la del header sería mentir.
- **El gate `sin_clientes` no se saca.** Con cero clientes nadie puede imputar horas, y el mensaje
  es honesto. Solo se le quita el `.eq("empresa_id")`.

### Las cuatro invariantes que L7 tiene que reemplazar, no borrar

1. **"El UPDATE escribe donde tiene que escribir."** `test_update_ajeno_no_escribe` es el único que
   mira `Almacen.escrituras` y distingue "no devolvió nada" de "no escribió nada". El caso ajeno
   desaparece, la técnica no debería perderse.
2. **"El 404 no es un oráculo."** Ya no hay ajeno, pero sigue habiendo inexistente, y el mensaje
   canónico tiene que seguir siendo uno solo.
3. **"La auditoría se etiqueta con la entidad, no con el header."** Se reescribe más filoso: con el
   header en empresa A, el evento de cliente registra NULL.
4. **"El `cliente_id` del body es un cliente real y activo."** Sobrevive vía `find_by_id` + `activo`.

---

## Bloque J — Handoff al dev de infra

Después de L. No depende de nadie y el otro dev trabaja en paralelo.

| # | Sesión | Dif. | |
|---|---|:---:|---|
| **J1** | Verificar `schema.sql` contra el catálogo vivo: reconstruir en una base limpia y diffear | 3 | Es el archivo del que él va a levantar RDS. **Con las migraciones 108 y 109 ya corridas** |
| **J2** | `.env.example` completo y verificado contra `settings.py` | 1 | Incluye `HORAS_PUBLICO_ENABLED` y `ASSESSMENT_ENABLED` |
| **J3** | `DEPLOY.md` y `BITACORA-CAMBIOS.md` al día | 2 | `CLAUDE.md` ya quedó al día en el cierre de G |
| **J4** | Documento de handoff: rutas públicas, techos medidos, decisiones que condicionan el cutover | 2 | Storage, `ban_duration`, `TRUSTED_PROXY_HOPS`, rate limit con `memory://` |
| **J5** | 🔴 **Decidir**: limpiar las 6 tablas huérfanas y las `ev_*`, o dejarlas documentadas como residuo | 2 | Es DDL destructivo. Si va, va **antes** de entregar el schema |

**Pendiente para J1:** el diagnóstico de replayabilidad tiene que cubrir las dependencias de
Supabase (`auth.uid()`, `auth.users`, schema `storage`, roles `anon`/`authenticated`/`service_role`).
El dev de infra levanta RDS pelado: si `schema.sql` las referencia, el replay muere en la primera
policy.

## Bloque I — Testing profundo

🔒 **Bloqueado por RRHH.**

| # | Sesión | Dif. | |
|---|---|:---:|---|
| **I1** | 🌐 Recorrido por rol: crear un `gerencia_lectura` y un `mandos_medios` reales | 3 | Los 4 usuarios de hoy son admin. 🟢 `manager_id` pasó de 0/19 a 11/31 |
| **I2** | 🌐 Flujos críticos con datos reales: alta, vacación con saldo por período, ausencia, adjunto (E2E contra Storage, nunca ejecutado), import de nómina, export por módulo, generar un reporte | 3 | Cierra todos los "construido, nunca ejercitado" |
| **I3** | 🌐 Smoke test de regresión final | 2 | Puerta de salida a producción |

## Bloque K — Limpieza

No bloquea nada. Va cuando haya aire.

| # | Sesión | Dif. | |
|---|---|:---:|---|
| **K1** | 🔴 Los archivos **al filo** (ver tabla abajo) | 2 | Tiene fecha: bloquean el próximo cambio en su módulo |
| **K2** | `test_limite_export.EXPORTS` es lista a mano → introspección | 2 | Un export nuevo pasa el barrido sin ser mirado. Ya pasó dos veces |
| **K3** | Los 2 hooks del front sobre 80 líneas | 2 | |
| **K4** | Test que compare `aplicar_filtro_estado` con `derive_estado` | 2 | |
| **K5** | Los archivos del front sobre 150 líneas | 4 | Una sesión por archivo. `offboarding/page.tsx` 311, `areas/page.tsx` 271 |
| **K6** | Las 7 comparaciones `empresa_id !=` post-lectura | 4 | Sin oráculo: elegancia, no seguridad. Ninguna es sobre clientes |
| **K7** | 🆕 Barrido de endpoints sin test por HTTP | 3 | Ver abajo — nace con snapshot, no con lista |

### K7 — el hueco que encontró el bug del 422

**Medido:** 82 endpoints reciben body Pydantic, **77 quedarían huérfanos**. La causa de fondo es
más ancha que el barrido: **solo 7 de 154 archivos de test atraviesan HTTP**.

Un barrido con 77 excepciones declaradas es una lista que nadie mira — el mismo defecto de K2.
La forma que sí sirve: introspección de `app.routes` filtrando los que declaran body, **snapshot
generado** de los huérfanos actuales, y el test rojea solo si aparece un path que no está en el
snapshot. Solo baja, nunca sube. Eso captura endpoints nuevos sin pedir 77 sesiones.

---

## Pendientes concretos

### 🔴 Endpoints sin puerta — encontrados por el barrido nuevo del front

| Endpoint | Consecuencia |
|---|---|
| `POST /api/costos/presupuesto` | **Fijar un presupuesto no se puede hacer desde la aplicación.** Los cero eventos en producción no eran falta de uso |
| Asignación single a proyecto | La pantalla usa el bulk y el alta por área |
| `deleteProyecto`, `fetchEmpresaConfig`, `subscribeEmpresaActiva`, `updateVacacion` | Declarados con su razón |

### Sueltas del bloque F

- El nombre del candidato sale del header `From`, no del CV. Ahora que se extrae el texto, puede salir de ahí
- El código de vacante tiene que poder editarse por RRHH — con dos cosas a resolver: colisión, y qué pasa con los mails ya recibidos con el código viejo
- La pantalla de pendientes trae todos los mails con adjuntos de la casilla (48 de ruido en la prueba)

### Archivos al filo — bloquean el próximo cambio en su módulo

`identificacion_service.py` **150/150** 🔴 · `routers/horas_cliente.py` 80/80 · `_clasificador_prompt.py` 150/150 · `CandidatoDetailPanel.tsx` 150/150 · `candidato_repo.py` 100/100 · `objetivo_repo.py` 100/100 · `vacante_repo.py` 100/100 · `cliente_repo.py` 98/100 · `horas_repo.py` 98/100 · `horas_publico.py` 79/80 · `ClienteModal.tsx` 147/150 · `CargaForm.tsx` 148/150 · `IntegracionesSection.tsx` 148/150 · `app/horas/page.tsx` 146/150 · `carga_horas_service.py` 143/150

Los dos primeros que toca L salen en **L1**.

### Deuda anotada

- `_campo_legible` deja los nombres en inglés en inglés: en el login se lee "username (falta), password (falta)" en una app en castellano. Es la pantalla más vista del sistema
- El contrato de errores generado (`backend/tests/_contrato_errores.json`) impone un orden: quien toque el handler y corra solo vitest ve verde hasta que corra pytest
- Los barridos de texto leen comentarios como si fueran código. Ya mordió dos veces: `services/clientes.ts` y el comentario de `ClienteModal` que nombraba el service
- `ruff check` sobre una ruta inexistente devuelve "All checks passed" con exit 0 — afecta a toda la familia de barridos que dependan de ruff
- `MailEnviadoRepo.ultimos` fue código muerto invisible al barrido: nombres genéricos (`ultimos`, `crear`, `listar`) pueden tapar huérfanos reales
- `noUnusedLocals` desactivado en `tsconfig.json`
- La card del organigrama muestra el contrato del primer integrante de cada grupo, no de cada persona
- Al extraer `_uno` en el clasificador, la regla "un evento por lote" salió del alcance de `test_auditoria_coherente`
- `main.py` conserva un `I001` preexistente (`registro_routers` vs `utils.errors`). Reordenarlo es reflow fuera de scope

---

## Lo que no depende de nosotros

### 🔴 RRHH — bloquean sesiones enteras

| Qué | Bloquea |
|---|---|
| **Cargar al menos un cliente** | El link de horas rechaza a **todos** los empleados sin eso. Con L, alcanza con **uno solo en todo el sistema**, no uno por empresa |
| Poblar `horas_contrato` (0/31) | El dato está en `turno` como texto: "8 A 17 HS.". Toda licencia se calcula hoy con 8 h asumidas |
| Crear un usuario `gerencia_lectura` y uno `mandos_medios` | **I1** |
| Cargar vacaciones e inventario de prueba | **I2** |
| Cargar `legajo` (0/31) | El import de vacaciones (comprometido) |
| Cargar `costos_nomina` (0 filas) | Historial salarial, masa salarial, presupuesto |
| Deduplicar `GESTION DE DEUDA` | Asignación y filtros por área |
| Definir si `valor_hora = 0` es cero o "no sabemos" | El reporte de costos lo suma como cero |
| Segundo lote de evaluaciones | Estadísticas anuales (comprometido) |

### Dev de infraestructura

- **Redis para el rate limit.** Con `memory://` el contador es por proceso. En el link de horas el rate limit es la **única** defensa del paso del DNI
- `HORAS_PUBLICO_ENABLED=true` en `sofia-backend` cuando se decida encender el link

### De la reunión

- ¿El import de nómina sigue creando "proyectos" solo, o se apaga? Hoy crea uno por cada gerencia del Excel
- La lista inicial de clientes

---

## Fuera de alcance — decidido, no pendiente

| Qué | Por qué |
|---|---|
| Todo AWS | Del dev de infra |
| **Tabla puente `cliente_empresas`** | La decisión no es N:M, es que el cliente no tenga empresa. La tabla puente sobra |
| **H5 — alertas configurables** 📄 | Construible, pero sin nada sobre qué alertar: 0 vacaciones, 0 períodos cerrados, 1 onboarding |
| **H2, H4, H6** 📄 | Bloqueados por datos: 0 egresos, `legajo` 0/31, 1 solo lote de evaluaciones |
| **E3-3** filtro por área en objetivos 📄 | Los operadores de RRHH no tienen área. Se explica al directorio |
| Assessment, Sucesión, vistas del organigrama, reporte adhoc, `ev_*` | Fuera del front por decisión |
| Editar una carga de horas | Revoca la decisión de irreversibilidad. Borrar sí está |
| Asignar por equipo 📄 | `empleados.equipo` es texto libre sin poblar |
| Plantillas base del sistema | Las crea RRHH |

---

## El camino corto

**L1 → L2 → L3 → L4 → L5 → L6 → L7 → J1 → J2 → J3 → J4 → K1 → I1 → I2 → I3**

Quince sesiones. Al final: los clientes son globales y cualquier empleado imputa horas contra
cualquiera, el dev de infra tiene un repo y un `schema.sql` que puede tomar, los archivos al filo
dejan de bloquear, los tres roles están probados con personas reales, y los flujos críticos se
ejercitaron con datos.

**Lo único que urge y no depende de código:** que RRHH cargue un cliente y cree los dos usuarios
de prueba.
