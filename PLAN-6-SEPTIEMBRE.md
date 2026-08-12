# Plan de trabajo — HR Karstec

> **Entrega comprometida: 20 de septiembre.**
> **Objetivo interno: 6 de septiembre**, para que el dev de infra tenga dos semanas de
> colchón con el sistema completo y estable.
>
> Hoy: 12 de agosto. **25 días de construcción, 14 de colchón.**

---

## 🔴 El condicionante que atraviesa todo el plan

El dev de infra ya migró tres proyectos a AWS (KarIA Reach, Agent_Admin y RRHH) y dejó
documentado el resultado en `docs/handoff-aws/`. El dato que cambia cómo trabajamos:

> **Migrar de Supabase SDK a asyncpg toca el ~40% del código de backend.**
> Cada query se revisa. Cada respuesta se serializa a mano.

O sea: **cada feature que construimos en estos 25 días es trabajo de porteo para él.**
No podemos evitarlo —hay que entregar el 20— pero sí podemos construir de manera que portear
cueste lo menos posible.

---

## Las cinco reglas de este plan

1. **El schema se congela una sola vez.** Todas las tablas nuevas salen de un único
   diagnóstico y un único lote de migraciones.
2. **Dos carriles en paralelo.** Claude Code construye features; Claude Design produce la
   propuesta visual. El carril de Design no bloquea al de Code.
3. **Diagnóstico read-only antes de cada implementación.** Es donde aparecen las sorpresas,
   con el código abierto y sin haber escrito nada.
4. **Construimos pensando en el porteo.** Ver la sección de abajo.
5. **Lo bloqueado por RRHH no frena el resto.** Se construye el contenedor, se conecta el
   dato cuando llega.

---

## Cómo construimos, sabiendo que esto se portea

Cuatro reglas que salen de los 50+ errores documentados en los tres proyectos anteriores.
No son teoría: son los errores que ya se cometieron.

**A. Los IDs se tipan `UUID`, nunca `str`.**
Es el error #1 de la lista y aparece en dos de los tres proyectos. Con Supabase el SDK convierte
solo; con asyncpg el UUID vuelve como objeto y un schema que declara `str` explota. Nosotros ya
lo pisamos del otro lado: `AreaCreate.empresa_id` era `str` y producía un 500 en producción.
**Quedan 5 casos así**, y dejaron de ser deuda menor: son bloqueantes de porteo.

**B. Un solo lugar para serializar.**
La recomendación explícita es un `serialize_db_record()` centralizado, en vez de conversiones
esparcidas por 50 controllers. Nosotros tenemos el equivalente en `model_dump(mode="json")`, que
ya nos mordió dos veces por faltar en un `update`. **Toda escritura nueva lo lleva.**

**C. Los buckets de Storage se centralizan antes de que el dev llegue.**
Hoy `documentos`, `cvs` y `avatars` están hardcodeados como constantes en 6 services. La
recomendación del documento —"Top 5", punto 2— es exactamente lo contrario: un wrapper
simétrico, para que el código de negocio no cambie cuando el backend pase a S3. Centralizarlos
ahora es una sesión; hacerlo después es tocar 6 archivos en medio de una migración.

**D. Nada de RLS en las tablas nuevas.**
El documento lo pone como decisión arquitectónica ("RLS OFF, auth en app layer") y coincide con
lo que ya decidimos: las 58 policies de producción no protegen nada porque la app entra como
`service_role`.

**Y la regla de oro que ya usamos, ahora con nombre:** antes de arreglar un bug que huele a
patrón, `grep` global y arreglar todo junto en un commit. El documento le atribuye un 70% menos
de bugs post-deploy.

---

## Fase 0 — Cerrar lo abierto (12 al 17 de agosto)

| # | Sesión | Estado |
|---|---|---|
| 0.1 | Commit del fix ASCII de `requirements.txt` | escrito, sin commitear |
| 0.2 | 🌐 Verificación visual del contraste de desplegables, Mac y Lenovo | pendiente |
| 0.3 | Actualizar `CLAUDE.md`: la suite es **3234**, no 3280 | 5 minutos |
| 0.4 | Apagar el link de horas con flag → v2 | decisión tomada |
| 0.5 | **J1-fix:** sacar la FK a `auth.users` de `schema.sql`, portar `fn_misma_empresa()` + los 8 triggers, crear `db/seed.sql` | diagnosticado |
| 0.6 | 🔴 **Los 5 IDs tipados `str`** que deberían ser `UUID` | patrón #1 de porteo |
| 0.7 | 🔴 **Centralizar los 3 buckets de Storage** en un solo módulo | 6 services hoy |

