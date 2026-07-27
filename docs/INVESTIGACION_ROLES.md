# INVESTIGACIÓN DE ROLES — HR Karstec (RRHH)
> Generada el 2026-05-29. Solo lectura. Metodología: grep exhaustivo en todo el código, lectura de archivos clave.

---

## Pregunta 1 — ¿Dónde se chequea el rol en el BACKEND?

### Búsqueda realizada

Se buscó en `backend/routers/*.py`, `backend/services/*.py`, `backend/repositories/*.py` toda ocurrencia de:
- `request.state.user["rol"]`
- `user.get("rol")`
- `admin_rrhh`
- `management`
- `FORBIDDEN`
- cualquier comparación de rol

### Resultado: CERO checks de rol en routers, services y repositories

**`backend/routers/*.py`** — hallazgos de `request.state.user`:

| Archivo | Línea | Qué hace con `request.state.user` |
|---|---|---|
| `routers/auth.py:40` | `service.logout(request.state.user["id"], token)` | Lee solo el ID para trazabilidad |
| `routers/empleados.py:51` | `created_by = request.state.user.get("id", "system")` | Lee solo el ID para trazabilidad |
| `routers/importacion.py:47` | `created_by = request.state.user.get("id", "importacion_csv")` | Lee solo el ID para trazabilidad |
| `routers/areas.py:41` | `created_by = request.state.user.get("id", "system")` | Lee solo el ID para trazabilidad |
| `routers/vacantes.py:39,70,75,80` | `request.state.user.get("id", "system")` / `request.state.user["id"]` | Lee solo el ID para trazabilidad / Gmail |
| `routers/integraciones.py:23,29,54,60,66` | `user_id: str = request.state.user["id"]` | Lee solo el ID |

**En NINGUNO de estos routers** se lee `request.state.user["rol"]` ni se toma ninguna decisión basada en él.

**`backend/services/*.py`** — resultado de grep para `admin_rrhh`, `management`, `FORBIDDEN`, `.rol`:
```
No matches found
```

**`backend/repositories/*.py`** — resultado de grep para los mismos términos:
```
No matches found
```

### Conclusión Pregunta 1

El rol se **popula** en `request.state.user` durante el middleware de auth, pero **nunca se consume** en ningún router, service ni repository para condicionar comportamiento.

**Lista de endpoints que SOLO puede usar admin_rrhh**: ninguno gateado.
**Lista de endpoints que puede usar management**: todos (igual que admin_rrhh).
**Lista de endpoints que puede usar empleado**: todos (igual que los otros dos).

Todos los endpoints autenticados funcionan exactamente igual sin importar el rol del usuario.

---

## Pregunta 2 — ¿Dónde se chequea el rol en el FRONTEND?

### Sidebar — `components/layout/Sidebar.tsx`

El Sidebar define los módulos como un array estático, sin ningún filtro por rol:

```typescript
// RRHH/frontend/components/layout/Sidebar.tsx — líneas 40-53
const NAV_ITEMS = [
  { label: "Dashboard",     href: "/dashboard",      icon: LayoutDashboard },
  { label: "Áreas",         href: "/areas",           icon: Layers },
  { label: "Empleados",     href: "/empleados",       icon: Users },
  { label: "Organigrama",   href: "/organigrama",     icon: GitBranch },
  { label: "Vacantes",      href: "/vacantes",        icon: Briefcase },
  { label: "Onboarding",    href: "/onboarding",      icon: UserPlus },
  { label: "Offboarding",   href: "/offboarding",     icon: UserMinus },
  { label: "Costos",        href: "/costos",          icon: DollarSign },
  { label: "Sucesión",      href: "/sucesion",        icon: TrendingUp },
  { label: "Assessment",    href: "/assessment",      icon: ClipboardList },
  { label: "Reportes",      href: "/reportes",        icon: BarChart3 },
  { label: "Configuración", href: "/configuracion",   icon: Settings },
] as const
```

