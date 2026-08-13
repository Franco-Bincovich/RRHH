# DIAGNÓSTICO DE ESCALA — Fase 2.5

> **Qué responde:** qué se rompe cuando el sistema pasa de 2 empresas / 31 colaboradores a
> **10 empresas / 1.005 colaboradores**. Es un documento de MEDICIÓN: cada número de acá se tomó
> contra una base cargada, no se estimó. Lo que no se pudo medir está declarado en §9.
>
> **Fecha:** 13/8/2026 · **Base:** local (`HR Karstec`, PostgreSQL 16.13, `localhost:5432`).
> **No se tocó Supabase en ningún momento.** Producción sigue con sus 31 colaboradores reales.
>
> **Reproducible:** `scripts/seed_escala.py` (semilla `20260813`) + `scripts/medir_escala.py`.

---

## 0. Resumen en una pantalla

**La base de datos NO es el problema.** Las consultas ejecutan en 0,1–1,7 ms y en varias el
*planning* cuesta más que la ejecución. Postgres con 1.000 colaboradores no transpira.

**Lo que se rompe es todo lo que está ENTRE la app y la base**, y en dos formas distintas:

| # | Qué | Cómo se manifiesta | Gravedad |
|---|---|---|---|
| 1 | **Los selectores de empleado muestran solo 100** | Silencioso. Con 400 en una empresa, 300 no se pueden elegir | 🔴 **Corrección, no lentitud** |
| 2 | **URLs de 51 KB contra PostgREST** | `/api/inventario/items` en consolidado ya devuelve **500** | 🔴 **Ya roto** |
| 3 | **6 endpoint×modo superan el techo REAL de producción** (25.107 B, medido contra Cloudflare) | `400 Bad Request` del gateway | 🔴 Alto |
| 4 | Dashboard: **25 round trips secuenciales**, fijos | 1,4 s local (y no baja con menos datos) | 🟠 Alto |
| 5 | 47 de 52 listados sin paginación | Exports de 3–6 s; `/api/equipo` devuelve 1.005 filas siempre | 🟠 Alto |
| 6 | Falta el índice `(empresa_id, <fecha>)` en 3 tablas | Página 1 descarta 1.326 filas para encontrar 20 | 🟠 Medio, **barato** |
| 7 | Rate limit de export: 30/hora **compartido y por IP** | El equipo entero de RRHH comparte 30 exports/hora | 🟠 Medio |
| 8 | El export de auditoría es **inalcanzable** | 422 a las 8.060 filas; hoy hay 20.000 | 🟠 Medio |

🔑 **El hallazgo estructural, que gobierna casi todo lo de arriba:** el sistema resolvió bien el
N+1 —**no hay ni uno**, los lookups están batcheados— pero lo resolvió mandando la lista de ids
**en la URL** (`?id=in.(uuid,uuid,…)`). Con 31 empleados esa lista pesa 1,1 KB y es invisible.
Con 1.005 pesa **37 KB**, y con 1.304 ítems de inventario **51 KB**. El techo real de producción
—**medido, no supuesto: 25.107 bytes**— queda en el medio.
**El arreglo del N+1 se convirtió, a escala, en el problema principal.**

> 🟢 **Actualización del 13/8 (posterior a la primera versión):** se midió el límite del gateway de
> producción, que era el hueco declarado en §9.1. **El resultado achicó el problema:** el techo son
> 25,1 KB de Cloudflare, no los 3,9 KB de un nginx de fábrica, así que **rompen 6 casos y no 26.**
> El detalle y la corrección están en §5.2 y §5.4.

---

## 1. PASO 1 — Replay del schema (los cuatro pasos + 113 y 114)

🟢 **Los seis pasos dieron exit 0.** Es la **primera vez que el schema se replaya en un Postgres
que no es Supabase**, y no apareció ningún bloqueante.

| # | Archivo | Exit | Nota |
|---|---|---|---|
| 1 | `backend/db/schema.sql` | **0** | 55 tablas |
| 2 | `backend/db/funciones_y_triggers.sql` | **0** | `fn_misma_empresa` + 8 `trg_emp_*` |
| 3 | `migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql` | **0** | 38 triggers `updated_at` |
| 4 | `backend/db/seed.sql` | **0** | 5 / 1 / 3 ✅ |
| 5 | `backend/migrations/113_lote_features_aditivo.sql` | **0** | no-op (ver abajo) |
| 6 | `backend/migrations/114_lote_features_post_deploy.sql` | **0** | no-op |

**Estado final:** 55 tablas · 46 triggers no internos · 140 FKs · 246 índices.

### 1.1 🟠 Dos correcciones para el handoff

**a. `docs/handoff-aws/README.md` declara conteos que ya no son los del archivo.** Su bloque de
verificación dice que tiene que dar **43** triggers; da **46**. No es drift de producción: es que
`schema.sql` y la 077 ya incorporaron las 3 tablas nuevas de la 113 (`perfiles_puesto`,
`recategorizaciones`, `eventos_agenda`) y cada una trae su trigger de `updated_at`. **35 + 3 + 8 = 46.**
El número escrito manda sobre la intuición del que corre el replay, así que si queda en 43, el dev
de infra va a leer un replay correcto como fallido.

**b. Las migraciones 113 y 114 son NO-OP contra `schema.sql`.** El propio encabezado de
`schema.sql` lo dice (*"va por delante de producción desde el 2026-08-13"*), pero conviene que esté
también acá porque cambia el procedimiento del cutover: **quien reconstruya desde `schema.sql` NO
tiene que correr la 113 ni la 114** — ya están adentro. Correrlas igual es inofensivo (son
idempotentes, verificado), pero pedirlas en el orden de reconstrucción induce a pensar que falta algo.

