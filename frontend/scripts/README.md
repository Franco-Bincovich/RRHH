# Arnés del recorrido visual

Tres scripts para **mirar la app entera** —las 45 rutas, en los dos temas, en desktop y en
mobile— sin credenciales, sin backend y sin base de datos. Se usa una vez por tanda de diseño:
es lo que encuentra el botón que se corta en mobile, la tabla que se parte contra el borde y el
relleno azul que `docs/SISTEMA-DE-DISENO.md` §3 no permite.

**Vive acá y no en `frontend/dev/`** porque el repo ya tiene lugar para esto: `backend/scripts/`
(los smoke) y `scripts/` en la raíz (medición y seed). Una cuarta carpeta con otro nombre para lo
mismo es la duplicación que este repo ya documenta en tres lados.

| archivo | qué hace |
|---|---|
| `mock-api.mjs` | Backend FALSO en `:8000`. Le contesta cualquier cosa al front para que las pantallas rendericen. |
| `shots.mjs` | 45 rutas × 2 temas × 2 anchos = **180 PNG**. |
| `sheets.mjs` | Arma **45 hojas de contacto** (las 4 vistas de una pantalla en una sola imagen). Es lo que se mira y lo que se manda. |

---

## Cómo se corre

`playwright` **no es dependencia del repo, a propósito**: son ~120 MB de navegador para una
herramienta que se usa una vez cada tanto. Se instala **afuera**, una sola vez:

```powershell
mkdir $env:TEMP\arnes-visual ; cd $env:TEMP\arnes-visual
npm init -y ; npm i playwright
npx playwright install chromium
```

Después, tres terminales desde `frontend/`:

```powershell
# 1 · el backend falso
node scripts/mock-api.mjs

# 2 · el front (sin .env.local pega solo contra http://localhost:8000, que es el mock)
npm run dev

# 3 · las capturas, con NODE_PATH apuntando a donde quedó playwright
$env:NODE_PATH = "$env:TEMP\arnes-visual\node_modules" ; node scripts/shots.mjs
$env:NODE_PATH = "$env:TEMP\arnes-visual\node_modules" ; node scripts/sheets.mjs
```

Las capturas salen en `%TEMP%\recorrido-visual\{shots,sheets}`. Para cambiarlo:
`$env:SALIDA = "D:\donde\sea" ; node scripts/shots.mjs`.

🔴 **Las capturas NO van al repo.** Son ~19 MB de PNG con datos inventados; versionadas, dentro de
tres meses alguien las lee como el estado real del producto. Se miran y se tiran.

⚠️ **`/login` se captura en un contexto SIN sesión.** Con sesión válida redirige a `/dashboard`
(el guard de `login/page.tsx`), así que si no se separa se sacan cuatro capturas del dashboard
creyendo que son del login.

⚠️ **`/assessment` y `/sucesion` redirigen a `/dashboard`**: están apagadas por flag. El script lo
reporta al final como `REDIRECT`, no es un error.

---

## 🔴 Por qué hicieron falta SIETE iteraciones — que es el valor de esto

La primera corrida dejó **20 de 45 pantallas en el error boundary**, y ninguna por un bug del
front: **la FORMA de cada respuesta es un contrato que el front da por sabido y que no se puede
adivinar desde afuera.** No hay un patrón único; hay uno por endpoint, y no está escrito en
ningún lado que se pueda leer de corrido. Los tres que costaron una iteración cada uno:

- **`GET /api/onboarding` devuelve un array pelado.** Contestarle `{items}` da
  `onboardings.map is not a function`.
- **`GET /api/candidatos` devuelve `{items, total, …}`.** Contestarle un array da
  `items is not iterable`. Son dos listados de la misma app.
- **`GET /api/empleados/{id}/recategorizaciones` devuelve un array y su hermano
  `GET /api/empleados/{id}/cesiones` devuelve un objeto `{items}`.** Misma entidad padre, misma
  forma de URL, dos contratos distintos.

Los otros cuatro fueron del mismo tipo: `/api/costos/dashboard` contra un `path.includes("/dashboard")`
que lo agarraba antes, `data.competencias` que es un objeto y no la lista de competencias,
`mails-pendientes` y `casilla/pendientes` con formas distintas, y las sub-listas de la ficha.

**Es la misma deuda que `services/dashboard.ts` documenta en su encabezado** —un espejo manual de
`schemas/dashboard.py` que `tsc` no puede verificar y que ya se rompió tres veces en agosto—,
vista desde el otro lado: si el contrato fuera generado del OpenAPI del backend, ni este archivo
ni ese espejo existirían. **La lista `ARRAYS` de `mock-api.mjs` es el registro de las siete
iteraciones**; cada línea es un contrato que alguien tuvo que descubrir rompiendo una pantalla.

---

## Qué NO prueba

- **Nada de datos.** Los números son inventados. Un `$NaN`, un `undefined` o un "Semana NaN" en
  una captura es casi siempre un campo que el mock no tiene, no un bug.
- **Nada de interacción.** Son capturas del estado inicial: no hay clicks, ni modales abiertos, ni
  formularios completados. El hover sí se puede medir a mano (`elementHandle.hover()` +
  `boundingBox()`), que es como se verificó que la tarjeta sube exactamente 3px.
- **Nada de permisos.** Corre siempre como `admin_rrhh`. Para mirar `gerencia_lectura` o
  `mandos_medios` hay que cambiarle el `rol` a la sesión que `shots.mjs` inyecta.
