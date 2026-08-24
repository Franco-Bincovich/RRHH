# Sistema de diseño — Capital Humano

> Aprobado por el equipo de Capital Humano el 16/8/2026, después de cuatro iteraciones.
> **Estas decisiones no se rediscuten.** Este documento es lo que Claude Code necesita para
> construir el frontend.

---

## 1. Los tokens

Verificados a 4.5:1 de contraste. Van a `app/globals.css`, reemplazando los bloques `:root` y
`.dark`. Los nombres son los que el proyecto ya usa, así que ningún componente cambia de clase.

```css
/* ─── CLARO ─────────────────────────────────────────── */
:root {
  --background: #F5F7FA;   --card: #FFFFFF;    --popover: #FFFFFF;
  --muted: #EFF2F6;        --secondary: #EFF2F6; --accent: #EEF2FE;

  --foreground: #0E1726;  --card-foreground: #0E1726;
  --popover-foreground: #0E1726;
  --muted-foreground: #59657A;   /* sube de #8a8a8a (3.45:1) a 5.89:1 */
  --secondary-foreground: #3B4759; --accent-foreground: #1B4FD8;

  --primary: #1B4FD8;     --primary-foreground: #FFFFFF;
  --ring: #1B4FD8;

  --border: #E2E7EE;      --input: #CBD3DE;
  --destructive: #B42318;
  --success: #0F7A5A;     --success-wash: #E7F5EF; --success-line: #B7E0CE;
  --warning: #8A5A00;     --warning-wash: #FDF3E2; --warning-line: #EBD3A3;
  --danger-wash: #FDEEEC;  --danger-line: #F2C4BE;

  --sidebar: #0E1726;    --sidebar-foreground: #C9D3E2;
  --sidebar-accent: #1B2436; --sidebar-accent-foreground: #FFFFFF;
  --sidebar-border: #1E2939; --sidebar-primary: #1B4FD8;
  --sidebar-primary-foreground: #FFFFFF; --sidebar-ring: #1B4FD8;

  --radius: 0.625rem;     /* 10px en paneles; 7px en controles */
}

/* ─── OSCURO ────────────────────────────────────────── */
.dark {
  --background: #0B1220;   --card: #151E2E;    --popover: #1C2637;
  --muted: #0E1626;        --secondary: #1C2637; --accent: #16223A;

  --foreground: #E7ECF3;  --card-foreground: #E7ECF3;
  --popover-foreground: #E7ECF3;
  --muted-foreground: #9AA7BB;
  --secondary-foreground: #C2CCDA; --accent-foreground: #7DA9FB;

  --primary: #7DA9FB;     --primary-foreground: #0B1220;
  --ring: #7DA9FB;

  --border: #26303F;      --input: #38445A;
  --destructive: #FF8A80;
  --success: #5FD3A6;     --success-wash: #0F2A22; --success-line: #1E4739;
  --warning: #E5B34B;     --warning-wash: #2A2312; --warning-line: #4A3D1C;
  --danger-wash: #2E1614;  --danger-line: #552724;

  --sidebar: #080E1A;    --sidebar-foreground: #B9C5D6;
  --sidebar-accent: #161F30; --sidebar-accent-foreground: #FFFFFF;
  --sidebar-border: #1A2434; --sidebar-primary: #7DA9FB;
  --sidebar-primary-foreground: #0B1220; --sidebar-ring: #7DA9FB;
}
```

**Dos avisos al aplicarlos:**
1. `--popover` en oscuro pasa a `#1C2637`. La regla de `globals.css` que arregla el popup de los
   `<select>` nativos usa ese token; el par sigue dando 12.80:1.
2. 🔴 `--primary-foreground` **deja de ser blanco en oscuro**. Todo `text-white` hardcodeado
   encima del botón primario pasa a `text-primary-foreground`.
3. 🔴 Al adoptar la paleta hay que **borrar la entrada de `BRECHAS_DECLARADAS`** en
   `contrasteTokens.test.ts`: el par `--primary` pasa de 3.68:1 a 7.97:1, y el test verifica la
   brecha en las dos direcciones.

**Tipografía:** Inter, una sola familia, escala de siete niveles. Cifras tabulares en todos los
números.

---

## 2. El tratamiento de superficie

