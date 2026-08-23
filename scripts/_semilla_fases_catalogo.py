"""
Fases de la semilla que tocan CATÁLOGOS: perfiles de puesto, agenda, objetivos y vacantes con
sus candidatos. Ninguna toca a un colaborador existente.

La quinta fase de catálogo —FORMACIÓN— vive en `_semilla_fases_formacion.py` y no acá: es la única que
siembra por DOS caminos de escritura distintos y arma un Excel para hacerlo, así que su archivo
tiene que explicar por qué. El corte es ése, no una división por líneas.

⚠️ TRES DE LAS CUATRO FASES DE ACÁ NECESITAN UNA EMPRESA CONCRETA en el header y la cuarta no:
los perfiles de puesto son del GRUPO (migración 113) y se crean sin `X-Empresa-Id`. No es una
inconsistencia: es la misma regla de Vista vs Acción, con un catálogo que no cuelga de ninguna
sociedad. Su hermano es `clientes`, el otro catálogo global del sistema.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

from _semilla_catalogo import EVENTOS, OBJETIVOS, PERFILES, VACANTES

HOY = date.today()


def _f(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


def sembrar_perfiles(cli) -> None:
    """6 perfiles del catálogo GLOBAL (no tienen empresa: son del grupo, migración 113).

    Al último se le pega el DELETE, que en este módulo es baja LÓGICA (`activo=False`): la fila
    sobrevive porque `vacantes.perfil_puesto_id` es `ON DELETE SET NULL` y un borrado real le
    arrancaría la trazabilidad a toda vacante creada desde ese perfil.
    """
    print("→ perfiles de puesto (6, uno dado de baja)")
    catalogo = {p["nombre"]: str(p["id"]) for p in
                (cli.get("/api/perfiles-puesto",
                         params={"page_size": 100, "incluir_inactivos": True}) or {}).get("items", [])}
    for p in PERFILES:
        cuerpo = {k: v for k, v in p.items() if k != "baja"}
        pid = cli.obtener_o_crear(
            "perfiles_puesto", p["nombre"],
            crear=lambda c=cuerpo: str(cli.pedir("POST", "/api/perfiles-puesto", json_body=c)["id"]),
            buscar=lambda n=p["nombre"]: catalogo.get(n))
        if pid and p.get("baja"):
            cli.hito("perfiles_baja", p["nombre"],
                     lambda i=pid: cli.pedir("DELETE", f"/api/perfiles-puesto/{i}"))
        print(f"    {p['nombre']}{' · dado de baja' if p.get('baja') else ''}")


def sembrar_eventos(cli, empresa: str) -> None:
    """5 recordatorios de agenda: 2 dentro de su ventana de aviso, 2 fuera y 1 resuelto."""
    print("→ agenda (5 recordatorios)")
    # `incluir_resueltas` VA EN True: el listado los oculta por default, y sin esto una segunda
    # corrida sin manifiesto no encontraría el evento resuelto y lo volvería a crear.
    existentes = {e["nombre"]: str(e["id"]) for e in
                  (cli.get("/api/eventos", params={"page_size": 100, "incluir_resueltas": True},
                           empresa=empresa) or {}).get("items", [])}
    for ev in EVENTOS:
        cuerpo = {"nombre": ev["nombre"], "fecha": _f(ev["dias"]),
                  "descripcion": ev["descripcion"], "dias_aviso": ev["dias_aviso"],
                  "es_publica": ev["es_publica"]}
        eid = cli.obtener_o_crear(
            "eventos_agenda", ev["nombre"],
            crear=lambda c=cuerpo: str(cli.pedir("POST", "/api/eventos", json_body=c,
                                                 empresa=empresa)["id"]),
            buscar=lambda n=ev["nombre"]: existentes.get(n))
        if eid and ev.get("resuelta"):
            cli.hito("eventos_resueltos", ev["nombre"],
                     lambda i=eid: cli.pedir("PUT", f"/api/eventos/{i}/resuelta",
                                             json_body={"resuelta": True}, empresa=empresa))
        print(f"    {ev['nombre']} · {_f(ev['dias'])}"
              f"{' · resuelto' if ev.get('resuelta') else ''}")



def sembrar_objetivos(cli, empresa: str, responsables: List[str]) -> None:
    """8 objetivos: 4 anuales y 4 operativos, los tres estados, con un subobjetivo colgando.

    Los hijos van DESPUÉS de los padres (`padre` referencia un título de la misma lista), y el
    estado se pone por su endpoint propio: el alta no lo acepta (nace `por_hacer`).
    """
    print("→ objetivos (4 anuales + 4 operativos)")
    # 🔴 EL LISTADO DEVUELVE RAÍCES CON LOS HIJOS ANIDADOS, así que hay que APLANAR para buscar
    # por título: sin esto el subobjetivo no se encuentra nunca y una corrida sin manifiesto lo
    # volvería a crear, colgado del mismo padre. Es la misma trampa que `ObjetivoListResponse`
    # documenta para el total (`len(items)` ya no es la cantidad de objetivos).
    raices = (cli.get("/api/objetivos", empresa=empresa) or {}).get("items", [])
    existentes = {o["titulo"]: str(o["id"])
                  for o in raices + [h for r in raices for h in (r.get("hijos") or [])]}
    ids: Dict[str, str] = {}
    for i, o in enumerate(sorted(OBJETIVOS, key=lambda x: bool(x.get("padre")))):
        cuerpo = {"empresa_id": empresa, "responsable_id": responsables[i % len(responsables)],
                  "titulo": o["titulo"], "descripcion": o["descripcion"],
                  "prioridad": o["prioridad"], "fecha_entrega": _f(o["dias"]),
                  "tipo": o["tipo"], "periodicidad": o["periodicidad"],
                  "parent_id": ids.get(o.get("padre") or "")}
        oid = cli.obtener_o_crear(
            "objetivos", o["titulo"],
            crear=lambda c=cuerpo: str(cli.pedir("POST", "/api/objetivos", json_body=c,
                                                 empresa=empresa)["id"]),
            buscar=lambda t=o["titulo"]: existentes.get(t))
        if not oid:
            continue
        ids[o["titulo"]] = oid
        if o["estado"] != "por_hacer":
            cli.hito("objetivos_estado", o["titulo"],
                     lambda i2=oid, s=o["estado"]: cli.pedir(
                         "PUT", f"/api/objetivos/{i2}/estado", json_body={"estado": s},
                         empresa=empresa))
        print(f"    [{o['tipo']}] {o['titulo'][:60]} · {o['estado']}")


def _buscar_vacante(cli, titulo: str, empresa: str) -> Optional[str]:
    for v in (cli.get("/api/vacantes", params={"page_size": 100}, empresa=empresa)
              or {}).get("items", []):
        if v.get("titulo") == titulo:
            return str(v["id"])
    return None


def sembrar_vacantes(cli, empresa: str, areas: List[dict]) -> None:
    """4 búsquedas nuevas con 9 candidatos, uno de ellos en `oferta` (habilita Contratar).

    El candidato se da de alta por MULTIPART (`POST /api/vacantes/{id}/candidatos` lo recibe por
    formulario, con el CV opcional) y nace en `postulado`: la etapa se mueve después, por su
    endpoint, que es como lo hace la pantalla.
    """
    print("→ vacantes y candidatos")
    for i, v in enumerate(VACANTES):
        area = areas[i % len(areas)]
        cuerpo = {"empresa_id": empresa, "area_id": area["id"], "titulo": v["titulo"],
                  "descripcion": v["descripcion"], "requisitos": v["requisitos"],
                  "tipo_contrato": v["tipo_contrato"], "modalidad": v["modalidad"],
                  "ubicacion": v["ubicacion"], "jornada": v["jornada"],
                  "prioridad": v["prioridad"]}
        vid = cli.obtener_o_crear(
            "vacantes", v["titulo"],
            crear=lambda c=cuerpo: str(cli.pedir("POST", "/api/vacantes", json_body=c,
                                                 empresa=empresa)["id"]),
            buscar=lambda t=v["titulo"]: _buscar_vacante(cli, t, empresa))
        if not vid:
            continue
        for c in v["candidatos"]:
            correo = f"{c['nombre'].lower()}.{c['apellido'].lower()}@correo-ejemplo.com.ar"
            campos = {"nombre": c["nombre"], "apellido": c["apellido"], "email": correo,
                      "cargo_anterior": c["cargo"], "empresa_anterior": c["empresa"]}
            cid = cli.obtener_o_crear(
                "candidatos", correo,
                crear=lambda i2=vid, d=campos: str(cli.pedir(
                    "POST", f"/api/vacantes/{i2}/candidatos", data=d, empresa=empresa)["id"]))
            if cid and c["etapa"] != "postulado":
                cli.hito("candidatos_etapa", correo,
                         lambda i2=cid, e=c["etapa"]: cli.pedir(
                             "PUT", f"/api/candidatos/{i2}/etapa", json_body={"etapa": e},
                             empresa=empresa))
        print(f"    {v['titulo']} · {len(v['candidatos'])} candidatos")