Los 12 ítems se renderizan para todos los usuarios sin excepción. No hay lógica del tipo `NAV_ITEMS.filter(item => hasAccess(item, session.rol))`. El UserMenu tiene incluso el nombre y email **hardcodeados**: `"Admin RRHH"` y `"admin@karstec.com"` — no lee la sesión.

```typescript
// RRHH/frontend/components/layout/Sidebar.tsx — líneas 108-111
<span className="truncate text-sm font-medium">Admin RRHH</span>
<span className="truncate text-xs text-muted-foreground">admin@karstec.com</span>
```

### AuthGuard — `components/layout/AuthGuard.tsx`

```typescript
// RRHH/frontend/components/layout/AuthGuard.tsx (archivo completo)
"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()

  useEffect(() => {
    const session = localStorage.getItem("session")
    if (!session) {
      router.push("/login")
    }
  }, [router])

  return <>{children}</>
}
```

`AuthGuard` chequea **exclusivamente si existe la clave `"session"` en localStorage**. No lee el rol, no compara valores, no redirige según permisos. Es un guard binario: hay sesión → pasa; no hay sesión → `/login`.

### Lectura del rol en el frontend — único hallazgo real

La única lectura funcional del rol está en la página de configuración, y es **puramente cosmética**:

```typescript
// RRHH/frontend/app/(dashboard)/configuracion/page.tsx — líneas 24-28, 350-352
const ROL_LABEL: Record<string, string> = {
  admin_rrhh: "Administrador RRHH",
  management:  "Gerencia",
  empleado:    "Empleado",
}

// ...más abajo, en el render:
<p className="mt-0.5 font-medium">
  {ROL_LABEL[session.user.rol] ?? session.user.rol}
</p>
```

Muestra el rol como texto informativo. No oculta ni muestra nada basado en él.

### Conclusión Pregunta 2

La UI es **idéntica para los 3 roles**. Ni el Sidebar, ni el AuthGuard, ni ninguna página condiciona elementos visuales o acceso a rutas según el rol del usuario. Un usuario con rol `empleado` y uno con rol `admin_rrhh` ven exactamente la misma interfaz y pueden navegar a los mismos módulos.

---

## Pregunta 3 — ¿Dónde se diferencia en las RLS policies?

### Tablas y sus políticas

Las RLS policies SÍ distinguen roles — pero con un asterisco fundamental.

**Patrón universal que se repite en las 24 tablas:**

```sql
-- Lectura: admin_rrhh y management ven todo
CREATE POLICY "tabla_select_admin_management"
    ON public.tabla FOR SELECT
    USING (public.get_current_user_rol() IN ('admin_rrhh', 'management'));

-- Lectura: empleado ve solo lo suyo (tablas con user_id o empleado_id → user_id)
CREATE POLICY "tabla_select_own"
    ON public.tabla FOR SELECT
    USING (user_id = auth.uid());  -- o EXISTS(JOIN a empleados)

-- Escritura: solo admin_rrhh (o a veces también management)
CREATE POLICY "tabla_write_admin"
    ON public.tabla FOR ALL
    USING (public.get_current_user_rol() = 'admin_rrhh');
```

**Tablas con política diferenciada por rol** (resumen):

| Tabla | admin_rrhh | management | empleado |
|---|---|---|---|
| `users` | SELECT+ALL | SELECT | SELECT propio |
| `empleados` | SELECT+ALL | SELECT | SELECT propio |
| `documentos_empleado` | SELECT+ALL | SELECT | SELECT propio |
| `vacantes` | SELECT+ALL | SELECT+INSERT | — |
| `candidatos` | SELECT+ALL | SELECT+ALL | — |
| `onboarding_instancias` | SELECT+ALL | SELECT | SELECT propio |
| `offboarding_instancias` | SELECT+ALL | SELECT | — |
| `costos_nomina` | SELECT+ALL | SELECT | — |
| `presupuesto_areas` | SELECT+ALL | SELECT | — |
| `sucesion_posiciones` | SELECT+ALL | SELECT | — |
| `planes_carrera` | SELECT+ALL | SELECT+ALL | SELECT propio |
| `assessment_campanas` | SELECT+ALL | SELECT | — |
| `areas` | SELECT+ALL | SELECT | SELECT (auth != null) |

