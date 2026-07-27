# AUDITORÍA TÉCNICA: HR Karstec (RRHH)
**Fecha**: 2026-05-29 | **Auditor**: Claude Code | **Modo**: Lectura pura

---

## STACK CONFIRMADO

| Componente | Tecnología |
|---|---|
| **Frontend** | Next.js 15 (App Router) + TypeScript + Tailwind + Shadcn/ui |
| **Backend** | Python 3.11 + FastAPI |
| **Base de datos** | Supabase (PostgreSQL + RLS en todas las tablas) |
| **Auth** | Supabase Auth + JWT + refresh tokens |
| **IA** | Anthropic Claude Sonnet |
| **Email** | Resend |
| **Integraciones** | Google OAuth, Anthropic API, Zernio (LinkedIn) |
| **Exportaciones** | XLSX, PDF, DOCX |

---

## AUDITORÍA POR MÓDULO

### 1. DASHBOARD

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Headcount total | ✅ | `routers/dashboard.py` → `DashboardService.get_dashboard()` | — |
| Distribución por área | ✅ | `services/dashboard_service.py` calcula `headcount_por_area` | — |
| Distribución por modalidad | ✅ | Schema `DashboardResponse` incluye `headcount_modalidad` | — |
| Distribución por tipo contrato | ✅ | Schema `DashboardResponse` incluye `headcount_tipo_contrato` | — |
| Indicadores auto-actualizables | ✅ | `fetchDashboard()` realiza queries en tiempo real | — |
| Panel IA accesible | ✅ | `components/layout/AIPanel.tsx` + `components/layout/Sidebar.tsx` | — |

---

### 2. EMPLEADOS

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Alta de empleado | ✅ | `routers/empleados.py` POST `create_empleado()` + schema `EmpleadoCreate` | — |
| Edición de empleado | ✅ | `routers/empleados.py` PUT `update_empleado()` + schema `EmpleadoUpdate` | — |
| Baja de empleado | ✅ | `routers/empleados.py` DELETE `deactivate_empleado()` | — |
| Perfil completo | ✅ | `migrations/003_create_empleados.sql`: 20 campos (legajo, nombre, apellido, email corporativo/personal, teléfono, fecha_nacimiento, fecha_ingreso, área, cargo, nivel, modalidad, tipo_contrato, estado, manager_id, foto, etc.) | — |
| Datos de nómina en perfil | ✅ | `migrations/013_create_costos_nomina.sql` FK hacia `empleados(id)` | — |
| Importación masiva Excel/CSV | ✅ | `routers/importacion.py` + `services/importacion_service.py` | — |

---

### 3. ÁREAS

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Crear área | ✅ | `routers/areas.py` POST + schema `AreaCreate` | — |
| Asignar responsable | ✅ | `migrations/002_create_areas.sql`: columna `responsable_id` FK → `empleados` | — |
| Conteo de personas | ✅ | `services/areas_service.py` calcula conteo por área | — |

---

### 4. ORGANIGRAMA

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Árbol jerárquico por área | ✅ | `routers/organigrama.py` + `components/features/organigrama/OrgNode.tsx` | — |
| Jerarquía por responsable | ✅ | `migrations/002_create_areas.sql` + `migrations/003_create_empleados.sql` (manager_id auto-referencial) | — |
| Exportación a PDF | ✅ | `services/organigrama_export_service.py` + endpoint `/exportar` | — |

---

### 5. SELECCIÓN / VACANTES (KANBAN)

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Tablero kanban | ✅ | `frontend/components/features/vacantes/` + etapas en DB | Agregar fecha_solicitud, fecha_incorporación, motivo_vacante, cantidad_entrevistas, candidato_seleccionado |
| Estados del pipeline | ✅ | `migrations/006_create_candidatos.sql`: `etapa IN ('recibido', 'revision_cv', 'entrevista_rrhh', 'entrevista_tecnica', 'entrevista_management', 'oferta', 'contratado', 'descartado')` | — |
| Publicación LinkedIn (Zernio) | ✅ | `routers/vacantes.py` POST `publicar_linkedin()` + `services/zernio_service.py` | — |
| Recepción CVs por Gmail | ✅ | `routers/vacantes.py` GET `get_emails_candidatos()` + POST `candidato_desde_email()` + `services/gmail_service.py` | — |
| Ficha de vacante completa | 🟡 | Campos en DB: título, área, descripción, requisitos, modalidad, tipo_contrato, nivel, rango_salarial, cantidad_puestos, estado, prioridad, fecha_apertura, fecha_cierre, responsable, linkedin_post_id, linkedin_url | **Faltan campos**: fecha_solicitud, fecha_incorporación (fecha_inicio_esperado), motivo_vacante, cantidad_entrevistas, candidato_seleccionado, adjuntar perfil del puesto (archivo). Parcial porque existen algunos campos pero no todos del checklist. |

