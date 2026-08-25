# SEMILLA-SMOKE — datos de prueba para el recorrido con Capital Humano

> **Qué es:** un sembrador de datos de prueba que escribe **por la API**, y su limpiador, que
> borra exactamente lo sembrado y nada más. Viven en `scripts/semilla_smoke.py` y
> `scripts/limpiar_semilla.py`.
> **Por qué existe:** ocho tablas están en cero y sus pantallas no se pueden probar ni mostrar.

---

## 1. Por qué por la API y no por INSERT

Tres razones, y son las que gobiernan el diseño de todos estos archivos:

1. **Un INSERT se saltea las guardas**, y entonces el smoke prueba filas que el sistema nunca
   habría producido. Es el "padrón del fake" aplicado a producción.
2. **Sembrar por la API ejercita los caminos de escritura.** Varios de estos endpoints (el puente
   candidato→empleado, el import de formación, el panel de atención) nacieron en el bloque A con
   tests verdes y **nunca corrieron contra la base real**. Si algo está roto, aparece acá.
3. **Los estados derivados los calcula el backend**: la `fecha_egreso` y el `motivo_baja` de una
   baja, los `*_anterior` de una recategorización, la `empresa_id` que cada fila hereda de su
   padre. A mano quedan inconsistentes y la pantalla muestra la inconsistencia.

🔴 **El limpiador va por la base, y la asimetría es deliberada.** Ninguna de las tres razones
aplica a un DELETE, y sobre todo **la API no puede borrar**: `empleados`, `costos_nomina`,
`recategorizaciones` y `offboarding_instancias` no tienen endpoint de baja —en recategorizaciones
es una decisión explícita del módulo— y el DELETE de `perfiles_puesto` es una baja LÓGICA.

---

## 2. Cómo se corre

La credencial **nunca va por la línea de comandos**: queda en el historial de PowerShell en texto
plano y sin vencimiento. Va por entorno, o por `scripts/.semilla.env` (ignorado por git).

```powershell
$env:SEMILLA_TOKEN = "eyJ..."      # cómo obtenerlo: docs/SMOKE-TEST.md §"Cómo obtener el token"
# — o —
$env:SEMILLA_USUARIO = "..."; $env:SEMILLA_PASSWORD = "..."   # el script hace el login

backend\venv\Scripts\python.exe scripts\limpiar_semilla.py          # 1. en seco, SIEMPRE primero
backend\venv\Scripts\python.exe scripts\semilla_smoke.py --solo perfiles   # 2. una fase sola
backend\venv\Scripts\python.exe scripts\semilla_smoke.py            # 3. el resto
```

| Flag | Para qué |
|---|---|
| `--base URL` | backend a sembrar. Default: `https://sofia-backend-pi.vercel.app` |
| `--pausa SEG` | espera entre escrituras (default 0.15) |
| `--solo FASE` | una sola fase, repetible |

Fases: `perfiles` · `personas` · **`usuarios`** · `recategorizaciones` · `offboarding` ·
`eventos` · `ausencias` · `vacaciones` · `nomina` · `formacion` · `objetivos` · `vacantes`.

⚠️ **El token dura ~1 hora** y la corrida completa son ~160 requests. Al primer 401 el script
**para** y dice dónde quedó: seguir con una credencial muerta llenaría el reporte de fallos
falsos y dejaría fases con ids a medias. Lo sembrado queda en el manifiesto y no se pierde;
con un token nuevo, las fases ya hechas se saltean solas.

---

## 3. Qué siembra

