# handoff-aws

> Carpeta única de la migración a AWS. Todo lo que el dev de infra necesita, y todo lo que él
> nos dejó, vive acá.

---

## Por qué existe esta carpeta

La migración a AWS la hace **otro dev**, en paralelo a nuestro trabajo de features. Sin un lugar
único, el material se dispersa: parte en `migracionAWS/`, parte en la bitácora, parte en un mail.
Cuando llega el cutover, nadie sabe qué versión es la buena.

**Regla:** si un documento es *para él* o *de él*, va acá. Si es de cómo trabajamos nosotros, va
en `docs/`.

---

## Qué hay adentro

### De él para nosotros — referencia, no instrucciones

| Archivo | Qué es | Cuándo leerlo |
|---|---|---|
| `COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md` | Análisis de 3 migraciones, 50+ errores, 5 patrones recurrentes | Antes de tocar auth, serialización o queries |
| `PATRONES_CODIGO_AWS.md` | Código de referencia: asyncpg, serializers, JWT, bcrypt, Terraform | Solo si hay que extender o debuggear esas capas |
| `README-DEV.md` | El índice original de los dos anteriores | Ya está resumido acá |

**Cómo se usan estos tres:**

- Son **contexto de decisiones ya tomadas**, no una lista de tareas.
- **El código existente del proyecto manda.** Si el proyecto ya tiene su versión de algo
  (`postgres_client`, `serializers`, `auth_service`), no se reemplaza para parecerse a estos
  patrones.
- **Nada de refactor preventivo.** Si el código funciona y no lo estamos tocando, se deja.
- El checklist de 50 items **no se ejecuta**: es referencia pasiva.

### De nosotros para él — se completa al cierre

| Archivo | Qué va | Cuándo |
|---|---|---|
| `HANDOFF.md` | El documento principal: rutas públicas, techos medidos, decisiones que condicionan el cutover | Fase 3 (J4) |
| `BARRIDO-PATRONES.md` | El resultado de los 4 greps de control, con lo que se arregló y lo que se declara | Fase 3 (3.5) |
| `STORAGE.md` | Los 3 buckets, qué guarda cada uno, y dónde se declaran | Fase 0 (0.7) |
| `RLS.md` | Las 58 policies que **no** se portan, y por qué | Fase 3 (J4) |

### Artefactos de reconstrucción

Estos no viven acá — viven donde el sistema los usa — pero se listan para que él sepa dónde
buscar:

| Archivo | Dónde | Qué es |
|---|---|---|
| `schema.sql` | `backend/db/` | **Fuente de verdad.** No usar las migraciones para reconstruir: producción driftea |
| `seed.sql` | `backend/db/` | Catálogos base sin los cuales el sistema arranca roto |
| `funciones_y_triggers.sql` | `backend/db/` | `fn_misma_empresa()` + los 8 triggers de cruce de empresa |
| `077_recrear_triggers_updated_at.sql` | `migracionAWS/backend/migrations/` | Los 35 triggers de `updated_at` |
| `.env.example` | `backend/` | Verificado contra `settings.py` |

**El orden de reconstrucción, sobre una base recién creada:**

```
schema.sql → funciones_y_triggers.sql → 077 → seed.sql
```

Cada uno con `psql -v ON_ERROR_STOP=1 -f`. Los cuatro tienen que dar exit 0.

---

## Los 4 greps de control

Salen de los patrones recurrentes documentados. Se corren antes de cada entrega y el resultado
queda escrito en `BARRIDO-PATRONES.md`.

```bash
grep -rn "uuid.*==" backend/                      # comparaciones UUID contra string
grep -rn "supabase_admin.auth" backend/           # SDK de auth remanente
grep -rn "model_dump()" backend/ | grep -v mode=  # escrituras sin serializar
grep -rn ": str" backend/schemas/ | grep _id      # IDs mal tipados
```

Que el dev los encuentre en septiembre cuesta horas de debugging. Que se los entreguemos
listados cuesta una sesión.

---

## Lo que ya sabemos que le espera

| Tema | Estado | Nota |
|---|---|---|
| FK a `auth.users` en `schema.sql:1236` | 🔴 se saca en Fase 0 | Único bloqueante del replay |
| 5 IDs tipados `str` en vez de `UUID` | 🔴 se arreglan en Fase 0 | Patrón #1 de la lista |
| 3 buckets de Storage hardcodeados en 6 services | 🔴 se centralizan en Fase 0 | Recomendación "Top 5" #2 |
| 58 policies RLS | ⬜ no se portan | La app entra como `service_role`: hoy no protegen nada |
| Rate limit con `memory://` | 🟠 necesita Redis | El contador es por proceso |
| Jobs en background | 🟠 no funcionan en Vercel | Resuelto por ECS |
| Encoding de `requirements.txt` en Windows | ✅ arreglado | El `⚠️` rompía `pip install` con locale cp1252 |

---

## Coordinación

**Lo que hay que confirmarle antes del 20 de agosto:**
- Qué versión de PostgreSQL va a tener RDS (asumimos 17, igual que producción)
- Cuándo hace el cutover de Storage a S3 — de eso depende si D2 (rutas de archivos de
  evaluaciones) entra o no
- Si necesita algo más de nosotros que no esté en esta carpeta

**La fecha:** el 6 de septiembre recibe el repo completo y estable. Tiene catorce días de
colchón hasta la entrega del 20.

---

*HR Karstec · Carpeta de handoff · 12/8/2026*
