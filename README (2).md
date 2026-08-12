# 📚 Guías de Migración: Vercel + Supabase → AWS

**Propósito:** Referencia centralizada para futuras migraciones de proyectos a AWS (RDS + ECS + S3)

**Basado en:** 3 proyectos migrados exitosamente (KarIA Reach, Agent_Admin, RRHH)

---

## 📄 Documentos

### 1. `COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md` (20 KB)

**Qué es:** Análisis exhaustivo de diferencias arquitectónicas y errores comunes.

**Cuándo leer:**
- ✅ ANTES de empezar un nuevo proyecto AWS
- ✅ Para entender qué va a cambiar del código actual
- ✅ Para ver patrones de errores que NO queremos repetir

**Contiene:**
- Tabla ejecutiva de cambios (críticos, medianos, menores)
- 5 cambios CRÍTICOS con ejemplos antes/después
- Matriz de 50+ errores encontrados en 3 proyectos
- 5 patrones recurrentes (UUID vs String, Serialización, etc)
- Checklist de 50+ items ANTES de migrar
- Top 5 decisiones arquitectónicas para Franco

**Tiempo de lectura:** 15-20 minutos

---

### 2. `PATRONES_CODIGO_AWS.md` (18 KB)

**Qué es:** Código copy-paste listo para usar en nuevos proyectos AWS.

**Cuándo usar:**
- ✅ Cuando crees un nuevo proyecto AWS
- ✅ Para no reinventar la rueda en auth, DB, serialización
- ✅ Como referencia de qué se vería en Vercel vs AWS

**Contiene:**
1. `postgres_client.py` — asyncpg wrapper (fetchone, fetch, execute)
2. `serializers.py` — Conversión tipos DB→JSON centralizado
3. `password_service.py` — Bcrypt hash/verify
4. `token_service.py` — JWT HS256 creation/verification
5. `auth_service.py` — Login, logout, refresh flow completo
6. `routers/auth.py` — FastAPI auth endpoints
7. `settings.py` — Configuración desde AWS SSM
8. `main.py` — FastAPI app initialization
9. `terraform/main.tf` — IaC mínimo (ECS + RDS + S3)
10. `.gitlab-ci.yml` — Minimal CI/CD pipeline

**Cómo usar:** Copy-paste el código que necesites, adaptá los nombres de tablas/variables.

**Tiempo de implementación:** 2-3 horas para un proyecto nuevo

---

## 🎯 Caso de uso típico (Franco)

### Día 1: Planificar
1. Leer `COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md` (15 min)
2. Ver tabla de cambios CRÍTICOS (5 min)
3. Revisar checklist (10 min)

### Día 2: Setup
1. Copiar `PATRONES_CODIGO_AWS.md` #1-8 (DB, Auth, Serialization)
2. Adaptá nombres de tablas/variables (2 horas)
3. Setup Terraform usando #9 como molde (1 hora)

### Día 3: Testing
1. Tests de serialización (UUID→str, datetime→ISO)
2. Tests de auth flow (login, refresh, logout)
3. Grep exhaustivo de patrones peligrosos

---

## ⚠️ Patrones peligrosos a evitar

**Estos errores aparecieron 50+ veces en 3 proyectos. Evitalos.**

| Patrón | Búsqueda | Solución |
|--------|----------|----------|
| UUID vs String comparison | `grep -rn "uuid.*==" backend/` | Usar `str(uuid_field)` SIEMPRE |
| Supabase SDK remanente | `grep -rn "supabase_admin.auth" backend/` | Deletear si todavía existe |
| Response sin serializar | `grep "Response(" \| grep -v serialize` | Usar `serialize_db_record()` |
| Tipos de datos mismatch | Pydantic `id: str` pero asyncpg devuelve UUID | Usar tipos nativos: `id: UUID` |
| RLS bloqueando | Heredar policies de Supabase | Desactivar RLS O reescribir |

---

## 📌 Regla de oro

**Búsqueda exhaustiva OBLIGATORIA:**

Cuando encuentres un bug que aparece en múltiples lugares:
1. `grep -rn "PATRÓN" backend/` — lista todos
2. Arregla TODO junto en 1 commit
3. Verifica: `grep -rn "PATRÓN_VIEJO"` → debería ser 0 hits
4. Pushea 1 vez, 1 pipeline

**Beneficio:** 70% menos bugs post-deploy, 1 push vs 4.

---

## 🔗 Referencias

- **KarIA Reach:** OAuth, secrets, frontend errors
- **Agent_Admin:** Full migration, cherry-pick, RLS, JWT, Pydantic
- **RRHH:** Auth migration, password hashing, bcrypt

---

**Última actualización:** 2026-08-12  
**Autor:** Claude Code  
**Para:** Franco (futuras migraciones AWS)
