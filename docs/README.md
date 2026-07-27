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
- API key de Anthropic
- API key de Resend — el backend **no arranca sin ella**: `resend_api_key` es un campo
  requerido en `config/settings.py`, aunque hoy ningún módulo envíe mails

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

- `backend/migrations/` (001 → 074) es **historial**, no bootstrap: documenta cómo se
  llegó hasta acá. Correrlas en orden contra una base vacía no reproduce producción de
  forma confiable. Cada cambio nuevo al schema se sigue versionando ahí.
- `backend/migrations/000_run_all.sql` está **deprecado**: tiene un guard que aborta la
  ejecución. Se conserva solo como historial.
- Detalle completo del procedimiento y sus límites: [`backend/db/README.md`](../backend/db/README.md).

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

## Documentación interna

- [`CLAUDE.md`](../CLAUDE.md) — contexto del proyecto y estado de las features
- [`MODELO_DATOS.md`](MODELO_DATOS.md) — fuente de verdad del modelo de datos
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — decisiones de arquitectura
- [`CHANGELOG.md`](CHANGELOG.md) — historial de cambios
- [`backend/db/README.md`](../backend/db/README.md) — reconstrucción de la base

Convenciones de código:

- [`BASES-DE-DESARROLLO.md`](BASES-DE-DESARROLLO.md) — bases de desarrollo
- [`ORDEN-Y-LEGIBILIDAD.md`](ORDEN-Y-LEGIBILIDAD.md) — orden y legibilidad
- [`SEGURIDAD-PENTEST.md`](SEGURIDAD-PENTEST.md) — seguridad y vulnerabilidades
- [`UX-UI.md`](UX-UI.md) — diseño de interfaces
