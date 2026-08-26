"""
Reglas de FORMA y DERIVACIÓN de campos del legajo, compartidas por los DOS escritores.

🔴 POR QUÉ ESTE MÓDULO EXISTE, y por qué no vive en `services/_nomina_parsers.py` (que sería el
lugar obvio). `empleados` tiene **dos escritores con vocabularios distintos**: el formulario, que
manda lo que tipeó una persona, y el import de nómina, que manda el Excel tal cual. Una regla que
viva en el parser del import solo alcanza a la mitad, y la otra mitad sigue escribiendo la
variante que la regla venía a evitar. En producción eso ya costó un conteo mal dado: `senior` (5,
del formulario) y `SENIOR` (1, del import) salían como DOS categorías en "Distribución de
plantilla" — ver `services/reportes/_reporte_distribucion._agrupar`.

Vive en `utils/` porque de acá pueden importar **schemas** y **services** sin invertir capas: el
molde es `utils/estados_empleado.py`, que hace lo mismo con el vocabulario de estados. Son
funciones puras, sin IO y sin Pydantic: quien las aplica es `schemas/_legajo_normalizado.py`, que
las cuelga de `EmpleadoBase`/`EmpleadoUpdate` y por herencia alcanza también a los dos schemas
del import.

⚠️ NORMALIZAR AL ESCRIBIR **NO REEMPLAZA** AL AGRUPAMIENTO DEFENSIVO DEL REPORTE, y confundirlo
sería el error caro: esto solo alcanza a las filas que se escriban de ahora en más. Las que ya
están en la tabla —y las columnas de texto libre que nadie va a normalizar nunca, como `turno`—
siguen necesitando que el reporte agrupe insensible a la caja. El porqué completo está escrito
en el docstring de `_agrupar`.
"""
from typing import Optional

# Espejo de `services/_nomina_parsers.VACIOS`: los literales que significan "no hay dato" y que
# NO son un valor. Se redeclara en vez de importarse para no invertir la capa (utils → services);
# son ocho literales estables y hay un test que compara las dos listas.
VACIOS_LEGAJO = {"", "NO APLICA", "N/A", "NA", "-", "--", "SIN DATOS", "SIN DATO"}

# Separadores de minutos que aparecen en la columna "Carga Horaria" del Excel real y en lo que
# tipea una persona. El punto es el que usa RRHH ("7.30 A 16.30 HS."), los otros dos son cortesía.
_SEP_MINUTOS = (".", ":", ",")

# La hora de almuerzo que se descuenta de la ventana del turno. Decisión de Capital Humano
# (14/8/2026), sin excepción por duración: un turno de 8 a 14 son 6 horas de ventana y 5 de
# contrato. Constante y no parámetro porque hoy no hay ninguna jornada que la exceptúe; el día
# que la haya, la excepción es un dato del legajo, no un argumento de esta función.
ALMUERZO_HORAS = 1.0


def _vacio(v: Optional[str]) -> bool:
    return not v or v.strip().upper() in VACIOS_LEGAJO


def normalizar_seniority(v: Optional[str]) -> Optional[str]:
    """Trim + `_`/`-` a espacio + colapso + Mayúscula Inicial Por Palabra.
    '' y los literales de `VACIOS_LEGAJO` → None.

    🔴 **EL VALOR GUARDADO ES, A LA VEZ, LA ETIQUETA QUE SE MUESTRA. Ésa es la decisión.**
    El problema tenía dos mitades —unificar `senior` con `SENIOR`, y que la pantalla no diga
    `semi_senior`— y la salida obvia era resolverlas por separado: guardar en minúscula y derivar
    una etiqueta al pintar. Se descartó, y el motivo es concreto: esa derivación tendría que
    existir en el front (ficha, combobox, chips de filtro) **y** en el backend (export, PDF,
    reportes), o sea DOS implementaciones de la misma regla sobre la misma columna. Es exactamente
    la divergencia pantalla-vs-archivo que el bloque N7 acaba de cerrar, reintroducida por la
    puerta de al lado. Canonizando a la forma legible **no hay una segunda implementación que
    pueda divergir**: la ficha, el Excel y el PDF muestran la columna tal cual.

    🔑 Y contesta sola la pregunta de "¿y si alguien escribe uno nuevo?": se ve igual que los
    conocidos, porque pasa por la misma función. No hay catálogo que actualizar.
    ⚠️ El repo ya tiene el mecanismo `value`/`label` para este mismo concepto, en
    `schemas/_perfil_puesto_campos.py` (`{"value": "semi_senior", "label": "Semi Senior"}`), y NO
    sirve acá: aquél es un vocabulario CERRADO de siete niveles y esto es texto libre. Un catálogo
    a mano sobre un campo abierto es el mapa que se desactualiza al primer valor nuevo.

    🔴 QUÉ SE PIERDE, dicho de frente: **un acrónimo pierde sus mayúsculas** ("PM" → "Pm"). Se
    acepta porque `seniority` es una PALABRA (el nivel de la persona), no un código — y el campo
    que sí es un código, `categoria`, va al revés justamente por eso: ver `normalizar_categoria`.
    Restaurar acrónimos exigiría una lista de excepciones, que es el mapa que esto evita.
    ⚠️ Los ACENTOS se preservan tal cual se tipean, no se inventan: "lider" queda "Lider" y no
    "Líder". Dos grafías que sólo difieran en el acento siguen siendo dos valores; lo que lo
    contiene en la práctica es que el combobox sugiere lo que ya existe.
    """
    if _vacio(v):
        return None
    limpio = " ".join(v.replace("_", " ").replace("-", " ").split()).lower()
    return " ".join(p[:1].upper() + p[1:] for p in limpio.split(" "))


