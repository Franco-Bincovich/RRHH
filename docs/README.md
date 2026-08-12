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

> **Creá un virtualenv nuevo. No uses ningún venv que encuentres en el árbol.**
> ⚠️ **Corregido el 12/8/2026: `backend/.venv/` NO está commiteado** — `git ls-files` no devuelve
> una sola entrada suya. Existe **en el disco de la Lenovo** como resto de la Mac (tiene `bin/` y
> no `Scripts/`), y por eso un clon limpio no lo trae. Si lo ves, ignoralo: no lo actives ni
> instales sobre él. El comando de abajo crea **`backend/venv/`**, que es el usable en Windows.

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
`ANTHROPIC_API_KEY`. *(Acá figuraba `RESEND_API_KEY`, contradiciendo el aviso de arriba en el
mismo archivo. Ya no existe en `settings.py`.)*

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

🔴 **`backend/pyproject.toml` YA NO EXISTE.** Se borró porque `@vercel/python` (uv) lo
interpretaba como paquete instalable y abortaba el build. La config quedó partida en dos archivos:
**`backend/ruff.toml`** y **`backend/pytest.ini`** (`asyncio_mode=auto`, `testpaths=tests`).

Las herramientas de test **sí están pineadas**, en `backend/requirements-dev.txt`:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

> ⚠️ **Instalá los DOS o vas a leer un rojo que no es del código.** Sin `pytest-asyncio` los tests
> async "no están soportados nativamente" y sin `python-docx` revientan los de export: **33 errores
> que no existen.** Y sin `ruff`, `tests/test_nombres_definidos.py` **falla, no se saltea**.

```bash
# Backend — pytest toma testpaths=tests de pytest.ini
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

- `backend/migrations/` (001 → 112, 110 archivos) es **historial**, no bootstrap: documenta
  cómo se llegó hasta acá. Correrlas en orden contra una base vacía no reproduce producción
  de forma confiable. Cada cambio nuevo al schema se sigue versionando ahí.
- `backend/migrations/000_run_all.sql` está **deprecado**: tiene un guard que aborta la
  ejecución. Se conserva solo como historial.
- ⚠️ `schema.sql` **no trae los 35 triggers de `updated_at`**: se recrean aparte. Ese y los
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
│   └── handoff-aws/      ← todo lo de la migración a AWS (del dev de infra y para él)
├── migracionAWS/         ← código *_NEW.py de la migración (asyncpg/RDS), aislado de backend/
└── backend/vercel.json   ← config de deploy. 🔴 El `vercel.json` de la RAÍZ se borró: era
                            config mono-proyecto y rompía el serving del front
```

## Índice de `docs/` — qué responde cada documento

**Si vas a montar infraestructura, empezá por `DEPLOY.md`.**

| Documento | Responde |
|---|---|
| [`DEPLOY.md`](DEPLOY.md) | Variables de entorno, cómo reconstruir la base, migraciones, techos de plataforma y orden de deploy |
| [`handoff-aws/`](handoff-aws/README.md) | 🆕 Todo lo de la migración a AWS: lo que dejó el dev de infra y lo que le entregamos. **Su material es contexto, no instrucciones** |
| [`BITACORA-CAMBIOS.md`](BITACORA-CAMBIOS.md) | Qué cambió en cada sesión y qué tiene que hacer infraestructura al respecto |
| [`SMOKE-TEST.md`](SMOKE-TEST.md) | Cómo correr el test de humo contra el backend real · resultados en [`SMOKE-TEST-RESULTADOS.md`](SMOKE-TEST-RESULTADOS.md) |
| [`DECISIONES.md`](DECISIONES.md) | Por qué se decidió cada cosa — y sobre todo, qué se descartó y por qué |
| [`PLAN-6-SEPTIEMBRE.md`](PLAN-6-SEPTIEMBRE.md) | 🟢 **Qué se hace ahora.** El plan vigente (12/8/2026), con la fecha de entrega y las dependencias externas |
| [`ORDEN-SESIONES-CODIGO.md`](ORDEN-SESIONES-CODIGO.md) | El tablero de bloques A–L: qué se cerró y qué quedó pendiente. Ya no es el plan, sigue siendo el inventario |
| [`DEUDA-TECNICA.md`](DEUDA-TECNICA.md) | Qué hay que limpiar, con gravedad y esfuerzo |
| [`MATRIZ-FILTROS.md`](MATRIZ-FILTROS.md) | Qué corte de información puede sacar RRHH sin pedir nada |
| [`ESTADO-VS-COMPROMISO.md`](ESTADO-VS-COMPROMISO.md) | Qué se comprometió con el directorio y qué existe de verdad |
| [`DIAGNOSTICO-CV-SCREENING.md`](DIAGNOSTICO-CV-SCREENING.md) | El diseño del screening de CVs (bloque F), de la casilla de Gmail al clasificador |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Por qué este stack y no otro |
| [`CLAUDE.md`](../CLAUDE.md) | Contexto del proyecto y estado de las features (vive en la raíz) |
| `backend/db/schema.sql` | 🔴 **El schema. Única fuente de verdad** — se lee del catálogo de Postgres, no del historial de migraciones |

**Normas de la agencia** (obligatorias, no descriptivas):
[`BASES-DE-DESARROLLO.md`](BASES-DE-DESARROLLO.md) ·
[`ORDEN-Y-LEGIBILIDAD.md`](ORDEN-Y-LEGIBILIDAD.md) ·
[`SEGURIDAD-PENTEST.md`](SEGURIDAD-PENTEST.md) ·
[`UX-UI.md`](UX-UI.md)

**Registro histórico** (obsoletos como plan, se conservan como registro de una etapa — la jerarquía
completa está en [`CLAUDE.md`](../CLAUDE.md) → *Fuente de verdad del TRABAJO*):
[`PLAN-DE-TRABAJO.md`](PLAN-DE-TRABAJO.md) · [`Plan de trabajo`](<Plan de trabajo>) ·
`PLAN_DESARROLLO_AHORA.md` · `PLAN_DESARROLLO_DESPUES.md` · `sesiones`