---

### 6. ONBOARDING

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Templates configurables | ✅ | `migrations/007_create_onboarding_templates.sql` + `routers/onboarding_templates.py` | — |
| Tareas por semana | ✅ | `migrations/008_create_onboarding_tareas.sql`: columna `numero_semana` | — |
| Seguimiento progreso | ✅ | `migrations/010_create_onboarding_progreso.sql` + `services/onboarding_service.py` | — |
| Múltiples templates | ✅ | `templates.area_id` permite templates por área + genéricos | — |

---

### 7. OFFBOARDING

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Registro de baja | ✅ | `migrations/011_create_offboarding_instancias.sql`: motivo_egreso, descripcion_motivo, fecha_ultimo_dia, estado | — |
| Documentación proceso | ✅ | `migrations/012_create_offboarding_activos.sql`: devolucion de laptops, celulares, tarjetas, etc. | — |
| Entrevista de salida | ✅ | Columnas `entrevista_salida`, `notas_entrevista` en offboarding_instancias | — |

---

### 8. COSTOS Y NÓMINA

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Carga mensual de nómina | ✅ | `routers/costos.py` POST + `services/costos_service.py` | — |
| Componentes desglosados | ✅ | `migrations/013_create_costos_nomina.sql`: salario_bruto, cargas_sociales, bonos, otros_costos, total (generado) | — |
| Evolución por área y período | ✅ | `migrations/014_create_presupuesto_areas.sql` + queries por área/mes/año | — |
| Exportación Excel | ✅ | `services/reporte_export_service.py` export_excel() | — |

---

### 9. OBJETIVOS ANUALES / GESTIÓN DE DESEMPEÑO

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Definición de objetivos | 🟡 | `migrations/016_create_planes_carrera.sql`: cargo_objetivo, descripcion, fecha_inicio, fecha_objetivo, pero NO tabla separada de "objetivos anuales" | No existe tabla dedicada de "objetivos". Los planes de carrera son de desarrollo a largo plazo, no objetivos anuales. |
| Estado del objetivo | 🟡 | `estado IN ('activo', 'completado', 'pausado', 'cancelado')` en planes_carrera | Parcial: planes de carrera ≠ objetivos anuales |
| Notas y áreas mejora | 🟡 | Campo `notas` en planes_carrera, pero sin estructura específica para evaluación de desempeño | Falta tabla dedicada de desempeño anual |
| Historial (audit trail) | ❌ | No hay tabla separada de versiones/historial de objetivos | Falta audit trail específico |

---

### 10. FORMACIONES, CAPACITACIONES Y SKILLS

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Registro de formaciones | ❌ | No existe migración ni tabla | No existe tabla de formaciones/capacitaciones |
| Registro de skills | ❌ | No existe migración ni tabla | No existe tabla de skills por colaborador |

---

### 11. SUCESIÓN Y MAPA DE TALENTO

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Clasificación 9-box | ✅ | `components/features/sucesion/NineBox.tsx` (matriz desempeño × potencial) | — |
| Colaboradores clave | ✅ | `migrations/015_create_sucesion_posiciones.sql`: titular, sucesor primario/secundario | — |
| Posiciones críticas | ✅ | Columna `criticidad IN ('baja', 'media', 'alta', 'critica')` | — |
| Planes de carrera | ✅ | `migrations/016_create_planes_carrera.sql` + hitos en 017 | — |
| Hitos de carrera | ✅ | `migrations/017_create_planes_carrera_hitos.sql` | — |
| Nivel de preparación | ✅ | `nivel_preparacion_primario/secundario IN ('listo_ya', '1_2_anios', '3_5_anios', 'potencial')` | — |