### El asterisco fundamental: el backend bypasea toda la RLS

```python
# RRHH/backend/integrations/supabase_client.py — líneas 17-24
def _create_admin_client() -> Client:
    """Instancia el cliente admin con la service key. Bypasea RLS — usar con criterio."""
    return create_client(settings.supabase_url, settings.supabase_service_key)

supabase_admin: Client = _create_admin_client()  # ← lo usan TODOS los repositories
```

Todos los repositories importan y usan `supabase_admin` exclusivamente. Al usar la `service_role` key, Postgres ignora **todas** las RLS policies. Ninguna policy de la tabla anterior se activa durante el uso normal de la aplicación.

**Las RLS policies son una segunda línea de defensa** (si alguien consulta Supabase directamente con un JWT de usuario), **pero no afectan en absoluto el comportamiento del backend**.

### Conclusión Pregunta 3

Las policies existen y están bien diseñadas, pero en la práctica actual son teóricas: el backend siempre usa `supabase_admin` (service key), que las bypasea. Las diferencias entre roles a nivel DB no se activan en ningún flujo del sistema.

---

## Pregunta 4 — ¿Qué dice la documentación del proyecto?

### CLAUDE.md — descripción de roles

```markdown
## Roles del sistema
| Rol | Descripción |
|-----|-------------|
| `admin_rrhh` | Control total. Único que puede crear usuarios, asignar permisos, configurar el sistema. |
| `management` | Acceso configurable por RRHH. Permisos granulares por módulo (lectura / lectura+escritura / sin acceso). |
| `empleado` | Acceso mínimo. Solo puede ver su propio perfil y sus propias evaluaciones. |
```

### ¿Está implementado?

| Descripción en CLAUDE.md | ¿Implementado? |
|---|---|
| `admin_rrhh`: "Único que puede crear usuarios" | ❌ No — cualquier usuario autenticado puede llamar `POST /api/auth/register` si existiera; no existe endpoint de creación de usuarios en el frontend |
| `admin_rrhh`: "asignar permisos, configurar el sistema" | ❌ No — no hay endpoint ni UI para esto |
| `management`: "Acceso configurable por RRHH" | ❌ No — no existe ningún sistema de configuración de permisos |
| `management`: "Permisos granulares por módulo" | ❌ No — ver Pregunta 5 |
| `empleado`: "Solo puede ver su propio perfil" | ❌ No — un usuario con rol `empleado` ve y puede usar todos los módulos igual que admin_rrhh |

**Veredicto**: la descripción de roles en CLAUDE.md es una **intención de diseño**, no una realidad implementada.

---

## Pregunta 5 — ¿Existe el concepto de "permisos por módulo" para management?

### Búsqueda exhaustiva

Se buscó en todo el proyecto:
- Tabla `permisos`, `permisos_modulo`, `modulo_acceso`, `configuracion_acceso`
- Columnas con `permiso`, `acceso`, `modulo`
- Cualquier código que lea una tabla de permisos

### Resultado: NO EXISTE

No hay ninguna tabla, columna, config, endpoint ni componente que implemente permisos granulares por módulo.

El listado completo de tablas del schema (migraciones 001–035) no incluye ninguna tabla relacionada con permisos configurables. La tabla `configuracion_empresa` (migración 030) guarda solo datos de la empresa (nombre, logo, RUT, etc.), no permisos de acceso.

La descripción de `management` en CLAUDE.md ("permisos granulares por módulo") es una funcionalidad **planificada que no se codificó**.

---

## Tabla resumen — qué puede hacer cada rol HOY

