# HANDOFF — lo que no está en el código

> **Para el dev que monta la infraestructura en AWS.** Esto no explica cómo levantar el sistema
> (eso es `docs/DEPLOY.md`) ni qué cambió en cada sesión (eso es `docs/BITACORA-CAMBIOS.md`).
> Esto es **lo que vas a necesitar saber y no vas a poder deducir leyendo los archivos**: por qué
> ciertas cosas están hechas de una forma que parece equivocada, qué se rompe exactamente al
> portear, y qué decisiones quedaron abiertas y no son tuyas.
>
> Verificado contra el código y contra el catálogo vivo el **25/8/2026**.
>
> 🔴 **Si algo de acá no coincide con el código, manda el código.** Este documento se va a
> pudrir; los archivos no.

---

## 1 · La arquitectura en una página

```
                    ┌──────────────────────────────────────┐
   navegador ─────► │  sofia-front  ·  Next.js 16          │
                    │  Vercel, Root Directory `frontend`   │
                    │  www.hrkarstec.site                  │
                    └───────────────┬──────────────────────┘
                                    │  HTTPS · URL ABSOLUTA
                                    │  NEXT_PUBLIC_API_URL (build-time)
                                    ▼
                    ┌──────────────────────────────────────┐
                    │  sofia-backend  ·  FastAPI (Python)  │
                    │  Vercel, Root Directory `backend`    │
                    │                                      │
                    │  AuthMiddleware  → verifica el JWT   │
                    │  SlowAPIMiddleware → rate limit      │
                    │  router → service → repository       │
                    └───┬────────────┬────────────┬────────┘
                        │            │            │
        ┌───────────────┘            │            └──────────────┐
        ▼                            ▼                           ▼
┌────────────────┐        ┌────────────────────┐      ┌──────────────────┐
│   Supabase     │        │    Anthropic       │      │   Google Gmail   │
│                │        │  claude-sonnet-4-6 │      │  OAuth, 1 casilla│
│ · PostgreSQL   │        │  reportes con IA   │      │  lee + envía     │
│ · Auth (JWT)   │        └────────────────────┘      └──────────────────┘
│ · Storage ×3   │
└────────────────┘
```

### Las cinco cosas que hay que entender de ese dibujo

**1 · El front NO habla con la base. Nunca.** Habla sólo con nuestro backend, por una URL
absoluta. No hay cliente de Supabase en el front, ni `NEXT_PUBLIC_SUPABASE_*`. 🔑 **Eso hace que
el cutover sea una sola variable**: `NEXT_PUBLIC_API_URL`. Es build-time, así que cambiarla
exige redeploy del front.

**2 · Son DOS proyectos de Vercel, y el orden de deploy no es opcional.** Backend primero,
`curl /health` → 200, después el front. Si una feature nueva del front tira 404 contra el
backend, salió el front antes: se espera y se reprueba, no se toca código.

**3 · Tres capas, sin excepción: `router → service → repository`.** No hay controllers. 🔴 **Y
sólo `repositories/` habla con la base** — hay un barrido que lo verifica por AST sobre todas las
demás capas (nº 11) con **4 familias de excepción declaradas** (reportes, dashboard, organigrama,
procesos) y un test que impide que pasen de 5. Para vos eso significa una cosa concreta y muy
buena: **el porteo a asyncpg toca `repositories/` y casi nada más.** Son 114 archivos.

**4 · Todo lo que sale al mundo pasa por un punto único**, y cada uno tiene un barrido que lo
sostiene:

| Salida | Punto único | Al portear |
|---|---|---|
| Storage | `integrations/storage.py` — los 3 buckets y las 4 operaciones | 🟢 **Se toca ESTE archivo y ninguno más** para pasar a S3. La API de afuera es neutral: no se ve un `from_()` ni un `signedURL` |
| Mails | `services/mailer/` — expone sólo `enviar_mail` | 🟢 Sin cambios: es Gmail, no Supabase |
| Exports | `services/export/` — expone sólo `build_export` | 🟢 Sin cambios |

**5 · El multiempresa viaja en un header, no en la URL.** `X-Empresa-Id`. Un valor ausente o
`"todas"` significa **vista consolidada**, no "sin permiso". Ver §2.

### Los flags que apagan módulos enteros

Tres módulos están apagados y el código está **entero**: se sacó el punto de entrada, no se borró
nada. Encenderlos es una variable de entorno y **cero cambios de código**.

| Módulo | Flag | Estado |
|---|---|---|
| Assessment | `ASSESSMENT_ENABLED=false` | Apagado porque **no se usa** |
| Link público de horas | `HORAS_PUBLICO_ENABLED=false` | 🔑 **Distinto: no está apagado, está SIN ENCENDER.** Código nuevo, completo y verde, esperando la variable y que RRHH cargue un cliente |
| Sucesión | dos flags en el front | Apagado por producto. **El backend está intacto y montado** |

> 🔴 **Los dos primeros gatean DOS cosas con el mismo flag: el montaje del router Y la lista de
> rutas públicas.** No es redundancia. Si sólo se desmontara el router, dejar sus rutas salteando
> el auth cambiaría el 401 por un 404, y esa diferencia contra el resto de las rutas desconocidas
> delataría que el módulo existe. Apagado, el módulo responde **401 `MISSING_TOKEN`**, que es
> exactamente lo que responde `/api/lo-que-sea`.

---

## 2 · Las decisiones que te van a parecer raras

### 2.1 · No hay RLS, y no es una omisión

Supabase tiene RLS y el sistema **no lo usa como barrera de seguridad**. Todo el backend pega con
la `service_role`, que **ignora RLS por definición**. La seguridad es app-level, en el WHERE de
cada query.

**Por qué:** el destino es RDS, donde no hay Supabase Auth ni `auth.uid()`, así que una barrera
construida sobre RLS habría que reconstruirla entera del otro lado. Se decidió no construirla dos
veces. **La decisión está tomada y cerrada: en AWS no va RLS.**

