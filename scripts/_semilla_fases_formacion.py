"""
La fase de FORMACIÓN de la semilla, aparte de sus hermanas de `_semilla_fases_catalogo.py`.

🔴 ESTÁ SOLA PORQUE SIEMBRA POR DOS CAMINOS DISTINTOS Y NO ES REDUNDANCIA. El alta por
formulario (`POST /api/capacitaciones/asignaciones`) exige `empleado_id`, así que **no puede
producir la fila de `nombre_libre`** —la persona suelta que no está en el padrón—, que es
justamente el caso que la pantalla distingue. Esa fila solo la crea el import de Excel (A5.2).
Sembrar por los dos deja las dos formas en la pantalla y, de paso, ejercita el lector del Excel
y el matcheo contra el padrón, que hasta hoy nunca corrieron contra la base real.

⚠️ EL EXCEL SE CONSTRUYE EN MEMORIA con openpyxl y se manda por multipart, con los encabezados
EXACTOS que espera `_formacion_import_transforms` ("Año", "Fecha", "Título", "Duración (hs)" —
con acento). El lector reintenta sin acentos, pero escribirlos bien es lo que prueba el camino
que el archivo real recorre.

⚠️ EL IMPORT COMPARTE LA FRANJA DE RATE LIMIT `scope="import"`: 10 por hora entre los NUEVE
endpoints de importación del sistema. Las dos llamadas de acá (preview + confirmar) se gastan
dos de esas diez, así que una tarde de pruebas de import y varias corridas de la semilla se
pisan entre sí. Por eso el manifiesto corta antes de pedir: una segunda corrida no gasta cupo.
"""
import io
from datetime import date, timedelta
from typing import Dict, List

from _semilla_catalogo import CAPACITACIONES, NOMBRES_LIBRES

HOY = date.today()
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]