> 🟢 **`backend/db/README.md` está desactualizado** (habla de 58 tablas, 41 triggers y de la 094).
> El vigente es `docs/handoff-aws/README.md`. No es un hallazgo de escala, pero es la clase de
> divergencia que este repo ya documentó como su modo de falla favorito.

---

## 2. PASO 2 — Los datos

`scripts/seed_escala.py` emite SQL por stdout y **no sabe conectarse a ninguna base**: la única
protección que un script destructivo puede darse a sí mismo. El `TRUNCATE` lo ejecuta el `psql` al
que uno se lo canaliza.

| Tabla | Filas | | Tabla | Filas |
|---|---|---|---|---|
| empresas | 10 | | costos_nomina | 22.360 |
| **empleados** | **1.005** | | auditoría | 20.000 |
| áreas | 58 | | horas_proyecto | 6.000 |
| proyectos | 31 | | solicitudes_vacaciones | 3.000 |
| proyecto_asignaciones | 1.119 | | solicitudes_ausencia | 2.000 |
| vacantes / candidatos | 200 / 1.000 | | empleado_capacitacion | 1.558 |
| objetivos | 420 | | inventario ítems / asign. | 1.304 / 636 |
| presupuesto_areas | 1.392 | | adjuntos | 900 |

**Reparto desparejo, a propósito** — 400 / 175 / 130 / 95 / 70 / 45 / 30 / 25 / 20 / 15. Un reparto
parejo de 100 por empresa habría escondido los dos problemas que la sesión buscaba: el listado que
aguanta 100 y muere en 400, y el modo consolidado. Dentro de cada empresa el reparto también es
desparejo (un área concentra ~30%). `manager_id` cargado en 762/1005.

> ⚠️ **Un fallo del seed que vale como hallazgo del sistema.** La primera carga usó
> `"Entre Rios"` sin tilde. Entró a la base sin ninguna queja —la columna es `text` y no hay CHECK—
> y **tumbó el listado entero de empleados con un 500** al serializar, porque
> `EmpleadoResponse.domicilio_provincia` es un `Literal` con los 24 nombres oficiales del IGN.
> O sea: **la validación de provincia vive solo en Pydantic, y cualquier fila que llegue a esa
> columna por fuera de la app (import, script de migración, el dump del cutover) puede romper el
> listado de forma diferida.** El import de nómina escribe domicilio como texto libre.
> Está anotado en `_provincias.py` que no hay CHECK y por qué; lo que no estaba dicho es que la
> consecuencia es un 500 en el listado, no un dato feo.

---

## 3. PASO 3 — ¿Se puede apuntar el backend a la base local?

🟢 **Sí, y sin tocar una línea de código.**

La app no habla con Postgres: habla con **PostgREST por HTTP**, y `settings.supabase_url` ya es una
variable de entorno. Alcanza con levantar un PostgREST contra la base local y moverla:

```bash
docker run -d --name rrhh-pgrst -p 3001:3000 \
  -e PGRST_DB_URI="postgres://authenticator:CLAVE@host.docker.internal:5432/HR%20Karstec" \
  -e PGRST_DB_SCHEMAS=public -e PGRST_DB_ANON_ROLE=anon \
  -e PGRST_JWT_SECRET="<32+ caracteres>" postgrest/postgrest:v12.2.3
```

Eso mide **el camino completo y real**: router → service → repository → PostgREST → Postgres, y la
respuesta serializada de vuelta. Incluye lo que una medición en SQL puro no ve: el costo de cada
round trip HTTP, la serialización Pydantic y el armado del JSON.

**Dos salvedades honestas, las dos acotadas:**

1. **Se sustituye `middleware.auth._verificar_token`**, que valida la firma ES256 contra el JWKS de
   Supabase (que en local no existe). Es una verificación criptográfica de microsegundos sobre una
   clave cacheada por proceso: no mueve ningún número de este informe. **Todo el resto del
   middleware corre igual**, incluida la resolución de `X-Empresa-Id`.
2. **Las latencias son de red local.** En producción cada round trip suma el viaje a Supabase
   (decenas de ms). Eso **agranda** todo lo medido acá, sobre todo el §5 (25 round trips). Los
   números de este informe son un **piso**.

> 🔑 **Y esto es en sí mismo un dato para el handoff a AWS:** que un PostgREST genérico sirva la app
> entera sin un cambio de código confirma que la capa de datos no tiene nada de Supabase adentro
> más allá del protocolo. Lo único propietario que apareció es que supabase-py arma la base REST
> como `{SUPABASE_URL}/rest/v1` — un prefijo de la plataforma, no de PostgREST.

---

## 4. 🔴 HALLAZGO #1 — Los selectores de empleado se cortan en 100, en silencio

**No es lentitud: es que el usuario no puede hacer su trabajo, y la pantalla no se lo dice.**

Todos los selectores de empleado del front piden **una sola página de 100** y renderizan el
resultado en un `<select>` plano, sin buscador server-side, sin "cargar más" y **sin decir que hay
más**. El backend topea `page_size` en `le=100` (`routers/empleados.py:25`), así que subir el
número no es opción.

| Archivo:línea | Pantalla | Con 400 empleados |
|---|---|---|
| `components/features/shared/SeleccionEmpleado.tsx:58` | selector compartido | 300 invisibles |
| `components/features/areas/AreaModal.tsx:43` | responsable de área | 300 invisibles |
| `components/features/capacitaciones/AsignacionModal.tsx:83` | asignar capacitación | 300 invisibles |
| `components/features/inventario/AsignarModal.tsx:59` | asignar ítem | 300 invisibles |
| `components/features/sucesion/NuevoPlanModal.tsx:33` | plan de carrera | 300 invisibles |
| `app/(dashboard)/onboarding/page.tsx:48` | iniciar onboarding | 300 invisibles |

