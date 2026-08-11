"""
La DECISIÓN de la identificación pública: qué desenlace le corresponde a un dni.

Salió de `identificacion_service.py`, que estaba en 150/150. El corte es por responsabilidad, no
por cantidad: acá vive QUÉ SE DECIDE y allá QUÉ SE HACE con esa decisión (registrar el intento,
nivelar el tiempo, levantar el error único, emitir la sesión). Este módulo no sabe nada de
excepciones, de logs ni de tiempo; aquél no sabe nada de los cinco motivos.

🔴 NUNCA LANZA, Y ESO ES EL PUNTO. Devuelve `(resultado, empleado|None)`. Que no lance es lo que
permite que el caller tenga UN SOLO `raise` en todo el flujo: si cada rama levantara su propia
excepción, cinco mensajes distintos serían un typo de distancia y el rechazo único —que es lo que
impide que esta ruta se vuelva un oráculo de dnis— dependería de la disciplina de quien edite.
La contracara de esa regla vive en el encabezado de `identificacion_service.py`.

Los cinco resultados SÍ se distinguen acá adentro y se guardan en
`intentos_identificacion.resultado`: el log es lo único que le permite a RRHH ver que alguien
está probando dnis. Los valores son los del CHECK de esa tabla (migración 104).
"""
from typing import Optional, Tuple

OK = "ok"


def decidir(repo, limitador, dni: str) -> Tuple[str, Optional[dict]]:
    """Decide el desenlace de una identificación. NUNCA lanza.

    🔴 EL ORDEN IMPORTA. El límite por dni va PRIMERO, antes de tocar la base: un contador que
    solo se consulta después de dos queries no protege a la base de nada.

    Args:
        repo: `repositories.identificacion_repo` (o un doble).
        limitador: `consumir_intento` — devuelve False si el dni superó su límite.
        dni: El valor ya normalizado (sin espacios) que mandó el cliente.

    Returns:
        `(resultado, empleado|None)`. `resultado` es uno de los cinco motivos o `OK`. El empleado
        vuelve incluso en el rechazo por `sin_clientes`, para que el log pueda decir a quién
        correspondía.
    """
    if not dni:
        return "sin_coincidencia", None
    if not limitador(dni):
        return "bloqueado", None

    filas = repo.buscar_por_dni(dni)
    if not filas:
        return "sin_coincidencia", None
    if len(filas) > 1:
        # 🔴 `empleados` tiene UNIQUE (empresa_id, dni) y NO unique global: el mismo dni puede
        # estar cargado en dos sociedades del grupo. Las tres salidas posibles eran preguntar
        # de qué empresa —que publica justo el dato que la respuesta se cuida de no dar—,
        # elegir una —que imputaría las horas a la sociedad equivocada, en silencio— o
        # RECHAZAR. Se rechaza: es fail-closed, y queda registrado como `ambiguo` para que
        # RRHH lo vea y lo corrija en los datos, que es donde está el problema.
        # Hoy los 31 dnis de producción son distintos: es una guarda, no un caso vivo.
        return "ambiguo", None

    empleado = filas[0]
    if empleado.get("estado") != "activo":
        return "inactivo", None
    if not repo.hay_clientes_activos():
        # Sin clientes no hay nada que cargar, así que identificarse no lleva a ningún lado.
        # Se devuelve el empleado igual para que el LOG pueda decir a quién correspondía.
        #
        # 🔴 LA PREGUNTA ES DEL SISTEMA, NO DE LA EMPRESA DEL EMPLEADO (migración 108). El gate
        # SE QUEDA —con cero clientes en todo el sistema nadie puede imputar y "sin_clientes" es
        # honesto—, pero cambia su condición de disparo: antes bastaba que la sociedad de esa
        # persona no tuviera clientes cargados para dejarla afuera aunque el sistema tuviera
        # otros. El valor del CHECK en `intentos_identificacion` no cambia.
        return "sin_clientes", empleado
    return OK, empleado
