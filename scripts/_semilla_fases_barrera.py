"""
LA FASE DE LA BARRERA: un recurso de cada tipo que hoy SOLO existe como dato real de Karstec, o
que no existe en absoluto, sembrado **EN LAS DOS EMPRESAS**.

🔴 POR QUÉ EN LAS DOS, que es lo único que la distingue del resto de las fases. Las demás
siembran donde haga falta para que la pantalla muestre algo; ésta existe para poder probar la
BARRERA DE EMPRESA, y esa prueba necesita un recurso AJENO al que apuntar: se pide con el header
de la empresa A un id que es de la B, y el contrato dice 404 idéntico al de "no existe". Con el
recurso en una sola empresa la prueba no se puede escribir — que es exactamente el estado en el
que estaban estos módulos el 23/8/2026, cuando el smoke de §5 dejó 22 endpoints sin tocar por no
querer mandarle un DELETE a un dato real de Karstec, y otros 14 sin nada que apuntar.

🔴 LOS NOMBRES NO VIVEN ACÁ: están en `_semilla_catalogo_barrera.py`, junto con las tres
búsquedas compartidas. El limpiador los necesita para reconocer estas filas sin el manifiesto, y
tiene que poder leerlos sin depender del sembrador. Ver el encabezado de ese archivo.

⚠️ EL ONBOARDING SE INICIA SOBRE EL TITULAR SEMBRADO, y es el único recurso de la fase que no
estaba en la lista original. Hizo falta igual: `PUT /api/onboarding/{instancia_id}/tareas/
{tarea_id}/completar` es uno de los 22, y la ÚNICA instancia de producción es de un colaborador
REAL — probarlo con ella significaba mandarle un PUT a un legajo de Karstec.
"""
from datetime import date
from typing import Dict, List, Optional

from _semilla_catalogo_barrera import (
    AREA, EMPRESA_CESION, ITEM, PERIODO, PLANTILLA_CLAVE, PROYECTO, ROL_PROYECTO, TAREA,
    TEMPLATE, TIPO_AUSENCIA, buscar, clave, titular,
)


def _area(cli, empresa: str) -> None:
    """El `empresa_id` explícito del `buscar` NO es redundante: ver su docstring."""
    cli.obtener_o_crear(
        "areas_barrera", clave(AREA, empresa),
        crear=lambda: str(cli.pedir("POST", "/api/areas", empresa=empresa, json_body={
            "empresa_id": empresa, "nombre": AREA,
            "descripcion": "Área de prueba del smoke. Se borra con limpiar_semilla.py."})["id"]),
        buscar=lambda: buscar(cli, "/api/areas", "nombre", AREA, empresa,
                              {"empresa_id": empresa}))


def _proyecto(cli, empresa: str, quien: Optional[dict]) -> None:
    """Proyecto + asignación + una carga de horas. Los tres juntos porque cada uno cuelga del
    anterior: sin asignación no hay `asignacion_id` que mandar, y sin proyecto no hay ruta."""
    pid = cli.obtener_o_crear(
        "proyectos_barrera", clave(PROYECTO, empresa),
        crear=lambda: str(cli.pedir("POST", "/api/proyectos", empresa=empresa, json_body={
            "empresa_id": empresa, "nombre": PROYECTO, "estado": "activo",
            "descripcion": "Proyecto de prueba del smoke."})["id"]),
        buscar=lambda: buscar(cli, "/api/proyectos", "nombre", PROYECTO, empresa))
    if not pid or not quien:
        return
    aid = cli.obtener_o_crear(
        "asignaciones_proyecto_barrera", clave(PROYECTO, empresa),
        crear=lambda: str(cli.pedir("POST", f"/api/proyectos/{pid}/asignaciones", empresa=empresa,
                                    json_body={"empleado_id": quien["id"],
                                               "rol": ROL_PROYECTO})["id"]),
        buscar=lambda: buscar(cli, f"/api/proyectos/{pid}/asignaciones", "empleado_id",
                              quien["id"], empresa))
    if not aid:
        return
    cli.obtener_o_crear(
        "horas_proyecto_barrera", clave(PROYECTO, empresa),
        crear=lambda: str(cli.pedir(
            "POST", f"/api/proyectos/{pid}/horas", empresa=empresa,
            json_body={"asignacion_id": aid, "fecha": date.today().isoformat(), "horas": 1.0,
                       "descripcion": "SMK · Hora de barrera"})["id"]))