⚠️ **La consecuencia operativa que sí te toca: la `SUPABASE_SERVICE_KEY` es la llave del reino.**
Cualquier proceso que la tenga lee y escribe todo. En AWS va en **SSM Parameter Store /
Secrets Manager**, nunca en un `.env` en disco ni en una variable de build.

### 2.2 · La barrera de empresa vive en el service layer, no en la base

**La regla:** todo endpoint que recibe un id de recurso de afuera valida que ese recurso sea de
la empresa del request. Preferentemente en el **WHERE de la query** (una sola ida a la base,
imposible de saltear); si el repo no lo acepta, comparando en el service.

**Por qué te lo cuento a vos:** porque es la única barrera que hay. No hay RLS abajo que la
respalde. **Si al portear un repo se te cae un `.eq("empresa_id", ...)`, no falla nada: devuelve
datos de otra empresa, con 200.** Un filtro que desaparece no da error, da resultados de más.

🔴 **Y el falso positivo que ya apareció tres veces: el router pasando `empresa_id` NO PRUEBA
NADA.** Un router que lo recibe y lo pasa a un service que lo acepta y lo ignora se lee perfecto
y no filtra nada. **Auditá de la query hacia arriba, no del router hacia abajo.**

Hay dos barridos que lo sostienen y conviene que los conozcas: el nº 38 verifica que todo
endpoint de escritura con id en el path reciba `Request` (sin `Request` no hay `empresa_id` en
ninguna capa, y el código se lee coherente — encontró un `PUT` de onboarding que con el header de
la empresa A y la instancia de la B devolvía **200 y completaba la tarea ajena**), y el nº 37
lista los 8 endpoints que legítimamente no la aplican.

### 2.3 · "No existe" y "es de otra empresa" devuelven exactamente lo mismo

Mismo status, mismo `code`, mismo mensaje: **404 `EMPLEADO_NOT_FOUND` / "Empleado no
encontrado"**. Nunca un 403.

**Por qué:** un 403 —o un mensaje distinto, o un status distinto— **confirma que el recurso
existe y que es de otro**. Eso es un oráculo de enumeración: con un script y una lista de UUIDs
se releva el padrón ajeno sin leer un solo dato.

🔴 **Y el orden de los gates importa tanto como el status.** La barrera de empresa va **ANTES**
de cualquier chequeo de estado que responda otro código. Caso real: `iniciar_onboarding`
chequeaba "ya tiene onboarding activo" antes de la empresa, así que un empleado de otra empresa
con onboarding activo respondía **409 `ONBOARDING_ALREADY_ACTIVE`** — y ese 409 confirmaba que
existía. **Si reordenás validaciones al portear, esta es la que no se puede mover.**

El mismo criterio rige en otros dos lugares: los cuatro motivos por los que un `state` de OAuth
puede no servir salen por un `AppError` único, y un `X-Empresa-Id` inexistente se descarta **en
silencio**, sin status propio.

### 2.4 · El ownership es fail-closed, y hay una función que lo verifica en runtime

`mandos_medios` sólo ve a los suyos, y "los suyos" es `manager_id` — no el área, no `es_lider`.
Aplica **sólo en VACACIONES y AUSENCIAS**; en el resto de las secciones el gate de permisos lo
frena con 403 antes de cualquier consulta.

🔴 **La excepción que tenés que conocer, porque es la única a la barrera de empresa de todo el
sistema.** Vive en `services/_alcance_mandos.py`, con nombre propio para que se lea como
excepción y no como patrón a copiar. Decisión de producto: **un empleado puede tener superior de
otra empresa del grupo, y para `mandos_medios` el `manager_id` REEMPLAZA al filtro de empresa**,
en lectura y en escritura. Lo justifica que el `manager_id` es un vínculo más fuerte que la
empresa: la empresa dice de qué sociedad cobra alguien, el `manager_id` dice quién responde ante
quién, que es la pregunta que el ownership contesta.

**Y acá está el fail-closed que importa.** Al soltar el `.eq("empresa_id")`, un ownership que
resuelva a "sin restricción" —la tupla `(None, False)`— deja de significar "veo toda mi empresa"
y pasa a significar **"veo la tabla entera de todas las empresas"**. Antes ese bug quedaba
contenido por el filtro de empresa; sin él, es una fuga total.

Por eso **la misma función que suelta la empresa verifica la invariante y falla cerrado**. Los
dos pasos viven juntos a propósito: **no se puede obtener el `empresa_id` aflojado sin pasar por
el chequeo.** Si al portear separás esas dos cosas "para que quede más limpio", estás abriendo
exactamente el agujero que el diseño cierra.

### 2.5 · Auditoría app-level, y por qué un diff excluye en vez de enumerar

No hay triggers de auditoría en la base: se dropearon en la migración 058. La captura es
app-level, con `AuditService.registrar(...)`, que **traga todo error** por diseño (un fallo al
registrar no puede tumbar la operación de negocio).

🔴 **La regla que parece al revés: un diff de UPDATE EXCLUYE campos derivados en vez de ENUMERAR
los que interesan.** Un alta o una baja FOTOGRAFÍAN un estado, y ahí una lista curada alcanza. Un
UPDATE contesta *"¿qué cambió?"*, y ahí **una lista curada MIENTE POR OMISIÓN**: si alguien edita
un campo que no está en la lista, el log dice que no pasó nada. Concreto: la lista curada de
`empleados` cubre 7 campos y la tabla tiene 29 columnas editables más.

Lo que se excluye son los campos **derivados de joins** (`area_nombre`, `empresa_nombre`…), y por
un bug real: el diff comparaba los `*Response` completos, y `prior` salía de un SELECT **con
joins** mientras `nuevo` salía de un UPDATE...RETURNING **sin joins**. Resultado: **93 de 113
eventos de producción eran `area_nombre: "SALUD" → null` y nada más** — cambios que nunca
ocurrieron, afirmados sobre empleados reales.

---

## 3 · Lo que se rompe al portear a asyncpg

> El detalle medido de los cuatro greps de control está en `BARRIDO-PATRONES.md`, de esta misma
> carpeta. Acá va lo que hay que entender antes de mirarlos.