**Por qué esto es lo más grave del informe:** todos los demás hallazgos son "tarda mucho", que el
usuario percibe y reporta. Este es **"tu empleado no existe"**, que el usuario no reporta como bug:
lo interpreta como que el dato no está cargado, y va a pedirle a desarrollo que lo cargue.

⚠️ **Y ya pasó una vez, con el mismo mecanismo.** El propio `cargarEmpleados.ts` documenta que un
`page_size=200` contra el endpoint con `le=100` devolvía 422 en el 100% de los requests y **dos
modales mostraron "no hay empleados" durante meses**, con la suite en verde. Ese caso se arregló
distinguiendo error de lista vacía. **El caso de hoy es el hermano silencioso: no hay error que
distinguir — el 200 es correcto y la lista está truncada.**

🟢 `components/features/costos/NominaModal.tsx:62` **sí** recorre las páginas en un loop. Es el
único que lo hace, y es el molde de lo que hay que hacer en los otros seis (o mejor: un combobox
con búsqueda server-side, ver §10).

---

## 5. 🔴 HALLAZGO #2 — La lista de ids viaja en la URL, y la URL tiene techo

### 5.1 El mecanismo

Los repos **no tienen N+1** — verificado contando los requests a PostgREST por endpoint: el número
es **constante** entre la empresa de 400 y la de 15. Los lookups se resuelven en lote:

```
GET /empleados?select=id,nombre,apellido,area_id&id=in.(uuid,uuid,uuid,…)
```

Eso es lo correcto contra el N+1. **Pero mueve el costo a la URL.** Cada UUID pesa 37 bytes
url-encodeados. 31 empleados → 1,1 KB. 1.005 → **37 KB**.

### 5.2 Los techos, medidos (no estimados)

| Capa | Último OK | Primer fallo | Respuesta |
|---|---|---|---|
| **🔴 PRODUCCIÓN — Cloudflare, delante de Supabase** | **25.107 B** | **25.108 B** | `400` con cuerpo `Bad Request` |
| PostgREST/warp pelado | 50.898 B | 50.912 B | `400` con cuerpo `Bad Request` en texto plano |
| nginx con config de fábrica *(referencia)* | 3.944 B | 3.949 B | `502`; arriba de 8 KB, `414` |

**La primera fila es la que manda, y está medida contra el proyecto de producción**
(`grmdiwxcvcjorlohpwji`, 13/8/2026) con requests de lectura que no escriben nada: un `GET` a
`/rest/v1/empresas?select=id&nombre=eq.<relleno>`, cuyo filtro no matchea ninguna fila y devuelve
`[]`. El borde es **determinista**: 25.107 devuelve `200` en 5 de 5 corridas y 25.108 devuelve
`400` en 5 de 5. El `server` de la respuesta es `cloudflare`, así que quien corta es el CDN, no
Kong ni PostgREST.

> 🟢 **Esto es MEJOR de lo que el informe asumía en su primera versión.** La estimación conservadora
> era el nginx de fábrica (3,9 KB), y con ese número **26 casos** quedaban del lado roto. Con los
> 25,1 KB reales de Cloudflare, **20 de esos 26 tienen margen de sobra y no son un problema.**
> La fila de nginx queda como referencia porque **el destino AWS puede tener un techo más bajo que
> el de hoy**. ⚠️ No lo midió esta sesión y no hay que darlo por sabido: **es una pregunta concreta
> para el dev de infra** — cuál es el largo máximo de URL del ALB y de CloudFront tal como los va a
> configurar. Si el destino queda por debajo de los 25,1 KB actuales, **el cutover ROMPE endpoints
> que hoy andan**, y la lista de cuáles está en §5.4. Ver §5.5.

### 5.3 🔴 Lo que YA está roto

**`/api/inventario/items` y `/api/inventario/items/exportar`, en modo consolidado, devuelven 500.**
No es lento: falla. La URL a `inventario_asignaciones` mide **50.973 bytes** y PostgREST la rechaza.
Reproducido de punta a punta; el `APIError` que sube trae `details: b'Bad Request'`, que es la firma
de una URL sobre el límite del servidor, no de un problema de datos.

### 5.4 Qué rompe de verdad, contra los 25.107 bytes reales

Máximo largo de URL que cada endpoint le manda a PostgREST, con **1.005 colaboradores**, contrastado
contra el techo medido de producción:

| URL máx | Modo | Tabla del lookup | Endpoint | vs. 25.107 |
|---:|---|---|---|---|
| **50.973** | consolidado | `inventario_asignaciones` | `/api/inventario/items` | 🔴 **ROMPE** (2,0×) |
| **50.973** | consolidado | `inventario_asignaciones` | `/api/inventario/items/exportar` | 🔴 **ROMPE** (2,0×) |
| **37.335** | consolidado | `empleados` | `/api/vacaciones/exportar` | 🔴 **ROMPE** (1,5×) |
| **34.020** | consolidado | `empleados` | `/api/ausencias/exportar` | 🔴 **ROMPE** (1,4×) |
| **33.201** | consolidado | `empleados` | `/api/capacitaciones/asignaciones/exportar` | 🔴 **ROMPE** (1,3×) |
| **27.062** | consolidado | `proyecto_asignaciones` | `/api/organigrama/proyectos` | 🔴 **ROMPE** (1,1×) |
| 23.958 | consolidado | `empleados` | `/api/vacaciones-pendientes/exportar` | 🟠 **al borde** — 1.149 B de margen |
| 20.397 | **grande** | `inventario_asignaciones` | `/api/inventario/items` (+ export) | 🟠 81% del techo |
| 18.077 | consolidado | `inventario_items` | `/api/inventario/asignaciones` (+ export) | 🟢 72% |
| 16.474 | consolidado | `objetivo_responsables` | `/api/objetivos` (+ export) | 🟢 66% |
| 14.871 | **grande** | `empleados` | `/api/vacaciones/exportar` | 🟢 59% |
| 13.155 | **grande** | `empleados` | `/api/ausencias/exportar` | 🟢 52% |
| 13.116 | **grande** | `empleados` | `/api/capacitaciones/asignaciones/exportar` | 🟢 52% |
| 10.844 | grande y consolidado | `proyecto_asignaciones` | `/api/horas-cliente` (+ export) | 🟢 43% |
| 10.721 | **grande** | `proyecto_asignaciones` | `/api/organigrama/proyectos` | 🟢 43% |
| 9.879 | **grande** | `empleados` | `/api/vacaciones-pendientes/exportar` | 🟢 39% |
| 7.768 | consolidado | `vacantes` | `/api/candidatos` (+ export) | 🟢 31% |
| 7.001 | **grande** | `inventario_items` | `/api/inventario/asignaciones` (+ export) | 🟢 28% |

