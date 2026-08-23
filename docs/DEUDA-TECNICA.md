# Deuda técnica — relevamiento verificado

> **2/8/2026.** Todo verificado contra el **código** y el **catálogo vivo de producción**
> (`grmdiwxcvcjorlohpwji`), no contra la documentación.
>
> ✅ **ACTUALIZADO tras la tanda de limpieza del mismo día.** Lo cerrado quedó tachado en su
> lugar, con el motivo — **no se borró**: una lista que solo muestra lo pendiente pierde la única
> forma de saber si un ítem se cerró o se olvidó. Ver el resumen al final.
>
> Gravedad: 🔴 rompe o expone datos · 🟠 va a romper · 🟡 fricción · ⬜ cosmético
> Esfuerzo: S ≤1 h · M 1-3 h · L >3 h

---

## 0.bis 🔴 LO QUE DEJÓ ABIERTO LA TANDA DE KPIs DEL DASHBOARD (21/8/2026)

Backend puro: los diez KPIs de `SISTEMA-DE-DISENO.md` §6 quedaron calculados. Lo que sigue
abierto son **tres divergencias entre superficies** y **una tarea de front con fecha**.

| # | Qué | Gravedad · esfuerzo |
|---|---|---|
| 1 | ~~**El front lee `kpis.costo_nomina`, que ya no existe.**~~ ✅ **CERRADO el 21/8/2026** con la tanda del dashboard: `services/dashboard.ts` re-sincronizado campo por campo, `formatVariacion` toma `number \| null`, y `_kpisDashboard.test.ts` monta el payload en un Proxy que revienta al leer una clave que el backend no manda. **Lo que NO se cerró es la causa** — ver §0.ter. | ✅ |
| 2 | **Rotación: el dashboard y el reporte R6 cuentan distinto.** KPI = bajas por `empleados.fecha_egreso`; R6 = filas de `offboarding_instancias` imputadas por `created_at`. El criterio del KPI es el correcto (el import de nómina da de baja sin crear instancia), pero unificar R6 no es cambiar la query: el reporte desagrega por `motivo_egreso`, que vive en la instancia, y el legajo tiene su propio `motivo_baja`. **Decisión de producto.** Hoy invisible: `offboarding_instancias` tiene 0 filas. | 🟠 · M |
| 3 | **"Total nómina" significa dos cosas.** Dashboard = `costos_nomina.total` (costo laboral). `/costos` (`costo_service.get_dashboard_costos`) = Σ `salario_bruto`. Cada una es defendible sola; comparadas dan números distintos del mismo mes. | 🟠 · S-M |
| 4 | **La antigüedad se calcula sobre `fecha_ingreso`, no sobre `fecha_ingreso_reconocida`.** La reconocida es mejor respuesta a efectos de convenio pero está en **10/31** (catálogo vivo, 21/8/2026): preferirla mezclaría dos criterios en el mismo promedio según quién la tenga cargada. Disparador para revisarlo: que RRHH la complete. | ⬜ · S |

⚠️ **Y una consecuencia de arquitectura que ya mordió una vez:** `calcular_extras` cablea SEIS
módulos, cada uno con su propio `supabase_admin`. Un test que la llame y parchee solo el de
`_dashboard_kpis` deja a los otros cinco pegándole al guard de `_cliente_real_en_tests`, que cae
en el `_safe` por KPI y aparece en `errores` — el test pasa y el barrido cubre menos de lo que
dice. Moldes de cómo se resuelve: `_sin_los_otros_kpis` (`tests/test_dashboard_kpis.py`) y la
lista `MODULOS` de `tests/test_reportes_columnas.py`, que además valida los selects nuevos contra
`db/schema.sql`.

---

## 0.ter 🔴 EL ESPEJO TS ↔ PYDANTIC NO TIENE TEST — propuesta, con lo que costaría

**El dato que la justifica: cuatro divergencias en un mes, y ninguna la vio `tsc`.**

| # | Qué pasó | Cómo se descubrió |
|---|---|---|
| 1 | `candidatos.estado` | a mano |
| 2 | `fecha_egreso` / `motivo_baja` | a mano |
| 3 | `kpis.costo_nomina` — el backend borró el campo, el front lo siguió declarando y pintando | a mano, un día después |
| 4 | **`kpis_extra.errores` — existe en el backend desde la Sesión 5 y el front NUNCA lo declaró.** El fail-safe por KPI devuelve el vacío del campo y lo anota ahí; sin leerlo, **un KPI caído se pinta como un cero medido**. | 21/8/2026, al sincronizar campo por campo |

🔴 **El 4 es el que muestra el tamaño real del problema:** no es "el backend cambió y el front
quedó viejo" —eso se nota— sino **un campo que nunca se copió**, que no rompe nada, que no
aparece en ningún diff, y que estuvo mintiendo en pantalla desde que nació.

**`tsc` no puede verlo, y no es una limitación que se pueda ajustar:** la interfaz de
`services/*.ts` es una AFIRMACIÓN del front sobre lo que llega, no una lectura del contrato. Si
la afirmación es falsa, TypeScript verifica el código contra la mentira y da todo por bueno.

### La propuesta — `tests/test_espejo_schemas_ts.py` (backend, pytest)

Molde exacto: **`tests/test_espejo_permisos.py`**, que ya hace esto mismo con `permisos.ts` ↔
`permisos.py` y funciona desde hace meses. Mecánica:

1. **Lado Pydantic: gratis y exacto.** `Modelo.model_fields` da nombres, anotación y si tiene
   default. Es lo que ya hace `tests/test_ids_tipados.py`.
2. **Lado TS: un parser de línea, no un AST.** Las interfaces de `services/*.ts` son planas y
   con un campo por línea; alcanza con leer `export interface X {` … `}` y partir cada línea en
   `nombre` / `tipo`. Va en un helper `tests/_interfaces_ts.py` (~40 líneas, límite 200).
3. **Una tabla de PARES declarada a mano, una sola vez**, porque los nombres difieren
   (`KPIResponse` ↔ `KPIDashboard`). Cada entrada lleva archivo + interfaz + modelo.
4. **Se comparan DOS cosas y ninguna más:** el conjunto de nombres **en las dos direcciones**
   (de más y de menos), y la **nulabilidad** (`Optional[X]` / default `None` ↔ `| null` o `?`).
   Los tipos profundos (int vs number, listas anidadas) **no**: los cuatro casos reales fueron
   campo ausente o nulabilidad, y comparar tipos exige un mapa de equivalencias que se vuelve
   otra cosa que mantener.
5. **Guardas contra el falso verde**, las de siempre: mínimo de pares y de campos; y una
   interfaz que el parser NO pueda encontrar es **ROJO, nunca salteo** — el modo de falla que
   este repo ya pagó cuatro veces este mes es justamente el control que deja de matchear y pasa.

**Costo:** ~120-150 líneas de test + ~40 de helper. **2-3 h** incluyendo declarar los pares.
Arrancaría por los tres espejos que ya mordieron (`dashboard`, `empleado`, `candidato`) y crece
de a uno; no hace falta declarar los ~30 de una.

**Riesgo asumido:** el parser es sobre texto. Un campo escrito en una línea rara, un `extends` o
un genérico lo dejan ciego — por eso la guarda del punto 5 convierte "no pude parsear" en rojo.

**El endgame, que NO es esto:** generar los tipos del front desde el OpenAPI que FastAPI ya
publica (`openapi-typescript`). Ahí el espejo deja de existir en vez de vigilarse. Cuesta una
dependencia, un paso de build y tocar todos los `services/*.ts`, así que es tarea propia — pero
es la que hay que hacer, y este barrido es el puente hasta entonces.

---

## 0. 🔴 CIERRE DEL BLOQUE A (19/8/2026) — la lista con la que arranca el frontend

El bloque A (backend) cerró con A3.3. El frontend arranca de acá: todo lo que sigue es backend
listo esperando UI, deuda de línea identificada, o una decisión de producto que el código no
puede tomar solo.

### Endpoints con backend y sin botón

| Endpoint | Sesión | Qué hace | Declarado en `test_callers_huerfanos.py` |
|---|---|---|---|
| `POST /api/candidatos/{id}/contratar` | A4.2 | Candidato en oferta → legajo en `preingreso` | sí, con disparador |
| `POST /api/empleados/{id}/activar` | A3.2 | `preingreso` → `activo`, valida `fecha_ingreso` no futura | sí, con disparador |
| `POST /api/offboarding/{instancia_id}/efectivizar` | previa a A3 | Baja EFECTIVA + cierre de instancia | sí, con disparador |
| `GET /api/dashboard/atencion` | A6 | Panel "Requiere tu atención" — calculadas + manuales | sí, con disparador |
| `POST /api/dashboard/atencion/resolver` | A6 | Resuelve una alerta MANUAL (409 si es calculada) | sí, con disparador |
| `POST /api/importacion/formacion/preview` | A5 | Preview del Excel de Formación | sí, con disparador |
| `POST /api/importacion/formacion/confirmar` | A5 | Confirma el import — catálogo + asignaciones | sí, con disparador |

Los siete tienen tests por HTTP verdes y están montados; ninguno es público. El disparador de
cada declaración en `_ENDPOINTS_SIN_FRONT` es "sale de la lista cuando `frontend/` lo llame" —
son literalmente los puntos de entrada del bloque B.

### Archivos en el techo — el corte va PRIMERO la próxima vez que se toquen

| Archivo | Líneas/límite | Qué falta para cortar |
|---|---|---|
| `registro_routers.py` | **197/200** | El próximo router nuevo (no un endpoint en uno existente) exige dividir esto primero. Molde pendiente de elegir: por dominio (routers de escritura/lectura ya separan así en varios módulos) o por familia (importación, dashboard, etc.). A6 y A3.3 evitaron el problema montando en routers existentes con aire — no va a ser posible indefinidamente. |
| `routers/capacitaciones.py` | 78/80 | El próximo endpoint del catálogo de Formación (no de import: eso ya salió por su propio router) exige el corte lecturas/escrituras, molde `eventos_agenda.py` / `eventos_agenda_escrituras.py`. |
| `repositories/asignacion_repo.py` | 95/100 | El próximo método de asignaciones de formación. Molde de corte: `_asignacion_row.py` (ya existe, es el satélite de mapeo) — el próximo corte sería un segundo satélite o mover escrituras, como se hizo con `evento_agenda_repo.py`. |
| `services/reporte_service.py` | 143/150 | El próximo reporte del catálogo. Molde: extraer el dispatcher a `reporte_generators.py` más generadores, patrón ya usado por `services/reportes/`. |

### Decisiones de producto que quedaron abiertas (el código no las puede tomar solo)

1. **"Vacaciones sin resolver" no existe como dato** (A6). `solicitudes_vacaciones` no tiene
   estado de aprobación — sus columnas son fechas, `dias`, `cancelada`, `tipo`, `periodo`,
   `dias_liquidados`; el "estado" que muestran las pantallas se DERIVA del calendario. El
   sistema de diseño promete la tercera alerta calculada sobre un modelo que no la tiene.
   Salidas sin decidir: (a) construir un flujo de aprobación — revierte la decisión de producto
   original de "sin flujos de aprobación"; (b) reinterpretar la alerta sobre `vacaciones_pendientes`
   (saldos adeudados por período, hoy 0 filas — otro significado); (c) sacarla del diseño.
2. **La recertificación anual de Formación está bloqueada para las filas CON empleado** (A5.1/A5.2).
   `UNIQUE (capacitacion_id, empleado_id)` no lleva el año: la misma persona en el mismo curso
   dos años seguidos es un duplicado para la base. `ux_ec_nombre_libre` sí lleva año+mes, pero
   solo rige `WHERE empleado_id IS NULL`. Hoy no choca (el Excel real de 2026 no tiene el caso);
   el import de 2027 sí. Es DDL (sumar el año a la clave, o una parcial equivalente) — decidir
   junto con quien defina el ciclo de recertificación, no como una migración técnica suelta.
3. **`tipo_contrato` no viaja en el puente candidato→empleado** (A4.2). `EmpleadoCreate` lo
   acepta pero `_candidato_contratar_mapeo.py` no lo completa desde ningún campo de `candidatos`
   ni de `vacantes` — la vacante SÍ tiene `tipo_contrato` (mismo vocabulario que `empleados`,
   verificado en su momento), así que técnicamente es mapeable, pero no se mapeó porque no
   estaba pedido y una decisión de "¿el contrato de la vacante es el contrato real, o RRHH lo
   define recién al contratar?" no es de código. Queda en el default del schema (si tiene) o
   vacío. **No verificado en esta sesión si esto sigue siendo así al día de hoy** — confirmar
   contra `_candidato_contratar_mapeo.py` antes de asumirlo en el bloque B.

⚠️ El punto 3 es memoria de sesiones anteriores, no releída en A3.3 — el resto de esta lista sí
se verificó contra el código de hoy (endpoints vía `test_callers_huerfanos.py`, archivos vía
medición directa).

### Lo que la auditoría del 19/8/2026 agregó a esta lista

Cinco ítems que salieron de auditar el backend contra `VERIFICACION-BACKEND.md`. **Ninguno se
arregló en esa sesión (era auditoría) ni en la de cierre (era inventario).** Los cinco son para
el bloque B o posteriores.

