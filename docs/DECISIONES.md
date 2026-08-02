# Decisiones — qué se descartó y por qué

> **Lo implementado vive en el código**, con más detalle y sin riesgo de divergir. Acá queda lo
> único que el código NO puede contar: **las opciones que se descartaron y el motivo**.
>
> Una decisión por bloque. Si una necesita más de una pantalla, es que no está decidida.
>
> Fusiona los 5 diagnósticos del 2/8/2026 (2.363 líneas). El razonamiento completo de cada uno
> está en el historial de git.

---

## Días de vacaciones no tomados: tabla propia, no filas sin fecha

**Se descartó:** una fila en `solicitudes_vacaciones` con `fecha_desde`/`fecha_hasta` en NULL.

**Por qué:** se diagnosticó sobre el código real y rompe **15 lugares**: 6 con crash y **9 en
silencio**. Los crashes son recuperables (se ven en el deploy). Los silenciosos son el motivo:
en SQL un predicado sobre NULL da NULL, que **no es TRUE**, así que la fila se cae del WHERE — y
como el count viaja en la misma query, **se cae también del total**. Un filtro no deja pasar las
filas sin fecha: **las esconde, y el total se esconde con ellas.** El noveno es el reverso:
`ORDER BY fecha_desde DESC` implica NULLS FIRST, así que cuando no las esconde las pone arriba.

**Quedó:** `vacaciones_pendientes`, tabla propia. Un día no tomado **no tiene fechas** porque
nadie faltó ningún día: es un saldo, no un hecho del calendario.

---

## `cuenta_ausentismo` vive en el HIJO, no en el padre ni en los dos

**Se descartó:**
- **En el padre solo** — dentro de "Licencia" puede haber subtipos que computan y otros que no
  (estudio vs. maternidad). RRHH no podría distinguirlos sin crear un padre nuevo, que es justo
  lo que la jerarquía vino a evitar.
- **En los dos** — serían **dos fuentes para el mismo hecho**. Un padre en `false` con un hijo en
  `true` no tiene respuesta correcta, y quien la resuelva va a inventar una regla (¿gana el hijo?
  ¿el más restrictivo?) que después nadie recuerda.

**Quedó:** la ausencia se carga contra UN tipo concreto y **ese tipo decide**. El padre conserva
la columna solo como **valor por defecto al crear un hijo** — ahorro de tipeo, no herencia:
editar el padre no toca a sus hijos.

---

## Subtipos de ausencia: `padre_id`, no aplanar ni texto libre

**Se descartó:**
- **Aplanar** (un tipo por combinación) — es lo más barato y rompe el requisito central:
  "cuántos días de enfermedad familiar" pasaría a ser un `LIKE` sobre un nombre **que RRHH edita
  desde la UI**. El día que alguien corrija el typo "compesatorio" del archivo real, el
  agrupamiento se parte en silencio. Un reporte que depende de la ortografía no es un reporte.
- **Texto libre** (`subtipo` en la ausencia) — es reintroducir `empleados.equipo`, que el repo ya
  documenta como error y que los datos confirman: **0 de 19 poblado**.

**Quedó:** self-FK con profundidad máxima 2. El agrupamiento va por ID, no por texto.

---

## "Injustificada" se desactiva: mezclaba dos ejes

**Se descartó** conservarlo. Es un valor del eje *calificación* (`justificada`) ocupando una fila
del eje *naturaleza* (`tipo_id`). Consecuencias reales: una ausencia con `tipo="Injustificada"` y
`justificada=true` **es representable y no significa nada**; y una enfermedad sin certificado se
puede cargar de dos formas razonables que dan reportes distintos.

**El argumento que cerró el caso:** `_reporte_ausentismo` **ya calculaba el ausentismo
injustificado leyendo `justificada`, no el tipo**. El eje correcto ya estaba en uso; el tipo solo
podía contradecirlo.

**Se desactiva, no se borra:** `solicitudes_ausencia.tipo_id` es una FK sin `ON DELETE`.

---

## El ownership cruzado NO toca `_ownership_filter`