def _f(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()



def _excel_formacion(filas: List[dict]) -> bytes:
    """Arma el Excel de formación en memoria, con los encabezados del archivo real."""
    from openpyxl import Workbook

    wb = Workbook()
    hoja = wb.active
    hoja.title = "Formacion"
    columnas = ["Año", "Fecha", "Proyecto", "Colaborador", "Tipo de capacitación", "Título",
                "Entidad capacitadora", "Modalidad", "Duración (hs)", "Estado"]
    hoja.append(columnas)
    for f in filas:
        hoja.append([f[c] for c in columnas])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def sembrar_formacion(cli, empresa: str, reales: List[dict]) -> None:
    """3 capacitaciones + ~20 asignaciones: 15 por formulario y 5 por import de Excel."""
    print("→ formación (3 capacitaciones + asignaciones)")
    catalogo = {c["nombre"]: str(c["id"]) for c in
                (cli.get("/api/capacitaciones", params={"solo_activos": False}, empresa=empresa)
                 or {}).get("items", [])}
    ids: Dict[str, str] = {}
    for c in CAPACITACIONES:
        cuerpo = dict(c, empresa_id=empresa)
        cid = cli.obtener_o_crear(
            "capacitaciones", c["nombre"],
            crear=lambda b=cuerpo: str(cli.pedir("POST", "/api/capacitaciones", json_body=b,
                                                 empresa=empresa)["id"]),
            buscar=lambda n=c["nombre"]: catalogo.get(n))
        if cid:
            ids[c["nombre"]] = cid
    _asignaciones_por_formulario(cli, empresa, reales, ids)
    _asignaciones_por_import(cli, empresa, reales)


def _asignaciones_por_formulario(cli, empresa: str, reales: List[dict], ids: Dict[str, str]) -> None:
    """15 asignaciones vinculadas a colaboradores del padrón, repartidas en los tres estados."""
    de_empresa = [e for e in reales if e["empresa_id"] == empresa][:5]
    estados = ["completado", "en_curso", "pendiente"]
    hechas = 0
    for i, (nombre, cid) in enumerate(ids.items()):
        for j, emp in enumerate(de_empresa):
            estado = estados[(i + j) % 3]
            cuerpo = {"capacitacion_id": cid, "empleado_id": emp["id"],
                      "fecha_asignacion": _f(-90 + j * 7), "fecha_limite": _f(30 + j * 5),
                      "anio": str(HOY.year), "mes": _MESES[HOY.month - 1]}
            aid = cli.obtener_o_crear(
                "asignaciones_formacion", f"{nombre}@{emp['id']}",
                crear=lambda c=cuerpo: str(cli.pedir("POST", "/api/capacitaciones/asignaciones",
                                                     json_body=c, empresa=empresa)["id"]))
            if aid and estado != "pendiente":
                cli.hito("asignaciones_estado", f"{nombre}@{emp['id']}",
                         lambda i2=aid, s=estado, j2=j: cli.pedir(
                             "PUT", f"/api/capacitaciones/asignaciones/{i2}",
                             json_body={"estado": s,
                                        "fecha_completado": _f(-20 + j2) if s == "completado" else None},
                             empresa=empresa))
            hechas += 1 if aid else 0
    print(f"    {hechas} asignaciones por formulario (con colaborador vinculado)")


def _asignaciones_por_import(cli, empresa: str, reales: List[dict]) -> None:
    """5 filas por Excel: 2 que matchean el padrón y 3 que entran como `nombre_libre`.

    🔴 ES EL ÚNICO CAMINO que produce una asignación SIN colaborador vinculado. Ver el encabezado.
    """
    if cli.manifiesto.id_de("import_formacion", "lote"):
        print("    import de formación: ya sembrado (manifiesto)")
        return
    # 🔴 DESDE EL 5, NO DESDE EL 0: `_asignaciones_por_formulario` cubre a los cinco primeros
    # colaboradores × las tres capacitaciones, o sea LAS QUINCE combinaciones posibles entre
    # ellos. `empleado_capacitacion` tiene `UNIQUE (capacitacion_id, empleado_id)`, así que
    # cualquier fila del Excel sobre esos cinco choca sí o sí. Medido el 23/8/2026: con `[:2]` el
    # import reportaba 2 duplicados en cada corrida — el backend se portaba bien (los rechazaba
    # por fila y no abortaba el lote), el que estaba mal era este script.
    de_empresa = [e for e in reales if e["empresa_id"] == empresa][5:7]
    personas = [f"{e['nombre']} {e['apellido']}" for e in de_empresa] + NOMBRES_LIBRES
    filas = []
    for i, quien in enumerate(personas):
        cap = CAPACITACIONES[i % len(CAPACITACIONES)]
        filas.append({
            "Año": str(HOY.year), "Fecha": _MESES[max(0, HOY.month - 2)],
            "Proyecto": "Plan anual de formación", "Colaborador": quien,
            "Tipo de capacitación": cap["tipo"], "Título": cap["nombre"],
            "Entidad capacitadora": cap["entidad_capacitadora"], "Modalidad": cap["modalidad"],
            "Duración (hs)": cap["duracion_horas"],
            "Estado": ["Finalizado", "En curso", "Sin iniciar"][i % 3],
        })
    try:
        previo = cli.pedir(
            "POST", "/api/importacion/formacion/preview",
            data={"empresa_id": empresa},
            files={"file": ("formacion-semilla.xlsx", _excel_formacion(filas),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        confirmado = cli.pedir("POST", "/api/importacion/formacion/confirmar",
                               json_body={"empresa_id": empresa, "filas": previo["filas_validas"]})
    except Exception as exc:  # noqa: BLE001
        cli.anotar_fallo("import_formacion", "preview/confirmar", exc)
        return
    cli.manifiesto.anotar("import_formacion", "lote", "hecho")
    print(f"    import de Excel: {confirmado['importados']} filas "
          f"({len(previo['sin_match'])} sin match → nombre_libre), "
          f"{len(confirmado['errores'])} errores")