**Tarjetas y filas OPACAS.** Sin transparencia ni desenfoque. Elevación por borde de 1px más
escalón de luminosidad.
Se probó con vidrio: el texto secundario perdía casi un punto de ratio (4,92 contra 5,49) y el
límite entre tarjetas quedaba difuso justo donde hay que comparar muchas de un vistazo.

**Vidrio SOLO en el sidebar y en los modales.** Ahí comunica "esto está adelante" y hay algo
detrás que importa. En una tarjeta de grilla no comunica nada y cuesta rendimiento: cada
superficie desenfocada obliga a recalcular lo de atrás, y con 400 filas se nota al hacer scroll.

**Fondo con color, suave.** Manchas muy diluidas: azul al 9%, verde al 7%. Con la azul al 15% el
texto secundario daba 4,18:1 y no pasaba.

**Movimiento al apuntar.** Tarjetas: elevación de 3px con borde iluminado. Filas de tabla:
desplazamiento de 2–3px, **sin elevación** — en una tabla la elevación rompe la alineación de
las columnas. Transiciones de 160ms.

**Densidad alta.** Filas de 46px. Un sistema de gestión no es una landing.

---

## 3. Los cinco patrones

### Filtros
Panel propio entre el encabezado y la tabla, nunca flotando sobre ella. Fila superior: buscador
que ocupa el ancho libre, selectores de 30px, y un "Más filtros" para el resto. Fila inferior
solo si hay filtros activos: contador ("2 filtros activos"), un chip por filtro con su valor y
una ✕ para quitarlo, y "Limpiar todo". Los chips usan `--accent` con borde `--primary`. El
total filtrado se repite en la paginación.

> 🔴 **CORRECCIÓN (23/8/2026) — acá decía que el chip es "el único lugar de la pantalla con
> relleno azul", y esa frase estaba MAL: se contradice con este mismo documento dos párrafos
> más abajo ("página actual en sólido", §3 › Tabla) y en §3 › Modal ("primario sólido"), y
> también con la barra de progreso. **Lo que está mal es la frase, no el código**: los tres
> rellenos azules que existen son correctos y deliberados. Lo que el chip sí es —y era lo que
> la frase quería decir— es el único relleno azul que NO es un control primario: usa
> `--accent` (el azul lavado), no `--primary`. Se saca la afirmación en vez de "arreglarla"
> porque una regla que el documento se desmiente a sí mismo no se puede defender con un test;
> `components/ui/decisionesVisuales.test.ts` la tenía declarada como no verificable justamente
> por eso.

### Tabla con paginación
Filas de 46px, encabezado de 32px en la superficie secundaria con mayúsculas de 10px,
separadores de 1px. Hover: fondo tenue, marca de 3px de `--primary` a la izquierda y
desplazamiento de 2px, en 160ms. Las acciones por fila **siempre visibles**, solo cambian de
color al apuntar: revelarlas en hover obliga a barrer la tabla para saber qué se puede hacer.
Pie con "Mostrando 1–12 de 1.042", selector de filas y paginación numérica con elipsis
(1 2 3 … 87), página actual en sólido.

### Ficha de detalle
Migas de pan. Barra de identidad: monograma de 46px, nombre, chip de estado, cuatro datos clave
en una línea, acciones a la derecha con la primaria al final. Abajo, tres columnas de paneles
independientes. Los datos son grillas etiqueta-valor de filas de 30px con el valor a la derecha
en cifras tabulares; cada panel tiene su propio "Editar" en 11px. Los historiales **no son
tabla**: son lista con fecha a la izquierda, "de → a" con la flecha en acento, y chip "Vigente"
en el registro actual.

