# Estado real del sistema vs. lo comprometido con el directorio

**HR Karstec (RRHH)** · **Verificado el 5 de agosto de 2026**

> ⚠️ **Vencimiento parcial, anotado el 12/8/2026.** El documento no se rehízo, pero **una semana
> de trabajo pasó por encima de él**: se cerraron los bloques E, F, G, H, L y J5. Lo que cambia de
> lo de abajo, sin tocar los veredictos que siguen valiendo:
> - Las referencias a **`routers/ev_instancias.py`** apuntan a un archivo **borrado** el 11/8
>   (bloque J5). El export de evaluaciones que sigue vivo es `evaluaciones_resultados_export.py`.
> - **Export**: pasó de 12 a **25 módulos** (bloque H). Cualquier fila que diga "no exporta"
>   conviene reverificarla contra `docs/MATRIZ-FILTROS.md`.
> - **Datos de producción** (12/8): 2 empresas · 31 empleados · `manager_id` **11/31** ·
>   4 clientes · 1 carga de horas · 3 candidatos · `auditoria` 156 filas. `costos_nomina`,
>   `solicitudes_vacaciones` y `solicitudes_ausencia` **siguen en 0**, que es lo que sostiene la
>   distinción 🟡 de arriba.
> - **Rehacerlo entero es una sesión propia**, y va antes de volver a mostrarle esto al directorio.

---

## Cómo se lee este documento

Contraste ítem por ítem entre lo que se comprometió con el directorio en **junio de 2026**
(plan de implementación + documento ejecutivo) y lo que el sistema **realmente hace hoy**.

**Todo se verificó de nuevo**, contra el código fuente y contra la base de datos de producción
consultada en vivo. Nada se arrastró de versiones anteriores de este documento.

### Los tres estados

| | Qué significa |
|---|---|
| ✅ **TERMINADO Y PROBADO** | Funciona, y se comprobó con datos reales cargados en producción. |
| 🟡 **TERMINADO, SIN PROBAR** | El sistema lo tiene construido, pero **nunca se usó de verdad**. La columna "qué falta" dice exactamente qué hace falta para poder probarlo: una acción de Franco, datos que tiene que cargar RRHH, o una cuenta que hay que conectar. |
| 🔴 **FALTA** | No está construido. La columna dice qué lo bloquea. |

> ⚠️ **La diferencia entre los dos primeros es lo más importante de todo el documento.**
> Buena parte de lo que se construyó en los últimos dos meses está entero y **nunca se ejercitó**,
> porque la base de datos está casi vacía. Eso no es lo mismo que "terminado", y no se puede
> presentar como tal: si el directorio abre una de esas pantallas hoy, la va a ver en blanco.

### Cómo está verificado

Cada fila trae la evidencia: el archivo y la línea del código, o el nombre del dato en la base.
Donde no se pudo verificar, dice **NO DETERMINADO** — nunca una suposición. La base se consultó
en vivo, no a través de las migraciones, porque producción puede haberse desviado de ellas.

---

## Resumen en una pantalla

**44 ítems comprometidos** (16 de la Entrega 2, 16 de la Entrega 3, 12 del frente AWS):

| | Cantidad | Lectura |
|---|---:|---|
| ✅ Terminado y probado | **13** | Funcionando con datos reales |
| 🟡 Terminado, sin probar | **14** | Construido y esperando datos o una acción |
| 🔴 Falta | **17** | De los cuales **12 son del frente AWS**, que no se empezó |