### 🔑 La respuesta a "¿ya está roto o es pronóstico?" — las dos cosas, y la distinción importa

**Hoy, con los 31 colaboradores reales de producción: NO hay nada roto.** La URL más grande que el
sistema genera hoy ronda **1,2 KB**, un 5% del techo. Nadie va a ver un error esta semana.

**A la escala objetivo: SEIS casos rompen**, y uno más queda a 1,1 KB del borde. No es un pronóstico
sobre un límite supuesto — el límite está medido y los largos de URL también.

**Y hay un caso intermedio que es el que más conviene mirar:** `/api/inventario/items` de **una sola
empresa** ya llega a **20.397 bytes con 400 empleados**. Está al **81% del techo**. Esa empresa no
necesita llegar a 1.005 personas para romperse: le alcanza con **crecer un 23%**.

**El umbral, en colaboradores:** la medición da ~37 bytes por UUID url-encodeado
(37.335 B ÷ 1.005 ids). **25.107 ÷ 37 ≈ 678 ids.** O sea: **cualquier consulta cuyo resultado toque
más de ~680 empleados distintos supera el techo de producción.** Para `inventario_items` el
divisor es el número de ítems, no de personas (1.304 ítems → 50.973 B), y por eso es el primero que
cae: hay más ítems que gente.

> 🟢 **La corrección honesta respecto de la primera versión de este informe:** decía "26 casos por
> encima del techo", tomando el nginx de fábrica (3,9 KB) como referencia conservadora. **Con el
> número real son 6, no 26.** Los otros 20 tienen margen y no hay que tocarlos. La conclusión de
> fondo no cambia —el batch por URL es un problema estructural de escala— pero el tamaño del
> trabajo sí: es acotado y se puede priorizar por caso en vez de por barrido.

### 5.5 ⚠️ Lo que esto le pide al cutover de AWS

Los 25,1 KB son un regalo de **Cloudflare**, no una propiedad de nuestro código. El destino AWS
tiene otro gateway y **puede ser más restrictivo que el actual**.

**Pregunta concreta para el dev de infra, antes del cutover:** *¿cuál es el largo máximo de URL que
van a admitir el ALB y CloudFront tal como los vas a configurar?* Si la respuesta queda por debajo
de 25.107, **el cutover rompe endpoints que hoy funcionan**, y los candidatos son las filas de 20 KB
para abajo de la tabla de arriba, en orden.

🔑 **Y la contracara, que conviene decirle en la misma frase:** en AWS con asyncpg **el problema
desaparece por completo**, porque los ids dejan de viajar por URL (`WHERE id = ANY($1)` es un
parámetro del protocolo binario, sin techo práctico). Así que el riesgo existe **solo en la ventana
en que la app siga hablando PostgREST detrás de un gateway de AWS**. Si el porteo a asyncpg es
simultáneo al cutover, no hay nada que hacer; si hay un período intermedio, hay que subir los
buffers del ALB.

---

## 6. PASO 4 — Los hallazgos por tipo

### 6.1 Consultas sin límite que traen todo

`/api/equipo` es el caso puro: **devuelve 1.005 filas siempre**, para cualquier empresa
seleccionada, incluida la de 15 personas. Es correcto por diseño —`routers/equipo.py:26` dice
explícito que el universo sale del **ownership del usuario**, no del header, y para `admin_rrhh` el
ownership no restringe— pero el comentario del propio archivo dice *"Sin paginación: lista corta"*,
y **esa premisa dejó de ser cierta**: la lista corta son 1.005 filas.

Los demás listados que traen todo: `costos/nomina` (1.005), `candidatos` (1.000), `sucesion/mapa`
(890), `inventario/items` (1.304 en consolidado), `objetivos` (420), `adjuntos` (900).

### 6.2 Listados sin paginación

**47 de 52** endpoints de listado no aceptan `page`/`page_size`. Solo paginan cinco: `empleados`,
`vacaciones`, `ausencias`, `vacaciones-pendientes` y `auditoria`.

Muchos de los 47 son legítimos (catálogos, `configuracion`, `integraciones`, `auth/me`: filas
acotadas por diseño). **Los que sí crecen con la dotación o con el número de empresas** son:
`equipo` · `candidatos` · `costos/nomina` · `objetivos` · `inventario/items` ·
`inventario/asignaciones` · `capacitaciones/asignaciones` · `sucesion/mapa` · `adjuntos` ·
`vacantes` · `horas-cliente` · `areas`.

### 6.3 Filtros del lado del cliente

Menos de lo que se temía — el bloque B hizo su trabajo. Quedan dos con consecuencia real:

- **`components/features/areas/useAreas.ts:46`** — la búsqueda por nombre filtra sobre el array ya
  traído. El endpoint `/api/areas` no tiene `search` ni paginación. Con 58 áreas hoy y ~180 con 10
  empresas, no duele en velocidad; **duele en que el export no ve el filtro** (invariante 1 del
  bloque B).
