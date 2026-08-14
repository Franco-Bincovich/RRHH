"""
🔴 EL NÚCLEO DEL MÓDULO: de dónde salen los `*_anterior` y cuándo se pisa al empleado.

Vive en un archivo propio, con nombre propio, porque son DOS REGLAS que no se leen del código
que las usa y que se rompen solas si alguien "simplifica". Las dos salen del mismo hecho: **la
fecha efectiva es editable hacia atrás.** En octubre pueden cargar una que rigió en agosto.

─────────────────────────────────────────────────────────────────────────────────────────────
REGLA 1 — los `*_anterior` salen de la última recategorización PREVIA a `fecha_efectiva`
─────────────────────────────────────────────────────────────────────────────────────────────
Y solo si no hay ninguna previa, del empleado.

El reflejo es leer al empleado y copiar sus valores actuales. Con fecha retroactiva eso es
FALSO por construcción: si hoy la persona es SENIOR y cargan una del 1/8, el valor anterior al
1/8 no es SENIOR — es el que tenía entonces. Copiar el actual escribe un histórico que se
contradice con la fila que le sigue: la del 1/8 diría "de SENIOR a SEMI_SENIOR" y la del 1/9
diría "de SEMI_SENIOR a SENIOR", o sea que la persona bajó y subió sin que eso haya pasado.

El fallback al empleado NO es una concesión: para la PRIMERA recategorización de alguien, el
empleado ES el estado anterior. No hay otra fuente.

⚠️ Un `*_anterior` en NULL es un dato válido, no un faltante: significa "eso no estaba cargado".
Hoy `seniority` está 3/31 y `categoria` 2/31, así que va a ser el caso normal por un tiempo.

─────────────────────────────────────────────────────────────────────────────────────────────
REGLA 2 — el UPDATE del empleado corre SOLO si la fila es la más reciente de esa persona
─────────────────────────────────────────────────────────────────────────────────────────────
Registrar el histórico y actualizar al colaborador son DOS COSAS DISTINTAS, y la fecha
retroactiva las separa. Si en octubre cargan una del 1/8 cuando ya existe una del 1/9, el
histórico tiene que quedar completo **pero el empleado no se toca**: pisarlo con el valor del
1/8 lo dejaría con un rol que dejó de tener hace un mes.

Sin esta regla el resultado final del empleado **depende del ORDEN EN QUE SE CARGARON las
filas**, no de las fechas. Es exactamente el mismo modo de falla que el import de nómina ya
tuvo con los superiores (`_nomina_superiores`): un resultado que depende del orden del archivo
en vez de los datos.

🔑 EL EMPATE SE RESUELVE A FAVOR DE LA NUEVA (`>=`, no `>`). Dos filas con la misma
`fecha_efectiva` son legales —no hay UNIQUE sobre `(empleado_id, fecha_efectiva)`— y ante un
empate la última cargada es la que expresa la intención más reciente de quien la cargó. Con `>`
estricto, corregir una recategorización del mismo día cargando otra encima no actualizaría al
empleado, que es lo contrario de lo que espera quien la carga.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from schemas.empleado import EmpleadoResponse
from schemas.recategorizacion import RecategorizacionResponse


def resolver_anteriores(previa: Optional[RecategorizacionResponse],
                        empleado: EmpleadoResponse) -> dict:
    """Los tres `*_anterior` de una recategorización. Ver REGLA 1 en el encabezado.

    Cada campo se resuelve POR SEPARADO y con su propio fallback, no en bloque: una previa que
    solo cambió el rol deja `seniority_nueva` en NULL, y ahí el seniority anterior sigue siendo
    el del empleado, no NULL. Resolver los tres juntos ("si hay previa, los tres salen de ella")
    borraría el seniority y la categoría cada vez que alguien registra un cambio de rol solo.

    Args:
        previa: última recategorización ANTERIOR a la fecha efectiva, o None si es la primera.
        empleado: el colaborador, para el fallback campo por campo.

    Returns:
        dict con `rol_anterior`, `seniority_anterior` y `categoria_anterior`.
    """
    rol_emp = empleado.roles[0] if empleado.roles else None
    if previa is None:
        return {"rol_anterior": rol_emp, "seniority_anterior": empleado.seniority,
                "categoria_anterior": empleado.categoria}
    return {
        "rol_anterior": previa.rol_nuevo if previa.rol_nuevo is not None else rol_emp,
        "seniority_anterior": (previa.seniority_nueva if previa.seniority_nueva is not None
                               else empleado.seniority),
        "categoria_anterior": (previa.categoria_nueva if previa.categoria_nueva is not None
                               else empleado.categoria),
    }


def es_la_mas_reciente(fecha: date, ultima: Optional[RecategorizacionResponse]) -> bool:
    """¿Esta fecha efectiva es la más reciente del empleado? Ver REGLA 2 en el encabezado.

    Args:
        fecha: fecha efectiva de la recategorización que se está cargando o editando.
        ultima: la de fecha efectiva MÁS ALTA que ya tiene ese empleado (excluyendo la propia
            fila cuando se está editando), o None si no tiene ninguna.

    Returns:
        True si corresponde aplicar los valores nuevos al empleado.
    """
    return ultima is None or fecha >= ultima.fecha_efectiva


def patch_empleado(rec: RecategorizacionResponse, empleado: EmpleadoResponse) -> dict:
    """Los campos de `empleados` que la recategorización pisa. Solo los que trae cargados.

    🔴 `roles` REEMPLAZA SOLO `roles[0]` Y CONSERVA LOS SECUNDARIOS. `EmpleadoUpdate.roles` es
    reemplazo de lista completa, así que mandar `[rol_nuevo]` **borraría todo rol secundario**.
    Hoy los 31 empleados tienen exactamente uno y el bug sería invisible; aparecería el día que
    alguien cargue dos, sin ningún error y sin forma de recuperar el borrado.

    ⚠️ Y el corte es `roles[1:]`, NO `roles`: el rol PRINCIPAL VIEJO se va, que es lo que
    significa "recategorizar". Conservarlo lo degradaría a secundario y la persona terminaría
    acumulando un rol por cada recategorización de su carrera. Es el error que la primera
    versión de esta función tenía y que el test de los dos roles cazó.
    `_normalizar_roles` deduplica preservando orden, así que si el rol nuevo ya estaba como
    secundario queda una sola vez y pasa a ser el principal — que es lo correcto.

    Devuelve un dict vacío si la recategorización no trae ningún valor nuevo, cosa que el CHECK
    de la base impide; el caller no necesita saberlo.
    """
    patch: dict = {}
    if rec.rol_nuevo is not None:
        resto = [r for r in (empleado.roles or [])[1:] if r != rec.rol_nuevo]
        patch["roles"] = [rec.rol_nuevo, *resto]
    if rec.seniority_nueva is not None:
        patch["seniority"] = rec.seniority_nueva
    if rec.categoria_nueva is not None:
        patch["categoria"] = rec.categoria_nueva
    return patch


def empresa_de(empleado: EmpleadoResponse) -> UUID:
    """La empresa que se persiste: la del EMPLEADO, nunca la del header.

    Vista vs Acción. El `X-Empresa-Id` decide qué se MIRA; de quién ES la fila lo decide la
    entidad padre. Molde: `_adjunto_padres.ensure_padre_de_empresa`, que valida el padre y
    devuelve SU empresa para etiquetar la hija. Acá el padre ya viene validado por
    `ensure_empleado_de_empresa`, así que solo hay que leerla.

    Raises:
        ValueError: si el empleado no tiene empresa. No puede pasar —`empleados.empresa_id` es
            NOT NULL— pero el schema la declara `Optional`, y sin este corte un None viajaría a
            un INSERT con `empresa_id` NOT NULL y saldría como 500 en vez de decir qué faltó.
    """
    if empleado.empresa_id is None:
        raise ValueError(f"El empleado {empleado.id} no tiene empresa cargada")
    return UUID(str(empleado.empresa_id))