**Nota sobre el conteo de tests.** No hay misterio: 3280 era el número *antes* de J5a. La
secuencia da 3280 → 3229 (J5a) → 3228 (J5b) → **3234** (los 6 del fix ASCII). `CLAUDE.md` quedó
viejo. No amerita sesión, solo corregir el dato.

---

## Fase 1 — El diagnóstico grande y el lote de migraciones (18 al 21 de agosto)

**La sesión más importante del plan.** Un solo diagnóstico read-only que cubre las cinco
features nuevas y produce la lista completa de DDL. Si sale bien, el schema se congela el 21.

| # | Sesión | Dif. |
|---|---|:---:|
| 1.1 | Diagnóstico read-only de las 5 features: qué tablas, qué columnas, qué se reusa | 4 |
| 1.2 | Lote único de migraciones (113 en adelante) + `schema.sql` | 3 |
| 1.3 | **Design:** propuesta visual — paleta, tokens, dashboard nuevo, 2-3 pantallas | 3 |

**Lo que 1.1 tiene que resolver, y no asumir:**

- **Perfiles de puesto** — qué campos de `vacantes` son descriptivos y cuáles de proceso.
  El perfil es plantilla, no proceso abierto.
- **Objetivos** — `periodicidad` (select) y `areas_involucradas` (texto libre). **Sin
  `area_id`:** los objetivos son de RRHH, el área principal siempre es la misma. El filtro usa
  el patrón que el sistema ya tiene en nueve campos: guardar libre, filtrar con desplegable de
  valores ya usados.
- **Recategorizaciones** — antes/después de `cargo`, `seniority` y `categoria`, los tres
  opcionales, más comentario e impacto salarial opcional. Actualiza el empleado además de
  registrar el histórico.
- **Próximos Ingresos / Bajas** — separar la **fecha efectiva** de la **burocrática**. Verificar
  qué admite hoy `empleados.estado`.
- **Eventos de agenda** — tabla para los recordatorios manuales (nombre + fecha), que conviven
  con los calculados. Todos avisan una semana antes.
- **Formación** — 🔒 bloqueado por el Excel. Pero el diagnóstico sí puede responder si reemplaza
  a Capacitaciones o convive: eso decide si son 1 o 4 sesiones.

**Restricción de porteo para 1.2:** cada tabla nueva es un repo y un service más que portear.
Antes de crear una tabla, la pregunta es si una existente la cubre.

**Al cerrar 1.2, el schema queda congelado.**

---

## Fase 2 — Features nuevas (22 de agosto al 1 de septiembre)

### Carril A — Backend y funcionalidad

| # | Feature | Sesiones | Depende de |
|---|---|:---:|---|
| 2.1 | **Perfiles de puesto** — sección nueva, CRUD, cards | 3 | 1.2 |
| 2.2 | **Perfil → vacante** — se elige un perfil, los campos se copian y se editan solo para esa vacante | 2 | 2.1 |
| 2.3 | **Recategorizaciones** — tabla, alta, histórico por persona, actualización del empleado | 3 | 1.2 |
| 2.4 | **Objetivos** — periodicidad, áreas involucradas, las dos vistas | 3 | 1.2 |
| 2.5 | **Próximos Ingresos / Bajas** — fecha efectiva vs. burocrática | 2 | 1.2 |
| 2.6 | **Eventos de agenda** — carga manual + los calculados | 2 | 1.2 |
| 2.7 | **Dashboard Ejecutivo** — KPIs, "Requiere tu atención", "Próximos eventos" | 4 | 2.6 |
| 2.8 | **Formación** | 3-5 | 🔒 Excel |

### Carril B — UX

| # | Sesión | Depende de |
|---|---|---|
| 2.9 | **Aprobación de la propuesta de Design con RRHH** | 1.3 |
| 2.10 | Sistema de diseño al repo: tokens, paleta, iconos | 2.9 |
| 2.11 | Navegación de 6 grupos + Comunicación a "Gestión" | 2.10 |
| 2.12 | "Empleados" → "Colaboradores" (solo el nombre) | — |
| 2.13 | Pasada de color y consistencia, por tandas de pantallas | 2.10 |

**Sobre 2.13:** 25 pantallas en dos modos, así que cuesta el doble. Va por tandas, priorizando
lo que RRHH mira todos los días: Dashboard, Empleados, Vacaciones, Ausencias.

**El carril B casi no genera trabajo de porteo** — es frontend y CSS. Cuando el carril A se
trabe esperando un dato de RRHH, se avanza por acá.

---

## Fase 3 — Cierre y handoff (2 al 6 de septiembre)