### 3.1 · Los IDs tipados `str` — son 89, pero sólo 4 rompen

`grep` da **89 campos id tipados `str` en `schemas/`**, y la primera reacción es tratarlos como
89 arreglos. **No lo son**, y la distinción es toda la diferencia:

| | Campos | Rompe |
|---|---|---|
| **ENTRADA** — viajan HACIA la base | **4** | 🔴 **Sí.** Con asyncpg, un `str` contra una columna `uuid` es error de query |
| **SALIDA** (`*Response`) | **81** | 🟡 No. El valor sale de la base y se serializa |
| **EXTERNOS** (Google, Supabase Auth) | **4** | ⬜ No son uuid nuestros |

Los cuatro de entrada: `PresupuestoCreate.area_id` (el más caro — único que llega a un INSERT
real de una tabla viva), `ObjetivosFiltros.responsable_id` (va a un WHERE: rompe la lectura), y
dos de assessment, que hoy no tienen camino hasta la base porque el módulo está apagado.

🔑 **El inventario NO sale del grep: sale de `backend/tests/test_ids_tipados.py`**, que hace esa
separación por introspección de Pydantic y tiene guardas de mínimo. Un grep no puede distinguir
entrada de salida. Ese test reemplazó a un grep que veía **38 de 92 campos** (`": str"` no
matchea `Optional[str]`, y `grep _id` no matchea el `id` pelado).

### 3.2 · `maybe_single()` y sus DOS trampas

Esta es la que más caro salió y la que más fácil se repite.

**Trampa 1 — elegir `.single()`.** Con 0 filas **lanza** en vez de devolver `None`, así que el
`return None` de abajo queda inalcanzable y el endpoint da **500 donde el service pretendía
404**. Usar `maybe_single()` salvo que la fila esté garantizada.

**Trampa 2 — la que nadie ve.** `maybe_single().execute()` **devuelve `None` PELADO**, no un
objeto con `.data = None`. Así que elegir bien la primera y escribir `if not res.data:` deja el
MISMO 500, porque `res` es `None` y `res.data` es un `AttributeError`.

```python
res = q.maybe_single().execute()
return res.data if res and res.data else None     # ← `res and`, no sólo `.data`
```

**El alcance era 24 call sites en 16 repos, todos rotos por lo mismo.** El más caro dejaba
`POST /api/offboarding` en **500 permanente** —para toda persona sin offboarding previo, o sea
para el primero de cualquiera— porque su guarda *"¿ya tiene uno activo?"* consulta justo el caso
de 0 filas: **el módulo nunca funcionó en producción**. Se descubrió sembrando datos de prueba,
no con un test.

🔴 **Por qué ningún test lo vio, que es la parte que te sirve a vos:** el doble de Supabase
devolvía `Resp(None)` donde el real devuelve `None`. **El fake no modelaba la única diferencia
que importaba.** Se arregló el fake y se agregó el barrido nº 36.

**Qué significa al portear:** asyncpg tiene su propia versión de esto — `fetchrow()` devuelve
`None` con 0 filas, `fetchval()` devuelve `None`, y ninguno lanza. La forma correcta cambia, así
que **los 24 call sites hay que reescribirlos, no traducirlos mecánicamente.** El barrido nº 36
te va a decir cuáles son.

### 3.3 · El guard del cliente real bajo tests

`integrations/_cliente_real_en_tests.py` hace que el cliente REAL de Supabase **falle ruidoso
bajo pytest, nombrando el módulo que lo pidió**. Existe porque la suite falsea la base módulo por
módulo —**71 archivos, ~172 sitios**— y esa lista se desactualiza sola cuando una función se
mueve de archivo: sin el guard, un test que perdió su parche pega contra producción en silencio.
Escape: `SUPABASE_REAL_EN_TESTS=1`.

🔴 **Qué te toca a vos: cuando reemplaces `supabase_admin` por el pool de asyncpg, este guard hay
que reconstruirlo, no borrarlo.** Si lo sacás, la suite entera pasa a poder pegarle a la base
real y nadie se entera hasta que un test escribe algo.

⚠️ **Efecto lateral, ya pagado una vez:** `calcular_extras` del dashboard toca SEIS módulos y
cada uno importa su propio `supabase_admin`, así que parchear uno solo ya no aísla. Un test que
no neutralice los otros cinco los ve caer contra el guard, entrar en su `_safe` y aparecer en
`errores` — **verde por fuera, roto por dentro**.

### 3.4 · La lista corta de minas ya identificadas

| Mina | Qué hacer |
|---|---|
| asyncpg devuelve **UUID nativos** | `str()` explícito en los mappers, o tipar `UUID` de punta a punta |
| FK `users.id → auth.users(id)` | 🔴 **Dropearla** y poner `DEFAULT gen_random_uuid()`, o no se puede insertar un usuario. `schema.sql` no la declara, a propósito |
| El `ON DELETE CASCADE` contra `auth.users` | **Es lógica de negocio viva**: el rollback del alta de usuario se apoya en él. Hay que reponerlo en la app |
| `passlib` está roto (bcrypt 5.0 sacó `__about__`) | `import bcrypt` directo |
| `schema.sql` **no trae funciones ni triggers** | **46** triggers no internos en producción (**38** `updated_at` + **8** `trg_emp_*`), 0 en el archivo. Se recrean aparte — ver `DEPLOY.md` §2. *(Medido contra el catálogo el 26/8/2026; acá decía 43, que era el conteo de agosto)* |
| `schema.sql` **tampoco trae RLS** | 55 de 55 tablas lo tienen encendido en producción y el archivo no lo declara. **El rebuild en RDS nace sin RLS, que es el resultado correcto pero por omisión.** Ver [`RLS.md`](RLS.md) |
| `ban_duration` de Supabase Auth | No tiene equivalente. La baja blanda de usuarios hay que reconstruirla revocando refresh tokens. 🔑 **La mitad que corta de verdad es `users.activo`, que es una columna nuestra y sobrevive la mudanza** |
| Modelo Anthropic | Que ningún string con fecha sobreviva. Alias sin fecha: `claude-sonnet-4-6` |
| `_BUCKET = "documentos"` hardcodeado en adjuntos | Parametrizar al pasar a S3. El E2E de adjuntos **nunca se ejecutó** por eso mismo |
| `integrations/_http1_workaround.py` | Workaround de `supabase 2.9.1`. **Se borra ENTERO** al actualizar la librería; su condición de salida está escrita adentro |
| Los cuatro techos de tiempo | 🚩 **RE-MEDIR.** Están calibrados contra Vercel. Ver `DEPLOY.md` §3 |

