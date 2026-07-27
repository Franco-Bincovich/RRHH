# Arquitectura — HR Karstec (RRHH)

## Stack elegido y por qué

- **Next.js 15 (App Router)** sobre otras opciones React: App Router con Server Components optimiza el tiempo de carga inicial. El equipo de desarrollo usa Claude Code que conoce muy bien este stack.
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