def normalizar_categoria(v: Optional[str]) -> Optional[str]:
    """Trim + colapso de espacios + MAYÚSCULAS. '' y los literales de `VACIOS_LEGAJO` → None.

    🔴 VA AL REVÉS QUE `seniority` A PROPÓSITO, y la asimetría es la regla, no una excepción: la
    categoría es un **CÓDIGO** (`C1`…`C7` en producción) y los códigos van en mayúscula; el
    seniority es una **PALABRA** y las palabras van con mayúscula inicial. Bajar ésta a minúscula
    daría `c6`, que no figura así en ninguna planilla de Capital Humano. Igual que allá, **el
    valor guardado es la etiqueta que se muestra**: no hay una segunda regla de presentación.

    ⚠️ **ACEPTA NÚMEROS PELADOS Y ESO ES REQUISITO, NO TOLERANCIA** (bloque 4): la categoría es el
    nivel dentro del seniority y producción ya tiene un `3` cargado. `str.upper()` deja los
    dígitos intactos, así que "3" entra y sale igual. Cualquier validación que exigiera una letra
    inicial expulsaría ese valor real: no la agregues.
    """
    if _vacio(v):
        return None
    return " ".join(v.split()).upper()


def _hora_a_decimal(txt: str) -> Optional[float]:
    """'8' → 8.0 · '7.30' → 7.5 · '16:30' → 16.5. None si no es una hora legible."""
    t = txt.strip()
    for sep in _SEP_MINUTOS:
        if sep in t:
            h, _, m = t.partition(sep)
            if not (h.strip().isdigit() and m.strip().isdigit()):
                return None
            minutos = int(m.strip())
            # "7.5" en una columna de horarios es 7:30, no 7 con 5 minutos; pero "7.05" es 7:05.
            # Un solo dígito después del separador se lee como DECENAS de minuto, que es como lo
            # escribe quien tipea "7.3" queriendo decir y media... y también quien quiere decir
            # 7 y 3 décimas. Ante la duda se rechaza: un turno mal leído escribe horas mal.
            if len(m.strip()) != 2 or minutos >= 60:
                return None
            return int(h.strip()) + minutos / 60
    return float(t) if t.isdigit() else None


def horas_desde_turno(turno: Optional[str]) -> Optional[int]:
    """Horas de contrato derivadas de la ventana del turno, menos la hora de almuerzo.

    Formato real de la columna "Carga Horaria" del Excel de nómina, medido en producción el
    25/8/2026 sobre las 31 filas que la tienen cargada: `"8 A 17 HS."` (28), `"8 A 14 HS."`,
    `"10 A 18 HS."` y `"7.30 A 16.30 HS."`. O sea **`<desde> A <hasta>` con un sufijo opcional**,
    y el punto como separador de minutos. El parseo acepta además `:` y `,`, y el sufijo `HS`
    con o sin punto, porque el campo también lo tipea una persona en el formulario.

    🔑 LA REGLA ESTÁ VERIFICADA CONTRA EL DATO, no supuesta: los 10 empleados con
    `horas_contrato` cargado a mano tienen 8, y todos tienen turno `"8 A 17 HS."` → 9 horas de
    ventana menos 1 de almuerzo = 8. La derivación reproduce exactamente lo que RRHH ya cargó.

    Devuelve None —y no un número inventado— cuando el texto no matchea, cuando la ventana no
    llega a superar el almuerzo, o cuando el resultado no es un entero de horas: la columna es
    `integer` y escribir un redondeo silencioso sería afirmar una jornada que nadie declaró.
    ⚠️ Un turno que cruza la medianoche (22 A 6) se interpreta como nocturno: +24 al cierre.
    """
    if _vacio(turno):
        return None
    limpio = turno.strip().upper().rstrip(".")
    for sufijo in (" HS", " HORAS", " H"):
        if limpio.endswith(sufijo):
            limpio = limpio[: -len(sufijo)].strip()
    partes = limpio.replace(" A ", "|").replace("-", "|").split("|")
    if len(partes) != 2:
        return None
    desde, hasta = (_hora_a_decimal(p) for p in partes)
    if desde is None or hasta is None or not (0 <= desde < 24) or not (0 <= hasta <= 24):
        return None
    if hasta == desde:
        return None  # no es un turno nocturno, es un tipeo: la ventana sería de 24 horas
    if hasta < desde:
        hasta += 24  # turno nocturno
    horas = hasta - desde - ALMUERZO_HORAS
    # El tope de 16 no es cosmético: sin él, un "8 A 7" (que se lee como nocturno de 23 horas)
    # escribiría una jornada imposible en una columna de la que después cuelga el cálculo de
    # licencias. Ante un valor absurdo, mejor la celda vacía que un número que nadie va a revisar.
    if horas <= 0 or horas > 16 or abs(horas - round(horas)) > 1e-9:
        return None
    return int(round(horas))