---

## 4 · Los 54 barridos estructurales

**Qué son y por qué te importan.** Son tests que **barren una superficie entera por
introspección o por AST**, no una lista escrita a mano. La propiedad que los hace valiosos: **lo
que se agregue después queda cubierto sin que nadie toque el test.** Y todos llevan **guarda de
mínimo** (`assert len(...) >= N`), sin la cual una extracción rota devolvería 0 elementos y el
barrido pasaría en el vacío — que es el modo de falla que este repo ya pagó cuatro veces.

🔴 **Para el porteo son tu red.** Cuando muevas `repositories/` a asyncpg, los que miran
estructura (acceso a datos, contrato de repos, selects, maybe_single) te van a decir qué se rompió
antes de que lo descubra un usuario.

> ⚠️ **CLAUDE.md los numera 1–54 y esa numeración es la canónica; el conteo "55" que circula
> viene de una sesión que no la recontó.** Los 54 archivos están verificados uno por uno el
> 25/8/2026: existen todos. El **porqué completo de cada uno vive en CLAUDE.md § Tests** — esta
> tabla es el índice, no una segunda copia (dos descripciones del mismo test divergen, y es
> exactamente el modo de falla que este repo documenta).

### Los que nacieron de un bug real — leé estos primero

| # | Barrido | El bug que lo parió |
|---|---|---|
| **36** | `test_maybe_single_guarda.py` | `POST /api/offboarding` en **500 permanente**: el módulo entero inutilizable en producción sin que nadie lo notara. 24 call sites en 16 repos. Ver §3.2 |
| **38** | `test_routers_escritura_request.py` | `PUT /api/onboarding/{id}/tareas/{id}/completar` **completaba la tarea de otra empresa y devolvía 200**. No hay parámetro que seguir: el handler simplemente no tomaba `Request` |
| **42** | `test_auditoria_destructivas.py` | **Un objetivo real de Karstec desapareció sin dejar rastro.** El barrido nº 8 no podía verlo: toma como alcance los módulos que YA emiten algún evento, y objetivos no emitía ninguno |
| **43** | `test_semilla_alcanza_lo_que_se_escribe.py` | El smoke escribe en PRODUCCIÓN. Dejó **86 filas en `reportes_generados`** y **dos archivos huérfanos en Storage** que el limpiador no conocía. Hallazgo de rebote: `DELETE /api/adjuntos/{id}` borra la fila y **deja el objeto en el bucket** — eso se porta tal cual a S3 |
| **33** | `test_espejo_codes_401.py` | `/vacantes` **mandaba al login a un usuario perfectamente autenticado, en cada carga, once días seguidos**: recibía un 401 `GMAIL_TOKEN_EXPIRED` de la casilla del sistema y el interceptor deslogueaba por `status` a secas |
| **3** | `test_selects_repos.py` | **6 de 11 reportes se entregaron "completos" y nunca funcionaron en producción**: pedían columnas inexistentes o embeds ambiguos (PGRST201). Los 799 tests pasaban porque el fake acepta cualquier `select()` |
| **39** | `dropdownMenuLabel.test.tsx` | **El menú de usuario no abría**: Configuración, Cambiar contraseña y Cerrar sesión inalcanzables, y el logout no tiene otra puerta. Un `<DropdownMenuLabel>` fuera de su `Group` **lanza** |
| **45** | `limpiarTodoRestituye.test.ts` | /empleados mostraba **20 filas al entrar y 16 después de "Limpiar todo"**, diciendo "0 filtros activos". 31 campos en 11 módulos estaban así |
| **24** | `loadingSeApaga.test.ts` | La pantalla de proyectos estuvo **caída en producción** por un `finally` perdido al dividir un componente |
| **25** | `pageSize.test.ts` | Dos modales decían "no hay datos" con 31 personas cargadas: pedían `page_size=200` contra un `le=100`, el 422 lo comía un `.catch` |
| **49** | `gatesDePagina.test.ts` | /usuarios rebotaba a `gerencia_lectura` contra el modelo de roles — **y había un test que lo FIJABA**. Un test puede proteger una regresión |
| **21** | `dialog.test.tsx` | Ídem: el test que estaba en su lugar verificaba **lo contrario** y protegía que 20 modales pisaran el `dvh` del primitivo con `90vh` |
| **53** | `test_columnas_empleados.py` | **12 columnas que la base tenía y el schema descartaba en silencio, 7 con dato en producción.** La más cara decide el cupo de vacaciones. Sexta aparición del mismo bug |
| **51** | `test_legajo_ficha_export.py` | La ficha y el export divergían en **11 campos**. El peor modo de falla de un export: se abre, tiene filas, y le faltan columnas |

### El índice completo