def _onboarding(cli, empresa: str, quien: Optional[dict]) -> None:
    """Template + una tarea + una instancia viva sobre el titular.

    La TAREA existe para que el PUT y el DELETE de `.../tareas/{tarea_id}` tengan a qué apuntar:
    son endpoints propios, no variantes del template. La INSTANCIA es otra cosa —el onboarding en
    curso de una persona— y su tarea de progreso es lo único que le da destino a
    `PUT /api/onboarding/{instancia_id}/tareas/{tarea_id}/completar`.
    """
    tid = cli.obtener_o_crear(
        "onboarding_templates_barrera", clave(TEMPLATE, empresa),
        crear=lambda: str(cli.pedir(
            "POST", "/api/onboarding/templates", empresa=empresa,
            json_body={"nombre": TEMPLATE, "empresa_id": empresa,
                       "descripcion": "Template de prueba del smoke."})["id"]),
        buscar=lambda: buscar(cli, "/api/onboarding/templates", "nombre", TEMPLATE, empresa))
    if not tid:
        return
    cli.obtener_o_crear(
        "onboarding_tareas_barrera", clave(TAREA, empresa),
        crear=lambda: str(cli.pedir(
            "POST", f"/api/onboarding/templates/{tid}/tareas", empresa=empresa,
            json_body={"titulo": TAREA, "semana": 1, "orden": 1,
                       "responsable_tipo": "rrhh"})["id"]))
    if not quien:
        return
    cli.obtener_o_crear(
        "onboarding_instancias_barrera", clave(TEMPLATE, empresa),
        crear=lambda: str(cli.pedir("POST", f"/api/onboarding/{quien['id']}/iniciar",
                                    empresa=empresa,
                                    json_body={"template_id": tid})["id"]),
        buscar=lambda: _onboarding_de(cli, quien["id"], empresa))


def _onboarding_de(cli, empleado_id: str, empresa: str) -> Optional[str]:
    """El onboarding activo de una persona, o None. 🔴 EL 404 ACÁ NO ES UN FALLO.

    `GET /api/onboarding/{empleado_id}` responde 404 `ONBOARDING_NOT_FOUND` cuando la persona
    todavía no tiene uno, que es EL CASO NORMAL de la primera corrida — el resto de las búsquedas
    de clave natural preguntan por un listado (que devuelve vacío) y ésta pregunta por un recurso
    puntual. Sin este catch, `Cliente.obtener_o_crear` lo anota como hallazgo y la corrida cierra
    con "2 FALLOS DE API" habiendo sembrado las dos instancias correctamente: un reporte que
    grita donde no pasó nada es un reporte que se deja de leer.
    """
    from _semilla_cliente import FalloAPI

    try:
        return str((cli.get(f"/api/onboarding/{empleado_id}", empresa=empresa) or {}).get("id"))
    except FalloAPI as exc:
        if exc.status == 404:
            return None
        raise