### Modal de formulario
Vidrio con blur de 28px sobre scrim al 35%, 460–560px, radio de 14px. Título más una línea que
explica **la consecuencia** ("Se crea el legajo y se habilita el alta temprana"). Campos en
grilla de dos columnas, alto 34px; el activo lleva borde `--primary` con anillo de 3px.
Validación en dos niveles: banner de resumen arriba con la cuenta ("Revisá 2 campos antes de
guardar") y, en cada campo, borde destructivo, anillo suave y mensaje de 11px que dice **qué
corregir**, no "campo inválido". Los avisos de impacto van en ámbar sobre el pie. Botones abajo
a la derecha: secundario fantasma, primario sólido.

### Vacío y carga
**Vacío:** la tabla mantiene su encabezado y los filtros quedan a la vista con sus chips. El
bloque central explica por qué no hay datos **con los valores reales** ("Bodegas Tupungato no
tiene personal de Sistemas suspendido") más dos salidas: quitar el último filtro o limpiar todo.
Nunca se borran los filtros solos.
**Carga:** esqueleto con la grilla exacta de la tabla —mismas columnas, mismos 46px— barras con
shimmer de 1,2s, filtros presentes pero deshabilitados, y el conteo real en el subtítulo, así la
pantalla no salta cuando llegan los datos.

---

## 4. Navegación — 6 grupos, 38 items

Sidebar acordeón: solo el grupo activo abierto, los demás con su contador. Ícono en cada item y
en cada grupo, de trazo, no relleno.

**Fuera de los grupos, arriba:** Dashboard · Reportes · Auditoría.

1. **Personas** — Colaboradores · Organigrama · Documentación / Legajos
2. **Reclutamiento** — Vacantes · Candidatos · Perfiles de puesto
3. **Incorporación** — Onboarding · Próximos Ingresos
4. **Talento y Desarrollo** — Objetivos · Evaluaciones · Formación · Plan de desarrollo *(Próximamente)*
5. **Gestión** — Ausencias / Licencias · Vacaciones · Recategorizaciones · Comunicación
6. **Egresos** — Offboarding · Bajas

**Administración** — al final: Empresas · Áreas · Usuarios · Períodos · Configuración · Costos ·
Proyectos · Clientes · Carga de horas *(Próximamente)*

**Inventario está fuera del menú** hasta nuevo aviso.

**Vocabulario:** se dice **"Colaboradores"**, no empleados. Y **"Capital Humano"**, no Recursos
Humanos. El renombre va en pantalla, exports y mensajes de error; **no** en tablas, columnas,
endpoints, ni en el valor `entidad` de la auditoría.

---

## 5. Tres pantallas que son tarjetas, no listas

- **Perfiles de puesto** — cada perfil una tarjeta: nombre del puesto, nivel, modalidad, resumen.
- **Reportes** — cada reporte descargable una tarjeta, con el botón visible.
- **Comunicación** — cada plantilla de mail guardada una tarjeta.

Las tres son cosas que **se eligen**, no registros que se comparan. Por eso tarjeta y no fila.

---

## 6. El dashboard

**Diez KPIs en dos bloques.**
*Operación:* Colaboradores activos · Búsquedas abiertas · Ingresos próximos 30 días · Ausencias
en curso · Recategorizaciones del mes · Rotación 12 meses.
*Indicadores del período:* Masa salarial del mes · Ausentismo del mes · Antigüedad promedio ·
Headcount por empresa.

El que requiere acción se despega con el fondo del semántico que corresponda, no con un número
en color.

**Requiere tu atención.** Dos tipos de alerta conviviendo: las que calcula el sistema (ingresos
próximos, fin de período de prueba, vacaciones sin resolver) y las que crea Capital Humano a
mano. Que se note cuál es cuál — las manuales llevan el nombre de quien las creó. Se marcan como
resueltas y ahí desaparecen.

**Próximos eventos.** Ingreso · fin de período de prueba · inicio de vacaciones · más los
manuales. Avisan una semana antes por defecto.

---

## 7. 🔴 Lo que NO existe y no se puede mostrar

Un prototipo anterior prometió seis cosas inexistentes. Lo que el equipo vea, lo da por hecho.

- **Competencias** en perfiles de puesto. La tabla tiene: nombre, descripción, funciones,
  requisitos, formación, experiencia, conocimientos técnicos, ofrecemos, modalidad, nivel, tipo
  de contrato, jornada. Nada más.
- **Contador de ocupantes o vacantes por perfil.** No hay vínculo perfil ↔ colaborador.
- **Flujo de aprobación de recategorizaciones.** Se registra y queda registrado.
- **Porcentaje de avance** en objetivos. Hay estado: por hacer, en curso, terminado.
- **Evaluaciones vencidas o programadas.** El sistema **importa resultados**, no corre ciclos.
- **Documentos próximos a vencer.** No hay lista de documentos obligatorios por persona.
- **Impacto porcentual** de una recategorización. Es un monto en pesos, opcional.

**Antes de dar una pantalla por terminada:** ¿esto que muestro, el sistema lo puede hacer? Si
suena razonable para un sistema de RRHH pero no está en el modelo, probablemente no exista.

---

*HR Karstec · Sistema de diseño · 16/8/2026*