- **`components/features/comunicacion/useSeleccionEmpleados.ts:30`** — busca empleados sobre la
  lista en memoria, que es la lista truncada a 100 del §4. **Los dos defectos se componen:** buscás
  a alguien que existe, está fuera de los primeros 100, y el buscador dice que no hay resultados.

El resto de los `.filter(` del barrido son derivaciones de UI sobre listas chicas (agrupar
candidatos por etapa, separar tipos padre/hijo, filtrar empresas activas): no son deuda.

### 6.4 N+1

🟢 **No hay ninguno.** Es el resultado más limpio del diagnóstico y merece decirse tal cual: el
conteo de requests a PostgREST es **idéntico** con 400 empleados y con 15 en los 52 endpoints
barridos. `_hora_row.py`, `_evaluacion_lotes_enrich.py` y los mappers con lookups por lote hacen lo
que dicen hacer. El precio de esa decisión es el §5, no un N+1 escondido.

### 6.5 Pantallas que arman estructuras completas

El organigrama **no era el sospechoso principal**: `/api/organigrama` tarda 237 ms y hace 3 queries.
Los que arman estructura cara son otros dos, y los dos por **round trips fijos**, no por volumen:

| Endpoint | Queries | 400 emp. | 15 emp. | consolidado |
|---|---:|---:|---:|---:|
| **`/api/dashboard`** | **25** | 1.369 ms | **1.376 ms** | 1.579 ms |
| **`/api/procesos`** | **15** | 799 ms | **859 ms** | 900 ms |
| `/api/organigrama/proyectos` | 6 | 372 ms | 353 ms | 499 ms |

🔑 **Leer la columna de 15 empleados.** El dashboard tarda **lo mismo con 15 que con 400**. Eso
dice que el costo no son los datos: son **25 viajes de ida y vuelta secuenciales**, cada uno de
~7 ms locales, ninguno dependiente del anterior. Un round trip trivial a PostgREST mide **6,84 ms**
en localhost; contra Supabase por internet son decenas. **El dashboard de producción va a estar
bastante peor que estos 1,4 s, y no porque haya más datos.**

Y son round trips *evitables*: `/api/procesos` hace **una query por cada valor de estado**
(`onboarding_instancias` × 3 estados, `offboarding_instancias` × 3, `vacantes` × varios), cuando es
un `GROUP BY estado`. El dashboard repite el mismo patrón.

### 6.6 Exports sin techo — ¿el límite cubre los 26?

**Sí, los 26 lo tienen** (el barrido estructural `test_limite_export.py` lo garantiza y se verificó
en vivo: el de auditoría cortó con 422 `EXPORT_DEMASIADAS_FILAS`). **El problema es el otro:**

🟠 **El export de auditoría es hoy inalcanzable.** Con 20.000 eventos, `/api/auditoria/exportar`
devuelve **422** tanto para la empresa grande (8.060 filas) como para el consolidado. El mensaje
dice "usá los filtros", que es correcto y accionable — pero la auditoría es justo el módulo del que
RRHH exporta el año entero. **Con 10 empresas de tráfico real (medido: 200.000 eventos en un año)
ningún corte razonable baja de 5.000.**

Y el límite es **por filas, no por tiempo**, que es lo que el propio `_limite_export.py` explica
que es el techo real. Los tiempos medidos, con el límite desactivado:

| Export | consolidado | grande | chica |
|---|---:|---:|---:|
| `vacaciones/exportar` | **5.981 ms** | 2.416 ms | 379 ms |
| `ausencias/exportar` | **3.777 ms** | 1.657 ms | 385 ms |
| `capacitaciones/asignaciones/exportar` | **3.009 ms** | 1.294 ms | 373 ms |
| `empleados/exportar` | 1.833 ms | 490 ms | — |
| `candidatos/exportar` | 1.616 ms | 1.095 ms | — |
| `costos/nomina/exportar` | 1.342 ms | 590 ms | — |

Los cuatro que no paginan (capacitaciones, inventario ítems, inventario asignaciones, objetivos)
siguen chequeando el límite **sobre la lista ya traída** — está declarado en `_limite_export.py` y
se confirma: no hay regresión, pero tampoco protección real.

### 6.7 🟠 Rate limit de export: 30/hora compartido, por IP

Esto no se buscaba y apareció solo: **el primer barrido de mediciones no pudo medir la mitad de los
exports porque se agotó la franja** y todo devolvía 429.

`shared_limit("30/hour", scope="export")` era **30 exports por hora en total** —compartidos entre
los 26 endpoints— y la clave era **la IP**. El equipo de RRHH son 3 personas detrás de una sola IP
de oficina: **compartían 30 exports por hora entre las tres**. Con 10 empresas y el modo
consolidado, una sesión normal de cierre de mes (un export por módulo por empresa) lo agotaba en
minutos.

> 🟢 **RESUELTO el 13/8/2026.** La franja pasó a **`100/hora POR USUARIO`**
> (`utils/rate_limit.py::limite_export`, aplicado en los 26 endpoints). La clave la calcula
> `usuario_o_ip`, que sale de `request.state.user` con fallback a la IP.
> 🔑 **Se pudo hacer sólo en el decorador y no en el baseline, por el orden del middleware:**
> `SlowAPIMiddleware` corre POR FUERA de `AuthMiddleware`, así que cuando el baseline calcula su
> clave todavía no existe `request.state.user`; el decorador envuelve al endpoint y se evalúa
> después de todo el middleware. **Efecto colateral bueno:** la franja de export dejó de depender
> de `TRUSTED_PROXY_HOPS`, que es la variable que más fácil queda mal en el cutover a AWS.