**Se descartó:** modificar `_ownership_filter.py` —el archivo del que dependen 13 endpoints— para
que compusiera la excepción.

**Por qué no hizo falta:** la intersección empresa ∩ ownership **nunca ocurrió ahí adentro**.
Ocurre en el WHERE del repo, como **dos predicados independientes** (`.eq("empresa_id")` y
`.in_("empleado_id", ids)`). Y el conjunto de ownership **ya era ciego a la empresa**:
`ids_subordinados` es un `.eq("manager_id")` pelado. Para obtener la semántica pedida alcanzó con
**no mandarle el `empresa_id` al repo**.

**La invariante de la que depende, y por eso se verifica en runtime:** para `mandos_medios` el
ownership nunca puede resolver a "sin restricción". Antes, un fallo ahí quedaba contenido por el
`.eq("empresa_id")`; sin ese filtro, `(None, False)` significa **la tabla entera de todas las
empresas**. Por eso soltar la empresa y chequear la invariante viven en la misma función.

---

## Superiores del import: segunda pasada, no fila por fila

**Se descartó** resolver el superior dentro del loop del import.

**Por qué:** el jefe puede estar en una fila **posterior**. En el archivo real, el único jefe
presente tiene 13 subordinados y está en la fila 11: 10 de ellos se procesan antes que él.
Resolviendo dentro del loop, esos 10 quedarían sin superior y los 3 posteriores sí lo tendrían —
**un resultado que depende del orden de las filas del Excel**.

**También se descartó** reusar `ResolutorIdentidad` de evaluaciones: su desempate **es el
superior**, y acá el superior es la incógnita. Sería circular. Lo que sí se comparte es
`clave_identidad`.

---

## Casilla del sistema para los mails, no la cuenta del que aprieta

**Se descartó** que el mail salga de la integración del usuario logueado.

**Por qué:** `usuario_integraciones` es por usuario y **un proceso automático no tiene un
`user_id` que aportar** — no habría de qué cuenta salir. Y el motivo decisivo es otro: **el
circuito de prueba y el real tienen que ser el mismo.** Con la casilla designada, pasar de la
cuenta personal de prueba a la de RRHH es reconectar otra cuenta al mismo usuario técnico: cero
código, y lo que se probó es lo que va a producción.

---

## Plantillas de mail: Markdown, no HTML editable

**Se descartó** dejar que RRHH escriba HTML.

**Por qué:** ese HTML llega al buzón del destinatario sin que nadie lo revise, y el repo **no
tiene ninguna dependencia de sanitización** (ni la va a sumar). Con Markdown, el conjunto de HTML
posible lo genera nuestro código: la superficie **no se acota, desaparece**.

**También se descartó versionar las plantillas.** La pregunta real es *"¿qué le llegó a Fulano?"*,
no *"¿cómo era la plantilla en marzo?"*. La primera la contesta el log guardando el texto ya
renderizado; versionar obligaría a reconstruir el render con valores que ya no existen.

---

## Variables de plantilla: allowlist, jamás "todo menos"

**Se descartó** exponer la fila del empleado y excluir algunos campos.

**Por qué:** con "todo menos", **cada columna nueva de `empleados` se vuelve variable de mail sin
que nadie lo decida**. Es el argumento inverso al de `sin_derivados` en auditoría, y por el mismo
motivo: allá la pregunta es "¿qué cambió?" y enumerar miente por omisión; acá es "¿qué se puede
mandar por mail?" y enumerar es la única respuesta segura.

**Fuera, con motivo:** sueldo (un mail se reenvía y queda para siempre, y saltearía el gate de
`Seccion.COSTOS`), documento, fecha de nacimiento, domicilio, contacto personal, y —el peor—
`potencial`/`desempeno`, evaluación interna que nunca se comunicó.

---

## Asignar un área a un proyecto: foto, no vínculo vivo

**Se descartó** que el proyecto quede atado al área.

