# HR Karstec — RRHH

Plataforma interna de gestión del ciclo de vida del empleado, multiempresa, operada por
el equipo de RRHH. Incluye reporting con IA. Este README cubre cómo levantar y entender
el repo; el estado de las features vive en [`CLAUDE.md`](../CLAUDE.md).

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 + FastAPI 0.115 (capas `router → service → repository`) |
| Frontend | Next.js 16.2.4 + React 19.2 + TypeScript 5 + Tailwind 4 + Shadcn/ui |
| Base de datos | Supabase (PostgreSQL + Auth + Storage) |
| IA | Anthropic Claude Sonnet (`claude-sonnet-4-6`) |
| Deploy | Vercel |

## Requisitos

- Python 3.11+
- Node.js 20+
- Cuenta en Supabase, con los buckets de Storage `documentos`, `cvs` y `avatars`
- API key de Anthropic — **obligatoria**: el backend no arranca sin ella

> 🔴 **`RESEND_API_KEY` ya NO se necesita.** Se sacó el 2/8/2026: los mails salen por Gmail,
> reusando el OAuth que ya existe. Era obligatoria y ningún service la importaba.
> **El inventario completo de variables está en [`DEPLOY.md`](DEPLOY.md)** — es el único
> lugar donde se mantiene, para que no vuelva a estar partido en tres.

## Instalación

```bash
git clone https://github.com/Franco-Bincovich/RRHH
cd RRHH
```

### Backend

> **Creá un virtualenv nuevo. No uses ningún venv que venga en el repo.**
> El repo arrastra un `backend/.venv/` commiteado por error: es un entorno de **macOS con
> Python 3.9**, incompatible con este proyecto (target: 3.11) y con Windows. Ignoralo —
> no lo actives ni instales sobre él. El comando de abajo crea `backend/venv/`, que está
> en `.gitignore` y no colisiona con él.

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env         # completar los valores reales
```

El `.env` va en **`backend/`**, no en la raíz: `config/settings.py` lo busca relativo al
directorio desde donde se levanta el server. Variables sin default (obligatorias):
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `JWT_SECRET`,
`ANTHROPIC_API_KEY`, `RESEND_API_KEY`.

### Frontend

```bash
cd frontend
npm install
```

No requiere `.env` para desarrollo local: la única variable que consume es
`NEXT_PUBLIC_API_URL`, con default `http://localhost:8000`. Para apuntar a otro backend,
crear `frontend/.env.local` con ese valor.

## Cómo correr

| Servicio | Comando | URL |
|---|---|---|
| Backend | `cd backend && uvicorn main:app --reload` | http://localhost:8000 |
| Frontend | `cd frontend && npm run dev` | http://localhost:3000 |
| Health check | — | http://localhost:8000/health |

## Tests y linting

`pytest` y `ruff` están **configurados** en `backend/pyproject.toml` pero **no están
pineados** en `requirements.txt` — hay que instalarlos aparte:

```bash
pip install pytest pytest-asyncio ruff
```

```bash
# Backend — pytest toma testpaths=["tests"] del pyproject
cd backend && pytest -v
cd backend && ruff check . --fix && ruff format .

# Frontend
cd frontend && npm test        # vitest
cd frontend && npm run lint    # eslint
```

## Reconstrucción de la base

La fuente de verdad para reconstruir el esquema es **`backend/db/schema.sql`**: se corre
contra una base limpia y ya incluye todo. **No** correr las migraciones encima.

```bash
# contra una base vacía (SQL Editor de Supabase o cualquier cliente Postgres)
psql "$DATABASE_URL" -f backend/db/schema.sql
```

- `backend/migrations/` (001 → 089, 87 archivos) es **historial**, no bootstrap: documenta
  cómo se llegó hasta acá. Correrlas en orden contra una base vacía no reproduce producción
  de forma confiable. Cada cambio nuevo al schema se sigue versionando ahí.
- `backend/migrations/000_run_all.sql` está **deprecado**: tiene un guard que aborta la
  ejecución. Se conserva solo como historial.
- ⚠️ `schema.sql` **no trae los 36 triggers de `updated_at`**: se recrean aparte. Ese y los
  demás detalles del rebuild, en [`DEPLOY.md`](DEPLOY.md) §2.

## Estructura

```
RRHH/
├── backend/
│   ├── main.py           ← entrada FastAPI, registro de routers y middleware
│   ├── config/           ← única fuente de config y env (settings.py)
│   ├── routers/          ← endpoints, sin lógica de negocio
│   ├── services/         ← lógica de negocio
│   ├── repositories/     ← único acceso a DB
│   ├── integrations/     ← wrappers externos (supabase, anthropic)
│   ├── schemas/          ← Pydantic in/out
│   ├── middleware/       ← auth (JWT vía JWKS de Supabase)
│   ├── utils/            ← permisos, errors, logger
│   ├── db/               ← schema.sql (reconstrucción) + README
│   ├── migrations/       ← SQL versionado (historial)
│   └── tests/
├── frontend/
│   ├── app/              ← App Router
│   ├── components/       ← ui/ (Shadcn) + features/
│   ├── services/         ← cliente HTTP y llamadas a la API
│   ├── hooks/  types/  utils/  styles/  lib/
├── docs/
└── vercel.json
```

## Índice de `docs/` — qué responde cada documento

**Si vas a montar infraestructura, empezá por `DEPLOY.md`.**

| Documento | Responde |
|---|---|
| [`DEPLOY.md`](DEPLOY.md) | Variables de entorno, cómo reconstruir la base, migraciones, techos de plataforma y orden de deploy |
| [`BITACORA-CAMBIOS.md`](BITACORA-CAMBIOS.md) | Qué cambió en cada sesión y qué tiene que hacer infraestructura al respecto |
| [`SMOKE-TEST.md`](SMOKE-TEST.md) | Cómo correr el test de humo contra el backend real · resultados en [`SMOKE-TEST-RESULTADOS.md`](SMOKE-TEST-RESULTADOS.md) |
| [`DECISIONES.md`](DECISIONES.md) | Por qué se decidió cada cosa — y sobre todo, qué se descartó y por qué |
| [`Plan de trabajo`](<Plan de trabajo>) | Qué se hace ahora (v2, el vigente) |
| [`DEUDA-TECNICA.md`](DEUDA-TECNICA.md) | Qué hay que limpiar, con gravedad y esfuerzo |
| [`MATRIZ-FILTROS.md`](MATRIZ-FILTROS.md) | Qué corte de información puede sacar RRHH sin pedir nada |
| [`ESTADO-VS-COMPROMISO.md`](ESTADO-VS-COMPROMISO.md) | Qué se comprometió con el directorio y qué existe de verdad |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Por qué este stack y no otro |
| [`CLAUDE.md`](../CLAUDE.md) | Contexto del proyecto y estado de las features (vive en la raíz) |
| `backend/db/schema.sql` | 🔴 **El schema. Única fuente de verdad** — se lee del catálogo de Postgres, no del historial de migraciones |

**Normas de la agencia** (obligatorias, no descriptivas):
[`BASES-DE-DESARROLLO.md`](BASES-DE-DESARROLLO.md) ·
[`ORDEN-Y-LEGIBILIDAD.md`](ORDEN-Y-LEGIBILIDAD.md) ·
[`SEGURIDAD-PENTEST.md`](SEGURIDAD-PENTEST.md) ·
[`UX-UI.md`](UX-UI.md)

**Registro histórico** (obsoletos como plan, se conservan como intención original del producto):
`PLAN_DESARROLLO_AHORA.md` · `PLAN_DESARROLLO_DESPUES.md`