⚠️ Y con `RATE_LIMIT_STORAGE_URI=memory://` el contador es **por proceso**, así que hoy en
serverless el límite efectivo es N× y esto no se nota. **El día que se conecte Redis en AWS —que es
lo correcto— el límite pasa a ser real.** Eso sigue vigente: la migración lo *crea*, no lo resuelve.
La diferencia es que ahora el número que se vuelve real es 100 por persona y no 30 para todo el
equipo.

### 6.8 Lo que crece con el número de EMPRESAS y no con el de filas

Tres cosas, y son de naturaleza distinta:

1. **El descarte del índice en los listados por empresa** (§7). Cuantas más empresas comparten la
   tabla, más filas descarta el índice de fecha para armar la página 1 de una empresa chica.
2. **Las URLs del §5 en modo consolidado**, que es el modo por defecto.
3. **Nada más.** No apareció ningún bucle sobre `empresas` en el backend. `/api/dashboard` hace 25
   queries **también** en consolidado: resuelve el consolidado sacando el `.eq("empresa_id")`, no
   iterando empresas. Es la decisión correcta y conviene que quede escrita, porque es justo lo que
   una feature nueva puede romper sin darse cuenta.

---

## 7. PASO 6 — Los índices

### 7.1 Lo primero: la base no es el cuello de botella

| Consulta | Ejecución | Planning |
|---|---:|---:|
| vacaciones, empresa, página 1 | 0,31 ms | 4,88 ms |
| auditoría, empresa, página 1 | 0,15 ms | 6,58 ms |
| empleados, listado por empresa | 0,47 ms | 7,24 ms |

**El planning cuesta 10–20× más que la ejecución.** A este volumen Postgres no es el problema, y
ningún índice va a mover la aguja de los tiempos que el usuario percibe: esos los explica el §5 y
el §6.5.

Hay *seq scans* —`empleados` filtrado por `empresa_id` (400 de 1.005 filas), `solicitudes_vacaciones`
en consolidado (3.000 filas)— y **están bien**: con el 40% de la tabla seleccionada el planner elige
seq scan a propósito y un índice sería peor.

### 7.2 🟠 Falta UN índice, y es el que crece con el número de empresas

El patrón es `WHERE empresa_id = X ORDER BY <fecha> DESC LIMIT 20`. Hoy hay un índice por
`empresa_id` **y otro** por la fecha, separados. El planner elige el de fecha y **descarta filas
hasta juntar 20 de la empresa pedida**. Cuantas más empresas, más descarta.

**Medido con `auditoria` escalada a 200.000 filas** (un año realista de 10 empresas), página 1 de la
empresa más chica:

| | Filas descartadas | Buffers | Tiempo |
|---|---:|---:|---:|
| **Hoy** (`idx_auditoria_created`) | **1.326** | 1.353 | 1,53 ms |
| **Con `(empresa_id, created_at DESC)`** | **0** | **23** | **0,096 ms** |

**59× menos buffers.** Y lo que importa no es el 0,1 ms: es que **la columna "filas descartadas"
crece linealmente con el número de empresas** y la versión con índice compuesto no crece nunca.

Los tres índices, con su medición:

| Índice propuesto | Consulta | Sin | Con | Mejora |
|---|---|---:|---:|---:|
| `costos_nomina (empresa_id, anio, mes)` | nómina del período | 26,57 ms | **0,57 ms** | **47×** |
| `auditoria (empresa_id, created_at DESC)` | auditoría pág. 1 | 1,53 ms | **0,096 ms** | **16×** |
| `solicitudes_vacaciones (empresa_id, fecha_desde DESC)` | vacaciones pág. 1 | 1,42 ms | **0,12 ms** | **12×** |
| `solicitudes_ausencia (empresa_id, fecha_desde DESC)` | ausencias pág. 1 | — | — | por simetría |

> **`costos_nomina` es el más rentable de los cuatro** y no estaba en la sospecha inicial: hoy usa
> `idx_costos_nomina_periodo (anio, mes)`, trae las 1.005 filas del mes de *todas* las empresas y
> descarta 605 en el filtro. Con 10 empresas y 22.360 filas ya cuesta 26 ms; escala con el padrón
> total, no con el de la empresa.

⚠️ **Lo que estos índices NO arreglan, medido:** la paginación profunda. Con `offset 2000` el índice
compuesto **no ayuda** (11,4 ms con, 9,7 ms sin): un `OFFSET` es O(offset) con cualquier plan. Si
alguien pagina hondo en auditoría, eso se arregla con paginación por cursor, no con un índice.

🔴 **Es lo más urgente del informe en términos de VENTANA, no de impacto:** los índices se agregan
en una migración y **el schema se congela el 21/8**. Un índice que no entra ahora se agrega
coordinando con el dev de infra en medio de su migración.

---

## 8. PASO 5 — El modo consolidado

Es el modo por defecto del sidebar, así que es el que un usuario ve primero.

**No hay explosión no-lineal por iterar empresas** — ya dicho en §6.8: el consolidado se resuelve
sacando el filtro, no recorriendo las 10. El dashboard hace 25 queries en los dos modos.

**Pero empeora, y de dos formas concretas:**

| Endpoint | grande (400) | consolidado (1.005) | factor |
|---|---:|---:|---:|
| `vacaciones/exportar` | 2.416 ms | **5.981 ms** | 2,5× |
| `ausencias/exportar` | 1.657 ms | 3.777 ms | 2,3× |
| `capacitaciones/asignaciones/exportar` | 1.294 ms | 3.009 ms | 2,3× |
| `empleados/exportar` | 490 ms | 1.833 ms | **3,7×** |
| `inventario/items` | 356 ms (ok) | **500** | 🔴 rompe |

1. **Crece con el total de filas, no con el número de empresas** — el factor 2,3–3,7× es
   proporcional a 1.005/400 = 2,5, más el costo extra de resolver los nombres de 10 empresas en vez
   de 1. Es lineal, pero sobre una base 2,5× más grande.