| # | Qué | Cuánto | Para ver |
|---|---|---|---|
| 1 | Perfiles de puesto | 6 (1 dado de baja) | texto corto y texto largo en la tarjeta; chip inactivo y Reactivar |
| 2 | Preingresos | 4 | entra en 3 días, en 20, HOY (botón Activar) y uno con la fecha ya pasada |
| 3 | Bajas | 3 | hace 2, 10 y 13 meses → la rotación 12m tiene que contar **2**, no 3 |
| 4 | Offboarding en curso | 2 | procesos abiertos sin efectivizar |
| 5 | Recategorizaciones | 6 | tres pares cambiados · solo seniority · con y sin impacto · **dos sobre la misma persona** · **una de este mes** (si no, el KPI del mes dice 0) |
| 6 | Agenda | 5 | 2 en ventana de aviso, 2 fuera, 1 resuelto |
| 6b | **Ausencias** | 5 | **2 en curso hoy** (el KPI cuenta las de hoy) + 3 pasadas, para que el ausentismo del mes deje de ser 0,0%; tipos distintos, una sin justificar |
| 6c | **Vacaciones** | 4 | tomada · planificada · **cancelada** (por `PUT /{id}/cancelar`, no se borra) · un día franco |
| 7 | Costos de nómina | 31 × 2 meses | masa salarial y su variación (el mes actual ~4% arriba) |
| 8 | Formación | 3 cursos + ~20 asignaciones | con colaborador vinculado **y** con `nombre_libre` |
| 9 | Objetivos | 8 (4 anuales, 4 operativos) | los tres estados, con un subobjetivo anidado |
| 10 | Vacantes y candidatos | +4 y +9 | uno en `oferta`+`activo` → habilita **Contratar** |
| 11 | **Usuarios de prueba** | 3 (uno por rol) | entrar con `admin_rrhh`, `gerencia_lectura` y `mandos_medios` — ver §9 |

**Lo que a propósito NO hace:** activar el preingreso que entra hoy. Ese botón tiene que
funcionar **en el recorrido**; apretado por la semilla, la pantalla llega con el caso resuelto y
nadie prueba la guarda de fecha, que es el corazón de `_empleado_activar`.

---

## 4. Idempotencia: correrlo dos veces no duplica nada

Dos capas, y las dos hacen falta (`_semilla_cliente.Cliente.obtener_o_crear`):

1. **El manifiesto** `scripts/.semilla-smoke.json` (fuera de git): el id exacto de cada fila
   creada. Capa rápida, y el registro de qué borrar después.
2. **La clave natural**, para cuando el manifiesto se perdió: antes de crear, se BUSCA la fila
   por su clave en el listado real —el legajo, el nombre del perfil, el título del objetivo— y
   si está, se adopta. Sin esta capa un manifiesto perdido duplicaría todo el padrón sembrado.

Por eso las claves son **constantes** en `_semilla_padron.py` / `_semilla_catalogo.py` y no se
generan al vuelo: un nombre aleatorio haría que la segunda corrida no reconozca nada de la
primera. **Cambiar un nombre después de sembrar deja esa fila huérfana del limpiador.**

---

## 5. Cómo se distingue lo sembrado de lo real

- **Colaboradores:** legajo `SMK-01`…`SMK-09` **y** dominio `@semilla.hrkarstec.site`. Los dos, no
  uno: el legajo es único *por empresa* y el mail lo es en todo el sistema. (Verificado el
  23/8/2026: los 31 colaboradores reales tienen el legajo **vacío**, así que el prefijo no puede
  colisionar con ninguno.)
- **Todo lo que cuelga de un colaborador sembrado** se resuelve por su `empleado_id`.
- **Catálogos** (perfiles, eventos, capacitaciones, objetivos, vacantes): por su nombre o título
  literal. Verificado que no hay intersección con lo real: la única vacante cargada se llama
  *"Analista contable"* y el único objetivo *"búsqueda líder de equipo"*.
- 🔴 **`costos_nomina` SOLO por manifiesto.** Esas filas cuelgan de colaboradores **reales** y una
  tabla de montos no admite marca de agua: nada distingue una fila sembrada de una que cargue
  RRHH en el mismo período, salvo su id. **Sin manifiesto, el limpiador no las toca.**

### 🔴 REGLA — TODO LO QUE EL SMOKE **TIPEA** LLEVA LA MARCA

Lo de arriba es lo que el SCRIPT siembra, y ahí la marca la pone el código. Esto es lo otro: el
smoke con navegador **también escribe en producción**, y ahí quien pone la marca es la persona
que está tipeando. Es una regla, no una costumbre:

