"""
Mixin Pydantic que aplica las reglas de `utils/legajo_reglas` a los schemas de empleado.

🔴 ES UN MIXIN Y NO DOS PARES DE VALIDADORES COPIADOS porque los campos viven en DOS schemas
—`EmpleadoBase` (alta) y `EmpleadoUpdate` (edición)— y de cada uno cuelga además el schema del
import de nómina (`EmpleadoCreateNomina` / `EmpleadoUpdateNomina`). Escribir la regla en un solo
lugar del que hereden los cuatro es lo que hace que **el formulario y el import no puedan volver
a escribir vocabularios distintos en la misma columna**, que es el bug que esto cierra.

`check_fields=False` es obligatorio: el mixin no declara los campos (los declara cada schema),
así que sin eso Pydantic rechaza los validadores por apuntar a campos que él no ve.
"""
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from utils.legajo_reglas import horas_desde_turno, normalizar_categoria, normalizar_seniority


class LegajoNormalizado(BaseModel):
    """Normaliza `seniority`/`categoria` y deriva `horas_contrato` del turno."""

    @field_validator("seniority", mode="after", check_fields=False)
    @classmethod
    def _seniority(cls, v: Optional[str]) -> Optional[str]:
        return normalizar_seniority(v)

    @field_validator("categoria", mode="after", check_fields=False)
    @classmethod
    def _categoria(cls, v: Optional[str]) -> Optional[str]:
        return normalizar_categoria(v)

    @model_validator(mode="after")
    def _derivar_horas_contrato(self):
        """`horas_contrato` sale del turno **solo si el payload no lo trae**.

        🔴 EL ORDEN DE PRECEDENCIA ES LA FEATURE: lo cargado a mano SIEMPRE gana. Quien escribe
        un número lo escribió por algo (una jornada reducida, un acuerdo particular), y una
        derivación que lo pise convierte el campo en no-editable — que es justo lo contrario de
        lo que se pidió. `None` acá no significa "borrar": significa "no dije nada", porque los
        dos repos de escritura descartan los None del payload (`exclude_none` en el update,
        filtro por `is not None` en el alta).

        Con esto el import de nómina pasa a poblar la columna sin tocar una línea suya: manda
        `turno` (la columna "Carga Horaria" del CSV) y nunca mandó `horas_contrato`, así que cae
        exactamente en esta rama. Era **0 de 31 filas importadas** — y de ese cero depende el
        cálculo de licencias del link público de horas, que sin jornada asume 8 y lo avisa.
        """
        if getattr(self, "horas_contrato", None) is None:
            derivadas = horas_desde_turno(getattr(self, "turno", None))
            if derivadas is not None:
                object.__setattr__(self, "horas_contrato", derivadas)
        return self


class RecategorizacionNormalizada(BaseModel):
    """Las MISMAS dos reglas, sobre los campos que la recategorización llama distinto.

    🔴 POR QUÉ HACE FALTA UN SEGUNDO MIXIN Y NO ALCANZA CON EL DE ARRIBA. `RecategorizacionCreate`
    no tiene `seniority` ni `categoria`: tiene `seniority_nueva` y `categoria_nueva`, que son las
    mismas dos cosas con otro nombre porque la tabla guarda el ANTES y el DESPUÉS. Un
    `field_validator` se ata al nombre del campo, así que el mixin de arriba no las alcanza.
    Lo que NO se duplica es la regla: las dos clases llaman a las mismas funciones de
    `utils.legajo_reglas`. Lo único que hay acá es el mapeo de nombres.

    🔴 EL BUG QUE CIERRA, y lo introdujo la normalización misma (25/8/2026). La recategorización
    escribe en DOS lados: la fila del historial (con estos campos) y el legajo del empleado (por
    `EmpleadoUpdate`, que SÍ pasa por el mixin de arriba). Sin esto, tipear "SENIOR" en el
    formulario dejaba al empleado en `Senior` —normalizado— y a la fila del historial diciendo
    **`Senior → SENIOR`**: un cambio que no ocurrió, sobre una pantalla cuyo único trabajo es
    contar qué cambió. Y `seniority_anterior` sale de `empleado.seniority`
    (`_recategorizacion_anteriores`), o sea del lado ya normalizado, así que las dos puntas de la
    misma fila hablaban vocabularios distintos.

    ⚠️ Es la misma familia del caso que el módulo ya tenía anotado en
    `services/_recategorizacion_edicion.py` (la fila que quedaba diciendo `semi_senior →
    semi_senior`). Con las dos puntas normalizadas, un "cambio" que sólo difiere en la caja pasa a
    verse como lo que es: nada.
    """

    @field_validator("seniority_nueva", mode="after", check_fields=False)
    @classmethod
    def _seniority_nueva(cls, v: Optional[str]) -> Optional[str]:
        return normalizar_seniority(v)

    @field_validator("categoria_nueva", mode="after", check_fields=False)
    @classmethod
    def _categoria_nueva(cls, v: Optional[str]) -> Optional[str]:
        return normalizar_categoria(v)