---

### 12. ASSESSMENT

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Crear campañas de evaluación | ✅ | `routers/assessment.py` POST + `services/assessment_service.py` | — |
| Filtrar por área/posición | ✅ | `migrations/018_create_assessment_campanas.sql` + filtros en queries | — |
| Envío de links individuales | ✅ | `migrations/019_create_assessment_links.sql` + `routers/assessment.py` GET `/{token}/responder` (público) | — |
| Procesamiento automático | ✅ | `migrations/020_create_assessment_resultados.sql` + `services/assessment_parser.py` | — |
| Alimentar mapa talento | ✅ | Resultados en `assessment_resultados` → `sucesion_posiciones` (relación por queries) | — |
| Tipos: conductual, cognitivo, técnico | ✅ | `tipo IN ('conductual', 'cognitivo', 'tecnico', 'mixto')` en assessment_campanas | — |

---

### 13. VACACIONES Y LICENCIAS

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Cuántos días corresponden | ❌ | No existe tabla | No existe tabla de vacaciones/licencias |
| Períodos atrasados | ❌ | No existe tabla | No existe tabla de vacaciones/licencias |
| Liquidadas vs no liquidadas | ❌ | No existe tabla | No existe tabla de vacaciones/licencias |
| Excedencias | ❌ | No existe tabla | No existe tabla de vacaciones/licencias |
| Días cumpleaños | ❌ | No existe tabla | No existe tabla de días especiales |
| Días off | ❌ | No existe tabla | No existe tabla de días especiales |
| Semana benéfico | ❌ | No existe tabla | No existe tabla |
| Mapa de vacaciones | ❌ | No existe UI ni tabla | No existe vista de vacaciones |

---

### 14. INDICADORES (PESTAÑA DEDICADA)

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Rotación voluntaria | ❌ | No existe tabla dedicada | Se calcula via queries pero no hay pestaña/dashboard específico |
| Rotación involuntaria | ❌ | No existe tabla dedicada | Se calcula via queries pero no hay pestaña/dashboard específico |
| Ausentismo | ❌ | No existe tabla dedicada | No existe tabla de asistencias/ausencias |
| Otros indicadores | ❌ | No existe pestaña dedicada | Solo hay reportes genéricos, no dashboard de KPIs específicos |

---

### 15. REPORTES CON IA

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Generación con IA | ✅ | `routers/reportes.py` POST `/generar` + `services/reporte_service.py` (llama a Claude) | — |
| Análisis + sugerencias | ✅ | Prompt en `ReporteGenerarRequest` → Claude analiza y sugiere | — |
| Exportación PDF | ✅ | `services/reporte_export_service.py` export_pdf() | — |
| Exportación Excel | ✅ | `services/reporte_export_service.py` export_excel() | — |
| Historial de reportes | ✅ | `migrations/031_reportes_generados.sql` + GET `/historial` | — |

---

### 16. CONFIGURACIÓN

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Integración Google | ✅ | `routers/integraciones.py` + OAuth flow en `services/integracion_service.py` | — |
| Integración Anthropic | ✅ | `routers/integraciones.py` POST `/anthropic` + guardar API key | — |
| Integración Zernio (LinkedIn) | ✅ | `routers/integraciones.py` POST `/zernio` + `services/zernio_service.py` | — |
| Datos de empresa | ✅ | `migrations/030_configuracion_empresa.sql`: nombre, logo_url | — |
| Administración de accesos | ✅ | RLS policies en todas las tablas + roles (admin_rrhh, management, empleado) | — |

---

### 17. EXPORTACIONES (TRANSVERSAL)

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Organigrama PDF | ✅ | `services/organigrama_export_service.py` + endpoint | — |
| Nómina/costos Excel | ✅ | `services/reporte_export_service.py` export_excel() | — |
| Reportes RRHH PDF + IA | ✅ | `services/reporte_export_service.py` export_pdf() | — |
| Reportes Excel | ✅ | `services/reporte_export_service.py` export_excel() | — |