> **Todo nombre que el smoke escriba en un formulario arranca con `SMK`, y todo mail que escriba
> termina en `@semilla.hrkarstec.site`. Los dos, siempre, aunque el campo sea opcional y aunque
> la fila se vaya a borrar en cinco minutos.**

Concretamente, campo por campo: nombre y apellido de una persona → `SMK Apellido` · legajo →
`SMK-NN` · email corporativo y personal → `algo@semilla.hrkarstec.site` · título de un objetivo,
nombre de una vacante, de un cliente, de un proyecto, de un ítem de inventario, de una
capacitación, de un evento de agenda → **prefijo `SMK ` y después lo que quieras**.

**LA EVIDENCIA DE QUE ALCANZA, Y ES MEDIDA.** En la corrida del 23-24/8/2026 el smoke creó **6
colaboradores por pantalla**, ninguno anotado en el manifiesto (el manifiesto sólo registra lo
que se siembra por la API). La limpieza los tuvo que encontrar de otra forma, y la clave natural
—el dominio del mail— **cazó 5 de los 6 sola**. El que se escapó es *Sebastián Videla*, con el
email corporativo `"a"`: **el único que se salió de la convención es el único que hubo que
buscar a mano**. No hacía falta un mecanismo nuevo; hacía falta usar el que ya existe.

**POR QUÉ NO HAY UN BARRIDO QUE LO IMPONGA, y no es un pendiente.** Los 45 barridos estructurales
del repo funcionan porque miran CÓDIGO: `test_semilla_alcanza_lo_que_se_escribe.py` puede exigir que
toda tabla en la que el código crea filas esté en `ORDEN` porque las dos cosas están escritas en
archivos. Lo que una persona tipea en un navegador contra producción no está en ningún archivo
—no hay AST de un formulario que alguien llenó— así que ningún test puede verlo. **Esta regla se
sostiene escribiéndola acá y leyéndola antes de correr el smoke**, que es exactamente por lo que
tiene que estar escrita como regla y no quedar como costumbre de quien lo corrió la última vez.

⚠️ **Y si se rompe igual:** lo que quedó sin marca no lo va a encontrar el limpiador. La salida
es la del 24/8 —ir a `storage.objects` y a las tablas a mano, con `created_at` del día del
smoke— y es cara. Anotarlo en el momento en `docs/SMOKE-TEST-RESULTADOS.md` es más barato que
reconstruirlo después.

### La red de seguridad

De las cuatro fases que tocan personas, **dos modifican el legajo** al que apuntan: recategorizar
pisa rol/seniority/categoría y efectivizar escribe `estado='baja'`. Ninguna se deshace con un
DELETE. Por eso las dos pasan por `_semilla_guarda.exigir_sembrado`, que **lee del sistema vivo**
y corta la corrida si el objetivo no lleva el dominio de la semilla — la comprobación no se hace
contra el diccionario en memoria, porque un manifiesto de otra base tendría uuids que acá
apuntan a cualquiera.

**La única fase que escribe sobre colaboradores reales es la de nómina**, y vive sola en
`_semilla_fases_nomina.py` para que la excepción se vea. No los muta: agrega filas en una tabla
hija y borrarlas devuelve el legajo al estado exacto de antes.

---

## 6. Cómo se borra

```powershell
backend\venv\Scripts\python.exe scripts\limpiar_semilla.py         # muestra el plan, no borra
backend\venv\Scripts\python.exe scripts\limpiar_semilla.py --si    # ejecuta
```

El orden de borrado es el de las FKs y no es intercambiable: `costos_nomina.empleado_id` y
`offboarding_instancias.empleado_id` son **ON DELETE RESTRICT**, así que con una sola fila viva de
cualquiera de las dos el DELETE del colaborador falla.

