# Arquitectura — HR Karstec (RRHH)

## Stack elegido y por qué

- **Next.js 16 (App Router)** sobre otras opciones React: App Router con Server Components optimiza el tiempo de carga inicial. El equipo de desarrollo usa Claude Code que conoce muy bien este stack.
- **FastAPI sobre Django/Flask**: proyecto con scope definido, necesitamos velocidad de desarrollo y tipado estricto con Pydantic. Django agrega demasiado overhead para este caso.
- **Supabase sobre RDS propio**: RLS nativo en PostgreSQL, Auth integrado, Storage incluido, menos infraestructura a mantener para un solo developer.
- **Vercel para frontend y backend**: deployment simplificado, preview environments automáticos, integración directa con GitHub.
- **Anthropic Claude Sonnet**: mejor relación calidad/costo para el motor de IA. Tool use nativo permite el patrón de agentes especializados.

## Decisiones de diseño

### Multi-tenancy
No aplica — la plataforma es para una única empresa. El aislamiento de datos se gestiona por `user_id` y `role` en cada tabla, con RLS en Supabase como segunda capa de defensa.

### Roles
Tres roles fijos: `admin_rrhh`, `management`, `empleado`. Los permisos de `management` son granulares y configurables por `admin_rrhh` en la tabla `permisos_usuario`.

### Assessment Engine
El motor de evaluación (Self AI replicado) usa el modelo Big Five / AREAS que es ciencia pública. Las preguntas, el algoritmo de scoring y los reportes son propios. No depende de ninguna API externa para el cuestionario conductual ni cognitivo.

### IA agéntica
Cuatro agentes especializados (Conductual, Cognitivo, Técnico, Decisión) orquestados con Anthropic Claude + tool use tipado. El Agente de Decisión tiene acceso a todos los datos del sistema filtrado por los permisos del usuario autenticado.

## Deuda técnica conocida
_(se completa a medida que avanza el desarrollo)_

| Fecha | Descripción | Prioridad |
|-------|-------------|-----------|
| — | — | — |

## Decisiones de arquitectura tomadas después (2026)

- **Multiempresa app-level, sin RLS.** El filtro de empresa va en el WHERE de cada query
  (`services/_empleado_scope.py`, `_with_empresa`), no en políticas de base. En el destino AWS
  **no habrá RLS**: la seguridad es app-level y definitiva. Un recurso de otra empresa devuelve
  el **mismo 404** que uno inexistente — nunca un 403, que sería un oráculo de enumeración.
- **Una excepción, y una sola:** para el rol `mandos_medios` el `manager_id` reemplaza al filtro
  de empresa. Está concentrada en `services/_alcance_mandos.py` con su porqué.
- **Auditoría app-level, no por triggers.** Los triggers de auditoría se dropearon en la
  migración 058: la captura la hace `AuditService`, que traga sus propios errores para no tumbar
  la operación de negocio.
- **Un punto de salida único por integración externa:** `services/export/` para archivos,
  `services/mailer/` para correo. Cambiar de proveedor es un archivo y una entrada en un dict.
- **Límites de líneas por tipo de archivo** (router 80, service 150, repo 100, componente 150,
  hook 80), medidos y sostenidos. Ver [`ORDEN-Y-LEGIBILIDAD.md`](ORDEN-Y-LEGIBILIDAD.md).