| # | Sesión | Qué |
|---|---|---|
| 3.1 | **J1 completo** — replay de `schema.sql` en un Postgres limpio, con las tablas nuevas | El archivo del que el dev levanta RDS |
| 3.2 | **J2** — `.env.example` verificado contra `settings.py` | |
| 3.3 | **J3** — `DEPLOY.md` y bitácora al día | |
| 3.4 | **J4** — documento de handoff en `docs/handoff-aws/` | Ver abajo |
| 3.5 | 🔴 **Barrido de patrones de porteo** | Ver abajo |
| 3.6 | 🌐 **Smoke test completo en el navegador** | Puerta de salida |
| 3.7 | 🌐 **Recorrido por rol** con los dos usuarios de prueba | |

**3.5 en concreto** — antes de entregar, correr los greps que el propio documento define y dejar
el resultado escrito:

```
grep -rn "uuid.*==" backend/                      → comparaciones UUID contra string
grep -rn "supabase_admin.auth" backend/           → SDK de auth remanente
grep -rn "model_dump()" backend/ | grep -v mode=  → escrituras sin serializar
grep -rn ": str" backend/schemas/ | grep _id      → IDs mal tipados
```

Lo que aparezca se arregla o se declara. Que el dev lo encuentre en septiembre cuesta horas de
debugging; que se lo entreguemos listado cuesta una sesión.

**3.4 — qué va en el documento de handoff:**
- Las 58 policies RLS que **no** se portan, y por qué
- Los 3 buckets de Storage y qué guarda cada uno
- Rate limit con `memory://`: el contador es por proceso, necesita Redis
- El bug de encoding en Windows, ya arreglado, para que no lo repita
- `TRUSTED_PROXY_HOPS`, `ban_duration`, `HORAS_PUBLICO_ENABLED`
- Los techos medidos y las decisiones que condicionan el cutover

---

## Fase 4 — Colchón (7 al 20 de septiembre)

Catorce días para: los bugs del deploy a AWS, el testing con datos reales de RRHH, y los ajustes
que salgan de mostrarles el sistema.

**Este colchón no es opcional.** El documento del dev mide 3 a 5 horas de debugging por proyecto
migrado, y esos proyectos eran más chicos que este.

---

## Dependencias externas — el riesgo real

| Qué | Bloquea | Si no llega antes del... |
|---|---|---|
| 🔴 **Excel de Formación** | 2.8 | **25 de agosto.** Después, importarlo bien es imposible |
| 🔴 **Un perfil de ejemplo** | 2.1 | 20 de agosto |
| 🟠 ¿Formación reemplaza a Capacitaciones? | 2.8 | 18 de agosto (entra en 1.1) |
| 🟠 ¿Carga de horas va a v2? | 0.4 | 18 de agosto |
| 🟠 ¿Inventario se sigue usando? | 2.11 | 25 de agosto |
| 🟠 **Confirmar con el dev qué necesita y cuándo** | 3.x | 20 de agosto |
| 🟡 ¿Sector y Gerencia son lo mismo? | limpieza de proyectos | 1 de septiembre |
| 🟡 Deduplicar "GESTIÓN DE DEUDA" | filtros por área | 1 de septiembre |
| 🟡 Aprobación de la propuesta visual | 2.10 en adelante | 27 de agosto |

**Franco resuelve solo, sin esperar a nadie:** crear los dos usuarios de prueba
(`gerencia_lectura` y `mandos_medios`). Dos altas, y destraban el recorrido por rol.

---

## Fuera de alcance — decidido

| Qué | Por qué |
|---|---|
| **Plan de desarrollo** | v2. Se muestra como "Próximamente" |
| **Carga de horas / Clientes / Horas por cliente** | v2 si RRHH confirma. Se apaga con flag, **no se borra** |
| Todo AWS: Terraform, CI/CD, porteo a asyncpg | Del dev de infra |
| Assessment, Sucesión, reporte adhoc | Fuera del front por decisión |
| Bloque K (limpieza) | No bloquea nada. Después del 20 |

---

## Resumen de carga

| Fase | Días | Sesiones |
|---|:---:|:---:|
| 0 — Cerrar lo abierto | 6 | 7 |
| 1 — Diagnóstico y migraciones | 4 | 3 |
| 2 — Features + UX | 11 | 25-30 |
| 3 — Cierre y handoff | 5 | 7 |
| **Total a Sept 6** | **25** | **~45** |

Menos de 2 sesiones por día. Alcanzable con el ritmo del proyecto, **siempre que las
dependencias externas lleguen a tiempo.**

---

*HR Karstec · Plan de trabajo · Actualizado 12/8/2026*