| # | Barrido | Qué vigila |
|---|---|---|
| 1 | `test_paridad_list_export.py` | El export acepta los mismos Query que el listado, en las dos direcciones |
| 2 | `test_limite_export.py` | Todo export llama a `verificar_limite_export` (por `inspect.getsource`: importarlo no alcanza) |
| 3 | `test_selects_repos.py` | Todo `select` con embed, validado por AST contra `schema.sql` como lo haría PostgREST |
| 4 | `test_espejo_permisos.py` | `permisos.ts` (front) contra `permisos.py` (backend) |
| 5 | `test_callers_huerfanos.py` | Símbolos que nadie llama; endpoints montados que el front nunca pide |
| 6 | `test_mappers_ejercitados.py` | Todo mapper de repo tiene quien lo ejercite |
| 7 | `test_contrato_repos.py` | La forma que los repos prometen devolver |
| 8 | `test_auditoria_coherente.py` | Los eventos de auditoría son coherentes con lo que el módulo hace |
| 9 | `test_nombres_definidos.py` | No hay nombres usados sin definir |
| 10 | `test_triggers_updated_at.py` | Los **38** triggers `updated_at`, igualdad estricta en las dos direcciones. 🔑 **No compara contra la base: compara `schema.sql` contra la migración 077**, que es lo que lo hace correr sin credenciales |
| 11 | `test_acceso_a_datos.py` | 🔴 **Sólo `repositories/` habla con la base.** 4 familias de excepción, y un test que impide que pasen de 5 |
| 12 | `test_storage_punto_unico.py` | Nadie nombra un bucket ni llama al SDK de Storage fuera de `integrations/storage.py` |
| 13 | `test_columnas_candidatos.py` | Toda columna de `candidatos` está expuesta o declarada — **en las dos direcciones** |
| 14 | `test_columnas_capacitaciones.py` | Ídem, generalizado a 2 tablas, con el concepto de `DERIVADOS` |
| 15 | `test_estado_preingreso_lecturas.py` | Toda comparación contra `empleados.estado`, declarada con su criterio |
| 16 | `test_estado_preingreso_escrituras.py` | Ídem para las escrituras: los 6 caminos con sus guardas |
| 17 | `nav-config.test.ts` | El menú contra el árbol de rutas REAL y contra `permisos.ts` |
| 18 | `barridoFront.test.ts` | Exports de `services/` que ningún componente importa |
| 19 | `contrasteTokens.test.ts` | Ratio WCAG de los 10 pares de la paleta, **en los dos temas** |
| 20 | `barridoSelect.test.ts` | Ningún `<select>` nativo fuera del primitivo (nació migrando 81 en 53 archivos con 29 constantes de estilo copiadas) |
| 21 | `dialog.test.tsx` | Ningún `<DialogContent>` declara su propio `max-h`/`overflow` |
| 22 | `test_ids_tipados.py` | 🔴 **El inventario de ids `str`, separando ENTRADA de SALIDA.** Ver §3.1 |
| 23 | `test_requirements_ascii.py` | Los `requirements*.txt` son ASCII puro (un emoji en un comentario carteleaba `pip install` en Windows) |
| 24 | `loadingSeApaga.test.ts` | Todo estado de carga que se prende se apaga en un `finally` |
| 25 | `pageSize.test.ts` | Ningún pedido supera `MAX_PAGE_SIZE` |
| 26 | `test_claude_md_no_miente.py` | 🔴 Los números que CLAUDE.md AFIRMA contra los que el repo TIENE. **Falla también por no poder medir** |
| 27 | `claudeMdNoMiente.test.ts` | La mitad de front del anterior; mide corriendo `vitest list` |
| 28 | `test_vocabulario.py` | Ningún mensaje al usuario dice "Empleado" ni "Recursos Humanos" |
| 29 | `vocabulario.test.ts` | Ídem en el front, distinguiendo prosa de identificador |
| 30 | `barridoPaginacion.test.ts` | Toda tabla de datos con `total` monta `<Pagination>` |
| 31 | `pantallasPublicas.test.tsx` | Las 4 pantallas de afuera de `(dashboard)`: estados, mensajes por campo, 44px, husos |
| 32 | `decisionesVisuales.test.ts` | 15 decisiones del sistema de diseño, **cada una con su cita del documento** |
| 33 | `test_espejo_codes_401.py` | Todo 401 del backend está decidido del lado del front |
| 34 | `barridoAcordeones.test.ts` | Ningún desplegable nace desplegado (2 excepciones declaradas) |
| 35 | `_destinosKpi.test.ts` | A dónde lleva cada KPI y **quién puede llegar** |
| 36 | `test_maybe_single_guarda.py` | 🔴 Todo `maybe_single().execute()` chequea el OBJETO. Ver §3.2 |
| 37 | `test_inventario_smoke.py` | `INVENTARIO-SMOKE.md` contra el código: 265 endpoints, 46 pantallas, 139 escrituras |
| 38 | `test_routers_escritura_request.py` | 🔴 Todo endpoint de escritura con id en el path recibe `Request` |
| 39 | `dropdownMenuLabel.test.tsx` | Todo `<DropdownMenuLabel>` vive dentro de un `<Group>` |
| 40 | `fieldError.test.tsx` | El mensaje por campo lo pinta un solo primitivo (estaba a mano en 44 lugares con 3 tamaños) |
| 41 | `barridoTarjetas.test.ts` | Toda tarjeta lleva el movimiento del sistema de diseño y lo saca del primitivo |
| 42 | `test_auditoria_destructivas.py` | 🔴 Toda escritura que BORRA FÍSICAMENTE emite un evento |
| 43 | `test_semilla_alcanza_lo_que_se_escribe.py` | 🔴 Toda tabla donde el código puede crear filas la conoce el limpiador. **Incluye buckets** |
| 44 | `barridoConfirmacion.test.ts` | Toda acción que borra pasa por `<ConfirmDialog>` (el eje es el verbo HTTP, no el texto del botón) |
| 45 | `limpiarTodoRestituye.test.ts` | Un filtro con valor SIEMPRE tiene su chip, aunque su catálogo esté vacío |
| 46 | `barridoEmpresaConcreta.test.ts` | Toda acción que exige empresa concreta está bloqueada en consolidado, **con el motivo a la vista**. 🔑 Lee `backend/routers/*.py` en vez de duplicar la lista |
| 47 | `barridoAvisoGuardado.test.ts` | Todo modal confirma cuando el guardado sale bien (29 de 30 no lo hacían) |
| 48 | `barridoCatalogosGateados.test.ts` | Nadie pide un catálogo que su rol no puede leer (`mandos_medios` disparaba un 403 por navegación) |
| 49 | `gatesDePagina.test.ts` | Ninguna página decide sola quién entra |
| 50 | `barridoTouchTarget.test.ts` | Ningún control baja de 44px en pantalla chica (97 controles en 8 pantallas; el más chico medía 24) |
| 51 | `test_legajo_ficha_export.py` | El export de empleados es un SUPERCONJUNTO de la ficha |
| 52 | `test_marca_un_solo_lugar.py` | El nombre de la plataforma se escribe en un solo lugar por lado |
| 53 | `test_columnas_empleados.py` | 🔴 Toda columna de `empleados` está expuesta o declarada |
| 54 | `test_filtros_publicados_sin_ui.py` | Todo filtro que un endpoint acepta, o lo manda el front, o está declarado |