2. **Es el modo donde las URLs del §5 revientan primero, y por amplio margen**: los **6** casos que
   superan el techo real de producción (25.107 B) son **los 6 de modo consolidado**. Ningún endpoint
   de una empresa sola lo cruza todavía — el peor va por el 81%. O sea que **el modo por defecto del
   sidebar es el único que hoy rompe**, que es la peor combinación posible: es el que el usuario ve
   primero sin elegirlo.

🔑 **La conclusión para el dashboard, que es lo que se sospechaba:** el dashboard **no** empeora de
forma no-lineal en consolidado (1.579 vs 1.369 ms, +15%). Su problema es otro y es peor: **es lento
en los tres modos por igual**, incluida la empresa de 15 personas.

---

## 9. Lo que NO se pudo medir, y por qué

1. 🟢 **~~El límite real de URL del gateway de Supabase.~~ MEDIDO el 13/8/2026 — ver §5.2.**
   Era el hueco que decidía si el §5 es pronóstico o presente. Se cerró con requests de lectura
   contra producción (`GET /rest/v1/empresas?select=id&nombre=eq.xxx…`, filtro que no matchea nada
   → `[]`, cero escrituras). **El gateway es Cloudflare y el límite es 25.107 bytes**, determinista
   (5/5 corridas por tamaño). La respuesta está en §5.2 y §5.4; **el resultado cambió las
   conclusiones del informe** y esas secciones ya están corregidas.
2. **Compatibilidad con PostgreSQL 17.6.** La base local es 16.13, así que el replay del §1 prueba
   sintaxis y orden, **no** la versión destino. Hay un contenedor `postgres:17.6` corriendo en esta
   máquina (`rrhh-escala`, puerto 55432) que lo permitiría; se dejó fuera por respetar el enunciado.
   Es media hora de trabajo y cierra la salvedad.
3. **Latencia real contra Supabase.** Todo se midió en localhost. Los round trips del §6.5 son un
   piso; en producción cada uno suma el viaje de red.
4. **Endpoints con `{id}` en la ruta** (ficha de empleado, detalle de vacante, historial salarial).
   El barrido descubre por `app.routes` y los saltea: medirlos exige elegir un recurso concreto por
   módulo. **Es la brecha más grande de cobertura de este informe** — la ficha de empleado es una
   pantalla muy usada y no está medida.
5. **Escrituras.** Solo se midieron `GET`. Los imports (nómina, objetivos, evaluaciones) tienen
   presupuesto de tiempo propio y a 1.000 filas son el próximo candidato a mirar.
6. **`/api/screening/criterio` devuelve 500** en los tres modos, y `/api/vacantes/casilla/pendientes`
   devuelve 400. Los dos dependen de integraciones externas (Gmail/Zernio) que en local no existen.
   **No se pudo determinar si son fallos reales o artefactos del entorno**; quedan como pendiente de
   verificación, no como hallazgo.

---

## 10. Cierre

### (a) Lo que NO aguanta, ordenado por cuánto se nota

1. **Los selectores de empleado cortados en 100** (§4). Silencioso, ya activo con una empresa de
   más de 100, y el usuario lo interpreta como dato faltante. Lo peor del informe.
2. **`/api/inventario/items` en consolidado: 500** (§5.3). Ya roto, no es pronóstico.
3. **6 endpoint×modo por encima del techo REAL de producción** (§5.4: 25.107 B, medido contra
   Cloudflare). Y uno más, `/api/inventario/items` de **una sola empresa**, al **81% del techo**:
   esa empresa rompe creciendo un 23%, sin necesidad de llegar a 1.005 personas.
4. **Dashboard 1,4 s y `/api/procesos` 0,9 s**, iguales con 15 que con 400 (§6.5). Es la primera
   pantalla que ve todo el mundo y en producción va a ser peor.
5. **Exports de 3–6 s en consolidado** (§6.6), con el de auditoría directamente **inalcanzable**.
6. **30 exports/hora por IP para todo el equipo** (§6.7). Hoy invisible por `memory://`; aparece
   cuando AWS conecte Redis.
7. **La página 1 de los listados por empresa descarta cientos de filas** (§7.2). El de menor impacto
   hoy y el de ventana más corta.

### (b) Qué es índice, qué es paginación, qué es rediseño

**ÍNDICE — una migración, entra en el lote que congela el 21/8.** Los cuatro del §7.2. Es la única
categoría con **fecha de vencimiento**, y la más barata: cuatro `CREATE INDEX`, cero código, cero
riesgo. Ganancia medida de 12× a 47×.

**PAGINACIÓN Y FRONT — backend + front, sin tocar el schema.** Los selectores de empleado (§4:
combobox con búsqueda server-side, o el loop de `NominaModal`) · `page`/`page_size` en los 12
listados que crecen (§6.2) · `search` server-side en `/api/areas` (§6.3) · subir o repensar el
límite del export de auditoría (§6.6) · revisar la franja de rate limit de export (§6.7).

**REDISEÑO — dos cosas, y solo dos.**
- **El batch por URL** (§5). No se arregla con un parche: hay que decidir entre resolver los
  lookups del lado de la base (una vista o un embed de PostgREST en vez de dos viajes), o cortar
  los `in.(…)` en tandas de ~100 ids en un solo lugar compartido. **Lo primero es más
  trabajo y menos deuda; lo segundo entra en una sesión.** 🔑 **Esta decisión conviene tomarla
  antes del cutover, porque en AWS/asyncpg el problema DESAPARECE solo** — un `WHERE id = ANY($1)`
  no tiene techo de URL. Puede que la respuesta correcta sea el parche de las tandas ahora y nada
  después.
- **Dashboard y `/api/procesos`** (§6.5): 40 round trips entre los dos, muchos resolubles con un
  `GROUP BY estado`. Es donde está la mejora más visible por unidad de trabajo.