| Capacidad | admin_rrhh | management | empleado |
|---|---|---|---|
| **BACKEND: acceder a cualquier endpoint** | ✅ Sí | ✅ Sí (idéntico) | ✅ Sí (idéntico) |
| **BACKEND: endpoint bloqueado por rol** | — | Ninguno | Ninguno |
| **FRONTEND: ver todos los módulos del Sidebar** | ✅ Sí | ✅ Sí (idéntico) | ✅ Sí (idéntico) |
| **FRONTEND: ruta bloqueada por rol** | — | Ninguna | Ninguna |
| **FRONTEND: UI diferente** | No | No | No |
| **DB (RLS): lectura propia solo** | — | — | Teórico (bypaseado) |
| **DB (RLS): escritura restringida** | Teórico (bypaseado) | Teórico (bypaseado) | Teórico (bypaseado) |
| **En qué difiere en la práctica** | Se muestra "Administrador RRHH" en /configuracion | Se muestra "Gerencia" en /configuracion | Se muestra "Empleado" en /configuracion |

---

## Veredicto

### **C — Los roles son puramente estructurales, sin diferenciación funcional real.**

Los tres roles (`admin_rrhh`, `management`, `empleado`) existen en la DB, viajan a través del login, se guardan en localStorage y se muestran como texto en la página de configuración. Eso es todo.

En ningún punto del backend (routers, services, repositories) se lee `request.state.user["rol"]` para tomar una decisión. En ningún punto del frontend se lee `session.user.rol` para condicionar UI, ocultar módulos o bloquear rutas. Las RLS policies están escritas correctamente pero son bypaseadas por `supabase_admin` en cada query.

---

## Si la decisión es unificar a un solo rol operativo

### Qué habría que tocar (lista mínima)

| Archivo | Qué cambiar | Impacto |
|---|---|---|
| `backend/migrations/001_create_users.sql` | Cambiar el CHECK constraint a solo `'admin_rrhh'`, o simplemente ignorar los otros valores | Solo en la DB |
| `backend/schemas/auth.py` línea 18 | `rol: str` → puede quedarse como está, o eliminarse si no se necesita | Ninguno en producción |
| `frontend/types/auth.ts` línea 1 | `UserRol = "admin_rrhh"` en lugar de union de 3 | Puramente de tipos |
| `frontend/app/(dashboard)/configuracion/page.tsx` líneas 24-28 | Eliminar `ROL_LABEL` map o dejarlo con un solo valor | Cosmético |
| `frontend/components/layout/Sidebar.tsx` líneas 108-110 | Reemplazar texto hardcodeado por datos reales de sesión | Mejora de UX |

### Qué NO se rompería si simplemente operan todo con `admin_rrhh`

Absolutamente nada del comportamiento actual. El sistema ya funciona así en la práctica — todos los usuarios tienen acceso a todo, independientemente del rol asignado. Operar con un único rol `admin_rrhh` es exactamente lo que el código hace hoy para cualquier usuario autenticado.

### Qué se perdería al unificar

1. **Las RLS policies dejarían de tener sentido semántico** — aunque hoy no se activan, si en el futuro se quisiera usar el cliente anon (en lugar de admin), la diferenciación de roles en policies ya no existiría.
2. **La posibilidad de extender el sistema** — si en el futuro se quisiera implementar el portal del empleado (ver solo el perfil propio), habría que reconstruir la estructura de roles desde cero.

### Recomendación técnica

Si el producto va a ser usado **exclusivamente por el equipo de RRHH** sin portal de empleado ni diferenciación de management, la unificación es segura y limpia el código. El único riesgo es si en el futuro se quisiera agregar los módulos de empleado (vacaciones, solicitudes) que requerirían distinguir entre "operador RRHH" y "empleado que solicita" — en ese caso, la estructura de 3 roles ya está preparada en la DB y las RLS policies, solo habría que activarla en el backend y el frontend.

---

*Investigación completada el 2026-05-29. Evidencia: grep de cero matches en `services/` y `repositories/` para cualquier referencia a rol; lectura directa de `AuthGuard.tsx`, `Sidebar.tsx`, `configuracion/page.tsx`, `auth_service.py`, `middleware/auth.py`.*