> 🚨 **La regla transversal que explica por qué estos barridos existen y por qué son así:**
> *un test sólo prueba lo que el fake puede desmentir*. Antes de dar un test por bueno hay que
> poder contestar **"¿qué tendría que ser distinto en el fake para que este test pueda fallar?"**.
> Pasó cinco veces documentadas en este repo: un fake que aceptaba `empresa_id` y lo ignoraba (la
> barrera de empresa entera sin probar), uno que ordenaba en Python (sacarle el `.order()` real
> dejaba todo en verde), uno que devolvía `Resp(None)` donde el real devuelve `None`… **Si al
> portear escribís dobles nuevos para asyncpg, esta es la pregunta que hay que contestar en el
> docstring de cada uno.**

---

## 5 · Lo que queda abierto — decisiones de Karstec, no técnicas

> 🔴 **Ninguna de estas cinco se resuelve programando.** Están acá para que sepas que existen y
> para que no las decidas vos de rebote al portear.

### 5.1 · La casilla del sistema está en un Gmail personal

Todos los mails del sistema salen de **una casilla designada**, no de la cuenta del que aprieta
el botón. Eso es correcto y está decidido (un proceso automático no tiene un `user_id` que
aportar, y así el circuito de prueba y el real son el mismo).

🔴 **Lo que no está decidido es cuál casilla.** Si es un Gmail personal en vez de una cuenta de
Google Workspace del dominio, hay tres consecuencias concretas:

1. La OAuth consent screen tiene que ser **External**, y mientras la app esté en **Testing** el
   `refresh_token` **caduca a los 7 días**. Alguien tiene que reconectar cada semana, y no hay
   ningún aviso: el síntoma es que los mails dejan de salir.
2. Los mails salen desde una dirección personal, con lo que eso comunica a un candidato.
3. **Si esa persona se va de la empresa, se va la casilla** — y con ella el historial de
   recepción de candidatos.

**La salida es una cuenta de Workspace del dominio** (consent screen Internal, sin caducidad de 7
días, y la casilla sobrevive a las personas). Es una compra y una decisión de Karstec.

### 5.2 · Unificar las 12 áreas en 7

Hoy hay **14 áreas** en producción (10 + 4 entre las dos sociedades), de las cuales **2 son de la
semilla del smoke**: 12 reales, repartidas de forma muy despareja. Capital Humano planteó
unificarlas en 7.

**Por qué no es un rename y por qué no lo puede decidir un dev:** el área es el eje de agrupación
de **reportes, filtros, ownership y organigrama**. Unificar dos áreas fusiona sus históricos, y
las series de meses anteriores pasan a contar distinto sin que nada lo diga en pantalla.

⚠️ **Y hay un detalle técnico que conviene resolver en la misma tanda:** `areas.codigo` es
**GLOBAL, sin empresa** — dos sociedades que quieran un área con el mismo código chocan, y el
operador no tiene forma de saber que el código lo tomó la otra. Hoy es teórico (los 14 códigos
están en NULL), pero se vuelve real justo el día que alguien ordene los códigos.

### 5.3 · Qué auditar en el CRUD de objetivos

El módulo de objetivos **borraba desde la UI sin dejar ningún rastro**, hasta que un objetivo
real desapareció. Ya se le cablearon los cuatro eventos del CRUD y nació el barrido nº 42.

🔴 **Lo que queda abierto es de producto, no de código: qué campos entran en el diff.** Objetivos
tiene texto largo, progreso que se toca seguido y un árbol padre/hijo. Auditar todo hace un log
ilegible; auditar una lista curada **miente por omisión** (ver §2.5). **Nadie definió el criterio,
y hasta que se defina el diff registra de más.**

⚠️ Anexo del mismo módulo, por si te cruzás con él: **`objetivos` es la única lista del sistema
que no pagina**, y su wrapper `{items, total, page, ...}` ya tiene la forma final. El front está
escrito contra el wrapper a propósito, para que el día que se pagine **no cambie una sola línea**.

### 5.4 · El trigger de base contradice lo que el service declara soportar

🔴 **Ésta es la más importante de las cinco para vos, porque la vas a chocar al reconstruir la
base.**

`services/_alcance_mandos.py` declara, como decisión de producto cerrada: **"un empleado puede
tener superior de otra empresa del grupo"** (§2.4).

Pero en la base hay un trigger que lo **prohíbe**:

```sql
-- migrations/094_recrear_triggers_empresa.sql
CREATE TRIGGER trg_emp_empleados ... ON public.empleados
  FOR EACH ROW EXECUTE FUNCTION public.fn_misma_empresa('area_id','areas','manager_id','empleados');
```

`fn_misma_empresa` verifica que el registro y las filas que referencia sean de la MISMA empresa.
Con ese trigger vivo, **asignarle a alguien un `manager_id` de otra sociedad falla**. O sea: el
service layer soporta un caso que la base rechaza.

**Hoy no se nota** porque nadie cargó un manager cruzado. Medido contra el catálogo vivo el
**26/8/2026**, ya sin la semilla: **11 de 31** empleados tienen manager (antes de limpiar eran
15 de 41, contando los 10 sembrados) y **los 11 lo tienen en su propia sociedad — cero cruzados**,
verificado con un join de `empleados` contra sí misma comparando `empresa_id`. Se va a notar el
primer día que RRHH intente cargarlo, y el error va a venir de la base con un mensaje que no dice
nada de todo esto.

**Las dos salidas, y hay que elegir una a conciencia:**

