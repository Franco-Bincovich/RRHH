# Aviso de búsqueda real — referencia de `perfiles_puesto`

> **Qué es:** el aviso de búsqueda que RRHH usa de verdad, provisto por Franco el 13/8/2026.
> **Para qué está acá:** es **la referencia de qué campos tiene que poder llenar un perfil de
> puesto**. Cuando alguien proponga una columna nueva en `perfiles_puesto`, la pregunta es si
> este documento la necesita.
>
> 🔴 **Las COMPETENCIAS no van.** El aviso real no las tiene: las inventó el prototipo. Está
> escrito acá para que nadie las vuelva a proponer creyendo que faltan.

---

## El aviso, tal cual

```
Aviso de Búsqueda: Analista SQL

Descripción del Puesto:
Estamos en la búsqueda de un Analista Junior Avanzado / Semi Senior para unirse a nuestro
equipo de trabajo. Es una excelente oportunidad para aquellos que desean continuar
desarrollando su carrera profesional en el área de análisis funcional.

Responsabilidades:
- Análisis de datos: realizar el análisis de datos provenientes de diversas fuentes para
  identificar patrones, tendencias y generar informes que respalden la toma de decisiones.
- Análisis de legislación: evaluar y mantener actualizados los requisitos legales y normativos
  aplicables al área funcional, asegurando el cumplimiento de las regulaciones vigentes.
- Relevamiento de requerimientos: conducir sesiones de relevamiento con las partes interesadas
  para comprender sus necesidades y documentar los requerimientos funcionales.
- Minería de datos: aplicar técnicas de minería de datos para extraer información relevante y
  transformar datos sin procesar en conocimiento útil.

Requisitos:
- Experiencia mínima de 1 a 3 años en análisis funcional o roles relacionados.
- Conocimiento en metodologías ágiles.
- Dominio en herramientas de modelado.
- Conocimientos en SQL y experiencia trabajando con bases de datos, excluyente.
- Buenas habilidades de comunicación, tanto escritas como orales.
- Capacidad para identificar problemas y ofrecer soluciones innovadoras.
- Título de Analista de Sistemas, o afines.

Ofrecemos:
- Oportunidades de desarrollo profesional y crecimiento dentro de la empresa.
- Excelente ambiente de trabajo en un equipo colaborativo.
- Beneficios de ley y otros beneficios corporativos.

Ubicación: Córdoba y la modalidad es híbrida (1 vez por semana en oficina).
```

---

## Contraste campo por campo contra `perfiles_puesto` (13/8/2026)

| Bloque del aviso | Columna | Estado |
|---|---|---|
| `Aviso de Búsqueda: Analista SQL` | `nombre` | ✅ |
| Descripción del Puesto | `descripcion` | ✅ |
| Responsabilidades (4 ítems) | `funciones` | ✅ |
| Requisitos → "Experiencia mínima de 1 a 3 años" | `experiencia` | ✅ |
| Requisitos → "Título de Analista de Sistemas, o afines" | `formacion` | ✅ |
| Requisitos → ágiles · herramientas de modelado · SQL/bases de datos | `conocimientos_tecnicos` | ✅ |
| Requisitos → comunicación · resolución de problemas | `requisitos` | ✅ (ver nota 1) |
| **Ofrecemos (3 ítems)** | **`ofrecemos`** | ✅ **agregado por la migración 116** |
| Modalidad: "híbrida" | `modalidad` | ✅ (`hibrido`) |
| Ubicación: "Córdoba" | — | ⛔ **por decisión: va en `vacantes.ubicacion`** |
| Modalidad: "(1 vez por semana en oficina)" | — | ⚠️ ver nota 2 |
| "Junior Avanzado / Semi Senior" | `nivel` | ⚠️ ver nota 3 |

### Nota 1 — el bloque "Requisitos" del aviso NO mapea 1:1 a la columna `requisitos`

El aviso pone **siete cosas de cuatro naturalezas distintas** bajo un solo título: experiencia,
formación, conocimientos técnicos y habilidades blandas. La tabla tiene una columna para las tres
primeras, así que **`requisitos` queda como el cajón de lo que no entra en ninguna** — hoy, las
dos habilidades blandas.

**Consecuencia práctica para la UI:** si el formulario muestra los cuatro campos sin explicar
la diferencia, RRHH va a pegar el bloque entero en `requisitos` y dejar los otros tres vacíos —
y ahí el perfil deja de servir para filtrar o para armar un aviso por partes. Lo que hace falta
no es una columna más: son los labels y el orden del formulario.

### Nota 2 — "(1 vez por semana en oficina)" no tiene columna, y está bien

`modalidad` es una lista cerrada (`presencial|remoto|hibrido`), así que "híbrida" entra pero el
detalle de cuántos días no. **No se agregó columna a propósito**, por el mismo criterio que dejó
la ubicación afuera: **cuántos días se va a la oficina es de la búsqueda concreta, no de la
plantilla** — puede cambiar entre dos búsquedas del mismo perfil. Su lugar natural es el texto
de la vacante (`vacantes.jornada` o `vacantes.copy_publicacion`).

⚠️ **Si resultara que el detalle es estable por perfil y no por búsqueda, ahí sí falta una
columna** (`modalidad_detalle text`). Hoy no hay evidencia de eso: hay un solo aviso.

### Nota 3 — "Junior Avanzado / Semi Senior" es un RANGO y `nivel` guarda un valor

El CHECK de `nivel` acepta `junior|semi_senior|senior|lider|manager|director|c_level`: uno solo.
El aviso busca en una franja de dos. Hoy se resuelve eligiendo `semi_senior` y dejando la franja
escrita en `descripcion`, que es de donde sale el texto del aviso igual. **No se convirtió `nivel`
en un rango** (dos columnas o un array) porque un solo aviso no alcanza para saber si la franja
es lo normal o la excepción.

---

*HR Karstec · Referencia de perfiles de puesto · 13/8/2026*