🔴 **Los TRES USUARIOS no se borran: se les REVOCA el acceso, y por la API.** Es el único paso
del limpiador que no va por base. `DELETE /api/usuarios/{id}` hace las dos mitades —`activo=false`
+ **ban permanente en Supabase Auth** (~100 años)— y deja su evento de auditoría. La fila queda y
en `/usuarios` se ven como inactivos, que es lo correcto: **un acceso revocado tiene que verse**.
El porqué completo está en el encabezado de `limpiar_semilla.py` y en `_semilla_baja_usuarios.py`.
Ese paso pide credencial de `admin_rrhh`; si falta, el resto de la limpieza corre igual y el
script termina con código 1 diciendo qué accesos quedaron vivos.

⚠️ **Lo que NO borra por default: los eventos de `auditoria`.** La tabla es inmutable por diseño
en este repo. `--con-auditoria` los borra también. **Es una decisión, no un default**: dejarlos
significa que `/auditoria` va a mostrar el alta de nueve personas que ya no existen.

---

## 7. Casos a probar DELIBERADAMENTE en el smoke de escritura

Cosas que no se descubren solas y que hay que ir a buscar. Se anotan acá y no en
`docs/DEUDA-TECNICA.md` porque todavía no son deuda: son preguntas sin responder.

### 🔴 Editar a alguien dado de baja

**Qué probar:** un `PUT /api/empleados/{id}` sobre alguien con `estado='baja'`, y sobre todo
**registrar una recategorización** sobre esa persona — que es el caso real, porque el write path
de recategorizaciones llama a `update_empleado` para pisar rol/seniority/categoría
(`_recategorizaciones_write.aplicar_al_empleado`).

**Por qué:** no está claro que haya ninguna guarda, y las dos respuestas posibles son un
hallazgo. Si **pasa**, el sistema deja editar el legajo de alguien que ya no trabaja y nadie
decidió que eso estuviera bien. Si **falla**, falla en un camino que hoy nadie ejercita y
probablemente con un 500 en vez de un mensaje.

**Cómo apareció:** la primera versión del orden de sembrado ponía las recategorizaciones
*después* de las bajas, así que lo habríamos descubierto de rebote. Se cambió el orden a
propósito —sembrar y descubrir son objetivos distintos, y para el recorrido con Capital Humano
gana sembrar datos coherentes— y el caso quedó anotado acá para buscarlo aparte. **Un hallazgo
que aparece por accidente del orden de un script es un hallazgo que la próxima vez no aparece.**

> ✅ **RESPONDIDO Y CERRADO EL 23/8/2026 — pasaba, y ahora se rechaza.** Ver abajo el hallazgo
> completo; la guarda vive en `services/_recategorizacion_egreso.py` y **lo que rechaza es lo
> IMPOSIBLE (efectiva después del egreso), no lo retroactivo**: cargar tarde un cambio que sí
> ocurrió mientras la persona trabajaba sigue entrando, que es el caso legítimo y frecuente.
> `fecha_egreso` NULL pasa siempre. Cubierto por cinco tests con mutation check de cuatro
> mutaciones (incluida "rechaza todo lo de alguien de baja", que mata el caso legítimo).
>
> 🔴 **EL HALLAZGO, COMO SE MIDIÓ.** La fase extra de licencias
> sembró una recategorización con fecha de este mes sobre **SMK-07, que ya estaba dado de baja**
> (egreso 2025-07-23). El alta devolvió **201** y además **pisó el legajo de la persona dada de
> baja**: `roles` pasó a `["Jefe de Mantenimiento"]` y `categoria` a `C6`. O sea que el sistema
> acepta **una recategorización con `fecha_efectiva` TRECE MESES POSTERIOR al egreso** y le
> reescribe el puesto a alguien que no trabaja más. No hay guarda de estado en
> `_recategorizaciones_write.crear` — sólo la de empresa.
>
> **Lo decidido:** se rechaza sólo `fecha_efectiva > fecha_egreso`, en el alta Y en el PUT (por
> edición se llegaba a la misma fila prohibida). No se rechaza "sobre alguien de baja", porque
> eso mataría el caso legítimo. El 422 lleva las dos fechas y dice qué hacer.
>
> ⚠️ **El dato sembrado quedó sucio y se reparó a mano:** esa recategorización estaba sobre
> SMK-07, ya dado de baja, así que el dashboard mostraba el bug como si fuera un dato. Se borró
> la fila, se restauró el legajo de SMK-07 con los `*_anterior` que la propia fila registraba
> (la fuente autoritativa) y la semilla la mudó a **SMK-08, que está activo**. Sobre SMK-07 hoy
> ni siquiera correría: la guarda la rechazaría con 422.

