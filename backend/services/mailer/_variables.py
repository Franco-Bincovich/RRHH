"""
CATÁLOGO de variables por contexto: qué puede usar una plantilla y de dónde sale cada valor.

Molde: el dict `_RENDERERS` de `services/export/engine.py` y el dispatcher de
`services/reportes/reporte_generators.py`. Vive EN CÓDIGO y no en una tabla a propósito: son
claves de programa con un resolver detrás, no datos que alguien edite. Una tabla de variables
invitaría a agregar una fila sin el resolver que la hace funcionar — una variable que existe en
la UI y nunca tiene valor.

## 🔴 POR QUÉ CADA PLANTILLA DECLARA SU CONTEXTO

`{{nombre_empleado}}` solo tiene sentido si el mail se manda EN CONTEXTO de un empleado. El
contexto declara de qué habla la plantilla, y de ahí sale qué variables puede usar. Con eso:
  · la UI ofrece SOLO las variables de ese contexto (RRHH no las escribe a mano);
  · el guardado RECHAZA una variable que el contexto no declara;
  · el render sabe qué entidades tiene que traer.

Sin el contexto, la única alternativa sería ofrecer todas las variables siempre y que la mitad
salga vacía según el caso — que es indistinguible de un bug para quien recibe el mail.

## 🔴 ES UNA ALLOWLIST, JAMÁS UN "TODO MENOS"

`_CAMPOS` enumera, variable por variable, de qué entidad y de qué campo sale el valor. Exponer
la fila entera del empleado (o un "todos los campos menos estos") haría que **cada columna nueva
de `empleados` se vuelva variable de mail sin que nadie lo decida**.

Es el argumento INVERSO al de `sin_derivados` en auditoría, y por el mismo motivo: allá la
pregunta es "¿qué cambió?" y enumerar MIENTE POR OMISIÓN (una columna nueva quedaría sin
auditar); acá la pregunta es "¿qué se puede mandar por mail?" y enumerar es la única respuesta
segura. La regla, escrita: **agregar una variable es una decisión, no una consecuencia de
agregar una columna.**

Lo que está FUERA, y por qué (lo verifica `tests/test_mail_variables.py`):
  · todo `costos_nomina` (sueldo) — un mail se reenvía, se imprime y queda en el buzón del
    destinatario para siempre; y saltearía el gate de `Seccion.COSTOS`, que existe justo para eso;
  · `dni`, `cuil` — documento;
  · `fecha_nacimiento` — dato personal; un saludo de cumpleaños necesita el NOMBRE, no la fecha;
  · los 6 `domicilio_*` — domicilio particular;
  · `telefono`, `telefono_alternativo`, `email_personal` — contacto personal (el corporativo sí);
  · `potencial`, `desempeno` — 🔴 el peor de todos: evaluación interna que nunca se comunicó;
  · `motivo_baja`, `entrevista_salida`, `notas_entrevista` — sensible, y sobre un vínculo que terminó;
  · cualquier `*_id` — un mail con un UUID adentro es un bug visible; va el nombre resuelto.
"""
from datetime import date, datetime
from typing import Dict, Optional, Tuple

# variable → (entidad de la que sale, campo de esa entidad).
# La entidad la provee el caller del render en un dict simple; ver `valores`.
_CAMPOS: Dict[str, Tuple[str, str]] = {
    # — empresa —
    "empresa_nombre": ("empresa", "nombre"),
    # — empleado —
    "nombre_empleado": ("empleado", "nombre"),
    "apellido_empleado": ("empleado", "apellido"),
    "nombre_completo": ("empleado", "_nombre_completo"),
    "email_empleado": ("empleado", "email_corporativo"),
    "area_nombre": ("empleado", "area_nombre"),
    "fecha_ingreso": ("empleado", "fecha_ingreso"),
    "modalidad_contratacion": ("empleado", "tipo_contrato"),
    "seniority": ("empleado", "seniority"),
    "superior_nombre": ("empleado", "manager_nombre"),
    # — vacación / ausencia —
    "fecha_desde": ("solicitud", "fecha_desde"),
    "fecha_hasta": ("solicitud", "fecha_hasta"),
    "dias": ("solicitud", "dias"),
    "tipo_licencia": ("solicitud", "tipo"),
}

# Variables que no salen de ninguna entidad: las calcula el render.
_CALCULADAS = ("fecha_hoy", "hora_ahora")

_EMPLEADO = ("nombre_empleado", "apellido_empleado", "nombre_completo", "email_empleado",
             "area_nombre", "fecha_ingreso", "modalidad_contratacion", "seniority",
             "superior_nombre")
_SOLICITUD = ("fecha_desde", "fecha_hasta", "dias", "tipo_licencia")

CONTEXTOS: Dict[str, Tuple[str, ...]] = {
    "ninguno": ("empresa_nombre",) + _CALCULADAS,
    "empleado": ("empresa_nombre",) + _EMPLEADO + _CALCULADAS,
    "vacacion": ("empresa_nombre",) + _EMPLEADO + _SOLICITUD + _CALCULADAS,
    "ausencia": ("empresa_nombre",) + _EMPLEADO + _SOLICITUD + _CALCULADAS,
}


def variables_de(contexto: str) -> Tuple[str, ...]:
    """Las variables que una plantilla de ese contexto puede usar. () si el contexto no existe."""
    return CONTEXTOS.get(contexto, ())


def campos_leidos() -> Tuple[Tuple[str, str], ...]:
    """De qué (entidad, campo) sale cada variable. Lo consume el test estructural que verifica
    que ninguna variable prohibida esté declarada — sin esto, ese test tendría que parsear el
    módulo a mano."""
    return tuple(_CAMPOS.values())


def valores(contexto: str, datos: dict, ahora: Optional[datetime] = None) -> Dict[str, str]:
    """Resuelve los valores de las variables del contexto a partir de `datos`.

    ⚠️ Una variable declarada pero SIN VALOR devuelve "" — no revienta. Un empleado sin área
    cargada, o sin superior (hoy `manager_id` está 0/19 en producción), es un DATO FALTANTE, no
    un error de programa: no puede tumbar el envío. Quien avisa es el preview, que marca las que
    quedaron vacías, y el render, que las loguea.

    Args:
        contexto: uno de CONTEXTOS.
        datos: {"empresa": {...}, "empleado": {...}, "solicitud": {...}} con dicts simples.
        ahora: inyectable para test (las variables calculadas dependen del reloj).

    Returns:
        {variable: valor ya formateado como texto}.
    """
    ahora = ahora or datetime.now()
    fuera: Dict[str, str] = {}
    for var in variables_de(contexto):
        if var == "fecha_hoy":
            fuera[var] = _texto(ahora.date())
        elif var == "hora_ahora":
            fuera[var] = ahora.strftime("%H:%M")
        else:
            entidad, campo = _CAMPOS[var]
            fuera[var] = _texto((datos.get(entidad) or {}).get(campo))
    return fuera


def _texto(valor) -> str:
    """Formatea un valor para un mail. Las fechas van dd/mm/aaaa, no ISO: el destinatario es una
    persona, no un sistema. None y "" dan "" — ver la nota de dato faltante en `valores`."""
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)