| | Consecuencia |
|---|---|
| **Sacar `manager_id` del trigger** | El modelo pasa a soportar de verdad lo que declara. Se pierde la única defensa a nivel base contra ese cruce puntual — pero el resto de los pares del trigger quedan |
| **Dejar el trigger y revertir la decisión de producto** | El `manager_id` vuelve a ser intra-empresa, y hay que reescribir `_alcance_mandos.py`, que es el módulo más delicado del sistema |

🔑 **Y un dato que hace la decisión menos abstracta:** `fn_misma_empresa` y sus 8 triggers son la
**única** defensa a nivel base contra el cruce de empresas por referencia, y **no están en
`schema.sql`** (que no trae funciones ni triggers). De los 12 pares que vigilan, **cero tienen FK
compuesta que los respalde**. Si se levantan sin ellos, esa defensa desaparece en silencio.

### 5.5 · La rotación se cuenta distinto en dos pantallas

El KPI del dashboard cuenta bajas por `empleados.fecha_egreso`; el reporte R6 las cuenta por
filas de `offboarding_instancias`. **El del KPI es el criterio correcto** —el import de nómina da
de baja **sin crear instancia**, así que R6 no ve esa vía— pero unificar R6 no es cambiar la
query: el reporte desagrega por `motivo_egreso`, que vive en la instancia, mientras el legajo
tiene su propio `motivo_baja`. **Es una decisión de producto.**

Hoy es invisible: `offboarding_instancias` está en **0 filas**, medido contra el catálogo vivo el
**26/8/2026** después de correr el limpiador. Es exactamente la forma en que la masa salarial
duplicada pasó meses sin que nadie lo notara.

> ⚠️ **Y estuvo visible unos días, que es el dato que hace la advertencia concreta.** El mismo
> 26/8, ANTES de limpiar, la tabla tenía **5 filas**, las cinco sobre colaboradores de la semilla
> del smoke; el limpiador se las llevó a las cinco. O sea que la divergencia entre el KPI y R6
> **sí se ve en cuanto la tabla tiene filas**, y va a volver a verse el día que RRHH cargue el
> primer offboarding real — con la diferencia de que esa vez los datos van a ser reales y nadie
> va a poder atribuirle el desvío a la semilla.

---

## 6 · Los tres usuarios de prueba — ✅ YA ESTÁN REVOCADOS (26/8/2026)

La semilla del smoke creó **tres usuarios reales en producción**, uno por rol, con contraseñas
conocidas y guardadas en texto plano en `scripts/.smoke.env`. **Los tres están revocados desde el
26/8/2026** — esto ya no es una tarea pendiente, es el estado del sistema:

| Usuario | Rol | Para qué existía | Estado |
|---|---|---|---|
| `mariano.delvalle@semilla.hrkarstec.site` | `admin_rrhh` | El rol que puede todo: el control contra el que se comparan los otros dos | 🔒 revocado |
| `silvina.achaval@semilla.hrkarstec.site` | `gerencia_lectura` | Lee todo y no escribe nada: toda escritura tiene que darle 403 | 🔒 revocado |
| `veronica.ledesma@semilla.hrkarstec.site` | `mandos_medios` | Sólo VACACIONES y AUSENCIAS, y sólo de los suyos | 🔒 revocado |

El dominio `@semilla.hrkarstec.site` es la marca de agua de la semilla; **no hay ningún otro
usuario con ese dominio** (verificado contra el catálogo, junto con los 6 usuarios reales, que
quedaron todos `activo=true`).

**Verificado contra el catálogo vivo el 26/8/2026, las tres mitades:**

- `users.activo = false` en los tres.
- **Ban en Supabase Auth en los tres** — `auth.users.banned_until` en **2126**, o sea permanente
  en cualquier sentido que importe.
- **Tres eventos `baja_usuario` en `auditoria`**, con `accion=DELETE`, todos del 26/8 16:10 UTC.
  Son la razón por la que la tabla pasó de 523 a **526 filas**.

**Cómo se revocaron:** los revocó `scripts/limpiar_semilla.py --si` (§7), que para ellos usa
`DELETE /api/usuarios/{id}` — **por la API y no por base, a propósito**: un DELETE desde el script
borraría sin dejar rastro en la auditoría, que es justo lo que no se quiere de un usuario con
acceso. Los tres eventos de arriba son esa decisión funcionando.

⚠️ **Es una baja BLANDA y está bien que lo sea.** Deja la fila y pone `activo=false` **+ el ban
en Supabase Auth**. En `/usuarios` se ven como inactivos, que es lo correcto: **un acceso revocado
tiene que verse.** Un usuario que desaparece de la pantalla es un usuario que nadie puede auditar.

- El `activo=false` corta la API. El ban corta el login **y** el refresh.
- 🔴 **LO ÚNICO QUE QUEDA VIVO DE ESTE PUNTO, Y ES PARA VOS: `ban_duration` no existe en RDS.**
  Después de la mudanza, de las dos mitades sobrevive sólo `users.activo`, que es una columna
  nuestra; el `banned_until` de `auth.users` se queda en Supabase junto con `auth`. **El ban hay
  que reconstruirlo revocando los refresh tokens** (`migracionAWS/token_repo_NEW`), o los tres
  vuelven a poder renovar sesión el día del cutover. 🔑 **Es un riesgo de MIGRACIÓN, no de hoy:**
  hoy están cortados por las dos vías.
- ✅ **`scripts/.smoke.env` ya no existe** — era el único archivo del repo con las tres
  contraseñas en claro, y estaba gitignoreado. (No confundir con `scripts/.semilla.env`, que sigue
  ahí y es otra cosa: la credencial de `admin_rrhh` para correr los scripts, también gitignoreada.)

---

## 7 · La semilla: cómo se borra y qué queda después

```bash
python scripts/limpiar_semilla.py        # SÓLO muestra el plan, no borra nada
python scripts/limpiar_semilla.py --si   # ejecuta
python scripts/limpiar_semilla.py --si --con-auditoria
```