**Fuera de eso hay 20 entregas más que no estaban comprometidas** (sección "Lo entregado que no
estaba comprometido") y **5 fallas graves que se encontraron y arreglaron** sin que nadie las
hubiera reportado (sección siguiente).

🔴 **El titular:** el sistema está mucho más construido de lo que se puede demostrar hoy. **El
cuello de botella no es desarrollo: son los datos.** Ocho módulos abren pantallas vacías porque
RRHH todavía no cargó vacaciones, ausencias, sueldos, inventario ni capacitaciones.

---

## Entrega 2 — 16 ítems

| # | Ítem comprometido | Estado | Evidencia | Qué falta / cómo quedó |
|---|---|---|---|---|
| **1** | Roles: administración completa, gerencia solo lectura, mandos medios sobre vacaciones y ausencias de su área | 🟡 | `backend/utils/permisos.py:78` (los tres roles) · `:107-112` (qué puede cada uno) · `:73` (mandos medios: solo vacaciones y ausencias) · espejo en la pantalla: `frontend/services/permisos.ts` | Los roles de administración y gerencia se usan todos los días. **El rol de mandos medios nunca se probó: no existe ningún usuario con ese rol.** Y hay un cambio de alcance: el alcance de un mando medio **no es su área, es la gente que le reporta** (`services/ownership.py`). Recién ahora es probable, porque el jefe de cada persona está cargado en 11 de 31 empleados |
| **2** | Aislamiento real por empresa: validar la empresa activa contra el acceso del usuario | ✅ | Barrera de empresa en **92 endpoints** (commits `bd95e98` + `9d7baa7`): toda consulta filtra por la empresa del pedido · validación de la empresa recibida: `backend/middleware/_empresa_header.py:13,17,47` | **Cambió de alcance, a favor.** No existe "acceso por usuario" porque la decisión de producto es que **todo usuario ve todas las empresas** — no hay tabla `acceso_empresa` y no la va a haber. El aislamiento se resolvió por una vía más fuerte: antes, el identificador de un dato de otra empresa entraba igual y la operación se ejecutaba sobre él; hoy responde "no encontrado". **Probado con las 2 empresas cargadas** |
| **3** | Registro de cambios en todos los módulos + pantalla de historial | ✅ | 29 servicios registran eventos · pantalla `frontend/app/(dashboard)/auditoria/page.tsx` · en el menú: `nav-config.ts:85` · **139 eventos reales** en la base | Dos huecos conocidos: la **importación de sueldos no deja registro** (`routers/importacion_nomina.py`), y un registro de presupuesto se etiqueta con la empresa que el usuario tiene seleccionada en pantalla en vez de la del dato (`services/_costos_write.py:80`). Con una sola empresa operando todavía no causó ningún error |
| **4** | Bloqueo de módulos con fecha configurable desde el panel | 🟡 | Tabla `periodos_cerrados` · `backend/routers/periodos.py`, activo en `main.py:171` · pantalla `/periodos` en el menú (`nav-config.ts:91`) · el bloqueo se aplica en vacaciones, ausencias y sueldos | **Nunca se cerró un período: la tabla tiene 0 filas.** Y hay una limitación de diseño que conviene saber: `services/_periodo_utils.py:57` hace que **el bloqueo solo alcance a los mandos medios**. Un usuario de administración puede seguir cargando sobre un período cerrado |
| **5a** | Legajo: **sexo** | ✅ | `backend/schemas/empleado.py:63` · se ve y se edita en la ficha | — |
| **5b** | Legajo: **horas de contrato** | ✅ | `schemas/empleado.py:69` | — |
| **5c** | Legajo: **gerencia** | ✅ | `schemas/empleado.py:71` | — |
| **5d** | Legajo: **superior inmediato** | ✅ | `schemas/empleado.py:103,121` · **cargado en 11 de 31 empleados** | Se completa con la importación de nómina. Falta que RRHH complete los 20 restantes |
| **5e** | Legajo: **domicilio completo** | 🟡 | Seis campos separados —calle, número, piso, localidad, provincia, código postal— en `schemas/empleado.py:80-85`; la provincia es una lista cerrada de las 24 jurisdicciones (`schemas/_provincias.py`) | **Los seis campos están vacíos para los 31 empleados.** Falta que RRHH los cargue. Hasta entonces no hay nada que consultar ni agrupar por provincia |
| **5f** | Legajo: **liderazgo** | 🔴 | El campo existe en la base pero **no aparece en ningún formulario ni pantalla**: no está en `schemas/empleado.py`. Lo único que lo escribe es la importación de nómina | Lo que sí se ve es un Sí/No de "es líder". Falta decidir si ese Sí/No reemplaza al campo de liderazgo comprometido, o si hay que mostrarlo |
| **5g** | Legajo: **presencialidad** | 🔴 | **No existe un campo con ese nombre.** Lo más cercano es "modalidad de trabajo" (presencial / remoto / híbrido), en `schemas/empleado.py:55,97` | Falta confirmar qué se comprometió. Si era presencial/remoto/híbrido, ya está. **Si era un porcentaje o una cantidad de días presenciales por semana, no hay dónde guardarlo** |
| **5h** | Legajo: renombrar **cargo → rol** | ✅ | `schemas/empleado.py:54` | **Se hizo distinto y es mejor:** no se renombró un campo, se unificaron los dos que había (cargo y rol) en **una lista de roles**, porque una persona puede tener más de uno. El campo viejo quedó marcado como obsoleto (`:58`) |
| **6a** | Historial de cambios de rol, área y seniority en la ficha | ✅ | `frontend/components/features/empleados/ficha/HistorialCambiosSection.tsx`, montado en `app/(dashboard)/empleados/[id]/page.tsx:104` · sale de los 139 eventos registrados | — |
| **6b** | Historial de **sueldo** en la ficha | 🟡 | `ficha/HistorialSalarialSection.tsx`, montado en `empleados/[id]/page.tsx:103` | 🔴 **Sale vacío para todos los empleados: no hay ni un sueldo cargado** (`costos_nomina`, 0 filas). La pantalla está terminada; **falta que RRHH cargue la nómina** |
| **7** | Adjuntos en legajo, motivos, vacaciones, ausencias y offboarding | 🟡 | `backend/services/_adjunto_padres.py:51-56` — soporta legajo, vacaciones, ausencias, offboarding **y búsquedas de personal** (esta última no estaba comprometida) | **Hay 1 solo archivo cargado en todo el sistema**, y por un problema de datos viejos está inaccesible. **"Motivos" no existe como entidad**: falta definir a qué apuntaba. La prueba de subida y descarga real contra el almacenamiento **nunca se corrió** |
| **8** | Historial de vacaciones desde el ingreso, en la ficha | 🟡 | `ficha/VacacionesSection.tsx`, montado en `empleados/[id]/page.tsx:105`, sin recorte de fechas | 🔴 **No hay ni una vacación cargada** (`solicitudes_vacaciones`, 0 filas). Falta el archivo histórico de RRHH |
| **9** | Inventario asignado dentro de la ficha | 🟡 | `ficha/InventarioSection.tsx`, montado en `empleados/[id]/page.tsx:102` | 🔴 **No hay ni un equipo cargado** (`inventario_items`, 0 filas) |
| **10** | Importar vacaciones desde Excel, por área o equipo | 🔴 | **El sistema no sabe leer archivos Excel.** Lo verificamos: no hay una sola línea que abra un Excel en todo el backend. Las tres importaciones que existen leen CSV | Falta construir el lector de Excel y el formato de vacaciones. **Bloqueado además por RRHH**: el archivo histórico solo identifica a la gente por número de legajo, y el legajo **está vacío en los 31 empleados** |
| **11** | Importar objetivos desde Excel | 🔴 | Ídem. No existe ningún camino de importación de objetivos | Falta todo. Es el ítem menos avanzado de la Entrega 2 |
| **12** | Importar evaluaciones de un sistema externo: promedios y nota única | ✅ | `backend/services/evaluacion_import_service.py` · promedios en `services/_evaluacion_metricas.py:33,58,80` · **funcionando con datos reales: 1 lote de julio 2026, 10 evaluados, 307 resultados** | **Dos diferencias con lo escrito:** el archivo es **CSV, no Excel** (es el formato que entrega el sistema externo, no lo elegimos), y **la nota única no la calcula nuestro sistema: viene ya calculada en el archivo**. Lo que sí calcula el sistema son todos los promedios y comparaciones |
| **13** | Exportar en Inventario, Evaluaciones y Objetivos | 🟡 | Inventario: `routers/inventario_items.py:35` y `inventario_asignaciones.py:49` · Objetivos: `routers/objetivos.py:49` · Evaluaciones: `routers/ev_instancias.py:35` y `evaluaciones_resultados_export.py:28` | **Solo el de evaluaciones se probó con datos reales.** Inventario exporta un archivo vacío (0 equipos) y objetivos casi vacío (1 objetivo) |
| **14a** | Un solo formato estándar de exportación | ✅ | Los 12 exportadores pasan por el mismo motor (`services/export/`), en 4 formatos: PDF, Excel, CSV y Word | — |
| **14b** | Exportación **en todos los módulos** | 🔴 | Hoy exportan 12: empleados, vacaciones, ausencias, capacitaciones, inventario (2), objetivos, evaluaciones (2), reportes, **sueldos** y **auditoría** | **Faltan 14 módulos**: búsquedas de personal, candidatos, proyectos, horas, onboarding, offboarding, áreas, procesos, usuarios, cesiones, sucesión, assessment, períodos y presupuesto. El organigrama "exporta" imprimiendo la pantalla desde el navegador, no con el motor |
| **15** | Vacaciones: historial desde el ingreso accesible desde el legajo | 🟡 | Es el mismo ítem que el 8 (aparece dos veces en el documento entregado) | Mismo estado: la pantalla está, no hay datos |
| **16** | Proyectos: asignar áreas o equipos completos, con selector automático | 🟡 | `backend/routers/proyecto_asignaciones.py:49` — asignar un área entera de una vez · también asignación múltiple manual (`:41`) | **Por área funciona; por equipo no existe** y no se va a construir: "equipo" es un campo de texto libre que nadie completó, así que no hay nada que agrupar. 🔴 **Y hay un problema de datos que lo rompe en silencio: dos de las 12 áreas son la misma, cargada con dos grafías distintas** (`GESTION DE DEUDA` y `GD - GESTION DE DEUDA`). Asignar esa área asigna a la mitad de la gente |

---

## Entrega 3 — 16 ítems

| # | Ítem comprometido | Estado | Evidencia | Qué falta / cómo quedó |
|---|---|---|---|---|
| **1** | Sistema de alertas configurables: motor periódico y pantalla de configuración | 🔴 | Buscamos la palabra en todo el sistema: **no hay una sola línea de código**. Las dos tablas que el documento llamaba "infraestructura existente" están **vacías y nunca se usaron** | Falta todo. **Y no hay "infraestructura que activar"**: son dos tablas sin catálogo de eventos ni de canales de aviso. Es construcción desde cero. ⚠️ Sí se construyó otra cosa parecida y no comprometida: **las alertas del tablero** (ver más abajo), que avisan de campos sin completar y módulos sin datos, pero **no son configurables ni corren solas** |
| **2** | Plantillas de mail editables + envío por Resend | 🟡 | Tabla `plantillas_mail` · pantalla de edición en `/configuracion` · `backend/routers/plantillas.py:41,47,53,58,64` · motor de envío en `services/mailer/` | **Cambió el proveedor: los mails salen por Gmail, no por Resend** (se sacó del sistema; ver "Cambios de alcance"). 🔴 **El sistema todavía no puede mandar un solo mail.** Falta una acción de Franco: **designar cuál de las casillas conectadas es la casilla oficial del sistema**. Hoy hay una cuenta de Google conectada, pero ninguna marcada como oficial, y **no existe el botón para marcarla** — hay que construirlo. No hay plantillas escritas ni mails enviados |
| **3** | Filtro por área en capacitaciones, inventario, objetivos y proyectos | 🟡 | Capacitaciones ✅ `routers/asignaciones_capacitacion.py` · Inventario (asignaciones) ✅ `routers/inventario_asignaciones.py:31,51` · Proyectos ✅ `routers/proyectos.py:30` | **Falta en 2 de 5 pantallas:** el listado de equipos de inventario (`routers/inventario_items.py:28`) y **objetivos** (`routers/objetivos.py:30-32`). En objetivos hay un impedimento de fondo: un objetivo se asigna a un usuario del sistema, no a un empleado, así que **no tiene área de la cual colgar**. Y los tres que existen no se pudieron probar de verdad: con 12 áreas y 31 empleados casi cualquier filtro devuelve casi todo |
| **4** | Filtro por proyecto en colaboradores, vacaciones, ausencias y evaluaciones | 🟡 | **Los cuatro lo tienen**, y el exportar acepta el mismo filtro que la pantalla: `routers/empleados.py`, `vacaciones.py`, `ausencias.py`, `evaluaciones_resultados.py` | Falta probarlo con volumen: vacaciones y ausencias **están vacías**, así que dos de los cuatro filtros nunca devolvieron una fila |
| **5** | Objetivos: subobjetivos, varios responsables, fechas de entrega distintas | 🔴 | Los tres faltan. `backend/schemas/objetivo.py:22`: **un solo responsable**, y `:5` documenta que es un usuario del sistema, no un empleado. No hay jerarquía ni fechas por subobjetivo | Requiere rediseñar el modelo de datos. 🟢 **La buena noticia: hay 1 solo objetivo cargado, así que hacerlo ahora es barato. Con datos cargados se vuelve caro** |
| **6** | Evaluaciones: estadísticas anuales, evolución por empleado, comparativas por área, gráficos exportables | 🔴 | Todas las pantallas de evaluaciones trabajan sobre **una sola carga por vez**: `routers/evaluaciones_resultados.py:48,55,65`. No hay comparación entre períodos | Falta construirlo, **y está bloqueado por datos**: hay **una sola carga de evaluaciones** (julio 2026). Sin una segunda, ninguna comparación temporal tiene con qué compararse |
| **7** | Offboarding: formulario estructurado + estadísticas de motivos con análisis de IA | 🟡 | Formulario con motivos tipificados · **entrevista de salida activada**: `repositories/offboarding_repo.py:71,76` y `routers/offboarding.py:75` — eran dos campos que existían en la base y **no los usaba nadie** | 🔴 **No hay ni un egreso cargado** (`offboarding_instancias`, 0 filas). **El análisis con IA no existe.** Sí hay un reporte de rotación por motivo (`services/reportes/_reporte_movimientos.py:44,52`), pero vive en el módulo de reportes y no es lo mismo |
| **8** | Organigrama: cards de proyectos desplegables con equipo y datos del contrato | 🟡 | `frontend/components/features/organigrama/CardsProyecto.tsx`, vista activa (`app/(dashboard)/organigrama/page.tsx:22`) | **Los datos del contrato no están en la card**: muestra el equipo y el rol de cada persona (`CardsProyecto.tsx:28`), no el valor hora ni las fechas. Y **dos de las tres vistas están apagadas** (`page.tsx:20-21`), incluido el organigrama clásico por empresa y área: está construido y no se puede llegar a él |
| **9** | Assessment: reactivar la pantalla + envío de links por mail + PDF de resultados | 🔴 | Ninguna de las tres. La pantalla está apagada (`frontend/app/(dashboard)/assessment/page.tsx:74`), el backend **está desconectado** (`backend/main.py:141`), el envío de links **no manda ningún mail** (`services/assessment_service.py:77-94` solo genera el link) y **no hay ninguna generación de PDF** | El módulo se apagó por decisión (ver "Cambios de alcance"). **El ítem pedía reactivarlo y se hizo lo contrario**, con motivo: estaba abierto sin contraseña |
| **10** | Assessment: empresa en las tablas de las migraciones 020-021 | ✅ | Las **cuatro** tablas de assessment tienen el campo de empresa (`migrations/055_retrofit_empresa_id.sql:113,124,135,146`) | Se hizo sobre las cuatro, no solo sobre las dos comprometidas |
| **11** | Sueldos: corregir empresa en nómina y presupuesto | ✅ | `migrations/055_retrofit_empresa_id.sql:58,69` — verificado en la base | — |
| **12** | Sucesión: corregir consultas lentas + empresa en sus tablas | ✅ | Consultas: commit `51832e2` — el análisis por área hacía **una consulta por empleado**; con 200 empleados pasó de **201 consultas a 2** · empresa: `migrations/055:80,91,102` | — |
| **13** | AWS: Dockerfile + docker-compose | 🔴 | No existe ninguno de los dos en el repositorio | El frente AWS no se empezó |
| **14** | AWS: CI/CD con GitHub Actions | 🔴 | No existe la carpeta de configuración de GitHub Actions | Ídem |
| **15** | AWS: ECS + balanceador + DNS | 🔴 | Sin configuración de infraestructura en el repositorio. Hoy el sistema corre en Vercel | Ídem |
| **16** | AWS: monitoreo CloudWatch + alertas de error | 🔴 | Sin configuración de monitoreo | Ídem |

---

## Frente AWS — 12 tareas

| # | Tarea | Estado | Evidencia | Qué falta |
|---|---|---|---|---|
| **A-1** | Dockerfile del backend | 🔴 | No existe | — |
| **A-2** | `.dockerignore` | 🔴 | No existe | — |
| **A-3** | Servicios de AWS (servidores, balanceador, certificados, registro de imágenes, monitoreo) | 🔴 | Sin configuración en el repositorio | Es trabajo del dev de infraestructura, no del código |
| **A-4** | Dominio y DNS en Route 53 | 🔴 | El dominio hoy lo sirve Vercel | — |
| **A-5** | Variables de configuración en Parameter Store | 🔴 | Hoy viven en Vercel | — |
| **A-6** | Dirección de producción en Google | **NO DETERMINADO** | El valor real no vive en el repositorio: está en Vercel y en la consola de Google. **Evidencia indirecta de que funciona**: hay una cuenta de Google conectada el 3/8/2026 con permisos de lectura y envío, o sea que el circuito completó al menos una vez | Confirmarlo en la consola de Google |
| **A-7** | CI/CD con GitHub Actions | 🔴 | No existe | — |
| **A-8** | Docker Compose para desarrollo local | 🔴 | No existe | — |
| **B-1** | Límites de uso en reportes con IA e importaciones masivas | ✅ | **23 límites configurados** en todo el sistema, por nivel de riesgo: importaciones 10 por hora, exportaciones 30 por hora, reportes con IA 20 por hora, login 5 por minuto, y un límite general para todo lo demás (`backend/main.py:90`) | Cubre y excede lo pedido. **Con una salvedad honesta**: los contadores viven en memoria de cada proceso, así que con varios procesos el límite real es más alto. Cerrarlo del todo es una tarea de infraestructura |
| **B-2** | Preguntas del assessment configurables desde el panel | 🔴 | No existe ninguna tabla de preguntas: las cuatro tablas de assessment son campañas, links, reportes y resultados (`backend/db/schema.sql:72,89,104,120`) | El módulo además está apagado |
| **B-3** | Seguridad del circuito de Google: token de un solo uso | ✅ | Tabla `oauth_states` · `backend/services/_oauth_state.py` · `_google_oauth.py:63,97` | **Se hizo, y era más grave de lo que el documento sugería**: antes el sistema usaba el identificador del usuario, que es un valor fijo y adivinable. Ahora es un número al azar, guardado cifrado, que vence a los 10 minutos y sirve una sola vez |
| **B-4** | Gunicorn | 🔴 | No aparece en la configuración del backend | En Vercel no aplica; hace falta el día de la mudanza a AWS |

---

## Los 18 módulos declarados operativos

| Módulo | ¿Responde el servidor? | ¿Se llega desde el menú? | Realidad |
|---|---|---|---|
| Tablero (dashboard) | ✅ `main.py:144` | ✅ | Operativo |
| Colaboradores | ✅ `main.py:117-118` | ✅ | **Operativo — 31 empleados cargados** |
| Vacaciones y ausencias | ✅ `main.py:120-124` | ✅ | 🔴 **Vacío**: 0 vacaciones, 0 ausencias |
| Capacitaciones | ✅ `main.py:152-153` | ✅ | 🔴 **Vacío**: 0 capacitaciones |
| Evaluaciones | ✅ `main.py:154-160` | ✅ | **Operativo — 1 carga real, 10 evaluados** |
| Inventario | ✅ `main.py:161-162` | ✅ | 🔴 **Vacío**: 0 equipos |
| Objetivos | ✅ `main.py:163` | ✅ | 🔴 **Casi vacío**: 1 objetivo |
| Proyectos | ✅ `main.py:166-168` | ✅ | **Operativo — 8 proyectos, 31 asignaciones**, pero **todas con valor hora en cero** |
| Onboarding | ✅ `main.py:129-131` | ✅ | 1 proceso cargado |
| Offboarding | ✅ `main.py:132` | ✅ | 🔴 **Vacío**: 0 egresos |
| Áreas | ✅ `main.py:116` | ✅ `nav-config.ts:89` | Operativo — 12 áreas, **2 son la misma duplicada**. (Hasta hace poco la pantalla existía pero **no estaba en el menú**; se agregó) |
| Organigrama | ✅ `main.py:143` | ✅ | **1 de sus 3 vistas** está visible |
| Búsquedas y candidatos | ✅ `main.py:127-128` | ✅ | 🔴 **Vacío**: 0 búsquedas, 0 candidatos |
| Sueldos y nómina | ✅ `main.py:133-134` | ✅ | 🔴 **Vacío**: 0 registros de nómina |
| **Sucesión (9-box)** | ✅ `main.py:135` — **el servidor responde igual** | 🔴 **OCULTO** | Apagado por decisión de producto. **No se borró nada**: los 11 componentes de pantalla, el servicio y las pruebas siguen ahí. Se prende cambiando dos líneas (`nav-config.ts:48` y `sucesion/page.tsx:25`) |
| Reportes PDF/Excel + IA | ✅ `main.py:146` | ✅ | Operativo, **pero la parte de IA está oculta**: el reporte con inteligencia artificial no está en el catálogo que ve el usuario. Se reactiva en una línea |
| Integraciones (Google, Anthropic, Zernio) | ✅ `main.py:150` | ✅ vía Configuración | **1 cuenta de Google conectada**. Anthropic y Zernio sin usar |
| **Assessment** | 🔴 **NO responde** — `main.py:141` lo deja fuera | 🔴 **OCULTO** | Apagado por seguridad: **tenía dos direcciones abiertas sin contraseña**. Hoy responde igual que una dirección que no existe, sin delatar que el módulo está ahí. Se reactiva con una variable de configuración, sin tocar código |

**En resumen:** 16 de los 18 son alcanzables; 2 están apagados a propósito. **Pero 8 de los 16
alcanzables abren pantallas vacías** por falta de datos. Además hay **3 módulos en uso que no
figuran en la lista de 18**: auditoría, períodos y "Mi equipo".

---

## Lo entregado que NO estaba comprometido

Todo esto se construyó después de junio y no está contabilizado en ninguno de los dos documentos.

| Qué | Estado | Evidencia |
|---|---|---|
| **Aislamiento entre empresas en 92 pantallas y operaciones** | ✅ | Commits `bd95e98` + `9d7baa7`. Antes, con el identificador de un dato de otra empresa se podía operar sobre él |
| **Verificación real de la identidad del usuario** | ✅ | `backend/middleware/auth.py`. 🔴 **Antes el sistema aceptaba credenciales sin verificar la firma: cualquiera podía fabricarse un acceso.** Es la falla más grave que se encontró en todo el período |
| **Sesión que vence por inactividad (8 horas)** | 🟡 | `backend/utils/_sesion_inactividad.py` · `utils/usuario_estado.py`. **Antes una sesión no vencía nunca.** Se probó en desarrollo, no con los usuarios reales |
| **Baja de usuarios que realmente saca a la persona** | 🟡 | `backend/services/usuario_service.py:66,94,100`. Antes, dar de baja a alguien **no lo sacaba del sistema**. Ahora es una baja reversible que además le corta la renovación de acceso. Nunca se ejecutó sobre un usuario real |
| **Módulo de envío de mails por Gmail con plantillas editables** | 🟡 | `services/mailer/` · `routers/plantillas.py`. Falta designar la casilla oficial |
| **Módulo de cierre de períodos completo** | 🟡 | Es el ítem 4 de la Entrega 2. Nunca se cerró un período |
| **Importación de evaluaciones de sistema externo** | ✅ | Es el ítem 12 de la Entrega 2 |
| **11 reportes descargables + 9 indicadores de tablero** | 🟡 | `services/reportes/` (9 módulos). Los de dotación funcionan; los de vacaciones, ausencias y costos **salen vacíos por falta de datos** |
| **Alertas del tablero** (campos sin completar, módulos sin datos) | ✅ | `services/_dashboard_alertas.py` — 107 líneas |
| **Panel de configuración de reglas de negocio** | 🟡 | La base de días hábiles y la escala de vacaciones **dejaron de estar escritas en el código** y se configuran desde `/configuracion`. Solo una regla se consume hoy; el resto se guarda y todavía no gobierna ningún cálculo |
| **Cálculo de saldo de vacaciones por período** | 🟡 | `services/_vacaciones_cupos.py` + `_vacaciones_fifo.py` (147 líneas cada uno): días según antigüedad, acumulación por 4 años, vencimiento e imputación por orden de antigüedad. **Nunca se ejercitó: no hay vacaciones cargadas** |
| **Filtro por rango de fechas en vacaciones y ausencias** | 🟡 | `repositories/_rango_fechas.py:33`, usado en `vacaciones_repo.py:27` y `ausencias_repo.py:33`. Incluye los casos que cruzan el borde del mes, que es lo que un reporte de ausentismo necesita. Sin datos para probarlo |
| **Límite de filas en las exportaciones, con aviso claro** | ✅ | `services/_limite_export.py:36,41`. Antes, una exportación grande **salía incompleta sin avisar**. Hoy avisa y pide acotar con filtros |
| **Subtipos de ausencia (dos niveles)** | 🟡 | `services/_tipos_jerarquia.py`. Permite "Enfermedad familiar → Madre/padre", como vienen los archivos reales. Sin ausencias cargadas |
| **Jefe de otra empresa del grupo** | 🟡 | `services/_alcance_mandos.py` (138 líneas). Un empleado puede reportar a alguien de otra empresa del grupo. Sin usuarios de ese rol, sin probar |
| **Asignar un área entera a un proyecto** | 🟡 | `routers/proyecto_asignaciones.py:49`. Es el ítem 16 de la Entrega 2 |
| **Importación de nómina con jefe incluido** | ✅ | Antes el archivo traía el jefe de cada persona **y el sistema lo descartaba**. Hoy lo resuelve: 11 de 31 cargados |
| **Lector de archivos unificado** | ✅ | `services/_import_encoding.py` |
| **Alta y baja de usuarios con roles** · **adjuntos** · **cesiones** (10 cargadas) | ✅ | Migraciones 063, 061 y 066 |
| **6 verificaciones automáticas que corren solas en cada cambio** | ✅ | Detectan clases enteras de error: que una exportación no acepte los mismos filtros que la pantalla, que una consulta pida un campo que no existe, que los permisos de pantalla y servidor se separen |

---

## Lo que se encontró roto y se arregló, sin que nadie lo hubiera reportado

Todo esto estaba fallando en producción y **nadie lo había notado**, porque fallaba en silencio.

| Qué pasaba | Cómo se detectó |
|---|---|
| 🔴 **6 de los 11 reportes nunca funcionaron.** Se habían entregado como terminados y pedían datos con nombres que no existían: salían en blanco | Las pruebas automáticas pasaban igual, porque el simulador de base de datos aceptaba cualquier nombre. Se construyó una verificación que compara contra la estructura real |
| 🔴 **94 registros de auditoría afirmaban cambios que nunca ocurrieron.** Cada vez que alguien editaba un empleado, el sistema anotaba que se le había borrado el área y la empresa. La pantalla se lo mostraba al usuario sobre empleados reales | Se detectó al revisar el historial. Corregido; los registros viejos no se borran porque la auditoría es inmutable, pero ya no se generan nuevos |
| 🔴 **El listado de plantillas de onboarding devolvía un error** desde hacía meses | Apareció al construir la verificación de consultas |
| 🔴 **La pantalla de Proyectos quedaba cargando para siempre**, con el servidor respondiendo bien. Una línea perdida en un cambio anterior | Se agregó una verificación automática que barre todo el sistema buscando pantallas que prendan el indicador de carga y no lo apaguen |
| 🔴 **Un archivo en formato UTF-16 se importaba como texto ilegible y la importación decía que había salido bien**, cargando nombres corruptos en la base | Se verificó en vivo antes de tocar nada. La causa: el sistema probaba un formato que **nunca falla**, así que el error nunca aparecía |
| 🔴 **La importación de sueldos perdía su registro de auditoría en silencio** | El evento se descartaba por un error de formato que el sistema se tragaba por diseño |

---

## Lo que cambió de alcance por decisión

No son faltas: son decisiones tomadas con fundamento. **No se van a entregar como estaban escritas.**

### Assessment — se apagó en vez de reactivarse

El ítem pedía reactivar la pantalla. Se hizo lo contrario, y por seguridad: **el módulo tenía dos
direcciones accesibles sin contraseña**. Hoy el servidor no lo publica y responde igual que a una
dirección inexistente, sin delatar que existe. **No se borró una línea de código**: se reactiva
con una variable de configuración. Lo que sigue faltando aunque se prenda: el envío de links por
mail y el PDF de resultados, que nunca se construyeron.

### Evaluaciones — el sistema no evalúa, importa resultados

Se comprometía un módulo de evaluación con estadísticas anuales. Lo que se construyó es la
**importación de resultados calculados afuera**, porque es como trabaja RRHH hoy. Las estadísticas
entre períodos no se pueden construir todavía: **hay una sola carga de evaluaciones**, y una
comparación necesita al menos dos.

### Sucesión — apagado por decisión de producto

Funciona y está completo. Se ocultó de la pantalla por decisión, no por un problema.
**El servidor responde igual** y todo el código está intacto: se prende cambiando dos líneas.

### Mails — Gmail en vez de Resend

Se comprometía conectar Resend. Se sacó del sistema y **los mails salen por Gmail**, reusando la
conexión que ya existía. Motivo: la cuenta de Google ya estaba conectada para leer postulaciones,
así que no había que sumar un proveedor más. Además RRHH escribe las plantillas en texto simple y
**el sistema genera el formato final**, para que no se pueda inyectar contenido peligroso.

### Aislamiento por empresa — no hay accesos por usuario

Se comprometía validar la empresa activa contra los accesos del usuario. **No existe ni va a
existir esa tabla**: la decisión de producto es que todo usuario ve todas las empresas. Lo que se
construyó es más fuerte en el eje que importa: el filtro por empresa viaja en las 92 consultas.

### Asignar por equipo — no se construyó, por datos

El campo "equipo" es texto libre y **nadie lo completó**. No hay nada que agrupar. El trabajo real
era por área, que sí está cargada.

---

## Lo que está bloqueado por datos, no por código

**Conteos reales de producción al 5 de agosto de 2026.** Esto es lo que distorsiona cualquier demo.

| Dato | Cargado | Consecuencia |
|---|---:|---|
| Empresas | **2** | — |
| Empleados | **31** | — |
| Áreas | **12** | 🔴 **2 son la misma, duplicada** |
| Proyectos / asignaciones | **8 / 31** | 🔴 **Las 31 asignaciones tienen valor hora en cero**: el reporte de costos las suma como cero, y "cero" no se distingue de "no lo sabemos" |
| Jefe de cada empleado | **11 de 31** | Hasta completarlo, el rol de mandos medios no se puede entregar |
| **Legajo** | **0 de 31** | 🔴 **Bloquea la importación de vacaciones**: el archivo histórico identifica a la gente solo por legajo |
| Seniority | **3 de 31** | El reporte de distribución sale casi todo en "sin especificar" |
| **Vacaciones** | **0** | Bloquea 4 entregas: historial en la ficha, saldo por período, filtros y reportes |
| **Ausencias** | **0** | Bloquea el reporte de ausentismo y los subtipos |
| **Nómina / sueldos** | **0** | 🔴 Bloquea el historial salarial, la masa salarial y el presupuesto |
| Presupuesto por área | **0** | Bloquea el reporte de presupuesto vs. real |
| **Inventario** | **0** | La sección del legajo sale vacía |
| **Capacitaciones** | **0** | — |
| Objetivos | **1** | 🟢 Rediseñar el modelo ahora es barato |
| Búsquedas / candidatos | **0 / 0** | — |
| Egresos | **0** | — |
| Cargas de evaluaciones | **1** | Bloquea las estadísticas entre períodos |
| Plantillas de mail / mails enviados | **0 / 0** | El sistema todavía no mandó un mail |
| Períodos cerrados | **0** | Nunca se cerró un período |
| Adjuntos | **1** | Y está inaccesible por un problema de datos viejos |
| Registros de auditoría | **139** | ✅ Funcionando |
| Cesiones | **10** | ✅ Funcionando |

> 🔴 **El patrón, y es el mensaje central de este documento: la funcionalidad está entera y el dato
> no existe.** Historial salarial, saldo de vacaciones, mails, ownership de mandos medios, subtipos
> de ausencia y buena parte de los reportes están construidos y salen vacíos.
> **No es deuda técnica ni trabajo pendiente de desarrollo: la acción es de RRHH.**

---

## Cómo se mantiene este documento

- **Se actualiza al cerrar cada ítem**, no al final de una fase: cambia el estado de esa fila, se
  reemplaza la evidencia por la del código nuevo y se vacía "qué falta".
- **Nunca se agrega un addendum.** Si algo es posterior, va **en su fila**. La versión anterior de
  este documento tenía el cuerpo de julio y un agregado de agosto, y **las tablas contradecían al
  agregado del mismo archivo** en doce puntos.
- **La evidencia es siempre `archivo:línea` o el nombre del dato en la base.** Nunca "según la
  documentación": los documentos internos se desactualizan y el código no miente.
- **La base se consulta en vivo**, no a través de las migraciones: producción puede haberse
  desviado de ellas.
- **Un ítem pasa de 🟡 a ✅ el día que se lo ejercita con datos reales, no el día que se termina de
  escribir.** Es la distinción que este documento existe para sostener.