1. 🔴 **`objetivos` no cumple tres de las seis reglas transversales, y es deuda PREEXISTENTE.**
   No pagina (`objetivo_repo.find_all` trae el árbol entero, sin `.range()`) · `ObjetivoResponse`
   tipa `id`/`empresa_id`/`responsable_id`/`parent_id` como `str` en vez de `UUID` (el "error #1
   del porteo") · **el CRUD manual no audita**: `objetivo_service` y `_objetivos_write` no llaman
   a `AuditService` en ningún punto, y el único evento del módulo lo emite el import por Excel.
   **Nada de esto lo introdujo el bloque A**: `objetivo_service.py` viene del commit `347afb3`, y
   la migración 119 sólo sumó `tipo`/`areas_involucradas`/`periodicidad`. La falta de auditoría
   ya estaba auto-declarada en `tests/test_auditoria_coherente.py`, que excluye a objetivos del
   barrido **a la espera de una definición de producto**.
   > **Qué auditar en el CRUD de objetivos no es una decisión técnica: la define Capital Humano.**
   > Un tablero interno del equipo de RRHH no tiene por qué dejar el mismo rastro que un legajo.
   >
   > 🔴 **Y hay una interacción sin resolver que impide tratar la paginación como tarea suelta:**
   > objetivos es un **árbol**, y hay una regla escrita —y correcta— de que **un hijo cuyo padre
   > no pasa el filtro se promueve a raíz** (`_objetivos_arbol.py`). Paginar un árbol con esa
   > regla **no es agregar `.range()`**: hay que decidir qué es "una página" (¿raíces? ¿nodos
   > aplanados?), qué pasa con un hijo promovido que cae en otra página que su padre, y cómo se
   > cuenta el `total` sin mezclar las dos cosas — el tope de export ya tiene esa trampa anotada
   > (`_objetivos_arbol.contar_con_hijos` vs. `count="exact"`). **Es diseño, y por eso no entra
   > en una sesión suelta.**
   > ⚠️ **Hoy `objetivos` tiene 1 fila en producción** (verificado contra el catálogo el
   > 19/8/2026), no 68 como se dijo en algún resumen: la urgencia es baja, el trabajo de diseño
   > no.

2. **`adjuntos.fecha_vencimiento` existe desde la migración 113, con índice parcial
   (`idx_adjuntos_vencimiento`), y tiene CERO wiring.** Verificado contra el catálogo el
   19/8/2026: la columna y el índice están, y **0 filas** la tienen cargada. No hay una sola
   referencia a `fecha_vencimiento` en `schemas/`, `services/`, `routers/` ni en todo el
   frontend. La migración la creó diciendo que era "para la alerta 'documentos próximos a vencer'
   del dashboard".
   > 🔴 **El riesgo real no es la columna muerta: es que alguien la vea y dé la alerta por
   > hecha.** El sistema de diseño declara "documentos próximos a vencer" como **inexistente**
   > (no hay lista de documentos obligatorios), y una columna con índice parece exactamente lo
   > contrario. Si se retoma, lo que falta no es DDL: es el catálogo de qué documentos vencen.

3. **Falta `GET /api/objetivos/{id}`.** `ObjetivoService.get_by_id` está escrito esperando la
   ruta, y `registro_routers.py:180-183` lo dice en un comentario propio. **No se construye
   ahora**: sería el **octavo** endpoint publicado sin botón, sumándose a los siete de la tabla
   de arriba. Se monta cuando el bloque B tenga la pantalla que lo pida, no antes.

4. **`Inventario` está visible en `nav-config.ts:76` sin ningún flag**, contra la decisión de
   dejarlo fuera del menú que `VERIFICACION-BACKEND.md` §10 declara como alcance cerrado. No es
   alcance que se coló en el bloque A —el ítem viene de commits viejos y `Seccion.INVENTARIO`
   tiene permisos normales—, es una decisión que quedó escrita en un lado y no aplicada en el
   otro. **Se resuelve en B1, junto con la navegación. Anotado, no tocado.**

5. **"Plan de desarrollo (Próximamente)" no existe en el front** — grep de `"Plan de desarrollo"`,
   `plan_desarrollo` y `roadmap` en `frontend/`: cero matches. **No es alcance perdido**: es un
   ítem de la navegación NUEVA y va en el bloque B. Se anota sólo para que nadie lo busque como
   si se hubiera borrado.

### 🔴 `identificacion_repo.registrar_intento` se traga TODO error — evaluado en A3.3, NO arreglado

El INSERT del log forense del link público está envuelto en `except Exception: logger.warning(...)`
desde antes de esta sesión, y sigue así. Es lo que vuelve **obligatorio, no recomendado**, el
orden de deploy de la migración 121 (CHECK primero, código después): si el código que escribe
`'preingreso'` sale antes que la migración, **cada intento de un preingreso se pierde SIN error,
SIN log y SIN fila** — el 23514 lo atrapa el except, no sube al usuario (el flujo público sigue
viendo el rechazo único de siempre) y lo único que queda es un `logger.warning` de severidad
baja que nadie monitorea en caliente. A fines prácticos: invisible.

**¿Merece arreglarse?** No se tocó en A3.3 — el pedido fue evaluar, no corregir. La evaluación:

- **A favor de dejarlo como está:** el motivo original sigue vigente. Si el INSERT del log
  fallara y la excepción se propagara, el tiempo de respuesta del endpoint público cambiaría
  según si el intento se pudo loguear o no, reabriendo por la ventana de timing el oráculo que
  el rechazo único cierra por la puerta (`identificacion_service.py`, sección "EL TIMING
  TAMBIÉN ES UN CANAL"). Envolver TODO en un `except` amplio es la forma más simple de
  garantizar que el forense nunca afecte el camino de éxito o de rechazo.
- **En contra de dejarlo como está:** "se traga todo" incluye errores que NO tienen nada que ver
  con timing — un 23514 por un CHECK desalineado (exactamente este caso), una columna renombrada,
  un typo en el nombre de tabla. Ninguno de esos afecta el timing si se detecta de otra forma:
  **loguear a nivel ERROR en vez de WARNING, o emitir una métrica contable** (un contador de
  "inserts forenses fallidos") no reintroduce el oráculo de timing —no cambia CUÁNDO responde el
  endpoint, solo qué tan visible es el fallo después— y sí habría hecho que este problema
  apareciera en un dashboard de errores en vez de depender de que alguien lea un WARNING.
- **El riesgo concreto de no tocarlo:** el próximo valor que alguien agregue a
  `intentos_identificacion.resultado` sin correr su migración primero repite el mismo modo de
  falla, y nadie se entera hasta que audite manualmente esta tabla o note un patrón de "faltan
  filas" contra el volumen esperado de intentos.

**Conclusión sin arreglar nada:** el diseño (tragar todo para proteger el timing) es correcto;
la SEVERIDAD del log (WARNING, no monitoreado) es lo discutible, y es una decisión de
observabilidad —qué se alerta y quién lo mira— no de código. Queda para quien defina la
estrategia de alertas del repo, no para esta sesión.

---

## 1. Código muerto

| Qué | Dónde | Callers reales | Gravedad | Esf. |
|---|---|---|---|---|
| ✅ ~~`costo_repo.py` (135 líneas)~~ | — | **BORRADO 2/8.** Callers reverificados uno por uno antes de tocar nada | ✅ | — |
| ✅ ~~`assessment_repo.py` (131)~~ | — | **BORRADO 2/8.** Ídem | ✅ | — |
| ✅ ~~`EliminarLoteButton.tsx` (74)~~ | — | **BORRADO 2/8.** Ídem | ✅ | — |
| ✅ ~~Tablas huérfanas: `configuracion_empresa`, `documentos_empleado`, `notificaciones`, `notificaciones_config`, `sucesion_posiciones`, `assessment_reportes`~~ | — | **DROPEADAS 11/8** por la migración 112 (J5b), junto con las 5 `ev_*`. Producción: 63 → 52 tablas | ✅ | — |

### 🔴 Lo que NO está muerto, aunque se sospechaba

| Qué | Por qué NO se borra |
|---|---|
| **Assessment** | El router se monta condicionalmente (`assessment_enabled=false`) — el módulo está apagado, **no muerto**. Los services, schemas y tests siguen vivos. Solo `assessment_repo` estaba huérfano, y se borró |
| **Sucesión** | Apagado en el front por dos flags; **todo el backend intacto y montado** |

> ✅ **`ev_*` SALIÓ de esta tabla el 11/8/2026: se borró entero (bloque J5).** Acá decía *"los 3
> routers están MONTADOS, borrarlos rompe endpoints publicados"*, y era cierto el 2/8. Lo que
> cambió no fue el criterio sino la medición: del otro lado de esos endpoints había **19 rutas
> publicadas por HTTP e inalcanzables desde la UI**, una rota hacía meses. J5a borró el código
> (17 archivos, 1.527 líneas) y J5b las tablas (migración 112). **La regla de abajo sigue en pie
> y este caso no la contradice**: no se borró porque "no se veía en la UI", se borró después de
> contar los callers reales y comprobar que no había ninguno.

> ⚠️ **Regla que sale de esto:** "está oculto en la UI" ≠ "está muerto". De los 5 sospechosos,
> **3 estaban vivos**. Verificar callers uno por uno, siempre.

---

## 1-bis. Preingresos — lo que A3.2 dejó abierto a propósito

### 🔴 El import de nómina puede dar de baja a un preingreso sin ninguna guarda

`services/nomina_empleados_service.py:136-137` llama a `dar_de_baja(...)` con solo mirar si la
fila del CSV trae `Fecha Baja`:

```python
if f["fecha_baja"]:
    self._emp_repo.dar_de_baja(empleado_id, f["fecha_baja"], UUID(empresa_id))
```

**No mira el estado en absoluto.** Un preingreso que aparezca en el archivo con esa columna
cargada pasa a `baja` **salteándose las cuatro guardas de `_offboarding_efectivizar`** — incluida
la que A3.2 agregó justamente para impedir que alguien que nunca entró figure como una baja del
mes, o sea como rotación inventada.

**No se arregló en A3.2 a propósito**, y el motivo no es alcance: cambiarlo altera el
comportamiento de un import que RRHH corre todos los meses, y **hay más de una respuesta
razonable** — saltear la fila y reportarla entre las que necesitan revisión, tratarla como
"preingreso cancelado" (que hoy no es un estado), o dejarla pasar porque el CSV es la fuente de
verdad de la nómina. Eso es una decisión de producto.

**Está anclado**, no solo escrito acá: `tests/test_estado_preingreso_escrituras.py` lo declara
como uno de los cinco caminos de escritura, con la razón en el encabezado. Si alguien le agrega
una guarda, el barrido lo va a mostrar.

### 🟡 El link público no distingue "todavía no entró" de "se fue" en el forense

`_identificacion_resolver.py:59` rechaza al preingreso —correcto— pero lo etiqueta `inactivo` en
`intentos_identificacion.resultado`, igual que a una baja. RRHH mira esa tabla para ver si
alguien está probando DNIs, y ahí los dos casos se ven iguales.

🔴 **Darle motivo propio EXIGE UNA MIGRACIÓN (la 121)**: el CHECK
`intentos_identificacion_resultado_check` acepta exactamente seis valores (`ok`,
`sin_coincidencia`, `inactivo`, `sin_clientes`, `ambiguo`, `bloqueado`) y `preingreso` no está.

⚠️ **Y no alcanza con escribir el valor nuevo y correr la migración después.** `registrar_intento`
**se traga todo error a propósito** (para no reintroducir por la ventana el oráculo de timing que
el service cierra por la puerta), así que un valor fuera del CHECK **no rompe el request: hace
desaparecer la fila del log en silencio**. Perder el registro entero es peor que la etiqueta
imprecisa. Es la misma mecánica que ya se documentó con `AuditService` y la FK de `empresa_id`.

**Orden obligatorio: primero la migración, después el valor.** Hay un test que fija el
comportamiento de hoy (`test_el_motivo_que_se_loguea_HOY_es_inactivo_y_no_uno_propio`) y que va a
rojear cuando se cambie, que es lo que va a recordar que la migración tiene que estar corrida.

### 🟡 El PUT del legajo puede saltearse la guarda de fecha del pase a activo

> ✅ **La MITAD de esta entrada se cerró el 20/8/2026: el PUT ya NO puede dar de baja.**
> `EmpleadoUpdate.estado` pasó de `EstadoEmpleado` (los 5 del CHECK) a `EstadoEditable` (cuatro,
> sin `baja`), así que la vía que escribía `estado='baja'` sin `fecha_egreso` ni motivo dejó de
> existir. Se decidió con el grep hecho: cero callers en backend, tests y front. El porqué completo
> está en `utils/estados_empleado.py`; el CHECK de la base **no se tocó**.
>
> 🔴 **Lo que sigue abierto es lo que esta entrada dice desde el principio:** el PUT puede llevar un
> `preingreso` a `activo` **sin verificar que la fecha de ingreso haya ocurrido**, salteándose la
> guarda que `POST /api/empleados/{id}/activar` existe para aplicar. Eso NO se cerró y sigue
> siendo el caso que el texto de abajo describe.
>
> ⚠️ **Y el cierre trajo su propia consecuencia asumida: tampoco se puede DESHACER una baja por el
> PUT.** Corregir una baja mal cargada dejó de ser una edición del legajo y hoy **no tiene ningún
> camino**: ni endpoint propio, ni pantalla. Se aceptó porque una baja mal hecha es un evento raro,
> auditado, y la alternativa era dejar abierta la puerta que rompe la fila para todos los demás
> casos. **Si RRHH lo pide, es una feature (un "revertir baja" con sus guardas), no un rollback de
> este cambio.** Gravedad 🟡 · Esfuerzo S.


`EmpleadoUpdate.estado` acepta los cinco valores del CHECK y **no valida nada más**: puede llevar
un `preingreso` a `activo` sin verificar que la fecha de ingreso haya ocurrido, que es
exactamente la guarda que `POST /api/empleados/{id}/activar` existe para aplicar.

Es deliberado —el PUT es la corrección manual de un dato mal cargado, y acotarlo lo volvería un
endpoint que a veces valida y a veces no— pero **no es gratis mientras el botón de activar no
esté en la UI**: hasta que el bloque B lo construya, el PUT es el ÚNICO camino disponible, que es
justo lo que no queremos que se vuelva costumbre. Está escrito en el encabezado de
`tests/test_estado_preingreso_escrituras.py`.

⚠️ **Y desde el 20/8/2026 tiene una segunda consecuencia, medida al agregar el orden por
`fecha_egreso`:** ese mismo PUT puede escribir `estado='baja'` **sin `fecha_egreso`**, porque no
pasa por `dar_de_baja` (que las escribe juntas en un solo UPDATE). Una baja sin fecha no cae en
ningún período —ya estaba anotado— y ahora además **sale ARRIBA de todo** en el orden
`fecha_egreso_desc` de la pantalla de Bajas, por la colocación de nulos de Postgres (ver la
entrada de abajo).

### ✅ ~~HAY DOS MOTIVOS DE BAJA Y NO SON EL MISMO DATO~~ — **CERRADO el 20/8/2026 por la opción (a)**

> **Se aplicó la opción (a) del análisis de abajo:** `_offboarding_efectivizar` copia
> `instancia.motivo_egreso` a `empleados.motivo_baja` en el mismo UPDATE que ya escribía el estado
> y la fecha. El reporte de Altas y bajas dejó de decir "Sin especificar" para las bajas de
> offboarding. **El análisis se conserva entero porque el PRECIO sigue vigente y hay que poder
> leerlo:** `motivo_baja` es texto libre y desde ahora convive con los 7 valores del vocabulario
> cerrado en la misma columna. Se aceptó porque las dos formas contestan la misma pregunta y el
> único lector ya trata el vacío con `or "Sin especificar"`.
>
> 🔴 **Solo hacia adelante:** las bajas efectivizadas ANTES de este cambio conservan `motivo_baja`
> en NULL. No hay backfill y no se escribió ninguno — habría que derivarlo de
> `offboarding_instancias`, y con las dos tablas en cero no hay nada que derivar todavía.
>
> ⚠️ **Lo que NO se cerró:** el camino inverso. Una baja del import de nómina sigue sin figurar en
> `motivos_egreso` del reporte de **Rotación**, que lee `offboarding_instancias` y no `empleados` —
> esa baja no tiene instancia. Es la mitad que queda, y no la resuelve este cambio.

**El análisis original, que sigue explicando el porqué:**

**Es el hallazgo del bloque 2 de la sesión de `fecha_egreso`, y es una decisión de producto
pendiente, no un bug que se arregle escribiendo código.** Hoy no se ve porque las dos tablas
están en cero.

| | `empleados.motivo_baja` | `offboarding_instancias.motivo_egreso` |
|---|---|---|
| Qué es | **TEXTO LIBRE** (migración 064, "para las bajas históricas del CSV") | **CHECK de 7 valores** (`renuncia`, `despido`, `acuerdo_mutuo`, `fin_contrato`, `jubilacion`, `fallecimiento`, `otro`) |
| Quién lo escribe | **solo el import de nómina** (columna `Motivo Baja`, `_nomina_empleados_transforms.py:120`) | **solo el flujo de offboarding**, al ABRIR el trámite (`OffboardingCreate.motivo`) |
| Quién lo lee | `_reporte_movimientos.py:61` — el listado nominal de bajas de "Altas y bajas" | `_reporte_dotacion.py:117-130` — `motivos_egreso` del reporte de Rotación |

🔴 **Los dos caminos de baja llenan columnas distintas, y ninguno llena la del otro.**
`_offboarding_efectivizar.efectivizar` escribe `estado='baja'` y `fecha_egreso` y **no toca
`motivo_baja`**. Consecuencia concreta, ya presente en el código: **toda baja hecha por el flujo
de offboarding aparece como "Sin especificar" en el reporte de Altas y bajas**, teniendo el
motivo guardado en la fila de al lado. Y al revés: una baja importada por CSV no figura en
`motivos_egreso` del reporte de Rotación, porque no tiene instancia.

**Por qué la pantalla de Bajas no se puede construir sin decidir esto primero.** Las tres salidas
tienen consecuencias distintas y ninguna es obviamente la correcta:

- **(a) Que `efectivizar` copie `instancia.motivo_egreso` a `empleados.motivo_baja`.** Es el
  cambio más chico (dos líneas en el write path) y el único que deja UNA columna con la
  respuesta siempre, sin joins en ningún listado. **Arregla de paso el "Sin especificar" del
  reporte de Altas y bajas.** El precio: mete un valor del vocabulario cerrado en una columna de
  texto libre, así que la columna pasa a tener las dos formas conviviendo, y cambia lo que un
  reporte ya publicado muestra — o sea que necesita su commit y su aviso, no colarse en otro.
- **(b) Join `empleados` → `offboarding_instancias` en el listado.** 🔴 **Es la peor de las tres
  y conviene descartarla por escrito:** el embed es *to-many* desde `empleados` (una persona
  puede tener una instancia cancelada y otra completada, `_CERRADOS` contempla las dos), así que
  devuelve un ARRAY y el mapper tendría que elegir cuál — lógica ambigua escondida en un mapper.
  Hay **dos FKs** entre las tablas, así que el embed exige nombrar la constraint o es PGRST201.
  Y sobre todo: lo pagarían **las ~37 pantallas** que usan `/api/empleados`, para una columna que
  le sirve a una sola.
- **(c) Endpoint propio de bajas.** Cabe en `routers/offboarding.py` (49/80), pero eso ya no es
  "exponer el motivo": es construir el módulo Bajas entero con su paginación, sus filtros y su
  export.

⚠️ **Lo que NO hay que hacer, y por eso queda escrito:** exponer `empleados.motivo_baja` en
`EmpleadoResponse` "porque es barato". Funcionaría para las bajas importadas y diría **vacío
para las de offboarding, que son las que SÍ tienen el motivo cargado** — propagaría a una
pantalla nueva el mismo bug que el reporte de Altas y bajas ya tiene. Gravedad 🟠 · Esfuerzo S
si es (a), M si es (c).

### 🟡 `fecha_egreso_desc` deja los NULOS ARRIBA — límite del cliente, no elección

En Postgres un `ORDER BY ... DESC` es **`NULLS FIRST`** por default, y `postgrest` 0.17.2 expone
`order(col, desc=, nullsfirst=, foreign_table=)` — **no tiene `nullslast`**
(`venv/Lib/site-packages/postgrest/base_request_builder.py:561`). O sea que `NULLS LAST` **no se
puede expresar desde el cliente**. Consecuencia en la pantalla de Bajas: una baja sin
`fecha_egreso` (ver la entrada de arriba) sale **primera**, arriba de las bajas recientes.

Está **pineado** en `tests/test_empleado_orden.py::TestLosNulosDeFechaEgresoQuedanArriba` para
que sea conducta declarada y no una sorpresa; el día que se resuelva, ese test es el que hay que
dar vuelta. Salidas posibles, ninguna en alcance de una sesión de código: una vista o RPC que
ordene del lado de la base, subir `postgrest`, o que la pantalla filtre `estado=baja` **y**
alguien garantice que toda baja lleva fecha (que es la entrada de arriba). Gravedad 🟡 · Esf. S.

### 🟡 ~~Mover una función mueve el punto de monkeypatch y el test SALE A LA RED~~ — **la CONSECUENCIA está cerrada (20/8/2026); la causa sigue**

> ✅ **Se implementó la salida (c) de las tres que esta entrada proponía:**
> `integrations/_cliente_real_en_tests.py`. Bajo pytest (o `APP_ENV=test`), **invocar** el cliente
> real levanta un `RuntimeError` que nombra el archivo y la línea que lo pidieron y dice qué
> sumarle al fixture. Verificado sacando `emp_baja_mod` del fixture de
> `test_offboarding_baja_efectiva.py`: falla con el mensaje nuevo y **sin `getaddrinfo` en la
> salida**, o sea que corta antes de tocar la red. Cubierto por
> `tests/test_cliente_real_bloqueado.py`.
>
> 🔴 **LO QUE NO SE CERRÓ, Y ES LA CAUSA: la lista a mano sigue existiendo.** 71 archivos de test
> y ~172 sitios de `monkeypatch.setattr(<modulo>, "supabase_admin", ...)`, 22 de ellos con listas
> de tres o más módulos. Mover una función **sigue** dejando su módulo fuera del fixture; lo que
> cambió es que ahora eso es un rojo inmediato y legible en vez de una salida a la red. Las otras
> dos salidas que esta entrada proponía —(a) un `conftest.py` que falsee la base para toda la
> suite, (b) un barrido que compare importadores contra parcheadores— **siguen siendo válidas y
> siguen sin hacerse**. La (a) es la que borraría la causa. Gravedad 🟡 · Esfuerzo M.
>
> ⚠️ **Dos límites del guard, escritos para no venderlo de más:**
> · **Un caller que se trague todo error se traga también esto.** El caso vivo es
>   `utils/empresas_cache.py`, que es fail-open por diseño: ahí el guard no avisa. Tampoco
>   escribe nada, que es lo que viene a impedir.
> · **No se porta solo a AWS.** Vive en el proxy de Supabase; con asyncpg el objeto es otro y el
>   agujero se reabre apuntando a RDS. El enganche allá es el pool de `postgres_client.py`.
>
> 🔑 **Y dejó un aprendizaje propio, que costó 21 rojos:** la primera versión del guard vivía en
> `_RootProxy.__getattr__`, y `monkeypatch.setattr(obj, name, val)` hace un `getattr` para
> guardarse el original ANTES de reemplazarlo — así que rojeaba a los tests que estaban falseando
> el cliente BIEN. **Leer un atributo no es usar la base; invocar sí.** El guard vive en
> `_MethodProxy.__call__` y hay un test que lo fija.

**El diagnóstico original, que sigue explicando la causa:**

Medido el 20/8/2026 al mudar `dar_de_baja` de `_empleado_write_repo.py` a `_empleado_baja_repo.py`.
`tests/test_offboarding_baja_efectiva.py` parchea `supabase_admin` **módulo por módulo**, con una
lista escrita a mano de los diez que consultan la base. Al mudarse la función, su módulo nuevo no
estaba en la lista, y el efecto no fue un fake incompleto ni un `AttributeError`: fue el **cliente
real de Supabase**, con `httpx` saliendo a la red y fallando con `getaddrinfo failed`.

🔴 **Acá no llegó a ningún lado porque la máquina no resuelve el host. En una con red y con las
credenciales de producción en el entorno, ese test escribe `estado='baja'` sobre la base real.**
No es hipotético: `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` salen de `settings`, y los tests las
llenan con valores falsos **solo si nadie las puso antes** (`os.environ.setdefault`). En una
sesión donde el `.env` esté cargado, ganan las reales.

**Lo que este repo ya tiene y no alcanzó:** el patrón de "parchear todos los módulos que
consultan" está documentado en el fixture de `test_estado_preingreso_padron.py`, y es correcto —
pero es una **lista a mano**, así que no puede saber que apareció un módulo nuevo. Salidas
posibles, ninguna decidida: (a) un `conftest.py` que falsee `integrations.supabase_client` una vez
para toda la suite y que los tests tengan que desactivar explícitamente; (b) un barrido que
compare los módulos que importan `supabase_admin` contra los que cada test parchea; (c) hacer que
el cliente real falle ruidosamente cuando `APP_ENV=test`. La (c) es la más barata y la que cierra
el riesgo sin tocar ningún test. Gravedad 🟠 · Esfuerzo S.

### 🟡 El barrido de columnas NO cubre `empleados`, que es la tabla central

`test_columnas_candidatos.py` cubre `candidatos` y `test_columnas_capacitaciones.py` cubre
`capacitaciones` + `empleado_capacitacion`. **`empleados` no está en ninguno de los dos**
(verificado por grep el 20/8/2026: cero menciones). No es un olvido — la generalización a los
~32 repos con `select("*")` está declarada como pendiente en la sección 8-ter — pero **esta
sesión es la evidencia de que la deuda tiene costo**: `fecha_egreso` es *exactamente* el caso que
ese barrido caza (una columna que el `select("*")` TRAE y que ningún campo del Response publica),
vivió así desde la migración 003, y la encontró una persona leyendo `schema.sql`, no un test.

🔑 **Y hay más de donde vino esa.** Contrastando el `CREATE TABLE public.empleados` contra
`EmpleadoResponse`, siguen sin exponerse **13 columnas**: `user_id`, `foto_url`, `potencial`,
`desempeno`, `updated_at`, `fecha_ingreso_reconocida`, `equipo`, `co_sourcing`, `product_owner`,
`liderazgo`, `motivo_baja`, `fecha_ingreso_prevista`, `fecha_baja_prevista`. **Ninguna se revisó
en esta sesión** — se tocó solo `fecha_egreso`, que era la que bloqueaba la pantalla. La
pregunta que el barrido haría por cada una (¿se decidió no exponerla, o se olvidaron?) sigue sin
contestar, y `motivo_baja` — que está en esa lista — ya se sabe que es de las segundas.
Gravedad 🟡 · Esfuerzo M (el inventario de las 66 columnas es el trabajo, no el test).

---

## 1-ter. 🔴 `must_change_password` NO TIENE ENFORCEMENT EN EL BACKEND (23/8/2026)

**Es un agujero, no un obstáculo del smoke.** Un usuario nuevo **puede usar la API completa con
la contraseña provisoria que le dio el admin, sin cambiarla nunca**, porque el único que lo
obliga es el AuthGuard del navegador.

**Dónde está cada mitad, medido:**

| Pieza | Archivo | Qué hace |
|---|---|---|
| lo escribe | `services/_usuario_alta.py:89` | el alta persiste `must_change_password: True` |
| lo devuelve | `services/auth_service.py:76` | el login lo manda en el payload de sesión |
| lo baja | `repositories/usuario_repo.py:58` | tras un cambio de contraseña exitoso |
| **lo aplica** | **`frontend/components/layout/AuthGuard.tsx:29`** | **y NADIE MÁS** |

**Lo que eso significa concretamente:** `middleware/auth.py` no lo mira, `utils/permisos.py` no
lo mira y ningún gate lo consulta. Con la contraseña temporal —que viaja por el canal que el
admin haya elegido para pasársela— se puede hacer `POST /api/auth/login` y de ahí **todo lo que
el rol permita**, indefinidamente. El navegador redirige a `/cambiar-password`; `curl` no.

**Por qué importa más de lo que parece:** la contraseña temporal la genera el sistema y la ve el
admin que crea al usuario. El diseño asume que deja de servir en cuanto la persona entra. Hoy no
deja de servir nunca, y **nada registra que se siguió usando**: `ultimo_acceso` se actualiza igual.

⚠️ **NO se arregló en la tanda que lo encontró (23/8/2026), a propósito.** Cerrarlo es una
decisión de producto antes que de código: hay que definir qué endpoints quedan permitidos con el
flag prendido (por lo menos `/api/auth/*` y `/api/usuarios/cambiar-password`, o el usuario queda
encerrado sin poder cambiarla) y qué pasa con las sesiones ya emitidas. Un `if` en el middleware
sin esa lista deja a todo usuario nuevo sin forma de entrar.

**Está sumado como caso a probar en `docs/INVENTARIO-SMOKE.md`** (sección 5): entrar por API con
un usuario que tiene `must_change_password=true` y ver que el sistema lo deja hacer todo.

---

## 1-quater. 🟠 LA BASE PROHÍBE EL JEFE DE OTRA EMPRESA QUE LA APP DECLARA SOPORTAR (23/8/2026)

**Medido sembrando, no deducido.** `PUT /api/empleados/{id}` con un `manager_id` de otra empresa
devuelve **500 `INTERNAL_ERROR`**. Lo rechaza el trigger `trg_emp_empleados`, que corre
`fn_misma_empresa('area_id','areas','manager_id','empleados')` (migración 094) y levanta
excepción cuando el padre es de otra sociedad.

🔴 **Contradice la decisión de producto del 2/8/2026 que documenta `services/_alcance_mandos.py`**
— *"un empleado puede tener superior de OTRA empresa del grupo, y para `mandos_medios` el
`manager_id` REEMPLAZA al filtro de empresa"*. Ese módulo es **la única excepción declarada a la
barrera de empresa** de todo el repo, y existe para un caso de datos que **la base no deja
crear**. Las dos mitades del sistema están escritas contra reglas opuestas.

**Los dos problemas son independientes y hay que decidirlos por separado:**

1. **Cuál de las dos reglas rige.** Si el jefe cruzado es legítimo, el trigger tiene que sacar el
   par `('manager_id','empleados')` de sus argumentos; si no lo es, `_alcance_mandos.py` está
   resolviendo un caso imposible y sobra su excepción entera. Hoy conviven y nadie eligió.
2. **El 500.** Aunque se decida prohibirlo, una violación de regla de negocio de la base no puede
   salir como `INTERNAL_ERROR`: la pantalla dice "error interno" donde el diseño diría "el
   superior tiene que ser de la misma empresa". Es la misma familia que el 500 de
   `maybe_single()` — un 4xx convertido en 5xx por no atrapar la excepción de abajo.

⚠️ **Hoy no se nota** porque `manager_id` se cargó a mano para 11 de 31 y presumiblemente siempre
dentro de la misma sociedad. Se descubrió al sembrar el usuario `mandos_medios` de prueba, que es
la primera vez que alguien arma esa jerarquía por la API.

---

## 2. Fugas y oráculos pendientes

| # | Qué | Dónde | Gravedad | Esf. |
|---|---|---|---|---|
| a1 | ✅ ~~**`EMPRESA_MISMATCH` 422 vivo**~~ — **CERRADO 2/8.** Los dos pasan al 404 del módulo, con el filtro **en el WHERE** (Forma A), no comparando después. `tests/test_empresa_mismatch_cerrado.py` fija el contrato Y que la empresa viaje en la query; con el bug reinstalado caen 6 de 10 | ✅ | — |
| a2 | **7 comparaciones `empresa_id !=` post-lectura** (Forma B). Todas devuelven 404, así que **no hay oráculo**, pero traen la fila antes de decidir: más caro y más fácil de olvidar al copiar | `evaluacion_service.py:33` · `adjunto_service.py:64` · `cesion_service.py:42` · `periodo_service.py:49` · `tipos_ausencia_service.py:80` · `reporte_export_service.py:42` | 🟡 | L |
| b | ✅ ~~**El import de costos no audita nada**~~ — **CERRADO 6/8.** Emite **UN evento por lote** desde `services/nomina_import_service.py` (el `confirmar` era el único de los tres imports sin capa de service: se creó, y el router bajó de 70 a 57 líneas) | ✅ | — |
| c | ✅ ~~**`_costos_write` audita con la empresa del HEADER**~~ — **CERRADO 6/8.** Los dos caminos auditan con la entidad: `nomina.empresa_id` (`:48`) y `presupuesto.empresa_id` (`:86`), y el docstring declara que el header es "solo VISTA" | ✅ | — |
| c2 | **9 eventos con `empresa_id NULL` en producción.** 6 legítimos (`alta_usuario` ×3, `cambio_password` ×3 — los usuarios no cuelgan de empresa) y **3 mal etiquetados**: `alta_adjunto`, `baja_adjunto` (sobre una vacante, que sí tiene empresa) y `baja_candidato` | tabla `auditoria` | 🟡 | M |
| d | **Barrido de los endpoints nuevos (~15 sesiones): sin hallazgos.** `/plantillas` (4), `/plantillas/enviar`, `/superiores-pendientes` (2), `/asignaciones/area`, `/configuracion` (3) — **todos** con `require_permission` y barrera de empresa donde reciben un id | — | ✅ | — |

> ✅ **De la sección quedan a2 y c2.** a1, b y c están cerrados (6/8). **c2 no se "arregla":** son
> 3 filas ya escritas en `auditoria`, que es inmutable por diseño. El bug que las produjo es el
> que cerró **c**.

---

## 3. Límites de líneas

### ✅ Sobre el límite — CERRADO 2/8: **el backend quedó en CERO archivos over-limit**

| Archivo | Antes | Ahora | Qué se hizo |
|---|---:|---:|---|
| `repositories/_onboarding_templates_row.py` | 159 | **87** | Partido en tres: `_row` (SELECT+mappers), `_filtros` (empresa y visibilidad), `_write` (payloads) |
| `services/_audit_payloads.py` | 167 | **119** | `_audit_payloads_offboarding.py`, siguiendo la instrucción que el propio archivo dejaba escrita |
| `repositories/ev_instancias_repo.py` | 146 | **98** | Satélite `_ev_instancias_row.py` |
| `repositories/ev_plantillas_repo.py` | 129 | **93** | Satélite `_ev_plantillas_row.py` |
| `services/reporte_anual.py` | 154 | **112** | `_reporte_anual_metricas.py` |
| `repositories/costo_repo.py` · `assessment_repo.py` | 135 · 131 | — | **Borrados**, no divididos |
| `services/usuario_service.py` | 149 | **77** | `_usuario_alta.py`. **Desbloquea la guarda de la casilla de correo** (sección 8) |
| `services/ev_instancias_service.py` | 149 | **113** | `_ev_instancia_crear.py`, forzado por el fix de a1 |

> 🔴 **EL APRENDIZAJE, que vale más que los ocho cortes:** dos satélites tenían escrito en su
> docstring *"acá el límite es 200"*, y por eso uno llegó a **159 sin que nadie lo notara**. Un
> `_*.py` dentro de `repositories/` **es un repositorio y su límite es 100**. Partir un archivo
> para respetar un límite es correcto; **redefinir el límite del archivo nuevo, no**.

### 🟡 `utils/estados_empleado.py` — 155/200 el 18/8, y está diseñado para crecer

Nació el 18/8 con 102 líneas (dos constantes de lectura) y el mismo día llegó a **155** al
recibir los dos tipos de escritura (`EstadoEmpleado`, `EstadoAlta`), que se mudaron ahí desde
`schemas/empleado.py` — ese archivo daba **202/200** con los tipos adentro, y el criterio del
corte fue que **el espejo del CHECK exista una sola vez**, no el tamaño.

**Quedan 45 líneas.** No es deuda hoy, pero se anota porque este módulo es, por diseño, donde
aterriza todo vocabulario nuevo de `empleados.estado`: una constante más o un tipo más entran
con su explicación, y la explicación es el 80% del archivo. **El próximo agregado hay que
medirlo antes de escribirlo.** Si hace falta cortar, el seam natural ya está marcado por los
encabezados de sección: lectura (constantes) contra escritura (tipos) — pero cortar por ahí
reintroduce el problema que el corte del 18/8 vino a resolver, así que la primera opción es
mover prosa a `docs/`, no partir el módulo.

### En el techo exacto — el próximo cambio EXIGE dividir primero (remedido **12/8**)

**Services 150/150:** `assessment_service.py` · `_clasificador_prompt.py` · `_vacaciones_write.py`.
**Repos 100/100:** `area_repo` · `candidato_repo` · `inventario_asignaciones_repo` · `objetivo_repo` · `planes_carrera_repo` · `vacante_repo` · **`sucesion_repo.py` (nuevo, 18/8)**.

> 🔴 **`sucesion_repo.py` llegó a 100/100 el 18/8 y el próximo cambio EXIGE dividir primero.**
> Entró un import y un comentario de dos líneas para cambiar `.neq("estado","baja")` por
> `.in_("estado", ESTADOS_EN_PLANTILLA)`; el archivo estaba en 97. **No se comprimió ningún
> comentario para que entrara** — es la regla del repo y era justamente la tentación acá.
>
> ⚠️ **El corte natural ya está identificado y NO es "partir la clase":** las cinco funciones
> libres de arriba (`_mapa_row`, `_parse_json_field`, `_score_de`, `_recencia`,
> `_scores_por_empleado`, ~50 líneas) son el mapper + el resolvedor de scores del assessment, y
> salen a un `_sucesion_row.py` con el molde de `_empleado_row.py` / `_area_row.py`, que es el
> mismo corte que ya se le hizo a los otros repos grandes. Queda `SucesionRepo` con sus dos
> métodos en ~45 líneas.
>
> 🔑 **Y antes de tocarlo, leer la entrada de la sección 4 sobre los dos predicados divergentes
> de este mismo archivo:** si esa decisión de producto se toma, el diff cae en estas mismas
> líneas y conviene hacer las dos cosas juntas en vez de pasar dos veces por un archivo lleno.
**Routers 80/80:** `adjuntos.py` · `candidatos.py` · **`offboarding_tramite.py` (nuevo, 17/8)** · **`empleados.py`** (ya estaba en 80/80 el 19/8 y la lista no lo decía; remedido el 20/8).
**Repos 100/100:** `empleado_repo.py` **llegó al techo el 20/8** (era 97: +1 import y +2 de docstring
al sumarle el motivo a `dar_de_baja`). **El próximo cambio EXIGE dividir primero.**

> ⚠️ **El corte de `empleado_repo.py` NO es obvio y conviene decidirlo con tiempo:** el archivo es
> `find_all` (~45 líneas, lo único que crece con cada filtro) más SEIS delegadores de una línea que
> son la interfaz pública del repo. Partir la interfaz la rompe para los ~40 call sites; el corte
> real es sacar `find_all` a un `_empleado_listado_repo.py` (molde: `_candidato_listado_repo.py`,
> que ya existe) y dejar acá la fachada. **No se hizo en esta sesión a propósito**: es un cambio de
> 40 call sites que no tiene nada que ver con las bajas.

> 🔴 **`routers/empleados.py` sigue en 80/80 después de la sesión del orden, y no por casualidad:**
> el parámetro `orden` entró **sin agregar una sola línea** — se extendieron la lista de import
> que ya existía y las dos firmas de una línea del listado y del export. **El próximo endpoint o
> el próximo import EXIGE dividir primero**, y el corte natural es el que ya tienen los otros
> seis módulos del repo: `empleados_escrituras.py` con `create`/`activar`/`update`, montado en el
> MISMO prefijo (las rutas no cambian). ⚠️ Ojo con el costo escondido: eso suma **2 líneas a
> `registro_routers.py`, que está en 197/200** — o sea que dividir el router obliga a mirar
> también el registro. Es la razón por la que esta sesión eligió no dividirlo.

> 🔴 **`offboarding_tramite.py` NACIÓ en 80/80, y eso es lo que hay que mirar de este corte.**
> El 17/8 se partió `offboarding_escrituras.py` (79/80) por el seam del módulo: **ciclo** —
> endpoints que cambian en qué estado está el proceso — contra **trámite** — endpoints que
> registran progreso dentro de una instancia ya creada. La división compró margen de un solo
> lado: `offboarding_escrituras.py` quedó en **46/80** y `offboarding_tramite.py` en **80/80**,
> porque los dos PUT que se mudaron se llevaron el encabezado que explica el criterio de corte,
> la nota del rate limit y la del orden de registro.
>
> **Consecuencia práctica, que es la que importa para la próxima sesión:** el lado con lugar es
> el de CICLO (34 líneas libres — ahí entra holgado el endpoint de efectivización de la baja que
> motivó esta división). El lado sin lugar es el de TRÁMITE: **el próximo endpoint de trámite no
> entra y exige dividir primero.**
>
> ⚠️ **Y cuando eso pase, el corte NO es un tercer archivo con un criterio nuevo.** Tres archivos
> con tres criterios distintos es cómo un módulo deja de tener un lugar obvio para cada endpoint,
> que es exactamente lo que este corte vino a resolver. Las dos salidas honestas son: subdividir
> DENTRO del criterio que se desborde (trámite por entidad: activos / entrevista), o bajar el
> encabezado compartido a un solo archivo y que los otros lo referencien en vez de repetirlo.
> **Lo que no se hace es recortar los comentarios para entrar** — la regla del repo, y el motivo
> por el que este archivo se declara en el techo en vez de haber sido podado.

> ⚠️ **Es una FOTO, no un inventario: medila antes de usarla.** La versión del 2/8 nombraba
> `evaluacion_repo`, `nomina_repo`, `vacantes.py` y `vacaciones.py`, que desde entonces se
> movieron, y cuatro `ev_*` que ya no existen.

### Frontend

| Archivo | Líneas | Corte | Esf. |
|---|---:|---|---|
| `app/(dashboard)/costos/page.tsx` | **624** | El peor del repo. Molde: `components/features/sucesion/` (855→85) | L |
| `app/(dashboard)/vacantes/[id]/page.tsx` | **451** | Ídem | L |
| `app/(dashboard)/onboarding/page.tsx` | **413** | Tabs a componentes | M |
| `components/features/costos/ImportarNominaCSVModal.tsx` | **377** | Hook + pasos | M |
| `app/(dashboard)/offboarding/page.tsx` | 311 · `NominaModal` 287 · `evaluacion/[token]` 258 · `VacanteModal` 251 · `AIPanel` 249 · +19 más sobre 150 | — | L |
| **Hooks sobre 80** | `useFiltrosVacaciones.ts` **95** · `useFiltrosAsignacionesCap.ts` **89** | Molde ya aplicado: `useOpcionesAusencias` (partir carga de opciones vs. estado del filtro) | S |

> ⬜ `dropdown-menu.tsx` (268) y `dialog.tsx` (**221**) son primitivos generados de shadcn/ui: **no cuentan**.
> ✅ `areas/page.tsx` salió de la lista: **261 → 128**. Total remedido el 12/8: **28 archivos > 150** (26 propios + los 2 primitivos).

---

## 4. Espejos y duplicaciones

| Qué | Estado verificado | Gravedad | Esf. |
|---|---|---|---|
| **`permisos.ts` ↔ `permisos.py`** | ✅ **CERRADO 2/8** — `tests/test_espejo_permisos.py` compara secciones, acciones, roles y el fail-closed, con guarda de mínimo por extracción. Nació en verde (era el momento más barato: no había nada que arreglar primero) | ✅ | — |
| **`MANDOS_MEDIOS_SECCIONES` duplicado** | ✅ **CUBIERTO por el mismo test**: sigue habiendo dos declaraciones, pero ya no pueden separarse en silencio | ✅ | — |
| **`_subset` duplicado** en los 6 `_audit_payloads*` | Es deliberado y está documentado (a diferencia de `sin_derivados`, que se importa) | ⬜ | — |
| **Filtro `empresa` duplicado 8× entre repos** | `_with_empresa` existe pero no todos lo usan | 🟡 | M |
| **`sucesion_repo` responde la MISMA pregunta con DOS predicados** | 🟡 **NUEVO 18/8.** `get_mapa_talento` (:81) pregunta `.eq("estado","activo")` y `get_analisis_posicion` (:89) `.in_("estado", ESTADOS_EN_PLANTILLA)` — dos métodos del mismo repo, sobre la misma tabla, para "¿quién está en juego?". **Hasta el 18/8 la divergencia era `activo` vs `!= baja` y daba igual** (los 31 empleados están en `activo`); ahora alguien en `licencia` aparece en el análisis por posición y no en el mapa de talento, y un preingreso en ninguno de los dos. **No se unificó en esta sesión a propósito:** cuál de los dos es el correcto es una decisión de producto sobre sucesión, y el módulo está **apagado en el front por dos flags**, así que hoy no lo ve nadie. Decidirlo antes de reactivarlo. Las dos comparaciones están declaradas en `tests/test_estado_preingreso_lecturas.py` | 🟡 | S |
| **Presupuesto de tiempo duplicado** | `_nomina_lote.py:65-105` y `_lote_mails.py:55-85`. Fue decisión consciente con 2 casos; con un 3º entrando (import de novedades) deja de serlo | 🟡 | M |

> 🔑 Con esto son **cinco** los barridos estructurales del repo (paridad list↔export, límite de
> export, selects de repos, espejo de permisos, nav↔permisos), **todos con guarda de mínimo**.
>
> ⚠️ **Corregido el 11/8/2026: hoy son TRECE, no cinco.** La frase de arriba se deja como quedó
> escrita —era cierta el 2/8— pero **no la uses como inventario**. La lista completa y al día vive
> en **`CLAUDE.md` → Tests**, y es el único lugar donde se enumera: un segundo listado en prosa
> vuelve a divergir, que es exactamente lo que documenta la sección 6 de este archivo.

---

## 5. Tests que no prueban

| Qué | Dónde | Mutación que sobreviviría | Gravedad |
|---|---|---|---|
| Fake que **acepta `empresa_id` y lo ignora** | `test_empleado_service.py:128` · `test_audit_instrumentacion_rrhh.py:81` · `test_domicilio_desglosado.py:119` | Borrar el `_with_empresa` del repo real | 🟡 (declarado) |
| Ídem, devolviendo constante | `test_empleado_area_empresa.py:71` (`return _resp(EMPLEADO, EMPRESA_A)`) | Ídem | 🟡 (declarado) |
| Fake de asignaciones sin empresa | `test_mail_envio.py:79` | El mailer no valida empresa (por diseño) | ⬜ |

**Hallazgo honesto:** el barrido **no encontró aserciones vacuas nuevas**. Los ~10 fakes permisivos
que aparecen están **todos declarados en su docstring** (`"acepta empresa_id y lo ignora"`,
`"permisivo"`) y tienen un archivo hermano que sí la honra — que es exactamente el patrón que
CLAUDE.md manda. La disciplina se sostuvo.

⚠️ **Lo que sí falta es cobertura, no calidad:**

| Hueco | Gravedad | Esf. |
|---|---|---|
| **Ningún test del alta/edición de plantillas de mail** (`plantillas_service.guardar/borrar`) — solo del render y los permisos | 🟠 | M |
| **Ningún test de `_asignaciones_bulk.asignar_bulk`** en su camino manual con proyecto inexistente | 🟡 | S |
| **`mail_enviado_repo` sin tests** (idempotencia probada solo con fake) | 🟡 | S |

### 🔴 El problema INVERSO: tests de texto que convierten un refactor en cambio de contrato

No es un test que no prueba: es uno que **rompe sin que cambie el comportamiento**.

`guardarCliente.test.ts:110` lee `ClienteModal.tsx` **por path** (`readFileSync`) y afirma **7
substrings** dentro del archivo (`guardarCliente`, `setEmpresaId(cliente?.empresa_id ?? ...)`,
`fetchEmpresas`, `cliente-empresa`, `{!isEdit && (`, `e.activa`, y la ausencia de
`createCliente`). Cualquier reorganización del componente —mover la lógica a un hook, extraer el
select a un subcomponente— rompe el test **sin que cambie una sola línea de comportamiento**.

Medido en L1: extraer la lógica a un hook rompe **4** assertions; extraer el select, **2**. Por
eso `ClienteModal.tsx` quedó sin dividir.

**Es la TERCERA aparición del mismo patrón** — un test de texto sobre un archivo convierte un
refactor en cambio de contrato:

| # | Dónde | Cómo se manifestó |
|---|---|---|
| 1 | `services/clientes.ts` | Un comentario que citaba una ruta entre backticks le "daba caller" al endpoint y tapaba el barrido de huérfanos |
| 2 | `ClienteModal.tsx` | Un comentario que nombraba `createCliente` rompía el `not.toContain` del propio test estructural |
| 3 | `guardarCliente.test.ts:110` | Las 7 assertions de substring bloquean la división del componente |

🚩 **L5 es el momento de reescribirlas contra la FUNCIÓN, no contra el archivo.** L5 tiene que
tocar ese bloque igual —al desaparecer el `<select>`, las assertions sobre `cliente-empresa`,
`fetchEmpresas`, `e.activa` y la línea de siembra quedan sin sujeto—, así que el costo de
rehacerlas bien ya está pago. ✅ **Hecho en L5**: cuatro assertions borradas, cuatro reescritas
contra la función, y las dos estructurales que no se pueden reescribir quedaron marcadas con su
motivo (no hay forma de observar "el modal no llama al service" sin renderizarlo, y renderizarlo
es imposible acá).

### 🔴 LA PREGUNTA TIENE UNA PREGUNTA PREVIA: ¿el fake ES lo que estoy probando?

La regla del repo es *"¿qué tendría que ser distinto en el fake para que este test pueda fallar?"*.
**L9 mostró que hay que contestar otra antes: ¿el fake ES lo que estoy probando?**

En L9 los tests atravesaban el service **de verdad** —`svc.get_detalle`, `svc.eliminar`, no armaban
el resultado por su cuenta— y aun así la mutación no rojeaba: la mutación vivía en el **repo real**
y los tests corrían contra `_RepoFalso`. `find_by_id` podía volver a recortar por empresa **con 37
tests en verde**. El nombre del test no engañaba; **engañaba el nivel**.

**Corolario operativo: cuando una mutación no rojea, revisar en qué CAPA vive la mutación y en qué
CAPA corre el test, antes de concluir que falta un caso.** Las dos veces que pasó, la conclusión
"falta un caso" habría sido incorrecta y habría llevado a agregar un test en la capa equivocada:

| Sesión | La mutación vivía en… | El test corría contra… | Verde con el bug |
|---|---|---|---|
| **L8** | `svc.exportar` (service) | filas armadas a mano desde el repo | 34 |
| **L9** | `_horas_vista_repo` (repo real) | `_RepoFalso` (service) | 37 |

Los dos se cerraron con un test que atraviesa **la capa mutada**: en L8 capturando lo que el service
le pasa a `build_export`, en L9 pegándole a la query real vía `Almacen`.

### 🔴 El padrón tiene que poder distinguir los DOS comportamientos que se comparan

No alcanza con que el fake modele "más de uno": tiene que modelar **la diferencia exacta** que
separa el comportamiento viejo del nuevo.

En L9 hubo que **sumar una tercera persona con cargas en dos sociedades**. Con Carla cargando en
una sola, `find_por_empleado` devolvía lo mismo recortando por empresa que sin recortar — "trae las
dos" y "trae la suya" eran indistinguibles, y el test no podía fallar aunque estuviera en la capa
correcta. Es la misma forma que *"todo fake nuevo modela DOS empresas"*, un escalón más adentro:
**dos filas no bastan si las dos caen del mismo lado del corte.**

### 🔴 Ejecutar el SCHEMA no dice si el CAMINO serializa

Barriendo `model_dump()` sin `mode="json"` sobre schemas con campos UUID salieron 6 candidatos.
**5 eran falsos positivos**: `_empleado_write_repo` (×2), `inventario_items_repo` y `vacante_repo`
(×2) convierten los UUID **a mano, línea por línea, DESPUÉS del `model_dump()`**
(`payload["area_id"] = str(...)`). El único real era `ev_plantillas_service.py:75`.

La prueba que los marcó como rotos ejecutaba el `model_dump()` **aislado** y le hacía
`json.dumps`. Eso responde "¿el schema devuelve UUIDs?", que no es la pregunta: la pregunta es
"¿qué le llega a PostgREST?". **Hay que leer el camino completo hasta la llamada, no evaluar el
schema en el vacío** — entre el dump y el insert puede haber cinco líneas que arreglan todo.

### 🔴 Un test que REPLICA adentro la transformación que quiere verificar no puede fallar

Apareció al tipar `AreaCreate.responsable_id`. El primer test de serialización que se escribió
hacía, dentro del propio test:

```python
payload = data.model_dump(exclude_none=True, mode="json")
json.dumps(payload)          # "verifica" que serializa
```

Eso pasa **aunque `area_repo` pierda el `mode="json"`**: el test estaba probando su propia línea,
no la del repo. Es la forma más pura del problema — ni siquiera hace falta un fake permisivo,
alcanza con copiar la transformación.

Se cerró con un doble de `supabase_admin` que hace `json.dumps` **en el punto donde corre de
verdad** (al salir el payload hacia PostgREST) y llamando al **repo real**. Recién ahí la mutación
"sacar `mode="json"`" rojea.

⚠️ Es el hermano de la pregunta de arriba: allá el fake no era lo que se probaba; acá **el test
era lo que se probaba**.

### 🟠 `TestElPisoDeTiempo` es intermitente en Windows — medido y reproducido el 17/8/2026

**El test:** `tests/test_identificacion_publica.py::TestElPisoDeTiempo`, 5 casos, todos con la
misma forma: `t0 = perf_counter()` → `await ...` → **`assert perf_counter() - t0 >= 0.12`**, con
`_PISO_SEGUNDOS` monkeypatcheado a 0.12. Mide el piso REAL a propósito: testearlo con el piso en 0
dejaría que borrar la nivelación entera pasara en verde, que es el bug que importa. Eso está bien
y **no se cambia a la ligera**.

**Reproducido, con nombre completo:**
`TestElPisoDeTiempo::test_todos_los_rechazos_esperan_el_mismo_piso[99999999]` —
`assert (478934.8076979 - 478934.692038) >= 0.12`, o sea **0.11566 s: 4,34 ms corto**.

**EL MECANISMO, medido — no es la CPU.** `asyncio` dispara los timers hasta
`loop._clock_resolution` **ANTES** de su vencimiento, a propósito: `_run_once` saca del heap todo
handle cuyo `when` caiga dentro de esa ventana. En esta máquina, medido:

```
time.get_clock_info('monotonic').resolution = 0.015625   (15,625 ms)
loop._clock_resolution                      = 0.015625
```

O sea que **`asyncio.sleep(0.12)` puede volver legítimamente a los ~0.1044 s** y seguir siendo
correcto. La aserción pide `>= 0.12` **sin tolerancia**, así que el test vive a 15,6 ms de un
rojo que no depende de nada del código. Medido en máquina ociosa, 400 `sleep(0.12)` seguidos:
**1 volvió por debajo de 0.12** (0,2 %), mínimo 0.11997.

🔴 **CORRECCIÓN DE LO QUE SE AFIRMÓ ANTES EN ESTA MISMA SESIÓN, y es el aprendizaje.** Se dijo que
"la carga empuja al verde, no al rojo, porque la granularidad del timer redondea el sleep hacia
arriba" y que por eso "el mecanismo anotado es imposible". **Las dos cosas son falsas**, y la
medición de arriba las desmiente: asyncio adelanta, no atrasa. La afirmación se construyó
razonando sobre cómo *debería* comportarse el reloj en vez de medirlo — el mismo error que esta
sección entera documenta, cometido sobre un test que investiga esta sección.

**El experimento, 12 corridas completas de la suite, todas a archivo:**

| Brazo | Condición | Corridas | Fallos |
|---|---|---:|---:|
| A | dos procesos pytest concurrentes, **`__pycache__` compartido** | 6 | **1** |
| B | dos procesos pytest concurrentes, **`PYTHONPYCACHEPREFIX` separado** | 6 | 0 |
| — | 12 corridas de solo `TestElPisoDeTiempo` con los 12 cores saturados | 12 | 0 |
| — | 5 corridas completas **secuenciales** | 5 | 0 |

⚠️ **1 contra 0 con n=6 NO distingue los dos brazos, y no hay que leerlo como que el caché es la
causa.** No existe mecanismo por el que compartir bytecode acorte un `sleep`: la contención de I/O
haría el camino más LENTO, o sea empujaría la aserción hacia el verde. Lo que el experimento sí
muestra es que **la concurrencia de dos event loops mueve el jitter de scheduling lo suficiente
como para exponer una fragilidad que ya estaba** — la saturación de CPU con busy-loops (12/12
verdes) no la expone porque no perturba dónde cae el deadline respecto del tick del timer.

**Qué hacer cuando moleste** (no se tocó ahora: el test es correcto y el rojo es del arnés, no del
código): bajar la aserción a `>= 0.12 - loop._clock_resolution`, o comparar contra el piso menos
un margen declarado con este porqué escrito al lado. **Lo que NO se hace es pisar
`_PISO_SEGUNDOS` a 0**, que devolvería el falso verde que el test existe para impedir.

🔑 **Y la regla de arnés que deja, que costó una sesión entera:** un fallo cuyo nombre no se
registró es un fallo que no se puede investigar. Este apareció con un `tail -2` sobre un pipe, se
perdió, y recuperarlo costó 12 corridas completas. **Toda corrida de pytest va a archivo, con
nombre propio, y se lee de ahí.** `.pytest_cache/v/cache/lastfailed` **no sirve de respaldo**: se
verificó que acumula entradas obsoletas (34, todas de node-ids que ya no resuelven) y que pytest
solo descarta las de tests que efectivamente corren, así que las de tests renombrados quedan para
siempre. `cache/nodeids` tampoco: es la unión acumulada de todo lo colectado alguna vez (4531
contra 3753 tests reales), no la colecta actual.

---

## 6. Documentación que miente

**`CLAUDE.md`** — desactualizado en **10 números verificables**:

| Afirma | Real | |
|---|---|---|
| "975 passed" | **1539** | tests backend |
| "61 archivos `test_*.py`" | **87** | |
| "backend va por **081**" | **089** | y 086-089: las 4 primeras corridas, la 089 pendiente |
| "hoy son **54**" repos | **67** | regla 14 (asyncpg) |
| "143 tests" front | **214** | |
| "52 tablas" | **58** | schema.sql |
| "113 archivos" services | **124** | |
| "79 archivos SQL" | **87** | migraciones |
| "180 gates" | **240** | `require_permission` |
| "48 endpoints" routers | 52 archivos de router | |

Además: la sección **"Líneas — REMEDIDO 28/7/2026"** está entera obsoleta (no incluye
`_onboarding_templates_row` 159, ni los hooks sobre 80); dice que `AusenciaModal` está en 149
(hoy 103) y `useFiltrosAusencias` en 93 (hoy 59).

> ✅ **La limpieza de `docs/` se hizo el 2/8/2026** (28 → 17 archivos). `MODELO_DATOS.md` se
> **borró** —describía 13 tablas inexistentes y se declaraba fuente de verdad del schema—, junto
> con las dos auditorías del 29/5, la extracción de Nexio, `INVESTIGACION_ROLES.md`, `CHANGELOG.md`
> y los 7 diagnósticos de sesión (fusionados en `DECISIONES.md`). `ESTADO-VS-COMPROMISO.md` y
> `MATRIZ-FILTROS.md` quedaron actualizados, y se sumaron `DEPLOY.md` y `DECISIONES.md`.
>
> **Lo único que sigue mintiendo es `CLAUDE.md`**, con los 10 números de arriba.

---

## 7. Datos inconsistentes en producción

| Qué | Evidencia | Gravedad | Esf. |
|---|---|---|---|
| **`GESTION DE DEUDA` y `GD - GESTION DE DEUDA`** — la misma área duplicada por el import (una por grafía del CSV). Con áreas duplicadas, "asignar el área" asigna a la mitad | tabla `areas`, 9 filas | 🟠 | S (RRHH) |
| 🔴 **`manager_id` sigue 0/19** — el import ya lo escribe (sesión del 2/8) pero **RRHH no reimportó**. Sin esto, `mandos_medios` no ve nada y el ownership cruzado no se puede probar | `empleados` | 🔴 | — (RRHH) |
| 🔴 **`legajo` 0/19** — bloquea el import de vacaciones pendientes, que solo trae legajo como ancla | `empleados` | 🔴 | — (RRHH) |
| **`valor_hora = 0` en las 19 asignaciones** — indistinguible de "no lo sabemos", y el reporte de costos lo suma | `proyecto_asignaciones` | 🟠 | S |
| **`seniority` 15/19 vacío** | `empleados` | 🟡 | — (RRHH) |
| **1 adjunto con `empresa_id` NULL** (fila legacy) — bloqueado en TODOS los modos por diseño, o sea inaccesible | `adjuntos` | 🟡 | S |
| **1 proyecto sin nadie asignado** — no aparece bajo ninguna área (es la definición, no un bug) | `proyectos` | ⬜ | — |
| **`costos_nomina` 0 filas** → el historial salarial (C1) sale vacío para todos. Feature entera, dato inexistente | | 🟠 | — (RRHH) |
| **`tipos_ausencia`: 3 activos** (Injustificada desactivada por la 088 ✅, "Otro" sigue activo a la espera del catálogo real) | | ⬜ | — |

---

## 7-bis. `db/schema.sql` — dos trampas de mantenimiento

Verificado el 7/8/2026 contra el catálogo vivo: el archivo está **exacto** (0 diferencias en
tablas, columnas, FKs, CHECKs e índices, en las dos direcciones). No es deuda de contenido. Lo
que sigue es deuda de **proceso**, y las dos muerden recién el día que alguien lo regenere.

### 🔴 Regenerarlo con `pg_dump` rompe el barrido de selects — y el rojo miente

`tests/_postgrest_schema.py` no parsea SQL: lo lee con dos regex hechos a medida del formato
actual del archivo.

| Regex | Qué exige hoy | Qué emite `pg_dump` |
|---|---|---|
| `_RE_TABLA` | que el `CREATE TABLE` cierre con `\n);` | formato propio, con tipos calificados por esquema |
| `_RE_FK` | `ALTER TABLE [public.]tabla ADD CONSTRAINT … FOREIGN KEY …` | **`ALTER TABLE ONLY public.tabla …`** |

**`_RE_FK` no contempla el `ONLY`.** Con un dump, las **153 FKs dejarían de parsearse**: `entre()`
devolvería siempre vacío, los embeds con FK nombrada tirarían `SelectInvalidoError` y
`test_selects_repos.py` caería en masa sobre sus 238 selects.

**Lo peligroso no es el rojo, es cómo se lee:** parece "el schema está mal" cuando el problema es
el formato. **Si alguna vez se regenera con otra herramienta, los dos regex se adaptan en la MISMA
tanda**, o se pierde medio día persiguiendo un bug que no existe.

### No hay script generador, ni procedimiento escrito

`schema.sql` se generó **a mano**, leyendo el catálogo. En `backend/scripts/` solo hay smoke
tests. `docs/DEPLOY.md` dice *"hay que regenerarlo desde el catálogo"* sin decir **con qué**, y
`backend/db/README.md` tampoco. O sea: el artefacto más crítico del rebuild no tiene forma
reproducible de rehacerse, y el próximo que lo intente va a improvisar un `pg_dump` — que es
exactamente lo que dispara la trampa de arriba.

---

## 8. Anotado y nunca hecho

| Pendiente | Dónde | Gravedad | Esf. |
|---|---|---|---|
| 🔴 **Guarda de baja del usuario que es la casilla de correo** — bloquear con 409. **No se hizo porque `usuario_service.py` está en 149/150** | `repositories/integracion_remitente_repo.py` 🚩 | 🟠 | M (exige dividir primero) |
| **Mapeo de columnas del archivo de novedades** — a la espera del archivo real de RRHH | `services/_import_csv.py` 🚩 | 🟡 | — |
| **Índice normalizado para el matcheo por nombre** — cuando el padrón pase de unos miles (hoy 19) | `repositories/_empleado_lookup_repo.py` 🚩 | ⬜ | — |
| **Un nieto de tipo de ausencia se puede crear por SQL directo** — el CHECK no puede consultar otra fila; la guarda vive en el service | `services/_tipos_jerarquia.py` 🚩 | ⬜ | — |
| **`objetivos.responsable_id` es FK a `users`, no a `empleados`** — bloquea filtro por área e import. **Con 1 fila la migración es trivial; con datos, cara** | CLAUDE.md, verificado en catálogo | 🟠 | M |
| **Filtro por provincia/localidad** — las 6 columnas existen (mig 081), sin domicilios cargados | | ⬜ | — |
| **`objetivos.py` / `inventario_items.py` (79 líneas)**: al dividirlos, agregarles `shared_limit("30/hour", scope="export")` | hay un test que lo recuerda | 🟡 | S |
| **Los 2 hooks del front sobre 80** (`useFiltrosVacaciones` 95, `useFiltrosAsignacionesCap` 89) — quedaron fuera de la tanda de límites del 2/8, que fue de backend | molde: `useOpcionesAusencias` | 🟡 | S |
| **E2E real de adjuntos nunca ejecutado** (`_BUCKET` hardcodeado a prod) | | 🟡 | — (cutover AWS) |
| **Reactivar `/configuracion` → desactivar "Otro"** cuando RRHH cargue sus tipos | mig 088 🚩 | ⬜ | — (RRHH) |

---

## 8-quater. Lo que A4.2 dejó abierto y medido (18/8/2026)

### 🟠 El puente hace DOS escrituras sin transacción — qué queda si falla la segunda

`POST /api/candidatos/{id}/contratar` crea el empleado y después marca al candidato. PostgREST no
da transacciones, así que si el paso 2 falla queda **el empleado creado y el candidato en
`activo`**. Está **medido en `tests/test_candidato_contratar_sin_transaccion.py`**, no supuesto:

| Reintento | Qué pasa | Por qué |
|---|---|---|
| Con el MISMO `email_corporativo` | **409 `EMAIL_CORPORATIVO_DUPLICADO`, no duplica** | choca `empleados_email_corporativo_key`, que es UNIQUE GLOBAL, y A4.1 lo traduce |
| Con OTRO `email_corporativo` | 🔴 **crea un SEGUNDO legajo para la misma persona** | las cinco guardas siguen pasando (el candidato quedó en `activo`) y nada más colisiona |

🔑 **Por qué nada más lo frena:** el puente **no setea `legajo`** —y `ensure_legajo_unico` corta
temprano cuando es `None`— ni **`dni`**, que es la otra unicidad de la tabla. O sea que la única
red es el email, y sólo si el operador repite el valor.

**No se implementó compensación, y es deliberado:** borrar el empleado recién creado sería una
segunda escritura que también puede fallar, y dejaría el caso peor — un alta auditada y después
borrada, sin rastro del porqué. **La salida correcta cuando esto importe es un endpoint de
reconciliación** que, dado un candidato en `activo` cuyo email corporativo ya existe como
empleado, cierre el estado sin crear nada. 🚩 Disparador: la primera vez que pase en producción.

### 🔴 `tipo_contrato` lo INVENTA el puente, y nadie lo decidió

`EmpleadoCreate.tipo_contrato` es **requerido** y el puente no tiene de dónde sacarlo:
`candidatos` no lo tiene, y el de la vacante es **otro vocabulario** (`efectivo | plazo_fijo |
contratado | pasantia` contra el TEXT libre de `empleados`, cuyo padrón real dice "Relación de
dependencia"). Sin un valor, `EmpleadoCreate(**campos)` levanta un ValidationError que el handler
global convierte en 500 — el puente entero inutilizable.

Se puso `TIPO_CONTRATO_POR_DEFECTO = "Relación de dependencia"`
(`services/_candidato_contratar_mapeo.py`), **el mismo default que ya aplica el formulario de alta
manual**, para que las altas por el puente y las manuales no queden en dos grupos distintos de
todo reporte que agrupe por ese campo. **Es un default de producto que nadie declaró.** 🚩
Disparador: que RRHH contrate por este camino a alguien con otro tipo de contrato. La salida NO es
copiar el de la vacante —son vocabularios distintos— sino **sumarlo al body**, que es una decisión
de producto de una línea.

### 🟡 Dos fixtures de candidato usan etapas que el CHECK rechazaría

`test_exports_limpieza.py:203` usa `etapa_pipeline="entrevista"` y `:219` /
`test_paginacion_candidatos_evaluados.py:146` usan `"nuevo"`. **Ninguno de los dos está en
`candidatos_etapa_check`** (`postulado | assessment | entrevista_rrhh | entrevista_tecnica |
oferta`). Pasan porque `CandidatoResponse.etapa_pipeline` es `str` sin validar, así que Pydantic
los acepta y la base nunca los ve.

No rompen nada hoy —esos tests no escriben— pero **son el molde del que copia el próximo**, y ahí
el valor sí llegaría a un INSERT. El padrón de A4.2 (`tests/_contratar_padron.py`) los evitó a
propósito y lo dice en su encabezado. **Arreglo real:** tipar `etapa_pipeline` como `Literal` de
los cinco, igual que se hizo con `estado` en A4.1 — cuesta lo mismo y cierra la clase entera.

### 🟠 `candidato_repo.py` quedó en 100/100 — el corte ya está identificado

Llegó al techo exacto con el delegador de `update_estado`. **El archivo hoy es legal y no se
toca**; lo que se anota es que **el próximo método exige dividir antes**. El corte identificado:
los dos delegadores de la ingesta por mail —`existe_cv_de_gmail` y `message_ids_procesados`— se
van con `_candidato_gmail`, que es el módulo cuyas funciones ya envuelven. Mismo criterio con el
que se anotaron `sucesion_repo` y `routers/empleados.py`.

---

## 8-ter. Lo que A4.1 midió y decidió NO arreglar (18/8/2026)

### 🔴 Las 5 unicidades sin protección — inventario de las 62, ordenado por probabilidad de que alguien las pise

A4.1 tradujo el 23505 de `empleados` a 409 (`services/_empleado_duplicado.py`). **El grep global
de la regla D encontró que no era el único caso**, y el alcance se acotó a propósito: se arregló
sólo `empleados`, que es el que bloqueaba el puente candidato→empleado.

De las **62 unicidades del catálogo**, la mayoría no puede chocar o ya está cubierta:

- **No pueden chocar:** las 20 del patrón `(id, empresa_id)` —existen para respaldar FKs
  compuestas y el `id` es un uuid generado—, `vacantes.codigo` (DEFAULT con `nextval`, atómico),
  `sesiones_horas.token_hash` y `oauth_states.state_hash` (256 bits de entropía).
- **Ya protegidas por pre-chequeo:** `users` (`email_existe`/`username_existe`),
  `clientes` (`existe_nombre`), `perfiles_puesto`, `tipos_ausencia`, `proyecto_asignaciones`
  (`ASIGNACION_DUPLICADA`, tratado como idempotencia), `horas_proyecto` (`LICENCIA_DUPLICADA`).
- **Ya protegidas por `on_conflict` (upsert):** `costos_nomina`, `presupuesto_areas`,
  `parametros_empresa`, `parametros_screening`, `plantillas_mail`, `usuario_integraciones`,
  `evaluacion_equivalencias`, `empleado_superior_pendiente`.
- **Ya protegida por traducción del 23505:** `objetivos` (`_objetivos_duplicado`) y ahora
  `empleados` (`_empleado_duplicado`).

**Quedan estas cinco, sin pre-chequeo, sin `on_conflict` y sin traducción — o sea que hoy un
choque sale como 500 `INTERNAL_ERROR`:**

| # | Tabla | Unicidad | Por qué está en este orden |
|---|---|---|---|
| 1 | ✅ `empleado_capacitacion` | `(capacitacion_id, empleado_id)` + `ux_ec_nombre_libre` | **CERRADO en A5 (19/8/2026)** — `_formacion_duplicado` traduce el 23505. Ver la nota de abajo. |
| 2 | `areas` | `codigo` — **GLOBAL, sin empresa** | Dos empresas que quieran un área con el mismo código chocan. Con 2 empresas y 12 áreas cargadas ya es alcanzable a mano, y el operador no tiene forma de saber que el código lo tomó otra sociedad. |
| 3 | `empresas` | `cuit`, `nombre` | Alta manual, campos que se tipean. `_validate_cuit` valida **formato**, no unicidad — es fácil leerlo como si cubriera las dos cosas. Baja frecuencia: se cargan 2–5 empresas en la vida del sistema. |
| 4 | `vacaciones_pendientes` | `(empleado_id, periodo)` | `insert` crudo. Hoy la tabla está en 0; se vuelve alcanzable cuando RRHH cargue los saldos por período. |
| 5 | `evaluacion_evaluados` / `evaluacion_resultados` | claves del lote | El import ya verifica por CONTEO y el `confirmar` crea el lote con período temporal, así que un choque acá es raro **y además no pierde datos**. Es el menos urgente de los cinco. |

> ✅ **`empleado_capacitacion` — RESUELTO dentro de A5 (19/8/2026), exactamente como esta nota lo
> pedía.** La decisión que faltaba se tomó con el archivo real en la mano: el import **reporta la
> fila duplicada** (no `on_conflict` — que además la parcial `ux_ec_nombre_libre` no soporta, por
> ser índice por expresión). `services/_formacion_duplicado.duplicado_legible` traduce el 23505
> de los DOS índices a `FORMACION_DUPLICADA` (409) con mensaje legible; reimportar el mismo
> archivo reporta duplicados fila por fila, sin 500 y sin duplicar
> (`tests/test_formacion_import.py::TestReimport`). El alta manual de asignaciones sigue con su
> `except Exception → YA_ASIGNADO` de siempre (`asignacion_service.create`) — más ancho, pero
> anterior y con un solo camino de escritura. La nota original queda abajo para el contexto de
> los otros cuatro casos de la tabla, que siguen abiertos.

> *(La nota original, del 17/8:)* `empleado_capacitacion` se arregla dentro de A5, cuando el
> import del Excel inserte sus 53 filas. Hoy el choque es hipotético porque las asignaciones se
> cargan de a una desde la UI y repetir la misma a mano es difícil. Con un import de 53 filas
> deja de serlo: una corrida repetida —que es el caso normal, no el excepcional: alguien
> reintenta porque no está seguro de si la primera terminó— choca en la primera fila ya cargada
> y el import entero muere con un 500 sin decir por qué. Es el mismo perfil de bug que ya pagó
> el import de objetivos, y ahí la salida fue exactamente ésta (`_objetivos_duplicado`). No
> adelantarlo: el arreglo correcto depende de si el import va a ser idempotente por
> `on_conflict` o va a reportar la fila duplicada, y eso se decide con el archivo real de RRHH
> en la mano.

> 🚩 **Y la misma UNIQUE tiene un segundo problema, distinto del choque por reintento: PROHÍBE la
> recertificación anual para las filas CON empleado.** `UNIQUE (capacitacion_id, empleado_id)` no
> lleva el año, así que la misma persona en el mismo curso en dos años distintos es un duplicado
> para la base — mientras que `ux_ec_nombre_libre` SÍ lleva `anio`/`mes` en la clave, pero solo
> rige `WHERE empleado_id IS NULL`. O sea: la recertificación anual —caso real del Excel, que la
> verificación (F) de la migración 116 celebra— **funciona para los nombres sueltos y está
> bloqueada para los matcheados.** Hoy no choca (las 2 repeticiones del archivo 2026 son cursos
> distintos); **el import de 2027 sí**. El arreglo es DDL (sumar el año a la clave, o una parcial
> equivalente) y quedó **fuera de alcance** de la sesión del 19/8 que cableó las columnas —
> decidirlo junto con el import de A5.2, que es quien define la semántica de idempotencia.

### 🟠 "Vacaciones sin resolver" — la tercera alerta del panel de atención NO existe (A6, 19/8/2026)

El sistema de diseño lista tres alertas calculadas para "Requiere tu atención"; se implementaron
DOS (ingresos próximos, fin de período de prueba). **"Vacaciones sin resolver" no se puede
calcular porque el dato no existe**: `solicitudes_vacaciones` no tiene estado de aprobación —sus
columnas son fechas, `dias`, `cancelada`, `tipo`, `periodo`, `dias_liquidados`— y el "estado"
que muestran las pantallas se DERIVA del calendario (`derive_estado`). "Sin flujos de
aprobación" fue decisión de producto de la primera época; el prototipo del sistema de diseño
promete encima de un modelo que no la tiene. Salidas posibles, ninguna decidida: (a) construir
el flujo de aprobación (feature grande, revierte una decisión); (b) reinterpretar la alerta
sobre `vacaciones_pendientes` (saldos adeudados por período — otro significado, hoy 0 filas);
(c) sacarla del diseño. **Se eligió alertar UNA cosa menos antes que una que miente** — decidir
con RRHH/directorio, no en una sesión de código.

### 🔴 Los 32 repos con `select("*")` — una pregunta que el repo no sabe hacer

`candidatos.estado` vivió meses con el `select("*")` trayéndola y el mapper descartándola, con
**tres barridos estructurales mirando ese módulo y los tres en verde**. La causa no es que
fallaran: es que los tres viajan en la dirección **código → base**, y este bug vive en la
contraria.

🔑 **Lo importante, y por eso está redactado así: `test_selects_repos` no está roto. Su aserción
es vacua POR CONSTRUCCIÓN.** Pregunta *"¿existe en la tabla todo lo que el `select` PIDE?"*, y
`_postgrest_schema._validar_columna` corta con un `return` en cuanto ve el asterisco. Un select
que pide todo no puede pedir de más. **Es la diferencia entre "hay que arreglar un test" y "hay
una pregunta que el repo no sabe hacer"**, y esa distinción es la que decide qué se construye:
lo primero se parchea, lo segundo necesita un barrido nuevo.

Los otros dos tampoco podían: `test_mappers_ejercitados` persigue mappers con
`if not rows: return []` —`_crow` recibe un dict, no tiene ese early-return y `descubrir()` ni lo
lista, y aunque lo listara, ejercitar un mapper prueba que su cuerpo CORRE, no que mapee todas las
columnas—, y `test_contrato_repos` compara métodos entre capas, que no sabe qué es una columna.

**Estado (remedido el 19/8/2026):** hoy son **30 archivos** de `repositories/` los que leen con
`select("*")` (el 32 era la medición anterior; la lista se mueve con cada corte de repo). El
patrón cubre **3 tablas — candidatos, capacitaciones y empleado_capacitacion — o sea 4 de esos
30 archivos** (`candidato_repo` + `_candidato_row`, `capacitacion_repo`, `asignacion_repo`):
`tests/test_columnas_candidatos.py` y `tests/test_columnas_capacitaciones.py`, este último con el
concepto `DERIVADOS` para los campos que resuelve un join (el porqué de no retrofitearlo en
candidatos está en el encabezado de `tests/_columnas_capacitaciones.py`). Quedan **26 sin
barrido**.
**Qué haría falta:** por cada repo, la tabla + el modelo de salida + la tabla de renombres y de
columnas no expuestas CON su razón (el inventario de candidatos son 11 entradas). El barrido en sí
ya está escrito y es genérico salvo por esas declaraciones.
**Por qué no se generalizó ahora:** parametrizar la maquinaria contra un solo caso fija una forma
que no se probó contra ningún segundo. Se generaliza con el dato del segundo repo, no antes.
**Gravedad:** 🟠 — cada repo sin cubrir es una columna que se puede estar descartando en silencio,
que es un bug sin síntoma.

### 🟡 Por qué el barrido de listas de estado NO generaliza — medido, no supuesto

`procesos_service._ESTADOS` declaraba `en_revision` para `vacantes`, un estado que no está en
ningún CHECK. La pregunta natural es si `_barrido_estado.py` se puede extender a "toda lista de
literales de estado contrastada contra el CHECK de su tabla". **Se midió: no.**

- El barrido actual busca **comparaciones** (`.eq/.neq/.in_("estado", X)`, `==`/`!=`, kwargs), y
  acá no hay ninguna: el valor llega a la query como una VARIABLE dentro de un `for`. Además cubre
  `empleados.estado` y nada más — su línea 176 nombra el `== "cerrada"` de vacantes como ejemplo
  de lo que **descarta**, no de lo que vigila. (Es fácil leerla al revés; quedó escrito.)
- Contrastar contra la **unión de los 11 CHECK** da **5 falsos positivos sobre 6 estructuras**,
  porque **el valor y su etiqueta humana conviven en la misma estructura**: `_ESTADO_LABEL` mapea
  `"cerrada" → "Cerrada"`, y `"Cerrada"` no está en ningún CHECK ni tiene por qué estar.
- **Lo indecidible es a qué TABLA pertenece cada lista.** Distinguir el valor de la etiqueta exige
  conocer la forma de cada estructura, y esa forma difiere por módulo — o sea, escribir un test por
  módulo, que es lo que ya se hizo.

🔑 **En `procesos_service` se pudo por un motivo que no se generaliza: `_ESTADOS` está indexado
POR NOMBRE DE TABLA**, así que la tabla es la clave del dict y no hay que adivinarla. Eso convirtió
un problema indecidible en una comparación directa, y por eso `tests/test_procesos_estados.py`
cubre las **5 tablas del panel** y no sólo la que estaba rota. **Si alguien aplana esa estructura,
se pierde el test** — está anotado también en `services/_procesos_catalogo.py`.

### 🟡 El loader de `schema.sql` cargaba una columna fantasma en 11 de 55 tablas — ARREGLADO

`tests/_postgrest_schema.cargar_schema` parsea las columnas con `linea.split()[0]` y salteaba las
líneas de constraint por palabra clave, **pero no las de comentario**. `schema.sql` documenta
columnas con comentarios `--` DENTRO del `CREATE TABLE` (los de la mig 081 en `empleados`, los de
la 098–101 en `candidatos`, los de la 113 en `vacantes`…), así que **11 de las 55 tablas cargaban
una columna llamada `--`**.

🔑 **Qué lo hacía invisible, que es la parte reutilizable:** el único consumidor era
`validar_select`, y una columna de más sólo **ensancha el conjunto de nombres ACEPTADOS**. Nadie
escribe `select("--")`, así que el fantasma no podía producir ni un rojo ni un falso verde — el
defecto era real y estrictamente inobservable desde el uso que se le daba.

**Qué barrido futuro habría roto:** cualquiera que **recorra `columnas[tabla]`** en vez de
preguntarle por un nombre concreto. El primero fue `test_columnas_candidatos`, que compara el set
de columnas contra los campos del schema: con el fantasma adentro habría exigido declarar `--` en
la tabla de no expuestas — una entrada absurda que quien la viera habría "resuelto" agregándola,
dejando el defecto tapado en el único lugar donde por fin era visible. Arreglado en la misma tanda
(A4.1), antes de escribir el barrido que dependía de él.

> **La regla que deja:** un lector de schema que se usa sólo para VALIDAR contra nombres dados
> puede tener defectos que ensanchan, y ninguno se nota. Antes de usarlo para ENUMERAR, verificar
> que lo que devuelve sean columnas y nada más.

---

## 8-bis. 🟠 `procesos_service` no degrada: una tabla que falla se lleva el panel entero

> **11/8/2026, bloque J5a.** Es lo que convirtió un DROP de tablas en un 500 de una pantalla que
> no tenía nada que ver. Se deja anotado, **no se arregló en esta sesión**.

`services/procesos_service.py:70-83` arma los procesos así:

```python
procesos = [self._build_proceso(t, p, l, eid) for t, p, l in _META]   # :77-80
except Exception as exc:
    raise AppError("Error al obtener procesos", "PROCESOS_ERROR", 500)  # :83
```

**Los 7 procesos viven o mueren juntos.** Si UNA tabla no responde —dropeada, renombrada, un blip
de PostgREST— el `except` se lleva las otras seis, que estaban perfectas. El usuario ve
"No se pudo cargar el panel de procesos" (`frontend/app/(dashboard)/procesos/page.tsx:90`) y no
tiene forma de saber cuál falló.

🔑 **El repo ya tiene el patrón correcto y este archivo no lo usa:** `services/dashboard_service.py`
calcula cada KPI con un `_safe` y devuelve los demás aunque uno falle, marcando el fallido en
`errores`. Portarlo acá es la corrección: un `_safe` por proceso, más una lista de fallidos en
`ProcesosResponse` (lo que obliga a tocar `schemas/procesos.py` y la pantalla).

⚠️ **Y hay un segundo modo de falla en el mismo archivo, más silencioso:** `_build_proceso:100`
hace `_ESTADOS[tabla]`, que revienta con `KeyError` si alguien agrega una entrada a `_META` y se
olvida de `_ESTADOS`. Sale por el mismo `except` genérico y produce el mismo 500 opaco, sin decir
que la causa es una tabla mal declarada y no la base. Las dos estructuras se editan a mano y nada
las ata. Gravedad 🟠 · Esfuerzo M.

---

## 8-quinquies. 🟡 El dashboard quedó con DOS paneles de avisos (19/8/2026, bloque B4)

> **Decisión de producto pendiente, no bug.** El código funciona y las dos listas son correctas;
> lo que falta definir es si tienen que seguir siendo dos.

Al cablear `GET /api/dashboard/atencion` (A6) la instrucción inicial era que el panel nuevo
**reemplazara** a `AlertasPanel`, para no mostrar la misma alerta dos veces. Se midió antes de
borrar nada y **la intersección entre los dos endpoints es CERO**:

| `GET /api/dashboard/atencion` (panel "Requiere tu atención") | `GET /api/dashboard` → `alertas` (panel "Alertas activas") |
|---|---|
| `ingreso_proximo` (calculada) | los 5 **bloqueos de módulo**: `costos_nomina`, `inventario_items`, `capacitaciones`, `presupuesto_areas`, `vacantes` vacías (`services/_dashboard_alertas_catalogo.py:31-52`) |
| `fin_periodo_prueba` (calculada) | **campos vacíos del padrón**: N empleados sin manager, con link al listado filtrado (`_dashboard_alertas.py:70-95`) |
| `evento_manual` (manual, con autor) | 2 **derivadas de KPIs**: vacantes activas, onboardings en curso (`_dashboard_alertas.py:98-107`) |

Reemplazar habría borrado la columna derecha entera, **que no la muestra ninguna otra pantalla** —
incluido el aviso de `costos_nomina` vacía, que hoy es la única explicación visible de por qué la
masa salarial y el historial salarial salen en cero. Por eso **conviven**: atención arriba (lo
accionable sobre personas esta semana), alertas abajo (la salud del sistema), con títulos que
dicen cuál es cuál.

🔴 **Lo que queda por decidir, y es de Capital Humano, no de desarrollo: si "no hay ítems de
inventario cargados" es una ALERTA o es otra cosa.** Un bloqueo de módulo no es un aviso que se
atiende y se cierra: es un estado que dura meses y que solo se resuelve cargando datos. Mezclarlo
en una caja llamada "alertas" junto a cosas que sí se resuelven en el día enseña a ignorar la
caja. Candidatos: un bloque de "puesta a punto" con checklist de carga inicial, un aviso por
módulo dentro de cada pantalla, o dejarlo como está. **Entra en el reestilado del dashboard, no
antes.** Gravedad 🟡 · Esfuerzo S (es mover, no construir).

---

## 9. Superficies que dibuja el NAVEGADOR y el tema oscuro no alcanza

> **11/8/2026.** Relevado entero al arreglar el contraste del popup de los `<select>`
> (`app/globals.css:131-158`, regla sobre `option`/`optgroup`). **Ese caso quedó cerrado; estos
> cuatro NO se tocaron.** Comparten el modo de falla —el navegador o el SO pintan el control con
> su propio estilo y el tema no llega— pero **cada uno necesita un mecanismo distinto**, y por eso
> ninguno se resuelve extendiendo la regla que se acaba de escribir.

| Qué | Dónde | Por qué la regla de `option` no lo cubre | Gravedad | Esf. |
|---|---|---|---|---|
| **Autofill de Chrome — cero reglas `-webkit-autofill` en TODO el repo** (verificado por grep sobre `.css`/`.tsx`/`.ts`). Chrome pinta su propio fondo claro ENCIMA del campo y el tema no lo saca | `app/login/page.tsx:111` (`autoComplete="username"`) y `:134` (`current-password`) · `components/features/usuarios/CambiarPasswordForm.tsx:78,82,86` | Es un pseudo-elemento del navegador sobre `input`, no un `option`. Pide su propia regla (`:-webkit-autofill` + `box-shadow` interior o `-webkit-text-fill-color`) | 🟠 | S |
| **8 `<textarea>` crudos sin `placeholder:text-muted-foreground`** — el placeholder cae al color de UA. De los 9 `<textarea>` que no usan el componente, **solo `ProyectoModal.tsx:89` lo declara** | `components/layout/AIPanel.tsx:207` · `features/comunicacion/EnvioLibre.tsx:30` · `features/configuracion/ScreeningSection.tsx:57` · `features/onboarding/NuevoTemplateModal.tsx:109` · `features/onboarding/AddTareaForm.tsx:57` · `features/onboarding/InlineEdit.tsx:74` · `features/screening/CorregirClasificacion.tsx:79` | No es el navegador dibujando: es que esquivan `components/ui/textarea.tsx:11`, que ya trae la clase. **Se arregla migrando al componente `Textarea`, no con CSS global** — el CSS taparía el desvío en vez de corregirlo | 🟡 | S |
| **132 tooltips nativos (`title=`) en 30+ archivos** — los dibuja el SISTEMA OPERATIVO | `title=` en `app/(dashboard)/` (areas, auditoria, empleados, reportes, costos, empresas, objetivos, offboarding, onboarding, proyectos, … 30 archivos) | 🔴 **No se pueden estilar con CSS de ninguna forma**, ni con `color-scheme`. La única salida es reemplazarlos por un componente de tooltip propio — es una tanda de UX, no un fix de contraste | ⬜ | L |
| **10 `<input type="checkbox">` sin `accent-color`** — cero usos de `accent-color` en el repo, así que el check se dibuja con el azul del SISTEMA y no con `--primary` | los 10 checkbox del front, incluidos los `multiselect` de `components/ui/FiltersBar.tsx` | Es una propiedad sobre `input`, no sobre `option`. Una línea en `@layer base`, pero es decisión de MARCA (coherencia con `--primary`), no el bug de legibilidad que se arregló | ⬜ | S |

### ✅ ~~El botón primario en modo oscuro no llega a 4.5:1~~ — **CERRADO el 19/8/2026**

> **Lo cerró la paleta de `docs/SISTEMA-DE-DISENO.md` §1**, aprobada por Capital Humano el 16/8
> después de cuatro iteraciones — o sea, por la vía que este ítem pedía: una decisión de marca,
> no un ajuste de test. La salida elegida fue la segunda de las dos que estaban planteadas acá:
> **`--primary-foreground` dejó de ser blanco en oscuro** y pasó al fondo de página (`#0B1220`),
> con `--primary` aclarado a `#7DA9FB`. El par pasó de **3.68:1 a 7.97:1**.
> Se arregló junto con `--sidebar-primary/--sidebar-primary-foreground`, que arrastraba la misma
> brecha con el mismo valor y **este ítem no mencionaba** (era el mismo azul declarado en una
> segunda variable; tocar una sola habría dejado el ítem activo del sidebar con el contraste
> viejo).
> Las dos entradas se **borraron** de `BRECHAS_DECLARADAS`, que es lo que el propio ítem
> anticipaba: la verificación es en las dos direcciones y una excepción que ya cumple pone el
> test en rojo. `BRECHAS_DECLARADAS` quedó **vacío**.

El diagnóstico original, que sigue siendo la explicación de por qué pasó. ⚠️ **Todo lo que
sigue hasta el aviso de los `input type="date"` es el texto del 11/8/2026, conservado sin
editar: describe el estado ANTERIOR al cierre, no el de hoy.** En particular, donde dice "no
se arregló" y "queda vigilado en `BRECHAS_DECLARADAS`", hoy se lee al revés: se arregló, y
por eso la entrada ya no está.

Salió al escribir `frontend/app/contrasteTokens.test.ts`, que mide los pares de tokens de verdad:

| par | modo claro | modo oscuro |
|---|---|---|
| `--primary` / `--primary-foreground` | `#1a56db` sobre blanco → **6.18:1** ✅ | `#3b82f6` sobre blanco → **3.68:1** 🟠 |

**El azul se aclaró para que el botón resaltara contra el fondo oscuro de la página, y eso bajó
el contraste del texto que va ENCIMA del botón.** Afecta a todo `variant="default"` de
`components/ui/button.tsx:11` (`bg-primary text-primary-foreground`) en modo oscuro — o sea, el
botón primario de cada pantalla. `docs/UX-UI.md:630` pide 4.5:1 para texto normal.

**No se arregló en esta sesión: es una decisión de MARCA**, no un fix mecánico. Las dos salidas
son oscurecer `--primary` en `.dark` (y perder resalte contra el fondo) o dejar de usar blanco
puro en `--primary-foreground`. Elegir por nuestra cuenta cambiaría el color del botón principal
del producto entero.

Mientras tanto **queda vigilado en las dos direcciones**: está declarado en `BRECHAS_DECLARADAS`
con su ratio medido, así que el test rojea si empeora **y también si mejora** (para que se saque
la excepción en vez de quedar de adorno).

> ⚠️ **Lo que SÍ debería estar cubierto y no se verificó en navegador:** los **29 `input type="date"`**
> (ícono `::-webkit-calendar-picker-indicator` y popup del calendario) y los **56 contenedores con
> `overflow-*-auto`** (scrollbars). Los dos dependen del `color-scheme` que **next-themes escribe
> inline en `<html>`** (`enableColorScheme` viene en `true` y `components/layout/ThemeProvider.tsx`
> no lo apaga). **No hay ninguna regla propia en el repo para ellos.** Si en la prueba visual
> aparecen mal, el diagnóstico cambia de raíz: querría decir que el `color-scheme` inline NO está
> llegando, y eso es un ítem nuevo — no se arregla con más CSS por control.

### 🟠 `utils/colorEmpresa.ts` — 26 hex que ningún token alcanza, porque se aplican INLINE

> **19/8/2026**, anotado al aplicar la paleta de Capital Humano. **No se tocó en esa sesión, a
> propósito**: el arreglo pasa por cambiar el MECANISMO, no el valor, y eso es una sesión propia.

`utils/colorEmpresa.ts` tiene **26 hex** repartidos en **8 paletas pastel** (`bg`/`text`/`dot` por
empresa, más `MULTI_PROY`) y se aplican con **`style={{ background, color }}` INLINE**. Las tres
componentes que las consumen son las del organigrama —**14 puntos de aplicación**, no los tres
que se suelen citar—: `components/features/organigrama/ArbolProyecto.tsx` (`:21`, `:32`, `:38`,
`:55`, `:126`, `:156`, `:162`, `:163`), `CardsProyecto.tsx` (`:16`, `:23`, `:32`, `:80`) y
`ArbolEmpresa.tsx` (`:13`, `:93`).

🔴 **El estilo inline gana sobre cualquier clase o variable.** Son 8 paletas pastel claras con
texto oscuro, y **en modo oscuro quedan como parches blancos**: ninguna clase de Tailwind ni
ningún token de `globals.css` los alcanza. Cambiar la paleta del producto —como se acaba de
hacer— no los mueve un milímetro.

🔴 **Y `contrasteTokens.test.ts` no los mira, porque solo lee `globals.css`.** No es una falla del
barrido: es su alcance. Un color que nace en un `.ts` y viaja por `style={{}}` no pasa por ninguna
hoja de estilo, así que no hay archivo donde el test pueda encontrarlo. Está anotado también en el
encabezado del propio test, para que un verde suyo no se lea como "el front entero cumple".

**Por dónde va el arreglo cuando se haga:** que las 8 paletas dejen de ser hex literales y pasen a
ser variables CSS con su variante oscura (o pares `bg-*`/`text-*` de Tailwind), y que los
componentes apliquen **clases**, no `style`. Mientras siga siendo `style={{}}`, cualquier tema que
se defina arriba es decorativo para estas tres pantallas. Gravedad 🟠 · Esfuerzo M.

---

## Orden recomendado de ataque

**✅ Tandas 1 a 5 — HECHAS el 2/8/2026**, salvo lo que se separó a propósito:
1. ✅ `EMPRESA_MISMATCH` ×2 · ✅ borrado de los 3 muertos · ✅ `CLAUDE.md`,
   `ESTADO-VS-COMPROMISO.md` y `MATRIZ-FILTROS.md` al día · ✅ los 7 over-limit (5 partidos,
   2 borrados) + `usuario_service` · ✅ el test del espejo de permisos.
2. 🚩 **Queda de la tanda 1:** auditoría del import de costos (2b), `_costos_write` con la empresa
   de la entidad (2c) y los 3 eventos mal etiquetados (2c2). **Se separaron a propósito: son fixes
   de COMPORTAMIENTO, no limpieza**, y merecen su propia sesión con tests de auditoría.
3. 🚩 **Queda de la tanda 4:** los **2 hooks del front sobre 80** (`useFiltrosVacaciones` 95,
   `useFiltrosAsignacionesCap` 89) y los 33 archivos del front sobre 150, con
   `costos/page.tsx` (624) y `vacantes/[id]/page.tsx` (577) a la cabeza.

**Fuera de código — pedidos a RRHH (bloqueantes reales).**
9. **Reimportar la nómina** para poblar `manager_id` (hoy 0/19): sin eso, `mandos_medios` no ve
   nada y todo el ownership cruzado que se construyó está sin ejercitar.
10. **Definir el ancla del import de vacaciones** (legajo en la nómina, o DNI en el archivo).
11. **Deduplicar `GESTION DE DEUDA`**.
12. Definir si `valor_hora = 0` es cero o "no sabemos".

> **Lo que NO recomiendo tocar en esta limpieza:** los 7 `empresa_id !=` de Forma B (2a2) — son
> correctos, solo menos elegantes, y migrarlos toca 6 services vivos por cero cambio observable.
> Y las 6 tablas huérfanas: se limpian en el cutover a AWS, como ya está decidido.