### (c) Sesiones estimadas

| Grupo | Sesiones | Nota |
|---|---:|---|
| Índices (migración) | **0,5** | 4 `CREATE INDEX` + verificación. **Antes del 21/8** |
| Selectores de empleado | **1** | Hacer el combobox una vez, cablearlo en 6 lugares |
| Paginación en los 12 listados | **2** | Backend y front; el molde ya existe (`empleados`) |
| Rate limit + límite de export | **0,5** | Dos números y su justificación escrita |
| Batch por URL (parche de tandas) | **1** | Un solo lugar compartido |
| Dashboard + procesos | **1,5** | `GROUP BY` y consolidar queries |
| Verificar el techo del gateway (§9.1) | **0,1** | Un request |
| **Total** | **~6,5** | |

Si el batch por URL se resuelve del lado de la base en vez de con tandas, sumar **2 sesiones** y
moverlo a después del cutover.

### (d) 🔴 La regla que las features nuevas tienen que cumplir

> **Antes de escribir un listado nuevo, contestá tres preguntas. Si alguna no tiene respuesta, el
> listado no está diseñado.**
>
> **1. ¿Cuántas filas devuelve con 10 empresas y 1.000 colaboradores?**
> Si la respuesta puede pasar de ~100, **nace paginado**: `page`/`page_size` con `le=100` en el
> router. No "después le agregamos paginación": agregarla después obliga a tocar el front, el
> export y el hook de filtros, que es exactamente por qué hoy hay 47 listados sin ella.
>
> **2. ¿Alguna consulta mete una lista de ids en la URL?**
> Todo `.in_("id", ids)` donde `ids` sale de otra consulta tiene un techo **medido de ~678
> elementos** en producción (25.107 bytes ÷ 37 bytes por UUID url-encodeado). Si la lista puede
> pasar de eso, **va en tandas o no va por URL**. La regla concreta: **un `.in_()` cuyo largo
> dependa del padrón es un bug de escala, aunque hoy funcione** — el número de hoy es 678 y lo fija
> el gateway, no nuestro código, así que puede bajar sin que nadie toque el repo (ver §5.5: en AWS
> puede ser más chico).
>
> **3. ¿Cuántos round trips hace la pantalla?**
> Contalos. Cada uno cuesta ~7 ms en local y decenas contra Supabase, **haya un dato o mil**. Si
> son más de 5, la pregunta es si alguno se puede resolver con un `GROUP BY` o un embed. El
> dashboard llegó a 25 sumando de a uno, y ninguno de los 25 fue una mala decisión por sí solo.
>
> **Y una que no es pregunta, es requisito:** **todo `WHERE empresa_id = X ORDER BY <fecha>` lleva
> su índice compuesto `(empresa_id, <fecha> DESC)` en la misma migración que crea la tabla.**
> Separados, el planner elige el de fecha y descarta filas de las otras nueve empresas — y ese
> descarte crece cada vez que se suma una empresa.
>
> **Cómo se verifica que la regla se cumplió:** `scripts/seed_escala.py` +
> `scripts/medir_escala.py --queries --urls`. Los dos descubren la superficie por introspección de
> `app.routes`, así que **un endpoint nuevo entra al barrido sin tocar nada**.

### (e) Qué no se pudo medir

Está en §9, con el porqué de cada uno.

🟢 **El que encabezaba esta lista ya se cerró:** el límite de URL del gateway de producción se midió
el 13/8 (**25.107 bytes**, Cloudflare) y el informe está corregido — §5.2, §5.4 y §5.5. **El
resultado achicó el problema de 26 casos a 6**, y abrió una pregunta nueva para el dev de infra: el
techo del ALB/CloudFront del destino, que puede ser **más bajo** que el de hoy.

Lo que queda sin medir, por orden de importancia:

1. **Los endpoints con `{id}` en la ruta** (§9.4) — **la brecha más grande que queda**. La ficha de
   empleado es de las pantallas más usadas y no está medida.
2. **Las escrituras** (§9.5), en especial los imports a 1.000 filas.
3. **Compatibilidad con PostgreSQL 17.6** (§9.2) — hay un contenedor 17.6 en la máquina que lo
   cierra en media hora.
4. **La latencia real contra Supabase** (§9.3): todo se midió en localhost, así que los tiempos de
   este informe son un piso.
5. **`/api/screening/criterio` (500) y `/api/vacantes/casilla/pendientes` (400)** (§9.6): dependen de
   integraciones externas ausentes en local; sin determinar si son fallos reales.

---

## Anexo — Cómo reproducir

```powershell
$env:PGPASSWORD = "rrhh2026"

# 1. Reconstruir (base vacía)
psql -h localhost -p 5432 -U postgres -d "HR Karstec" -v ON_ERROR_STOP=1 -f backend/db/schema.sql
psql ... -f backend/db/funciones_y_triggers.sql
psql ... -f migracionAWS/backend/migrations/077_recrear_triggers_updated_at.sql
psql ... -f backend/db/seed.sql

# 2. Poblar (~10 s)
python scripts/seed_escala.py | psql -h localhost -p 5432 -U postgres -d "HR Karstec" -v ON_ERROR_STOP=1

# 3. PostgREST + roles (ver el docstring de scripts/medir_escala.py)
docker run -d --name rrhh-pgrst -p 3001:3000 -e PGRST_DB_URI="..." ... postgrest/postgrest:v12.2.3

# 4. Medir
$env:PGRST_SERVICE_KEY = "<jwt HS256 con role=service_role>"
python scripts/medir_escala.py              # tiempos por endpoint
python scripts/medir_escala.py --queries    # round trips (detector de N+1)
python scripts/medir_escala.py --urls       # largo de URL vs los techos medidos
```

*HR Karstec · Diagnóstico de escala · 13/8/2026*
