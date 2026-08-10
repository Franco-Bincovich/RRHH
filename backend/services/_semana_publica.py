"""
"Lo que cargaste esta semana": la tabla de solo lectura del link público.

Función libre que recibe el repo — mismo molde que `_sesion_horas` y `_carga_licencia`. El
service la delega en una línea.

🔴 LA SEMANA ES LUNES A DOMINGO, Y LA DECIDE EL BACKEND.
No la elige el cliente: el endpoint NO acepta fechas. Dos motivos, y el segundo es el que manda:
  1. El mockup dice "lo que cargaste esta semana", no "elegí un rango". Un parámetro que nadie
     pidió es superficie de más en una ruta pública.
  2. Un rango libre convertiría este GET en un lector del HISTORIAL COMPLETO de la persona.
     Acotado a la semana en curso, lo peor que puede leer alguien que se robó un token vigente
     son siete días — y el token vive 30 minutos.

Lunes como primer día es el estándar ISO y el que usa el calendario laboral local. Se calcula con
`weekday()` (0 = lunes), no con `isoweekday()`, para no sumar una conversión que se lee al revés.

⚠️ LAS LICENCIAS ENTRAN POR SOLAPAMIENTO, no por contención: una licencia del viernes al martes
aparece en las DOS semanas que cruza. El porqué está en `_semana_publica_repo.licencias_de`.
"""
from datetime import date, timedelta
from typing import List

from schemas.horas_publico import CargaDeLaSemana, LicenciaDeLaSemana, SemanaResponse


def rango_semana(hoy: date) -> tuple:
    """(lunes, domingo) de la semana que contiene a `hoy`. `hoy` se inyecta para poder testear
    los bordes sin depender de cuándo corre la suite."""
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes, lunes + timedelta(days=6)


def _carga(h) -> CargaDeLaSemana:
    """Proyecta una fila a lo MÍNIMO. Sin `id`: el empleado no puede editar ni borrar."""
    return CargaDeLaSemana(
        fecha=h.fecha, cliente_nombre=h.cliente_nombre, proyecto_texto=h.proyecto_texto,
        tarea_texto=h.tarea_texto, horas=h.horas, modalidad=h.modalidad,
    )


def _licencia(fila: dict) -> LicenciaDeLaSemana:
    """`motivo` se expone como `observaciones`: es el nombre con el que la persona lo escribió
    en el formulario de carga, y devolverle otro la haría dudar de si es lo mismo."""
    return LicenciaDeLaSemana(
        fecha_desde=fila["fecha_desde"], fecha_hasta=fila["fecha_hasta"],
        dias=fila["dias"], observaciones=fila.get("motivo"),
    )


def armar(repo, empleado_id: str, hoy: date) -> SemanaResponse:
    """La semana en curso del empleado. `empleado_id` viene de la SESIÓN, nunca del request.

    El total suma SOLO las horas cargadas, no las licencias: son dos unidades distintas —horas
    contra días— y sumarlas daría un número que no significa nada. La equivalencia en horas de
    una licencia se calcula al cargarla y se le muestra ahí.
    """
    desde, hasta = rango_semana(hoy)
    horas: List = repo.horas_de(empleado_id, desde.isoformat(), hasta.isoformat())
    licencias = repo.licencias_de(empleado_id, desde.isoformat(), hasta.isoformat())
    return SemanaResponse(
        desde=desde, hasta=hasta,
        total_horas=round(sum(float(h.horas or 0) for h in horas), 2),
        cargas=[_carga(h) for h in horas],
        licencias=[_licencia(f) for f in licencias],
    )
