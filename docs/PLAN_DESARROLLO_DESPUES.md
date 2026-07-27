# Plan de desarrollo — DESPUÉS (Fase nueva)
**Proyecto:** HR Karstec (RRHH) · **Para:** Claude Code · **Estado:** fuente de verdad de lo nuevo de cero

Todo lo de este documento es **desarrollo nuevo** (no existe ni en Nexio ni en HR Karstec). **Depende de que `PLAN_DESARROLLO_AHORA.md` esté terminado** (cimiento multiempresa + módulos portados).

Las reglas transversales del documento AHORA (multiempresa, un solo operador, sin aprobaciones, auditoría por trigger, identificador de sección, patrón router→service→repo + apiFetch/Shadcn) **siguen aplicando acá**.

---

## 1. Estructura de proyectos (base de casi todo lo demás)

Modelo organizativo completo: **Empresa → Áreas → Equipos → Empleados**, con **Proyectos** transversales.

- `equipos (id, empresa_id, area_id, nombre)` — subdivisión dentro de un área (ej. Sistemas → Desarrollo / Testing / IA). Empleado pertenece a **1** equipo.
- `proyectos (id, empresa_id_duena, nombre, ...)` — cada proyecto tiene una empresa **dueña**.
- `proyecto_empresa (proyecto_id, empresa_id)` — **M:N**: un proyecto puede sumar empresas **colaboradoras** del grupo.
- `empleado_proyecto (empleado_id, proyecto_id, fecha_desde, fecha_hasta null, ...)` — **M:N**: un empleado en varios proyectos a la vez. Es la **asignación** (define el árbol por proyecto y qué proyectos le aparecen al empleado en su link de horas).
- **Regla clave:** un empleado tiene **UNA** empresa de pertenencia (la que paga su sueldo). Los cruces son por proyecto, no por nómina. Un área puede tener empleados de distintas empresas; un proyecto puede juntar gente de varias empresas.

### Catálogos configurables (globales, compartidos por todo el sistema)
- `seniorities`, `roles`, y catálogos de `tipos_ausencia`, `tipos_licencia`, `motivos_baja`, `categorias_capacitacion`, etc.
- Patrón común: vienen con **valores predeterminados** de fábrica + se pueden **crear y guardar nuevos**. Conviven los fijos con los nuevos. (Hoy `empleados` usa `nivel` enum y `rol` texto; migrar a referenciar estos catálogos.)

---

## 2. Costeo por proyecto

**Unidad = hora trabajada.** Costo del proyecto = Σ (horas × costo/hora congelado), acumulado de inicio a fin (incluye a los que ya no están).

### 2.1 Costo/hora del empleado
- Soporta dos métodos: **manual** (campo `costo_hora` en empleado) o **derivado** de la nómina (costo mensual ÷ horas estándar).
- **Regla:** si hay costo/hora manual, **pisa** al derivado. Al cambiarlo, mostrar **cartel de advertencia** antes de confirmar.

### 2.2 Tabla de horas
- `horas_proyecto (id, empresa_id, empleado_id, area_id, proyecto_id, fecha_trabajada, horas, costo_hora_snapshot, fecha_carga, origen, created_at)`.
- `fecha_trabajada` = el día/período que indica el empleado (no la fecha de envío) → costo siempre imputado al período correcto.
- `costo_hora_snapshot` = costo/hora **congelado** al momento de la carga (el costo histórico no se mueve si después cambia el sueldo).
- `fecha_carga` = cuándo se envió (auditoría).

### 2.3 Carga de horas por LINK PÚBLICO
- Es el **primer uso concreto de los links públicos**. El empleado **no entra al sistema**: usa un formulario público con token (patrón existente `assessment_links` + ruta `/<token>` que el `AuthMiddleware` deja pasar).
- Formulario: **DNI** (identifica al empleado, sin login) + **área** + **proyecto** + **fecha del trabajo** + **cantidad de horas**.
- **Carga múltiple:** permitir agregar varias filas (día + proyecto + horas) en un solo envío, para no repetir el formulario. Cada fila genera un registro en `horas_proyecto`.
- Esto alimenta la **planilla de costos**.

---

## 3. Presupuesto vs. real

- `presupuesto_proyecto (id, empresa_id, proyecto_id, monto_estimado, umbral_aviso_pct null, umbral_sobrepaso_pct null, version, created_at)`.
- **Monto total estimado** por proyecto (por ahora; la tabla soporta desglose futuro por horas/período).
- **Re-estimable con histórico:** cada cambio guarda la versión anterior (campo `version` + registros previos).
- **Dos umbrales opcionales y configurables** al cargar el monto:
  - aviso al **acercarse** a X% del presupuesto;
  - aviso al **superar** X%.
  - Si no se cargan, no hay alertas — solo se muestra el desvío.
