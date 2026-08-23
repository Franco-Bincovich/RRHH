"""
La fase de LICENCIAS: ausencias y vacaciones. Tres pantallas de uso diario que quedaron en cero
en la primera tanda de la semilla.

🔴 LOS TIPOS DE AUSENCIA NO SE INVENTAN: se LEEN de `GET /api/ausencias/tipos`. El catálogo es
global (las cuatro filas base no tienen `empresa_id`) y RRHH lo edita desde la UI, así que un
nombre hardcodeado acá se rompe el día que alguien lo renombra —y peor, "Injustificada" está
DESACTIVADA a propósito (mezclaba el eje *calificación* con el eje *naturaleza*, ver CLAUDE.md),
o sea que una lista escrita a mano la incluiría y el alta fallaría contra el CHECK.

⚠️ `justificada` ES UN HECHO DE LA INSTANCIA, NO UNA PROPIEDAD DEL TIPO. `tipos_ausencia`
tiene `cuenta_ausentismo`, que es la POLÍTICA (si computa o no en la tasa); `justificada` dice
si ESTA ausencia concreta tenía respaldo. Una licencia por maternidad puede estar justificada y
aun así no computar. Por eso la semilla varía las dos cosas por separado.

🔴 DOS AUSENCIAS TIENEN QUE ESTAR EN CURSO HOY. El KPI "ausencias en curso" del dashboard
cuenta las que solapan la fecha de hoy; sin ninguna vigente la card dice 0 y no se puede probar.
Las otras van a meses pasados para que el ausentismo del mes deje de ser 0,0%.

⚠️ EL ESTADO DE UNA VACACIÓN ES DERIVADO, no una columna: `cancelada` > `planificada` (si hoy <
fecha_desde) > `tomada`. Por eso la semilla no manda ningún estado — lo produce con las FECHAS,
y la cancelada se cancela por su endpoint propio (`PUT /{id}/cancelar`, que no borra la fila).
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

HOY = date.today()

# `legajo` apunta a PERSONAS de `_semilla_padron`. Solo los 5 ACTIVOS: una ausencia de alguien
# que todavía no ingresó no existe, y el KPI de ausentismo la contaría igual.
# `dias_desde`/`dias_hasta` son relativos a hoy — las dos primeras lo cruzan (en curso).
AUSENCIAS = [
    dict(legajo="SMK-05", tipo="Enfermedad", dias_desde=-2, dias_hasta=3, justificada=True,
         motivo="Reposo indicado por el médico laboral."),
    dict(legajo="SMK-08", tipo="Personal", dias_desde=0, dias_hasta=1, justificada=True,
         motivo="Trámite personal impostergable."),
    dict(legajo="SMK-06", tipo="Enfermedad", dias_desde=-24, dias_hasta=-21, justificada=True,
         motivo="Cuadro gripal con certificado."),
    dict(legajo="SMK-09", tipo="Otro", dias_desde=-40, dias_hasta=-40, justificada=False,
         motivo="No se presentó ni avisó."),
    dict(legajo="SMK-07", tipo="Licencia", dias_desde=-70, dias_hasta=-64, justificada=True,
         motivo="Licencia por matrimonio."),
]

# La cancelada se crea a futuro y se cancela después: cancelar una ya tomada no tendría sentido.
VACACIONES = [
    dict(legajo="SMK-05", dias_desde=-45, dias_hasta=-31, tipo="vacaciones",
         comentario="Receso de invierno.", cancelar=False),
    dict(legajo="SMK-08", dias_desde=35, dias_hasta=49, tipo="vacaciones",
         comentario="Licencia planificada para el próximo trimestre.", cancelar=False),
    dict(legajo="SMK-06", dias_desde=70, dias_hasta=77, tipo="vacaciones",
         comentario="Se reprograma por cobertura del sector.", cancelar=True),
    dict(legajo="SMK-09", dias_desde=-12, dias_hasta=-12, tipo="dia_free",
         comentario="Día franco por aniversario.", cancelar=False),
]


def _f(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


def _tipos(cli) -> Dict[str, str]:
    """`{nombre: id}` de los tipos ACTIVOS. Leídos del sistema, nunca hardcodeados."""
    datos = cli.get("/api/ausencias/tipos") or {}
    return {t["nombre"]: str(t["id"]) for t in datos.get("items", []) if t.get("activo")}


def _buscar(cli, ruta: str, empleado_id: str, desde: str, empresa: str) -> Optional[str]:
    """Clave natural: (empleado, fecha_desde) no se repite dentro de la semilla."""
    pagina = cli.get(ruta, params={"empleado_id": empleado_id, "page_size": 100},
                     empresa=empresa) or {}
    for f in pagina.get("items", []):
        if str(f.get("fecha_desde")) == desde:
            return str(f["id"])
    return None


def sembrar_ausencias(cli, personas: Dict[str, dict], exigir_sembrado) -> None:
    """5 ausencias: 2 en curso hoy y 3 en meses pasados, con tipos y justificación variados."""
    print("→ ausencias (2 en curso hoy + 3 pasadas)")
    catalogo = _tipos(cli)
    if not catalogo:
        print("    ✗ el catálogo de tipos de ausencia vino vacío: no se puede sembrar")
        return
    for a in AUSENCIAS:
        persona = personas.get(a["legajo"])
        if not persona:
            continue
        tipo_id = catalogo.get(a["tipo"])
        if not tipo_id:
            print(f"    ✗ tipo '{a['tipo']}' no está en el catálogo activo: {sorted(catalogo)}")
            continue
        exigir_sembrado(cli, persona, "cargar una ausencia")
        desde = _f(a["dias_desde"])
        cuerpo = {"empleado_id": persona["id"], "tipo_id": tipo_id, "fecha_desde": desde,
                  "fecha_hasta": _f(a["dias_hasta"]), "justificada": a["justificada"],
                  "motivo": a["motivo"]}
        cli.obtener_o_crear(
            "ausencias", f"{a['legajo']}@{desde}",
            crear=lambda c=cuerpo, e=persona["empresa_id"]: str(cli.pedir(
                "POST", "/api/ausencias", json_body=c, empresa=e)["id"]),
            buscar=lambda i=persona["id"], d=desde, e=persona["empresa_id"]:
                _buscar(cli, "/api/ausencias", i, d, e))
        curso = "EN CURSO" if a["dias_desde"] <= 0 <= a["dias_hasta"] else "pasada"
        print(f"    {a['legajo']} · {a['tipo']:11} {desde} → {_f(a['dias_hasta'])} · {curso}"
              f" · {'justificada' if a['justificada'] else 'SIN justificar'}")


def sembrar_vacaciones(cli, personas: Dict[str, dict], exigir_sembrado) -> None:
    """4 licencias: una tomada, una planificada, una cancelada y un día franco.

    El estado NO se manda: lo deriva el service de las fechas y del flag `cancelada`. Cancelar
    va por `PUT /{id}/cancelar`, que marca la fila y no la borra — así la licencia cancelada
    sigue estando en el histórico, que es lo que la pantalla tiene que poder mostrar.
    """
    print("→ vacaciones (tomada · planificada · cancelada · día franco)")
    for v in VACACIONES:
        persona = personas.get(v["legajo"])
        if not persona:
            continue
        exigir_sembrado(cli, persona, "cargar una licencia")
        desde = _f(v["dias_desde"])
        cuerpo = {"empleado_id": persona["id"], "fecha_desde": desde,
                  "fecha_hasta": _f(v["dias_hasta"]), "tipo": v["tipo"],
                  "comentario": v["comentario"], "periodo": HOY.year}
        vid = cli.obtener_o_crear(
            "vacaciones", f"{v['legajo']}@{desde}",
            crear=lambda c=cuerpo, e=persona["empresa_id"]: str(cli.pedir(
                "POST", "/api/vacaciones", json_body=c, empresa=e)["id"]),
            buscar=lambda i=persona["id"], d=desde, e=persona["empresa_id"]:
                _buscar(cli, "/api/vacaciones", i, d, e))
        cancelada = False
        if vid and v["cancelar"]:
            cancelada = cli.hito("vacaciones_canceladas", f"{v['legajo']}@{desde}",
                                 lambda i=vid, e=persona["empresa_id"]: cli.pedir(
                                     "PUT", f"/api/vacaciones/{i}/cancelar", empresa=e))
        estado = ("cancelada" if cancelada else
                  "planificada" if v["dias_desde"] > 0 else "tomada")
        print(f"    {v['legajo']} · {v['tipo']:16} {desde} → {_f(v['dias_hasta'])} · {estado}")