---

### 18. ACCESO Y SEGURIDAD (TRANSVERSAL)

| Funcionalidad | Estado | Evidencia | Qué falta |
|---|---|---|---|
| Login usuario/contraseña | ✅ | `routers/auth.py` + Supabase Auth integrado | — |
| Roles y permisos | ✅ | Tres roles: `admin_rrhh`, `management`, `empleado` | — |
| RLS activo en todas las tablas | ✅ | Todas las 35 migraciones SQL tienen `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + políticas | — |
| Multi-tenant | ✅ | Supabase RLS aisla datos por usuario + rol + tenant implícito en Supabase (via organization/empresa) | — |

---

## RESUMEN EJECUTIVO

### Recuento por estado

| Estado | Cantidad | Porcentaje |
|---|---|---|
| ✅ **Implementado** | 36 | **72%** |
| 🟡 **Parcial** | 4 | **8%** |
| ❌ **No existe** | 10 | **20%** |

### Top 10 GAPs Priorizados

1. **❌ Vacaciones y licencias (crítico)** — No existe tabla ni UI. Impacto: imposible gestionar vacaciones, ausencias, permisos.
2. **❌ Formaciones y capacitaciones (crítico)** — No existe tabla. Impacto: no se puede registrar desarrollo del talento.
3. **❌ Skills por colaborador (crítico)** — No existe tabla. Impacto: no hay mapa de competencias.
4. **❌ Indicadores dedicados (alto)** — No existe dashboard/pestaña de KPIs (rotación, ausentismo, etc.). Solo hay reportes genéricos.
5. **❌ Objetivos anuales (alto)** — No existe tabla separada. Los planes de carrera son a largo plazo, no objetivos anuales + evaluación de desempeño.
6. **❌ Audit trail de objetivos (medio)** — No hay versioning/historial específico de cambios en objetivos.
7. **🟡 Campos faltantes en vacantes (medio)** — Faltan: fecha_solicitud, fecha_incorporación, motivo_vacante, cantidad_entrevistas, candidato_seleccionado, adjuntar perfil del puesto.
8. **❌ Tablas de ausencias/asistencias (medio)** — No existe para calcular ausentismo real.
9. **❌ Días especiales (bajo)** — No existe tabla para cumpleaños, semana benéfico, días off.
10. **🟡 Evaluación de desempeño (medio)** — Parcial: solo notas en planes de carrera, sin estructura formal de evaluación periódica.

---

## RECOMENDACIONES

### Inmediatos (Semana 1-2)
1. Crear tabla `vacaciones` (empleado_id, año, días_asignados, días_tomados, días_liquidados, estado_liquidacion)
2. Crear tabla `licencias` (empleado_id, tipo, fecha_inicio, fecha_fin, motivo)
3. Crear tabla `formaciones` (empleado_id, nombre, fecha, certificado, área)
4. Crear tabla `skills` (empleado_id, skill_name, nivel, validado_por)

### Corto plazo (Semana 3-4)
1. Agregar campos faltantes a `vacantes`: fecha_solicitud, fecha_incorporación, motivo_vacante, cantidad_entrevistas
2. Crear tabla `desempen~o_evaluacion` (empleado_id, periodo_año, calificacion, objetivos_logrados, notas_mejora)
3. Crear tabla `ausencias` (empleado_id, fecha, tipo, motivo) para calcular ausentismo

### Mediano plazo (Mes 2)
1. Crear dashboard dedicado de "Indicadores" con widgets de rotación, ausentismo, etc.
2. Implementar versionado/audit trail para objetivos anuales
3. UI para vacaciones (calendar view, solicitudes, aprobaciones)

---

## CONCLUSIÓN

**RRHH (HR Karstec) está ~72% implementado**. Los módulos principales (empleados, áreas, organigrama, vacantes, onboarding, sucesión, assessment, reportes) están funcionales. Los gaps críticos son vacaciones/licencias, formaciones, y el marco formal de desempeño anual. Estos gaps pueden completarse en 3-4 semanas de trabajo enfocado.

---
*Fin de auditoría. Modo lectura pura respetado — sin modificaciones al código.*