---

## 8. Archivos

| Archivo | Qué es |
|---|---|
| `scripts/semilla_smoke.py` | entrada: CLI, contexto y orden de las fases |
| `scripts/_semilla_credencial.py` | de dónde sale el token (nunca de la línea de comandos) |
| `scripts/_semilla_cliente.py` | HTTP, manifiesto e idempotencia |
| `scripts/_semilla_guarda.py` | la red de seguridad sobre colaboradores reales |
| `scripts/_semilla_padron.py` · `_semilla_catalogo.py` | los datos inventados (y el índice de qué borrar) |
| `scripts/_semilla_fases_personas.py` · `_nomina.py` · `_catalogo.py` · `_formacion.py` · `_licencias.py` | las fases |
| `scripts/_semilla_usuarios.py` | los tres usuarios de prueba y a quién tiene a cargo el mando medio |
| `scripts/_semilla_fases_usuarios.py` | la fase: alta, cambio de contraseña y `.smoke.env` |
| `scripts/_semilla_baja_usuarios.py` | la revocación de accesos, por la API (ver §6) |
| `scripts/limpiar_semilla.py` | el limpiador |

---

## 9. Los tres usuarios de prueba (uno por rol)

**Por qué existen:** `docs/SMOKE-TEST.md` declara como su límite más grande que *"los 4 usuarios
de producción son admin_rrhh, así que todo el modelo de permisos se ejercita desde el rol más
amplio"*. Estos tres lo cierran sin tocar ninguna credencial real — que además no se puede: no
sabemos sus contraseñas y resetearlas es intervenir la cuenta de una persona.

| Usuario | Rol | Para qué |
|---|---|---|
| `smk.admin` | `admin_rrhh` | el control contra el que se comparan los otros dos |
| `smk.gerencia` | `gerencia_lectura` | lee todo, toda escritura le da 403 |
| `smk.mando` | `mandos_medios` | solo vacaciones y ausencias, y solo de los suyos |

**Las contraseñas las genera el script** (`secrets`, 20 chars) y **no se imprimen nunca**: van a
`scripts/.smoke.env`, que está en `.gitignore`. 🔴 **Ese archivo es de un solo uso: se borra al
terminar el smoke** (`Remove-Item scripts\.smoke.env`), y lo dice adentro. Borrarlo NO revoca
nada — para eso está el limpiador.

**La jerarquía del mando medio.** `smk.mando` está vinculado a **SMK-10 (Verónica Ledesma)** y
tiene a cargo a **SMK-02, SMK-04, SMK-06 y SMK-08**. Los otros tres con licencias sembradas
—SMK-05, SMK-07 y SMK-09— quedan afuera **a propósito**: son el control. Medido el 23/8/2026:

| Endpoint | admin | mando |
|---|---:|---:|
| `GET /api/ausencias` | 5 | **2** (Carla Zabaleta, Ludmila Sarquís) |
| `GET /api/vacaciones` | 4 | **2** (las mismas) |
| `/empleados`, `/costos/nomina`, `/auditoria`, `/vacantes`, `/objetivos` | 200 | **403** |

🔴 **Los cuatro a cargo son de la MISMA empresa que el jefe, y no es una preferencia.** Un
`manager_id` de otra empresa devuelve **500**: lo rechaza el trigger `trg_emp_empleados`
(migración 094). Eso **contradice** lo que declara `services/_alcance_mandos.py` — está reportado
en `docs/DEUDA-TECNICA.md` §1-quater y no se tocó acá.
