"""
Fases de la semilla que tocan PERSONAS SEMBRADAS: los 10 colaboradores nuevos, sus
recategorizaciones y su offboarding (instancias abiertas y bajas efectivizadas).

🔴 TODO LO DE ESTE ARCHIVO APUNTA A GENTE QUE ESTE SCRIPT CREÓ, sin una sola excepción. Las dos
últimas fases MODIFICAN el legajo al que apuntan —recategorizar pisa rol/seniority/categoría, y
efectivizar escribe `estado='baja'`— así que las dos pasan por `_semilla_guarda.exigir_sembrado`,
que lo verifica CONTRA EL SISTEMA antes de escribir. La única fase que escribe sobre
colaboradores reales es la de nómina, y vive aparte en `_semilla_fases_nomina.py` justamente
para que la excepción se vea.

🔴 EL ORDEN ES EL DEL CICLO DE VIDA, y no es intercambiable:
  1. `sembrar_empleados` — los 9 nacen (4 en `preingreso`, 5 en `activo`).
  2. `sembrar_recategorizaciones` — sobre los 5 activos, ANTES de darlos de baja: una carrera se
     recategoriza mientras la persona trabaja, y así el histórico de la ficha se lee como un
     histórico y no como algo que pasó después de que se fue.
  3. `sembrar_offboarding` — 5 instancias; 3 se efectivizan y 2 quedan abiertas.

🔴 LO QUE ESTE ARCHIVO NO HACE, A PROPÓSITO: activar el preingreso que entra HOY. El botón
Activar tiene que funcionar EN EL RECORRIDO — si la semilla lo aprieta, la pantalla llega con el
caso ya resuelto y nadie prueba la guarda de fecha, que es el corazón de `_empleado_activar`.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

from _semilla_guarda import exigir_sembrado
from _semilla_padron import DOMINIO, PERSONAS, RECATEGORIZACIONES

HOY = date.today()



def _f(dias: int) -> str:
    return (HOY + timedelta(days=dias)).isoformat()


def _mail(p: dict) -> str:
    limpio = f"{p['nombre']}.{p['apellido']}".lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        limpio = limpio.replace(a, b)
    return f"{limpio}@{DOMINIO}"



def _buscar_empleado(cli, legajo: str, empresa: str) -> Optional[str]:
    """Clave natural del colaborador: su legajo. Es único por empresa y lo lleva la marca."""
    pagina = cli.get("/api/empleados", params={"search": legajo, "page_size": 100},
                     empresa=empresa)
    for e in pagina.get("items", []):
        if (e.get("legajo") or "") == legajo:
            return e["id"]
    return None


def sembrar_empleados(cli, empresas: List[dict], areas: Dict[str, list]) -> Dict[str, dict]:
    """Los 9 colaboradores nuevos. Devuelve `{legajo: {id, empresa_id, ...}}`.

    Reparte entre las empresas disponibles alternando, para que el modo consolidado y el filtro
    por empresa tengan las dos algo que mostrar.
    """
    print("→ colaboradores nuevos (4 preingresos + 5 activos + el jefe del mando medio)")
    creados: Dict[str, dict] = {}
    for i, p in enumerate(PERSONAS):
        empresa = empresas[i % len(empresas)]
        area = areas[empresa["id"]][i % len(areas[empresa["id"]])]
        estado = "preingreso" if p["grupo"] == "preingreso" else "activo"
        cuerpo = {
            "empresa_id": empresa["id"], "area_id": area["id"], "nombre": p["nombre"],
            "apellido": p["apellido"], "email_corporativo": _mail(p), "roles": [p["rol"]],
            "modalidad_trabajo": "presencial", "tipo_contrato": "efectivo",
            "fecha_ingreso": _f(p["dias"]), "legajo": p["legajo"], "estado": estado,
            "seniority": p["seniority"], "categoria": p["categoria"], "horas_contrato": 8,
        }
        eid = cli.obtener_o_crear(
            "empleados", p["legajo"],
            crear=lambda c=cuerpo: cli.pedir("POST", "/api/empleados", json_body=c)["id"],
            buscar=lambda lg=p["legajo"], e=empresa["id"]: _buscar_empleado(cli, lg, e))
        if eid:
            creados[p["legajo"]] = dict(p, id=eid, empresa_id=empresa["id"])
            print(f"    {p['legajo']} {p['nombre']} {p['apellido']} · {estado} · {empresa['nombre']}")
    return creados


def _buscar_recategorizacion(cli, empleado_id: str, fecha: str, empresa: str) -> Optional[str]:
    """Clave natural compuesta: el par (empleado, fecha efectiva) no se repite en la semilla."""
    pagina = cli.get("/api/recategorizaciones",
                     params={"empleado_id": empleado_id, "page_size": 100}, empresa=empresa)
    for r in pagina.get("items", []):
        if str(r.get("fecha_efectiva")) == fecha:
            return str(r["id"])
    return None


def sembrar_recategorizaciones(cli, personas: Dict[str, dict]) -> None:
    """Las 5 recategorizaciones. Van sobre los colaboradores SEMBRADOS — ver `_semilla_padron`.

    Se cargan de la más VIEJA a la más nueva a propósito: cada una calcula sus `*_anterior`
    leyendo la previa (`_recategorizacion_anteriores`), así que cargarlas al revés produciría
    una cadena correcta pero un log de auditoría que cuenta la carrera al revés.
    """
    print("→ recategorizaciones (5, dos sobre la misma persona)")
    for r in sorted(RECATEGORIZACIONES, key=lambda x: x["dias"]):
        persona = personas.get(r["legajo"])
        if not persona:
            continue
        exigir_sembrado(cli, persona, "recategorizar")   # pisa rol/seniority/categoría
        fecha = _f(r["dias"])
        cuerpo = {"empleado_id": persona["id"], "fecha_efectiva": fecha, "motivo": r["motivo"],
                  "rol_nuevo": r["rol"], "seniority_nueva": r["seniority"],
                  "categoria_nueva": r["categoria"], "impacto_salarial": r["impacto"]}
        cli.obtener_o_crear(
            "recategorizaciones", f"{r['legajo']}@{fecha}",
            crear=lambda c=cuerpo, e=persona["empresa_id"]: str(cli.pedir(
                "POST", "/api/recategorizaciones", json_body=c, empresa=e)["id"]),
            buscar=lambda i=persona["id"], f=fecha, e=persona["empresa_id"]:
                _buscar_recategorizacion(cli, i, f, e))
        print(f"    {r['legajo']} · {fecha} · {r['motivo'][:48]}")


def _buscar_instancia(cli, empleado_id: str, empresa: str) -> Optional[str]:
    """El listado de offboarding no acepta filtro por empleado: se busca en la página completa.

    Es también la clave natural del módulo — el backend impide dos instancias abiertas para la
    misma persona (`OFFBOARDING_ALREADY_ACTIVE`), así que una por colaborador es el invariante.
    """
    for o in (cli.get("/api/offboarding", params={"page_size": 200}, empresa=empresa) or []):
        if str(o.get("empleado_id")) == empleado_id:
            return str(o["id"])
    return None


def sembrar_offboarding(cli, personas: Dict[str, dict]) -> None:
    """5 instancias: 3 se efectivizan (las bajas) y 2 quedan abiertas para que /offboarding
    tenga proceso en curso que mostrar."""
    print("→ offboarding (3 bajas efectivizadas + 2 procesos abiertos)")
    for p in PERSONAS:
        if p["grupo"] not in ("baja", "offboarding"):
            continue
        persona = personas.get(p["legajo"])
        if not persona:
            continue
        exigir_sembrado(cli, persona, "abrir el offboarding")   # la baja escribe en el legajo
        ultimo = _f(p["egreso_dias"]) if p["grupo"] == "baja" else _f(p["ultimo_dia"])
        cuerpo = {"empleado_id": persona["id"], "motivo": p["motivo"],
                  "fecha_ultimo_dia": ultimo,
                  "descripcion_motivo": f"Registrado para la prueba de recorrido ({p['motivo']})."}
        iid = cli.obtener_o_crear(
            "offboarding", p["legajo"],
            crear=lambda c=cuerpo, e=persona["empresa_id"]: str(cli.pedir(
                "POST", "/api/offboarding", json_body=c, empresa=e)["id"]),
            buscar=lambda i=persona["id"], e=persona["empresa_id"]: _buscar_instancia(cli, i, e))
        # 🔴 EL `print` INFORMA LO QUE PASÓ, NO LO QUE SE PENSABA HACER. La primera versión
        # imprimía "baja efectivizada <fecha>" incondicionalmente, así que el 23/8/2026 —cuando
        # `POST /api/offboarding` devolvió 500 en las cinco— la salida afirmó tres bajas que
        # nunca ocurrieron, arriba del renglón de error que decía lo contrario. En un script
        # cuya salida ES el reporte, eso no es un detalle cosmético: es el reporte mintiendo.
        efectivizada = False
        if iid and p["grupo"] == "baja":
            efectivizada = cli.hito(
                "offboarding_efectivizado", p["legajo"],
                lambda i=iid, f=_f(p["egreso_dias"]), e=persona["empresa_id"]: cli.pedir(
                    "POST", f"/api/offboarding/{i}/efectivizar",
                    json_body={"fecha_egreso": f}, empresa=e))
        if not iid:
            estado = "SIN INSTANCIA (falló el alta)"
        elif p["grupo"] != "baja":
            estado = "en curso"
        else:
            estado = (f"baja efectivizada {_f(p['egreso_dias'])}" if efectivizada
                      else "instancia creada, SIN efectivizar (falló la baja)")
        print(f"    {p['legajo']} · {p['motivo']} · {estado}")

