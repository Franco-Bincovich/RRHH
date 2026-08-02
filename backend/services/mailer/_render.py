"""
De plantilla + contexto a (asunto, cuerpo) listos para enviar.

## 🔴 SINTAXIS: `{{variable}}`, RESUELTA POR REEMPLAZO LITERAL

Doble llave, snake_case, sin espacios adentro. Es inconfundible dentro de un texto normal —un
`{{` no aparece en castellano por accidente, y `{simple}` o `%var%` sí pueden— y RRHH ya la vio
en Google Docs, Notion y Mailchimp: no hay que enseñarla.

⚠️ **NUNCA `str.format` NI f-strings PARA RESOLVERLAS.** `"{x.__class__.__init__.__globals__}"
.format(x=algo)` es un camino conocido a los internals del proceso, y el texto de la plantilla lo
escribe un usuario. Acá la resolución es una sustitución por regex contra un diccionario de
valores YA calculados: no se evalúa nada.

## 🔴 LA VARIABLE QUE EL CONTEXTO NO PROVEE: LAS TRES COSAS, EN TRES MOMENTOS

  1. **Al GUARDAR se RECHAZA** (`variables_invalidas`). Es la barrera principal y el único
     momento en que hay un humano mirando la pantalla y puede corregir un typo.
  2. **Al RENDERIZAR no se rompe** (`render` la deja en "" y la reporta en `faltantes`). Una
     variable declarada pero sin valor —el empleado sin área, `manager_id` en 0/19— es un dato
     faltante, no un error de programa: no puede tumbar un envío.
  3. **Al PREVISUALIZAR se avisa**: el preview muestra `faltantes` para que RRHH lo vea ANTES.

**Ninguna sobra.** Sin (1), un typo (`{{nombre_emplado}}`) llega al destinatario como texto
literal. Sin (2), el día que se saque una variable del catálogo, todas las plantillas guardadas
que la usen revientan con 500 en el primer envío. Sin (3), RRHH se entera por el destinatario.

## Preview y envío usan ESTE MISMO renderer
Si fueran dos, divergen — la lección de los filtros duplicados front/back. `render` no sabe si lo
que devuelve se va a mandar o a mostrar.
"""
import re
from typing import Dict, List, Optional, Tuple

from services.mailer._variables import valores, variables_de

# Nombre de variable: letras, números y guión bajo. Se toleran espacios alrededor del nombre
# ({{ nombre }}) porque es el error de tipeo más frecuente y rechazarlo no compra nada.
_VAR = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def variables_usadas(texto: str) -> List[str]:
    """Las variables que aparecen en un texto, sin repetir y en orden de aparición."""
    vistas: Dict[str, None] = {}
    for m in _VAR.finditer(texto or ""):
        vistas.setdefault(m.group(1), None)
    return list(vistas)


def variables_invalidas(contexto: str, *textos: str) -> List[str]:
    """Las variables usadas que el contexto NO declara. [] = la plantilla se puede guardar.

    Es la barrera (1) de las tres. Se corre sobre asunto Y cuerpo juntos: una variable inválida
    en el asunto es igual de mala que en el cuerpo, y separarlas daría dos mensajes de error
    para el mismo problema.
    """
    permitidas = set(variables_de(contexto))
    usadas: List[str] = []
    for texto in textos:
        usadas.extend(v for v in variables_usadas(texto) if v not in permitidas and v not in usadas)
    return usadas


def render(contexto: str, asunto: str, cuerpo: str, datos: dict,
           ahora=None) -> Tuple[str, str, List[str]]:
    """Sustituye las variables y devuelve `(asunto, cuerpo, faltantes)`.

    `faltantes` son las variables VÁLIDAS que quedaron sin valor. No es un error: es lo que el
    preview pinta en amarillo y lo que el envío loguea a WARNING.

    ⚠️ Una variable que el contexto no declara (por ejemplo, si se sacó del catálogo después de
    guardar la plantilla) se reemplaza por "" y también se reporta. NO se deja el `{{...}}` en el
    texto: un mail que le llega al destinatario con `{{nombre_emplado}}` adentro es peor que uno
    con un hueco — el hueco se lee como un dato que falta, el literal como un sistema roto.

    El escapado NO se hace acá: lo hace `_markdown.a_html`, DESPUÉS de esta sustitución, para que
    los valores —que salen de la base, no de la plantilla— también queden escapados. Un empleado
    llamado `Ana <script>` es el vector real.
    """
    vals = valores(contexto, datos, ahora)
    faltantes: List[str] = []

    def _reemplazar(m: re.Match) -> str:
        nombre = m.group(1)
        valor = vals.get(nombre, "")
        if not valor and nombre not in faltantes:
            faltantes.append(nombre)
        return valor

    return _VAR.sub(_reemplazar, asunto or ""), _VAR.sub(_reemplazar, cuerpo or ""), faltantes


def datos_de_ejemplo(contexto: str) -> dict:
    """Valores de muestra para previsualizar sin elegir un empleado.

    ⚠️ Es el FALLBACK, no la opción principal: con datos inventados los huecos REALES (el área sin
    cargar, el superior vacío) no se ven, y son justamente el problema que hoy existe. Sirve para
    el contexto 'ninguno' y para cuando todavía no hay empleados cargados.
    """
    ejemplo = {
        "empresa": {"nombre": "Empresa de ejemplo"},
        "empleado": {"nombre": "Ana", "apellido": "Gómez", "_nombre_completo": "Ana Gómez",
                     "email_corporativo": "ana.gomez@ejemplo.com", "area_nombre": "Sistemas",
                     "fecha_ingreso": "2024-03-01", "tipo_contrato": "Relación de dependencia",
                     "seniority": "Senior", "manager_nombre": "Juan Pérez"},
        "solicitud": {"fecha_desde": "2026-01-05", "fecha_hasta": "2026-01-19", "dias": 15,
                      "tipo": "vacaciones"},
    }
    return ejemplo if contexto in ("empleado", "vacacion", "ausencia") else {"empresa": ejemplo["empresa"]}


def contexto_valido(contexto: Optional[str]) -> bool:
    """¿Es un contexto conocido? Lo usa el guardado antes de validar las variables."""
    return bool(contexto) and bool(variables_de(contexto))