✅ **CORRIÓ EL 26/8/2026 Y LA SEMILLA ESTÁ BORRADA, verificada tabla por tabla contra el
catálogo vivo.** Hasta ese día este párrafo decía *"al 25/8 la semilla sigue entera y no se corrió
nunca el limpiador"*, y era cierto: había **10 colaboradores sembrados, 3 usuarios de prueba, 2
áreas `SMK ·` y 2 proyectos `SMK ·`**. Ya no queda ninguno de los cuatro grupos. Los tres usuarios
quedaron revocados, no borrados (§6, que es el comportamiento correcto y está explicado ahí).

**Cómo distingue lo sembrado de lo real — dos capas, y el plan es la UNIÓN:**

1. **El manifiesto**: el id exacto de cada fila creada. Es la única capa que sirve para
   `costos_nomina`, porque esas filas cuelgan de colaboradores **reales** y una tabla de montos
   no admite marca de agua.
2. **La clave natural**, para cuando el manifiesto se perdió: el legajo `SMK-xx`, el dominio
   `@semilla.hrkarstec.site`, y el prefijo `SMK ·` en los nombres de catálogo.

Se unen y no se elige una: un manifiesto incompleto (una corrida cortada) igual limpia todo, y
una clave natural que no encuentre nada no deja filas sin dueño.

⚠️ **`periodos_cerrados` es el único recurso sin nombre propio** — un período es un rango de
fechas y nada más— así que su clave natural son las fechas literales: **enero de 2019**, elegidas
para que ninguna carga real pueda coincidir. Si algún día RRHH cierra enero de 2019, el limpiador
se lo borraría.

### Qué queda después de correrlo

| Queda | Detalle |
|---|---|
| **Los 3 usuarios de prueba, como INACTIVOS** | Baja blanda, no borrado: `activo=false` + ban en Auth + 3 eventos en `auditoria`. ✅ Hecho el 26/8. Ver §6 |
| **Los eventos de `auditoria`** | 🔴 **La tabla es INMUTABLE por diseño en este repo.** Sin `--con-auditoria`, /auditoria va a mostrar el alta de diez personas que ya no existen. Con el flag, se borran los eventos que apuntan a lo sembrado |
| **Lo que cargó RRHH de verdad** | Los 31 colaboradores reales, la vacante real, el objetivo real, los 4 clientes, las 12 áreas reales |

### 🔴 Y lo que hay que decirle a quien mire el dashboard después

**`costos_nomina` está en 0 y con eso la mitad del dashboard está en el estado sin datos**
(medido el 26/8/2026, después de limpiar). Antes de limpiar tenía **62 filas, todas sembradas**:
o sea que el dashboard con datos que se vio esos días era la semilla, no carga de RRHH.

**Qué se va a ver vacío o en cero, y NO es un bug:**

- **"Masa salarial del mes"** → $0, y **"variación" va a decir "sin base de comparación"**, no
  "+0%". Eso también es correcto: `masa_salarial_variacion_pct` es `Optional` y vale `None`
  cuando el mes anterior no tiene nada — antes decía `0.0`, o sea que la pantalla AFIRMABA que la
  masa no cambió sobre un dato inexistente.
- **El historial salarial** de cada ficha → vacío. 🔑 **La serie de `costos_nomina` ES el
  historial** (la tabla tiene `UNIQUE (empleado_id, anio, mes)`, o sea una fila por mes): la
  feature está entera, el dato no existe.
- **El reporte de masa salarial (R5) y el de presupuesto vs real** → sin filas.
- **`/costos`** → la planilla vacía.

🚩 **Decílo ANTES de cualquier recorrido, porque la pantalla se ve exactamente igual que cuando
el reporte estaba roto.** El repo ya pagó esa confusión: seis reportes se entregaron como
"completos" habiendo estado rotos en producción desde el día uno, y el síntoma era el mismo — una
pantalla en blanco.

Lo mismo con otras dos cosas que van a leerse como bugs y no lo son:

- **`seniority` cargado en 3 de 31** (medido el 26/8 sin la semilla). "Distribución de plantilla"
  va a decir **"Sin especificar: 28"**, y esa vez va a ser el dato correcto. Ídem `categoria`
  (**2 de 31** → "Sin especificar: 29"). ⚠️ Acá decía "13 de 41" y "12 de 41", que era la
  medición CON la semilla: los 10 sembrados venían con los dos campos cargados. El
  "Sin especificar: 28" da igual por coincidencia (41−13 = 31−3), así que **el error no se
  notaba mirando la pantalla** — hubo que ir al catálogo.
- **Con 31 colaboradores y un proyecto que concentra 13, casi todo filtro devuelve casi todo.**
  No es un filtro roto: es el reparto real de la gente.

---

## 8 · Qué leer, y en qué orden

| Si necesitás… | Andá a |
|---|---|
| **Levantar el sistema** | `docs/DEPLOY.md` — §0 desde cero, §6 Google Cloud, §7 migración fallida |
| **Las variables de entorno** | `.env.example` en la raíz — completo, con build-time marcado |
| **Los 4 greps de porteo, medidos** | `docs/handoff-aws/BARRIDO-PATRONES.md` |
| **El schema real** | `backend/db/schema.sql` — 🔴 **la única fuente de verdad**, leída del catálogo |
| **Qué cambió y qué te afecta, por sesión** | `docs/BITACORA-CAMBIOS.md` |
| **Qué endpoints y pantallas existen** | `docs/INVENTARIO-SMOKE.md` — generado, no escrito |
| **Por qué se decidió cada cosa** | `docs/DECISIONES.md` y `CLAUDE.md` |
| **Qué está roto y declarado** | `docs/DEUDA-TECNICA.md` |
| **El código nuevo de asyncpg** | `migracionAWS/` — repos-molde, auth completo, migraciones 075-077 |

> ⚠️ **Los tres documentos que dejó el dev de infra anterior** (`COMPARATIVA_VERCEL_SUPABASE_VS_AWS.md`,
> `PATRONES_CODIGO_AWS.md`, `README-DEV.md`) son **CONTEXTO de decisiones ya tomadas, NO
> instrucciones a ejecutar.** Su checklist de 50 ítems no se corre, y **no se hace refactor
> preventivo para parecerse a sus patrones**: el código existente manda.
