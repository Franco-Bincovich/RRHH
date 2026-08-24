"""EL DESCUBRIMIENTO de bajas lógicas: qué services dan de baja SIN borrar la fila.

Sale de `_inv_destructivo` porque ese archivo llegó a su límite de 200 y porque son dos cosas
distintas: allá viven las DECLARACIONES (`BAJA_LOGICA`, `BAJA_CONDICIONAL`) y acá el detector
que las contrasta contra el código.

🔴 POR QUÉ HACE FALTA UN DETECTOR Y NO ALCANZA CON LAS DECLARACIONES. `evidencia_baja_logica()`
pregunta "¿lo declarado sigue siendo cierto?" y por construcción **no puede ver lo que nunca se
declaró**. El smoke de escritura del 23/8/2026 borró de verdad los DELETE del sistema y encontró
dos bajas lógicas sin declarar —`adjuntos` (`estado='eliminado'`) y `users` (`activo=false`)— que
el inventario mostraba como «🔴 borra la fila», o sea que le mentía al tester en la columna que
existe para decidir si aprieta el botón.
"""
from typing import List

from _inv_backend import BACKEND


# Lo que delata una baja lógica dentro del service, sin depender de seguir el salto
# router → service → repo (que es lo que daba CERO detecciones).
# ⚠️ Se comparan en MINÚSCULA. `onboarding_templates_service` dice "Soft delete si tiene
# instancias" con mayúscula y se escapaba de un match sensible a la caja — la misma clase de
# agujero que el detector angosto de más arriba.
_SENALES = ("soft delete", "soft-delete", "baja lógica", "baja es lógica", "baja blanda",
            "estado='eliminado'", 'estado="eliminado"', "estado='baja'", 'estado="baja"',
            '"activo": false', "'activo': false")
_NOMBRES_BAJA = ("def delete", "def eliminar", "def borrar", "def dar_de_baja")


def sospechosas_de_baja_logica() -> List[str]:
    """Services con un método de baja que EVIDENCIA no destruir la fila.

    🔴 Es la mitad que faltaba: `evidencia_baja_logica()` mira si lo DECLARADO sigue siendo
    cierto y no puede ver lo que nunca se declaró. Esto recorre `services/`, se queda con los
    métodos de baja y devuelve aquellos cuyo cuerpo o docstring dice que la fila sobrevive.
    El caller (el test) exige que cada uno esté en `BAJA_LOGICA` o en `BAJA_CONDICIONAL`.

    Busca sobre el TEXTO y no por AST a propósito: la señal está en la prosa tanto como en el
    literal del update, y este repo obliga a docstring en services.

    🔴 LA VENTANA ES EL ARCHIVO ENTERO, NO EL MÉTODO. La primera versión miraba 1200 caracteres
    a partir del `def delete` y encontraba 4 de las 7 reales: `cliente_service` y
    `perfil_puesto_service` explican su baja lógica en el docstring de MÓDULO, arriba de todo,
    lejos del método. Un detector que se pierde la mitad de los casos deja pasar exactamente lo
    que este chequeo existe para encontrar. **Acá un falso positivo cuesta una línea de
    declaración y un falso negativo cuesta un inventario que miente**, así que la ventana se
    ensancha a propósito.
    """
    out: List[str] = []
    for archivo in sorted((BACKEND / "services").glob("*.py")):
        if archivo.name.startswith("_"):
            continue
        texto = archivo.read_text(encoding="utf-8", errors="ignore")
        if not any(m in texto for m in _NOMBRES_BAJA):
            continue
        if any(s in texto.lower() for s in _SENALES):
            out.append(f"services/{archivo.name}")
    return out