def _inventario(cli, empresa: str, quien: Optional[dict]) -> None:
    """Ítem + su asignación. Las dos tablas estaban en CERO filas: sin esto, cinco endpoints de
    inventario no tienen a qué apuntar ni con un id propio, mucho menos con uno ajeno."""
    iid = cli.obtener_o_crear(
        "inventario_items_barrera", clave(ITEM, empresa),
        crear=lambda: str(cli.pedir("POST", "/api/inventario/items", empresa=empresa, json_body={
            "empresa_id": empresa, "nombre": ITEM, "tipo": "notebook",
            "descripcion": "Ítem de prueba del smoke."})["id"]),
        buscar=lambda: buscar(cli, "/api/inventario/items", "nombre", ITEM, empresa))
    if not iid or not quien:
        return
    cli.obtener_o_crear(
        "inventario_asignaciones_barrera", clave(ITEM, empresa),
        crear=lambda: str(cli.pedir("POST", "/api/inventario/asignaciones", empresa=empresa,
                                    json_body={"item_id": iid, "empleado_id": quien["id"]})["id"]))


def _sueltos(cli, empresa: str, quien: Optional[dict]) -> None:
    """Los cuatro que no tienen hijas: cesión, plantilla de mail, período y tipo de ausencia."""
    if quien:
        cli.obtener_o_crear(
            "cesiones_barrera", clave(EMPRESA_CESION, empresa),
            crear=lambda: str(cli.pedir(
                "POST", f"/api/empleados/{quien['id']}/cesiones", empresa=empresa,
                json_body={"fecha": date.today().isoformat(),
                           "empresa_cesion": EMPRESA_CESION})["id"]))
    # 🔴 La plantilla se crea con PUT y no con POST: el endpoint es un UPSERT (`PlantillaUpsert`
    # lleva el `id` opcional). No es una excepción del smoke — es la forma del módulo.
    # Nace `activa=False`: una plantilla de prueba activa aparece en el selector de envío.
    cli.obtener_o_crear(
        "plantillas_barrera", clave(PLANTILLA_CLAVE, empresa),
        crear=lambda: str(cli.pedir("PUT", "/api/plantillas", empresa=empresa, json_body={
            "clave": PLANTILLA_CLAVE, "contexto": "ninguno",
            "asunto": "SMK · Asunto de barrera",
            "cuerpo": "Cuerpo de prueba del smoke.", "activa": False})["id"]),
        buscar=lambda: buscar(cli, "/api/plantillas", "clave", PLANTILLA_CLAVE, empresa))
    cli.obtener_o_crear(
        "periodos_barrera", clave(f"{PERIODO[0]}..{PERIODO[1]}", empresa),
        crear=lambda: str(cli.pedir("POST", "/api/periodos", empresa=empresa, json_body={
            "empresa_id": empresa, "desde": PERIODO[0], "hasta": PERIODO[1]})["id"]))
    cli.obtener_o_crear(
        "tipos_ausencia_barrera", clave(TIPO_AUSENCIA, empresa),
        crear=lambda: str(cli.pedir("POST", "/api/ausencias/tipos", empresa=empresa,
                                    json_body={"nombre": TIPO_AUSENCIA})["id"]),
        buscar=lambda: buscar(cli, "/api/ausencias/tipos", "nombre", TIPO_AUSENCIA, empresa,
                              {"incluir_inactivos": True}))


def sembrar_barrera(cli, empresas: List[dict]) -> Dict[str, str]:
    """Los recursos, uno por empresa. Devuelve `{empresa_id: legajo del titular}`."""
    print("→ barrera de empresa (los recursos que faltaban, × cada empresa)")
    titulares: Dict[str, str] = {}
    for e in empresas:
        emp = str(e["id"])
        quien = titular(cli, emp)
        if quien is None:
            print(f"    ⚠️ {e['nombre'][:40]}: sin colaborador SEMBRADO y ACTIVO — se saltean "
                  "cesión, asignación de proyecto, horas, inventario y onboarding")
        else:
            titulares[emp] = quien.get("legajo") or quien["id"]
        _area(cli, emp)
        _proyecto(cli, emp, quien)
        _onboarding(cli, emp, quien)
        _inventario(cli, emp, quien)
        _sueltos(cli, emp, quien)
        print(f"    {e['nombre'][:40]} · titular {titulares.get(emp, '—')}")
    return titulares