**Por qué:** `proyecto_asignaciones` lleva `rol`, `valor_hora` y fechas **por persona**, y
`horas_proyecto` cuelga de una asignación concreta. Un vínculo vivo no tendría dónde poner el
valor hora de alguien que todavía no entró, y **sacar a una persona del área le borraría una
asignación con horas cargadas** — que es justo lo que `ASIGNACION_CON_HORAS` (409) protege.

**Y la barrera va en dos pasos, no en uno:** el área se valida contra el header (404) y los
empleados se resuelven **sin** filtro de empresa. Pasarle el `empresa_id` a `empleados_de_area`
sería redundante y **silencioso**: un área ajena devolvería lista vacía y el endpoint respondería
"0 asignados, 0 errores" sin decir nada.

> ⚠️ **"El área filtra candidatos, NO asigna" nunca fue una decisión.** Era un comentario que
> describía lo implementado; la documentación lo copió y al ponerlo en mayúsculas lo volvió norma.

---

## "Asignar por equipo" no se construyó

**Se descartó** por datos, no por diseño: `empleados.equipo` es texto libre y está **0 de 19**
(15 dicen "NO APLICA", 4 vacío). **No hay nada que agrupar.** El trabajo real era por ÁREA, que
sí está cargada 19/19. Crear la entidad `equipos` entregaría una pantalla vacía hasta que RRHH la
defina y la cargue.

---

## Base de import: NO se construyó la abstracción

**Se descartó** un `ImportGenerico<T>` con callbacks para parsear, validar, resolver y persistir.

**Por qué:** de las siete piezas que parecían compartidas, **solo tres lo estaban de verdad**
(encoding, parsers de valores, reloj del presupuesto). El ciclo preview→confirmar es un **patrón,
no código**: las dos implementaciones existentes no comparten una línea y está bien así, cada una
tiene el schema de su dominio. Y el riesgo concreto: **el archivo real no está definido**, así que
una base diseñada contra un archivo hipotético acierta en lo fácil (leer un CSV) y erra en lo que
importa (qué hace duplicada una fila, qué la hace inválida).

**Lo que hace que "el día del archivo sea solo el mapeo" no es una abstracción**: es que el
vocabulario de columnas viva en un archivo aparte.

---

## El lector de CSV: `permitir_latin1` es un flag, no un descuido

**Se descartó** unificar los dos decodificadores bajo una sola política.

**Por qué:** adoptar el estricto (el de evaluaciones) **habría roto el import de nómina**, que
falla ante latin-1 — el formato de los archivos que RRHH manda todos los meses. Y adoptar el
permisivo le habría sacado a evaluaciones su estrictez. **La duplicación real era la DETECCIÓN;
la política difiere por los archivos de cada flujo.**

**El bug que arregló:** los routers hacían `except → latin-1`, y **latin-1 nunca falla**. Un CSV
en UTF-16 entraba como `'ÿþA\x00p\x00e\x00l...'` y el import **se completaba**, cargando nombres
ilegibles.

---

## Idempotencia de ausencias: la identidad es quién + cuándo + qué tipo

**Se descartó** un chequeo en el service. Un SELECT previo tiene ventana de carrera: dos requests
concurrentes con la misma fila pasan los dos y escriben los dos. Y PostgREST **necesita una
constraint única** para `on_conflict`.

**Lo que la clave prohíbe, aceptado explícitamente:** dos filas con el mismo empleado, tipo y
fechas exactas que difieran solo en `motivo`. No son dos ausencias: es la misma cargada dos veces.
**No prohíbe solapamientos parciales** — eso sigue permitido, es un subconjunto estricto.

---

## Los módulos apagados no se borran

Assessment y sucesión están **apagados, no muertos**: se sacó el punto de entrada, no el código.

🔴 **El flag del front nunca es un `const` con literal.** TypeScript colapsa `const x = false` al
tipo literal `false`: en un componente eso marca el cuerpo inalcanzable y **`next build` falla**;
en un módulo de datos, la rama `true` del ternario deja de type-checkear, así que **reactivar el
módulo rompería el build en vez de funcionar**. Por eso es `useState(false)` en las páginas y
`: boolean` anotado explícito en la config.
