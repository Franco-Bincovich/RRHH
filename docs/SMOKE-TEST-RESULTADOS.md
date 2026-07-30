<!-- Generado por backend/scripts/smoke_test.py — no editar a mano las tablas -->

_Corrida: 2026-07-30 01:39 UTC · base `https://sofia-backend-pi.vercel.app` · 199 rutas enumeradas_

**4 ROTO · 2 SOSPECHOSO · 62 NO PROBADO · 290 OK**

## Hallazgos

### 🔴 ROTO — 4

- **`GET /api/sucesion/planes [consolidado]`** — 500 del servidor — excepción no atrapada
- **`GET /api/sucesion/planes [empresa]`** — 500 del servidor — excepción no atrapada
- **`GET /api/vacaciones-pendientes [consolidado]`** — 500 del servidor — excepción no atrapada
- **`GET /api/vacaciones-pendientes [empresa]`** — 500 del servidor — excepción no atrapada

### ⚠️ SOSPECHOSO — 2

- **`GET /api/integraciones/google/auth [consolidado]`** — 503 manejado: `GOOGLE_NOT_CONFIGURED` — condición de negocio, no un crash
- **`GET /api/integraciones/google/auth [empresa]`** — 503 manejado: `GOOGLE_NOT_CONFIGURED` — condición de negocio, no un crash

## Los 10 más lentos

| # | Endpoint | Tiempo | Veredicto |
|---|---|---|---|
| 1 | `GET /api/dashboard [empresa]` | **0.67s** | ✅ |
| 2 | `GET /api/procesos [consolidado]` | **0.63s** | ✅ |
| 3 | `GET /api/procesos [empresa]` | **0.61s** | ✅ |
| 4 | `GET /api/dashboard [consolidado]` | **0.57s** | ✅ |
| 5 | `GET /api/integraciones/google/callback` | **0.52s** | ✅ |
| 6 | `GET /api/adjuntos` | **0.48s** | ✅ |
| 7 | `GET /api/empleados/{id} [consolidado]` | **0.41s** | ✅ |
| 8 | `GET /api/integraciones/google/callback [empresa]` | **0.39s** | ✅ |
| 9 | `GET /api/organigrama/proyectos [empresa]` | **0.34s** | ✅ |
| 10 | `GET /api/organigrama/proyectos [consolidado]` | **0.33s** | ✅ |

## Resultados por módulo

### `adjuntos` — 3 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ⬜ | GET | `/api/adjuntos [consolidado]` | 422 | 0.22s | requiere params que el smoke no provee: entidad, entidad_id |
| ⬜ | GET | `/api/adjuntos [empresa]` | 422 | 0.23s | requiere params que el smoke no provee: entidad, entidad_id |
| ⬜ | GET | `/api/adjuntos/{id}/url` | — | — | `/api/adjuntos` no tiene filas — sin id real que probar |

### `areas` — 4 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/areas [consolidado]` | 200 | 0.28s | 9 elemento(s) |
| ✅ | GET | `/api/areas [empresa]` | 200 | 0.28s | 9 elemento(s) |
| ✅ | GET | `/api/areas/{id} [consolidado]` | 200 | 0.26s | respuesta no-lista |
| ✅ | GET | `/api/areas/{id} [empresa]` | 200 | 0.26s | respuesta no-lista |

### `auditoria` — 4 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/auditoria [consolidado]` | 200 | 0.27s | 20 elemento(s) |
| ✅ | GET | `/api/auditoria [empresa]` | 200 | 0.27s | 20 elemento(s) |
| ⬜ | GET | `/api/auditoria/exportar [consolidado]` | 429 | 0.21s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/auditoria/exportar [empresa]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |

### `ausencias` — 7 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/ausencias [consolidado]` | 200 | 0.22s | vacío coherente: `solicitudes_ausencia` tiene 0 filas |
| ✅ | GET | `/api/ausencias [empresa]` | 200 | 0.22s | vacío coherente: `solicitudes_ausencia` tiene 0 filas |
| ⬜ | GET | `/api/ausencias/exportar [consolidado]` | 429 | 0.21s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/ausencias/exportar [empresa]` | 429 | 0.21s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ✅ | GET | `/api/ausencias/tipos [consolidado]` | 200 | 0.23s | 4 elemento(s) |
| ✅ | GET | `/api/ausencias/tipos [empresa]` | 200 | 0.23s | 4 elemento(s) |
| ⬜ | GET | `/api/ausencias/{id}` | — | — | `/api/ausencias` no tiene filas — sin id real que probar |

### `auth` — 195 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/adjuntos` | 401 | 0.48s | 401 sin token |
| ✅ | POST | `/api/adjuntos` | 401 | 0.22s | 401 sin token |
| ✅ | DELETE | `/api/adjuntos/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | PUT | `/api/adjuntos/{id}/principal` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/adjuntos/{id}/url` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/areas` | 401 | 0.20s | 401 sin token |
| ✅ | POST | `/api/areas` | 401 | 0.25s | 401 sin token |
| ✅ | DELETE | `/api/areas/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | GET | `/api/areas/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | PUT | `/api/areas/{id}` | 401 | 0.17s | 401 sin token |
| ✅ | GET | `/api/auditoria` | 401 | 0.21s | 401 sin token |
| ✅ | GET | `/api/auditoria/exportar` | 401 | 0.29s | 401 sin token |
| ✅ | GET | `/api/ausencias` | 401 | 0.24s | 401 sin token |
| ✅ | POST | `/api/ausencias` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/ausencias/exportar` | 401 | 0.23s | 401 sin token |
| ✅ | GET | `/api/ausencias/tipos` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/ausencias/tipos` | 401 | 0.30s | 401 sin token |
| ✅ | DELETE | `/api/ausencias/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/ausencias/{id}` | 401 | 0.23s | 401 sin token |
| ✅ | PUT | `/api/ausencias/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | POST | `/api/auth/logout` | 401 | 0.27s | 401 sin token |
| ✅ | GET | `/api/candidatos` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/candidatos/{id}` | 401 | 0.21s | 401 sin token |
| ✅ | GET | `/api/candidatos/{id}/cv-url` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/candidatos/{id}/etapa` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/capacitaciones` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/capacitaciones` | 401 | 0.24s | 401 sin token |
| ✅ | GET | `/api/capacitaciones/asignaciones` | 401 | 0.20s | 401 sin token |
| ✅ | POST | `/api/capacitaciones/asignaciones` | 401 | 0.20s | 401 sin token |
| ✅ | GET | `/api/capacitaciones/asignaciones/exportar` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/capacitaciones/asignaciones/{id}` | 401 | 0.32s | 401 sin token |
| ✅ | PUT | `/api/capacitaciones/asignaciones/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/capacitaciones/asignaciones/{id}/certificado` | 401 | 0.22s | 401 sin token |
| ✅ | POST | `/api/capacitaciones/asignaciones/{id}/certificado` | 401 | 0.20s | 401 sin token |
| ✅ | DELETE | `/api/capacitaciones/{id}` | 401 | 0.22s | 401 sin token |
| ✅ | GET | `/api/capacitaciones/{id}` | 401 | 0.25s | 401 sin token |
| ✅ | PUT | `/api/capacitaciones/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/cesiones/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/cesiones/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | GET | `/api/costos/dashboard` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/costos/nomina` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/costos/nomina` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/costos/nomina/empleado/{empleado_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/costos/nomina/exportar` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/costos/presupuesto` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/dashboard` | 401 | 0.21s | 401 sin token |
| ✅ | GET | `/api/dashboard-equipo` | 401 | 0.21s | 401 sin token |
| ✅ | GET | `/api/empleados` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/empleados` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empleados/exportar` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/empleados/provincias` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empleados/roles-conocidos` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empleados/seleccionables` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empleados/valores-conocidos` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empleados/{empleado_id}/cesiones` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/empleados/{empleado_id}/cesiones` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/empleados/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empleados/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/empleados/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/empresas` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/empresas` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/empresas/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/empresas/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PATCH | `/api/empresas/{id}/activa` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/empresas/{id}/logo` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/equipo` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/ciclos` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/ciclos` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/ciclos/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | PUT | `/api/evaluaciones/ciclos/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/ciclos/{id}/cerrar` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/importar/confirmar` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/importar/preview` | 401 | 0.17s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/instancias` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/instancias` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/instancias/exportar` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/instancias/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/instancias/{id}/finalizar` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/evaluaciones/instancias/{id}/resultados/{criterio_id}` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/plantillas` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/plantillas` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/evaluaciones/plantillas/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/plantillas/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/evaluaciones/plantillas/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/plantillas/{id}/criterios` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/evaluaciones/plantillas/{id}/criterios/{criterio_id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/evaluaciones/plantillas/{id}/criterios/{criterio_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/resultados/lotes` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/evaluaciones/resultados/lotes/eliminar` | 401 | 0.17s | 401 sin token |
| ✅ | DELETE | `/api/evaluaciones/resultados/lotes/{lote_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados` | 401 | 0.20s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/export` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/{evaluado_id}/ficha` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/metricas` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/importacion/nomina-empleados` | 401 | 0.17s | 401 sin token |
| ✅ | POST | `/api/importacion/nomina/confirmar` | 401 | 0.20s | 401 sin token |
| ✅ | POST | `/api/importacion/nomina/preview` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/integraciones` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/integraciones/anthropic` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/integraciones/google/auth` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/integraciones/zernio` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/integraciones/{tipo}` | 401 | 0.17s | 401 sin token |
| ✅ | GET | `/api/inventario/asignaciones` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/inventario/asignaciones` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/inventario/asignaciones/exportar` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/inventario/asignaciones/{id}/devolver` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/inventario/items` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/inventario/items` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/inventario/items/exportar` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/inventario/items/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/inventario/items/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/inventario/items/{id}` | 401 | 0.20s | 401 sin token |
| ✅ | GET | `/api/inventario/items/{id}/historial` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/objetivos` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/objetivos` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/objetivos/exportar` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/objetivos/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/objetivos/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/objetivos/{id}/estado` | 401 | 0.20s | 401 sin token |
| ✅ | GET | `/api/offboarding` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/offboarding` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/offboarding/{instancia_id}/activos/{activo_id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/offboarding/{instancia_id}/entrevista` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/onboarding` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/onboarding/templates` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/onboarding/templates` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/onboarding/templates/{template_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/onboarding/templates/{template_id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/onboarding/templates/{template_id}` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/onboarding/templates/{template_id}/tareas` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/onboarding/templates/{template_id}/tareas/{tarea_id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/onboarding/templates/{template_id}/tareas/{tarea_id}` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/onboarding/{empleado_id}` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/onboarding/{empleado_id}/iniciar` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/onboarding/{instancia_id}/tareas/{tarea_id}/completar` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/organigrama` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/organigrama/proyectos` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/periodos` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/periodos` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/periodos/{id}/reabrir` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/procesos` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/proyectos` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/proyectos` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/proyectos/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/proyectos/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/proyectos/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/proyectos/{proyecto_id}/asignaciones` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/proyectos/{proyecto_id}/asignaciones` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/proyectos/{proyecto_id}/asignaciones/bulk` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/proyectos/{proyecto_id}/asignaciones/{asig_id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/proyectos/{proyecto_id}/asignaciones/{asig_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/proyectos/{proyecto_id}/horas` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/proyectos/{proyecto_id}/horas` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/proyectos/{proyecto_id}/horas/{hora_id}` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/reportes/generar` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/reportes/historial` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/reportes/{reporte_id}/exportar` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/sucesion/analisis` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/sucesion/hitos/{hito_id}/completar` | 401 | 0.17s | 401 sin token |
| ✅ | GET | `/api/sucesion/mapa` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/sucesion/planes` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/sucesion/planes` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/sucesion/planes/{plan_id}/hitos` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/sucesion/planes/{plan_id}/hitos` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/sucesion/planes/{plan_id}/readiness` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/usuarios` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/usuarios` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/usuarios/cambiar-password` | 401 | 0.18s | 401 sin token |
| ✅ | DELETE | `/api/usuarios/{user_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacaciones` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/vacaciones` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/vacaciones-pendientes` | 401 | 0.20s | 401 sin token |
| ✅ | POST | `/api/vacaciones-pendientes` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacaciones-pendientes/empleado/{empleado_id}` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/vacaciones-pendientes/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/vacaciones-pendientes/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacaciones/empleado/{empleado_id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacaciones/exportar` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/vacaciones/saldo/{empleado_id}` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/vacaciones/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/vacaciones/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | PUT | `/api/vacaciones/{id}/cancelar` | 401 | 0.19s | 401 sin token |
| ✅ | GET | `/api/vacantes` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/vacantes` | 401 | 0.19s | 401 sin token |
| ✅ | DELETE | `/api/vacantes/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacantes/{id}` | 401 | 0.19s | 401 sin token |
| ✅ | PUT | `/api/vacantes/{id}` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacantes/{id}/candidatos` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/vacantes/{id}/candidatos` | 401 | 0.19s | 401 sin token |
| ✅ | POST | `/api/vacantes/{id}/candidatos-desde-email` | 401 | 0.18s | 401 sin token |
| ✅ | GET | `/api/vacantes/{id}/emails-candidatos` | 401 | 0.18s | 401 sin token |
| ✅ | POST | `/api/vacantes/{id}/publicar-linkedin` | 401 | 0.19s | 401 sin token |
| ⬜ | GET | `/docs` | — | — | la plataforma no enruta este path (ver vercel.json) |
| ⬜ | GET | `/docs/oauth2-redirect` | — | — | la plataforma no enruta este path (ver vercel.json) |
| ⬜ | GET | `/openapi.json` | — | — | la plataforma no enruta este path (ver vercel.json) |

### `candidatos` — 3 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/candidatos [consolidado]` | 200 | 0.23s | vacío coherente: `candidatos` tiene 0 filas |
| ✅ | GET | `/api/candidatos [empresa]` | 200 | 0.22s | vacío coherente: `candidatos` tiene 0 filas |
| ⬜ | GET | `/api/candidatos/{id}/cv-url` | — | — | `/api/candidatos` no tiene filas — sin id real que probar |

### `capacitaciones` — 8 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/capacitaciones [consolidado]` | 200 | 0.21s | vacío coherente: `capacitaciones` tiene 0 filas |
| ✅ | GET | `/api/capacitaciones [empresa]` | 200 | 0.22s | vacío coherente: `capacitaciones` tiene 0 filas |
| ⬜ | GET | `/api/capacitaciones/asignaciones [consolidado]` | 422 | 0.20s | requiere params que el smoke no provee: (ver detail) |
| ⬜ | GET | `/api/capacitaciones/asignaciones [empresa]` | 422 | 0.20s | requiere params que el smoke no provee: (ver detail) |
| ⬜ | GET | `/api/capacitaciones/asignaciones/exportar [consolidado]` | 429 | 0.21s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/capacitaciones/asignaciones/exportar [empresa]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/capacitaciones/asignaciones/{id}/certificado` | — | — | `/api/capacitaciones/asignaciones` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/capacitaciones/{id}` | — | — | `/api/capacitaciones` no tiene filas — sin id real que probar |

### `costos` — 7 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ⬜ | GET | `/api/costos/dashboard [consolidado]` | 422 | 0.21s | requiere params que el smoke no provee: mes, anio |
| ⬜ | GET | `/api/costos/dashboard [empresa]` | 422 | 0.20s | requiere params que el smoke no provee: mes, anio |
| ⬜ | GET | `/api/costos/nomina [consolidado]` | 422 | 0.20s | requiere params que el smoke no provee: mes, anio |
| ⬜ | GET | `/api/costos/nomina [empresa]` | 422 | 0.21s | requiere params que el smoke no provee: mes, anio |
| ⬜ | GET | `/api/costos/nomina/empleado/{empleado_id}` | — | — | `/api/costos/nomina/empleado` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/costos/nomina/exportar [consolidado]` | 422 | 0.20s | requiere params que el smoke no provee: mes, anio |
| ⬜ | GET | `/api/costos/nomina/exportar [empresa]` | 422 | 0.21s | requiere params que el smoke no provee: mes, anio |

### `dashboard` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/dashboard [consolidado]` | 200 | 0.57s | respuesta no-lista |
| ✅ | GET | `/api/dashboard [empresa]` | 200 | 0.67s | respuesta no-lista |

### `dashboard-equipo` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/dashboard-equipo [consolidado]` | 200 | 0.27s | respuesta no-lista |
| ✅ | GET | `/api/dashboard-equipo [empresa]` | 200 | 0.28s | respuesta no-lista |

### `docs` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ⬜ | GET | `/docs` | — | — | la plataforma no enruta este path (ver vercel.json) |
| ⬜ | GET | `/docs/oauth2-redirect` | — | — | la plataforma no enruta este path (ver vercel.json) |

### `empleados` — 16 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/empleados [consolidado]` | 200 | 0.23s | 19 elemento(s) |
| ✅ | GET | `/api/empleados [empresa]` | 200 | 0.23s | 19 elemento(s) |
| ⬜ | GET | `/api/empleados/exportar [consolidado]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/empleados/exportar [empresa]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ✅ | GET | `/api/empleados/provincias [consolidado]` | 200 | 0.20s | 24 elemento(s) |
| ✅ | GET | `/api/empleados/provincias [empresa]` | 200 | 0.20s | 24 elemento(s) |
| ✅ | GET | `/api/empleados/roles-conocidos [consolidado]` | 200 | 0.22s | 7 elemento(s) |
| ✅ | GET | `/api/empleados/roles-conocidos [empresa]` | 200 | 0.25s | 7 elemento(s) |
| ⬜ | GET | `/api/empleados/seleccionables [consolidado]` | 422 | 0.21s | requiere params que el smoke no provee: empresa_id |
| ⬜ | GET | `/api/empleados/seleccionables [empresa]` | 422 | 0.21s | requiere params que el smoke no provee: empresa_id |
| ⬜ | GET | `/api/empleados/valores-conocidos [consolidado]` | 422 | 0.20s | requiere params que el smoke no provee: campo |
| ⬜ | GET | `/api/empleados/valores-conocidos [empresa]` | 422 | 0.20s | requiere params que el smoke no provee: campo |
| ✅ | GET | `/api/empleados/{empleado_id}/cesiones [consolidado]` | 200 | 0.24s | 1 elemento(s) |
| ✅ | GET | `/api/empleados/{empleado_id}/cesiones [empresa]` | 200 | 0.24s | 1 elemento(s) |
| ✅ | GET | `/api/empleados/{id} [consolidado]` | 200 | 0.41s | respuesta no-lista |
| ✅ | GET | `/api/empleados/{id} [empresa]` | 200 | 0.22s | respuesta no-lista |

### `empresas` — 4 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/empresas [consolidado]` | 200 | 0.23s | 1 elemento(s) |
| ✅ | GET | `/api/empresas [empresa]` | 200 | 0.22s | 1 elemento(s) |
| ✅ | GET | `/api/empresas/{id} [consolidado]` | 200 | 0.22s | respuesta no-lista |
| ✅ | GET | `/api/empresas/{id} [empresa]` | 200 | 0.23s | respuesta no-lista |

### `equipo` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/equipo [consolidado]` | 200 | 0.22s | 19 elemento(s) |
| ✅ | GET | `/api/equipo [empresa]` | 200 | 0.29s | 19 elemento(s) |

### `evaluaciones` — 21 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/evaluaciones/ciclos [consolidado]` | 200 | 0.22s | vacío coherente: `ev_ciclos` tiene 0 filas |
| ✅ | GET | `/api/evaluaciones/ciclos [empresa]` | 200 | 0.22s | vacío coherente: `ev_ciclos` tiene 0 filas |
| ⬜ | GET | `/api/evaluaciones/ciclos/{id}` | — | — | `/api/evaluaciones/ciclos` no tiene filas — sin id real que probar |
| ✅ | GET | `/api/evaluaciones/instancias [consolidado]` | 200 | 0.25s | vacío coherente: `ev_instancias` tiene 0 filas |
| ✅ | GET | `/api/evaluaciones/instancias [empresa]` | 200 | 0.23s | vacío coherente: `ev_instancias` tiene 0 filas |
| ⬜ | GET | `/api/evaluaciones/instancias/exportar [consolidado]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/evaluaciones/instancias/exportar [empresa]` | 429 | 0.22s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/evaluaciones/instancias/{id}` | — | — | `/api/evaluaciones/instancias` no tiene filas — sin id real que probar |
| ✅ | GET | `/api/evaluaciones/plantillas [consolidado]` | 200 | 0.23s | vacío coherente: `ev_plantillas` tiene 0 filas |
| ✅ | GET | `/api/evaluaciones/plantillas [empresa]` | 200 | 0.23s | vacío coherente: `ev_plantillas` tiene 0 filas |
| ⬜ | GET | `/api/evaluaciones/plantillas/{id}` | — | — | `/api/evaluaciones/plantillas` no tiene filas — sin id real que probar |
| ✅ | GET | `/api/evaluaciones/resultados/lotes [consolidado]` | 200 | 0.33s | 1 elemento(s) |
| ✅ | GET | `/api/evaluaciones/resultados/lotes [empresa]` | 200 | 0.29s | 1 elemento(s) |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados [consolidado]` | 200 | 0.32s | 10 elemento(s) |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados [empresa]` | 200 | 0.27s | 10 elemento(s) |
| ⬜ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/export [consolidado]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/export [empresa]` | 429 | 0.22s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/{evaluado_id}/ficha [consolidado]` | 422 | 0.20s | requiere params que el smoke no provee: (ver detail) |
| ⬜ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/{evaluado_id}/ficha [empresa]` | 422 | 0.20s | requiere params que el smoke no provee: (ver detail) |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/metricas [consolidado]` | 200 | 0.29s | respuesta no-lista |
| ✅ | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/metricas [empresa]` | 200 | 0.28s | respuesta no-lista |

### `health` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/health [consolidado]` | 200 | 0.19s | respuesta no-lista |
| ✅ | GET | `/health [empresa]` | 200 | 0.19s | respuesta no-lista |

### `integraciones` — 6 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/integraciones [consolidado]` | 200 | 0.22s | 3 elemento(s) |
| ✅ | GET | `/api/integraciones [empresa]` | 200 | 0.22s | 3 elemento(s) |
| ⚠️ | GET | `/api/integraciones/google/auth [consolidado]` | 503 | 0.21s | 503 manejado: `GOOGLE_NOT_CONFIGURED` — condición de negocio, no un crash |
| ⚠️ | GET | `/api/integraciones/google/auth [empresa]` | 503 | 0.20s | 503 manejado: `GOOGLE_NOT_CONFIGURED` — condición de negocio, no un crash |
| ✅ | GET | `/api/integraciones/google/callback [consolidado]` | 200 | 0.26s | respuesta no-lista |
| ✅ | GET | `/api/integraciones/google/callback [empresa]` | 200 | 0.39s | respuesta no-lista |

### `inventario` — 10 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/inventario/asignaciones [consolidado]` | 200 | 0.25s | vacío coherente: `inventario_asignaciones` tiene 0 filas |
| ✅ | GET | `/api/inventario/asignaciones [empresa]` | 200 | 0.25s | vacío coherente: `inventario_asignaciones` tiene 0 filas |
| ⬜ | GET | `/api/inventario/asignaciones/exportar [consolidado]` | 429 | 0.21s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/inventario/asignaciones/exportar [empresa]` | 429 | 0.29s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ✅ | GET | `/api/inventario/items [consolidado]` | 200 | 0.23s | vacío coherente: `inventario_items` tiene 0 filas |
| ✅ | GET | `/api/inventario/items [empresa]` | 200 | 0.25s | vacío coherente: `inventario_items` tiene 0 filas |
| ✅ | GET | `/api/inventario/items/exportar [consolidado]` | 200 | 0.22s | archivo de 4905 bytes (application/vnd.openxmlformats-officedoc) |
| ✅ | GET | `/api/inventario/items/exportar [empresa]` | 200 | 0.24s | archivo de 4905 bytes (application/vnd.openxmlformats-officedoc) |
| ⬜ | GET | `/api/inventario/items/{id}` | — | — | `/api/inventario/items` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/inventario/items/{id}/historial` | — | — | `/api/inventario/items` no tiene filas — sin id real que probar |

### `objetivos` — 4 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/objetivos [consolidado]` | 200 | 0.29s | vacío coherente: `objetivos` tiene 0 filas |
| ✅ | GET | `/api/objetivos [empresa]` | 200 | 0.22s | vacío coherente: `objetivos` tiene 0 filas |
| ✅ | GET | `/api/objetivos/exportar [consolidado]` | 200 | 0.23s | archivo de 4882 bytes (application/vnd.openxmlformats-officedoc) |
| ✅ | GET | `/api/objetivos/exportar [empresa]` | 200 | 0.22s | archivo de 4882 bytes (application/vnd.openxmlformats-officedoc) |

### `offboarding` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/offboarding [consolidado]` | 200 | 0.23s | vacío coherente: `offboarding_instancias` tiene 0 filas |
| ✅ | GET | `/api/offboarding [empresa]` | 200 | 0.26s | vacío coherente: `offboarding_instancias` tiene 0 filas |

### `onboarding` — 6 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/onboarding [consolidado]` | 200 | 0.21s | vacío coherente: `onboarding_instancias` tiene 0 filas |
| ✅ | GET | `/api/onboarding [empresa]` | 200 | 0.24s | vacío coherente: `onboarding_instancias` tiene 0 filas |
| ✅ | GET | `/api/onboarding/templates [consolidado]` | 200 | 0.24s | vacío coherente: `onboarding_templates` tiene 0 filas |
| ✅ | GET | `/api/onboarding/templates [empresa]` | 200 | 0.23s | vacío coherente: `onboarding_templates` tiene 0 filas |
| ⬜ | GET | `/api/onboarding/templates/{template_id}` | — | — | `/api/onboarding/templates` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/onboarding/{empleado_id}` | — | — | `/api/onboarding` no tiene filas — sin id real que probar |

### `openapi.json` — 1 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ⬜ | GET | `/openapi.json` | — | — | la plataforma no enruta este path (ver vercel.json) |

### `organigrama` — 4 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/organigrama [consolidado]` | 200 | 0.28s | 1 elemento(s) |
| ✅ | GET | `/api/organigrama [empresa]` | 200 | 0.27s | 1 elemento(s) |
| ✅ | GET | `/api/organigrama/proyectos [consolidado]` | 200 | 0.33s | respuesta no-lista |
| ✅ | GET | `/api/organigrama/proyectos [empresa]` | 200 | 0.34s | respuesta no-lista |

### `periodos` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/periodos [consolidado]` | 200 | 0.22s | vacío coherente: `periodos_cerrados` tiene 0 filas |
| ✅ | GET | `/api/periodos [empresa]` | 200 | 0.32s | vacío coherente: `periodos_cerrados` tiene 0 filas |

### `procesos` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/procesos [consolidado]` | 200 | 0.63s | respuesta no-lista |
| ✅ | GET | `/api/procesos [empresa]` | 200 | 0.61s | respuesta no-lista |

### `proyectos` — 8 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/proyectos [consolidado]` | 200 | 0.30s | 6 elemento(s) |
| ✅ | GET | `/api/proyectos [empresa]` | 200 | 0.27s | 6 elemento(s) |
| ✅ | GET | `/api/proyectos/{id} [consolidado]` | 200 | 0.28s | respuesta no-lista |
| ✅ | GET | `/api/proyectos/{id} [empresa]` | 200 | 0.29s | respuesta no-lista |
| ✅ | GET | `/api/proyectos/{proyecto_id}/asignaciones [consolidado]` | 200 | 0.33s | 1 elemento(s) |
| ✅ | GET | `/api/proyectos/{proyecto_id}/asignaciones [empresa]` | 200 | 0.31s | 1 elemento(s) |
| ✅ | GET | `/api/proyectos/{proyecto_id}/horas [consolidado]` | 200 | 0.29s | vacío coherente: `horas_proyecto` tiene 0 filas |
| ✅ | GET | `/api/proyectos/{proyecto_id}/horas [empresa]` | 200 | 0.27s | vacío coherente: `horas_proyecto` tiene 0 filas |

### `publicas` — 4 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/auth/login` | 405 | 0.23s | alcanzable sin token (405) |
| ✅ | GET | `/api/auth/refresh` | 405 | 0.20s | alcanzable sin token (405) |
| ✅ | GET | `/api/integraciones/google/callback` | 200 | 0.52s | alcanzable sin token (200) |
| ✅ | GET | `/health` | 200 | 0.18s | alcanzable sin token (200) |

### `reportes` — 3 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/reportes/historial [consolidado]` | 200 | 0.22s | vacío coherente: `reportes_generados` tiene 0 filas |
| ✅ | GET | `/api/reportes/historial [empresa]` | 200 | 0.24s | vacío coherente: `reportes_generados` tiene 0 filas |
| ⬜ | GET | `/api/reportes/{reporte_id}/exportar` | — | — | `/api/reportes` no tiene filas — sin id real que probar |

### `sucesion` — 7 endpoint(s) 🔴

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| 🔴 | GET | `/api/sucesion/planes [consolidado]` | 500 | 0.23s | 500 del servidor — excepción no atrapada |
| 🔴 | GET | `/api/sucesion/planes [empresa]` | 500 | 0.24s | 500 del servidor — excepción no atrapada |
| ⬜ | GET | `/api/sucesion/analisis [consolidado]` | 422 | 0.22s | requiere params que el smoke no provee: area_id |
| ⬜ | GET | `/api/sucesion/analisis [empresa]` | 422 | 0.20s | requiere params que el smoke no provee: area_id |
| ✅ | GET | `/api/sucesion/mapa [consolidado]` | 200 | 0.23s | 19 elemento(s) |
| ✅ | GET | `/api/sucesion/mapa [empresa]` | 200 | 0.23s | 19 elemento(s) |
| ⬜ | GET | `/api/sucesion/planes/{plan_id}/hitos` | — | — | `/api/sucesion/planes` no tiene filas — sin id real que probar |

### `usuarios` — 2 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/usuarios [consolidado]` | 200 | 0.23s | 4 elemento(s) |
| ✅ | GET | `/api/usuarios [empresa]` | 200 | 0.22s | 4 elemento(s) |

### `vacaciones` — 7 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/vacaciones [consolidado]` | 200 | 0.22s | vacío coherente: `solicitudes_vacaciones` tiene 0 filas |
| ✅ | GET | `/api/vacaciones [empresa]` | 200 | 0.22s | vacío coherente: `solicitudes_vacaciones` tiene 0 filas |
| ⬜ | GET | `/api/vacaciones/empleado/{empleado_id}` | — | — | `/api/vacaciones/empleado` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/vacaciones/exportar [consolidado]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/vacaciones/exportar [empresa]` | 429 | 0.20s | 429: el barrido agotó la franja de rate limit (ver 'Limitaciones') |
| ⬜ | GET | `/api/vacaciones/saldo/{empleado_id}` | — | — | `/api/vacaciones/saldo` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/vacaciones/{id}` | — | — | `/api/vacaciones` no tiene filas — sin id real que probar |

### `vacaciones-pendientes` — 3 endpoint(s) 🔴

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| 🔴 | GET | `/api/vacaciones-pendientes [consolidado]` | 500 | 0.23s | 500 del servidor — excepción no atrapada |
| 🔴 | GET | `/api/vacaciones-pendientes [empresa]` | 500 | 0.22s | 500 del servidor — excepción no atrapada |
| ⬜ | GET | `/api/vacaciones-pendientes/empleado/{empleado_id}` | — | — | `/api/vacaciones-pendientes/empleado` no tiene filas — sin id real que probar |

### `vacantes` — 5 endpoint(s)

| | Método | Endpoint | Status | Tiempo | Detalle |
|---|---|---|---|---|---|
| ✅ | GET | `/api/vacantes [consolidado]` | 200 | 0.23s | vacío coherente: `vacantes` tiene 0 filas |
| ✅ | GET | `/api/vacantes [empresa]` | 200 | 0.23s | vacío coherente: `vacantes` tiene 0 filas |
| ⬜ | GET | `/api/vacantes/{id}` | — | — | `/api/vacantes` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/vacantes/{id}/candidatos` | — | — | `/api/vacantes` no tiene filas — sin id real que probar |
| ⬜ | GET | `/api/vacantes/{id}/emails-candidatos` | — | — | `/api/vacantes` no tiene filas — sin id real que probar |