- Se mide contra el **consumo real** (Σ de `horas_proyecto`). Reporta desvío, % consumido y alertas.

---

## 4. Organigrama unificado

Árbol **Empresas → Proyectos → (desplegable) Empleados**:
- Termina en proyectos por defecto (vista prolija); cada proyecto se **despliega** con clic para mostrar las personas asignadas.
- La persona muestra su **empresa de pertenencia** por color; tags para "otra empresa" y "en más de un proyecto".
- Convive con la vista **Organizacional** (Empresa → Áreas → Equipos → Empleados) — la jerarquía de pertenencia. Toggle entre ambas vistas dentro de la sección Organigrama.
- Funcionalidad real: colapsar/expandir nodos y scroll/pan (el módulo Organigrama de HR Karstec ya existe — extenderlo, no rehacerlo).

---

## 5. Catálogo de informes

Todos exportables (PDF/Excel). Incluye los reportes con IA que HR Karstec ya tiene.

- **Costos:** por proyecto (horas, personas, costo real) · por empresa y área · evolución por período · por empleado · **presupuesto vs. real** (desvío, % consumido).
- **Informe por empresa (detallado):** listado completo de empleados con puesto, rol, seniority y costo.
- **Informe por proyecto (detallado):** listado de empleados, **a qué empresa pertenece cada uno**, costos, cargos, horas involucradas, roles y seniority.
- **Dotación:** headcount por empresa/área/equipo · altas y bajas · dotación por proyecto (pico, promedio, total que pasó).
- **Horas:** por persona/proyecto/período · horas que faltan cargar.
- **Vacaciones y licencias:** tomadas/pendientes/atrasadas · mapa de vacaciones.
- **Indicadores:** ausentismo · rotación voluntaria e involuntaria.
- **Desarrollo:** capacitaciones · matriz de skills · evaluaciones de desempeño y objetivos.
- **Selección:** vacantes (tiempo de cobertura, postulantes, etc.).
- **Con IA:** reportes con análisis y sugerencias.

---

## 6. Skills
- `skills (id, nombre, ...)` (catálogo) + `empleado_skills (empleado_id, skill_id, nivel, ...)` (pivot). Alimenta el informe de matriz de skills y la sucesión.

## 7. Días especiales + balance de vacaciones
- `dias_especiales` / `calendario_laboral` (cumpleaños, días off, semana benéfico, feriados). Lo consumen vacaciones/ausencias/asistencia para calcular días hábiles.
- **Balance de vacaciones:** días que corresponden, períodos atrasados, si están liquidadas, si se excedió. (Las columnas se dejaron preparadas en `solicitudes_vacaciones` en la fase AHORA; acá se implementa la lógica.)

## 8. Capa de permisos (transversal — va al final)
- Dos ejes: `acceso_empresa (usuario_id, empresa_id, habilitado)` + `acceso_seccion (usuario_id, seccion, habilitado)`.
- **On/off por sección** (no niveles ver/editar).
- Todos arrancan con acceso total. Cada usuario puede editar el acceso de los **demás, pero no el propio**. La sección "Accesos" **no se puede apagar**.
- **Gestión de usuarios:** todos pueden crear usuarios y asignar accesos. Alta por **mail con contraseña genérica + cambio obligatorio al primer ingreso**. Incluir **recuperación de contraseña**. Contraseña: requiere letras y números. (Usuarios = operadores tipo RRHH; el empleado no entra.)
- Se enchufa en pocos lugares: filtro del menú lateral + guard de ruta + el login devuelve qué secciones/empresas ve la persona. No toca los módulos ya construidos (por eso cada uno registró su identificador de sección).

## 9. Links públicos (generalizado)
- Generalizar el patrón usado en la carga de horas para otros usos que alimenten la base. Detalle a definir al llegar. Base: patrón `assessment_links` (token + ruta pública sin auth).

---

## 10. Orden sugerido (esta fase)
1. Estructura de proyectos + equipos + catálogos (base de todo).
2. Costeo por proyecto (asignaciones + `horas_proyecto` + link público de carga).
3. Presupuesto vs. real.
4. Organigrama unificado (vistas organizacional + por proyecto).
5. Informes (empezando por costos por proyecto, por empresa y por proyecto).
6. Skills · Días especiales · Balance de vacaciones.
7. Indicadores (ausentismo/rotación — usa datos de la fase AHORA + bajas).
8. **Capa de permisos** (al final, transversal).
9. Links públicos generalizados.
