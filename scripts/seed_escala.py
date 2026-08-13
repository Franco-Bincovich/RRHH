#!/usr/bin/env python3
"""Generador de datos de ESCALA para el diagnostico de Fase 2.5 (10 empresas / ~1000 colaboradores).

QUE HACE
    Emite por stdout un script SQL que puebla la base LOCAL de diagnostico. No se conecta a
    ninguna base por su cuenta: escribe SQL y nada mas. El unico que escribe es el psql al que
    se lo canalices, y sos vos quien elige a que base apunta.

        $env:PGPASSWORD = "rrhh2026"
        python scripts/seed_escala.py | psql -h localhost -p 5432 -U postgres -d "HR Karstec" -v ON_ERROR_STOP=1

    🔴 NUNCA apuntarlo a Supabase. La base de produccion tiene los 31 colaboradores REALES y
    este script arranca con TRUNCATE. Que el script no sepa conectarse solo es la unica
    proteccion que puede darse a si mismo; el resto lo pone la linea de comando.

REPRODUCIBLE
    `random.seed(SEMILLA)` y los UUID salen de esa misma secuencia (uuid.UUID(int=...)), asi
    que dos corridas producen los MISMOS ids. Sirve para comparar mediciones entre sesiones:
    si el plan de una query cambia, cambio el codigo o el indice, no los datos.

POR QUE EL REPARTO ES DESPAREJO
    400 / 175 / 130 / 95 / 70 / 45 / 30 / 25 / 20 / 15. Un reparto parejo de 100 por empresa
    esconde los dos problemas que esta sesion busca: el listado que aguanta 100 y muere en 400,
    y el modo consolidado, que con 10 empresas parejas parece lineal.

FORMATO
    COPY ... FROM STDIN en formato texto, que es varios ordenes de magnitud mas rapido que
    INSERT fila por fila. Los triggers (`fn_misma_empresa`, `set_updated_at`) SI se disparan
    con COPY: los datos que entran por aca pasan por las mismas validaciones que los de la app.
"""
import random
import sys
import uuid
from datetime import date, timedelta

SEMILLA = 20260813
random.seed(SEMILLA)

# ── Reparto desparejo, a proposito. Suma 1005. ────────────────────────────────
REPARTO = [400, 175, 130, 95, 70, 45, 30, 25, 20, 15]

EMPRESAS = [
    "Karstec Servicios", "DOSUBA", "Nexia Logistica", "Altamira Salud",
    "Grupo Rioja", "Sudeste Tecnologia", "Panamericana Retail", "Delta Agro",
    "Cordillera Energia", "Vientos del Sur",
]

NOMBRES = ["Sofia", "Mateo", "Valentina", "Santiago", "Camila", "Benjamin", "Martina", "Lucas",
           "Emilia", "Joaquin", "Isabella", "Tomas", "Catalina", "Bautista", "Lucia", "Thiago",
           "Renata", "Facundo", "Delfina", "Ignacio", "Julieta", "Bruno", "Agustina", "Nicolas",
           "Paula", "Federico", "Carolina", "Gonzalo", "Micaela", "Rodrigo"]
APELLIDOS = ["Gomez", "Rodriguez", "Fernandez", "Lopez", "Martinez", "Perez", "Garcia", "Sanchez",
             "Romero", "Sosa", "Torres", "Alvarez", "Ruiz", "Ramirez", "Flores", "Benitez",
             "Acosta", "Medina", "Herrera", "Aguirre", "Pereyra", "Gimenez", "Molina", "Silva",
             "Castro", "Ortiz", "Nunez", "Rojas", "Vega", "Cabrera"]

AREAS_BASE = ["Sistemas", "Administracion", "Comercial", "Operaciones", "Recursos Humanos",
              "Finanzas", "Legales", "Marketing", "Logistica", "Calidad", "Produccion",
              "Compras", "Mantenimiento", "Atencion al Cliente", "Seguridad e Higiene",
              "Planeamiento", "Auditoria Interna", "Innovacion"]

CARGOS = ["Analista", "Analista Senior", "Coordinador", "Jefe", "Gerente", "Asistente",
          "Responsable", "Especialista", "Tecnico", "Supervisor"]
SENIORITY = ["junior", "semi_senior", "senior", "lider", None]
MODALIDAD = ["presencial", "remoto", "hibrido"]
TIPO_CONTRATO = ["efectivo", "plazo_fijo", "contratado", "pasantia"]
TURNOS = ["manana", "tarde", "noche", None]
# 🔴 Los nombres van con sus acentos y en la forma OFICIAL. `EmpleadoResponse.domicilio_provincia`
# es un `Literal` con las 24 jurisdicciones del IGN (`backend/schemas/_provincias.py`): un
# "Entre Rios" sin tilde entra a la base sin problema —la columna es text y no hay CHECK— pero
# revienta al SERIALIZAR la respuesta, y tumba el listado entero de empleados con un 500.
PROVINCIAS = ["Buenos Aires", "Ciudad Autónoma de Buenos Aires", "Córdoba", "Santa Fe",
              "Mendoza", "Tucumán", "Salta", "Entre Ríos", "Neuquén", "Chubut"]
SEXOS = ["F", "M", "X"]

# Los 5 tipos base de `backend/db/seed.sql`. 🔴 Los UUID van FIJOS y son los de produccion
# (`_carga_licencia.py` tiene uno hardcodeado). Se repiten aca porque el TRUNCATE ... CASCADE
# de mas abajo se los lleva: `tipos_ausencia.empresa_id` referencia a `empresas`, asi que
# truncar empresas arrastra el catalogo base. Reponerlos es parte de dejar la base usable.
TIPOS_AUSENCIA = [
    ("9ae8a905-c0be-403b-8206-b1f4039ec465", "Enfermedad", True, True, True),
    ("9f3b7c2a-1d4e-4a6b-8c5d-0e1f2a3b4c5d", "Licencia", True, True, True),
    ("ec28dbd2-ffa1-47c8-b116-2e3aff840d3b", "Personal", True, True, True),
    ("e67f449a-6b53-479f-afad-e902cfa3d523", "Otro", True, True, True),
    ("da054f82-340d-4ffb-a481-ac7712a5dbb3", "Injustificada", False, False, True),
]

CLIENTES = ["Aguas del Norte", "Banco Litoral", "Cooperativa Andina", "Editorial Pampa",
            "Farmacias Unidas", "Grupo Sanitario", "Hospital Central", "Industrias Maipu",
            "Jockey Club", "Kiosco Digital", "Laboratorios Cuyo", "Municipalidad de Salta",
            "Naviera Atlantica", "Obra Social Norte", "Petroquimica Sur"]

CAPACITACIONES = ["Seguridad e Higiene", "Excel Avanzado", "Liderazgo de Equipos",
                  "Prevencion de Fraude", "Onboarding Corporativo", "Ingles Tecnico",
                  "Primeros Auxilios", "Proteccion de Datos"]
ITEMS_TIPO = ["notebook", "monitor", "celular", "silla", "auriculares", "teclado", "token"]

HOY = date(2026, 8, 13)


def u() -> str:
    """Devuelve un UUID derivado de la secuencia sembrada (reproducible entre corridas)."""
    return str(uuid.UUID(int=random.getrandbits(128), version=4))


def esc(v) -> str:
    """Escapa un valor para el formato texto de COPY (\\N para NULL)."""
    if v is None:
        return r"\N"
    if isinstance(v, bool):
        return "t" if v else "f"
    s = str(v)
    return (s.replace("\\", "\\\\").replace("\t", "\\t")
             .replace("\n", "\\n").replace("\r", "\\r"))


OUT = []


def w(linea: str = "") -> None:
    """Acumula una linea del script SQL de salida."""
    OUT.append(linea)


def copia(tabla: str, cols: list, filas: list) -> None:
    """Emite un bloque COPY ... FROM STDIN con las filas dadas."""
    if not filas:
        return
    w(f"COPY public.{tabla} ({', '.join(cols)}) FROM STDIN;")
    for f in filas:
        w("\t".join(esc(x) for x in f))
    w("\\.")
    w()


def dia(desde: date, hasta: date) -> date:
    """Elige una fecha uniforme en [desde, hasta]."""
    return desde + timedelta(days=random.randint(0, (hasta - desde).days))


# ══════════════════════════════════════════════════════════════════════════════
w("-- Generado por scripts/seed_escala.py — datos de ESCALA, base local de diagnostico.")
w(f"-- Semilla {SEMILLA}. Reproducible: dos corridas dan los mismos ids.")
w("SET client_encoding = 'UTF8';")
w("SET session_replication_role = 'origin';")
w("BEGIN;")
w()
w("-- Limpieza: el script es re-corrible. Solo toca las tablas que el mismo puebla.")
w("""TRUNCATE TABLE
    auditoria, adjuntos, horas_proyecto, presupuesto_areas, costos_nomina,
    inventario_asignaciones, inventario_items, empleado_capacitacion, capacitaciones,
    objetivos, candidatos, vacantes, vacaciones_pendientes, solicitudes_ausencia,
    solicitudes_vacaciones, proyecto_asignaciones, proyectos, clientes,
    empleados, areas, users, empresas
  RESTART IDENTITY CASCADE;""")
w()

# ── Reponer los catalogos base que el CASCADE se lleva ────────────────────────
# `tipos_ausencia`, `parametros_empresa` y `reglas_vacaciones_escala` cuelgan de `empresas`
# por su columna `empresa_id` (que en la fila GLOBAL va NULL), asi que truncar `empresas`
# CASCADE las vacia. Sin ellas el sistema arranca roto: sin tipos no se puede crear ninguna
# ausencia (FK NOT NULL) y sin la fila global de parametros el reporte de ausentismo tira 500.
# Los valores son los de `backend/db/seed.sql`, que es su fuente.
filas = [[i, n, b, a, c, None, None] for i, n, b, a, c in TIPOS_AUSENCIA]
copia("tipos_ausencia", ["id", "nombre", "es_base", "activo", "cuenta_ausentismo",
                         "empresa_id", "padre_id"], filas)
w("INSERT INTO public.parametros_empresa (empresa_id, base_dias_habiles, corte_antiguedad_mes,")
w("  periodo_vacacional_desde_mes, periodo_vacacional_hasta_mes, primer_anio_mes_corte,")
w("  primer_anio_dias, vencimiento_anios) VALUES (NULL, 22, 10, 10, 4, 7, 5, 4);")
w("INSERT INTO public.reglas_vacaciones_escala (empresa_id, antiguedad_anios, dias)")
w("  VALUES (NULL, 0, 14), (NULL, 5, 21), (NULL, 15, 28);")
w()

# ── users ─────────────────────────────────────────────────────────────────────
users = []
filas = []
for i in range(14):
    uid = u()
    rol = "admin_rrhh" if i < 4 else ("gerencia_lectura" if i < 8 else "mandos_medios")
    users.append(uid)
    filas.append([uid, f"usuario{i}@hrkarstec.site", NOMBRES[i], APELLIDOS[i], rol, True])
copia("users", ["id", "email", "nombre", "apellido", "rol", "activo"], filas)

# ── empresas ──────────────────────────────────────────────────────────────────
empresas = []
filas = []
for i, nom in enumerate(EMPRESAS):
    eid = u()
    empresas.append(eid)
    filas.append([eid, nom, True, f"{nom} S.A.", f"30-{70000000 + i * 111}-{i % 10}"])
copia("empresas", ["id", "nombre", "activa", "razon_social", "cuit"], filas)

# ── parametros_empresa: una fila por empresa (la global del seed ya existe) ────
filas = [[u(), e, random.choice([20, 21, 22, 23])] for e in empresas]
copia("parametros_empresa", ["id", "empresa_id", "base_dias_habiles"], filas)

# ── areas ─────────────────────────────────────────────────────────────────────
# Proporcionales a la dotacion: la empresa de 400 tiene 18 areas, la de 15 tiene 3.
areas_por_empresa = {}
filas = []
cod = 0
for idx, eid in enumerate(empresas):
    n = max(3, min(18, REPARTO[idx] // 25 + 2))
    lista = []
    for j in range(n):
        aid = u()
        lista.append(aid)
        cod += 1
        filas.append([aid, AREAS_BASE[j % len(AREAS_BASE)], f"A{cod:04d}", 1, True, eid])
    areas_por_empresa[eid] = lista
copia("areas", ["id", "nombre", "codigo", "nivel", "activo", "empresa_id"], filas)

# ── empleados ─────────────────────────────────────────────────────────────────
# El reparto DENTRO de la empresa tambien es desparejo: un area concentra ~30%.
empleados = []                 # (id, empresa_id, area_id, estado, fecha_ingreso)
emp_por_empresa = {e: [] for e in empresas}
filas = []
dni_seq = 20000000
legajo_seq = 0
mail_seq = 0
for idx, eid in enumerate(empresas):
    n = REPARTO[idx]
    areas = areas_por_empresa[eid]
    pesos = [3.0] + [1.0] * (len(areas) - 1)      # la primera area concentra
    for k in range(n):
        pid = u()
        area = random.choices(areas, weights=pesos)[0]
        ingreso = dia(date(2014, 1, 1), date(2026, 6, 30))
        r = random.random()
        if r < 0.88:
            estado, egreso, motivo = "activo", None, None
        elif r < 0.96:
            estado = "baja"
            egreso = dia(max(ingreso, date(2024, 1, 1)), HOY)
            motivo = random.choice(["renuncia", "despido", "fin_contrato", "jubilacion"])
        elif r < 0.99:
            estado, egreso, motivo = "licencia", None, None
        else:
            estado, egreso, motivo = "suspendido", None, None
        dni_seq += random.randint(3, 40)
        legajo_seq += 1
        mail_seq += 1
        nom, ape = random.choice(NOMBRES), random.choice(APELLIDOS)
        empleados.append((pid, eid, area, estado, ingreso))
        emp_por_empresa[eid].append(pid)
        filas.append([
            pid, f"L{legajo_seq:05d}", nom, ape,
            f"{nom.lower()}.{ape.lower()}{mail_seq}@hrkarstec.site",
            dia(date(1966, 1, 1), date(2004, 12, 31)),     # fecha_nacimiento
            ingreso, egreso, area, random.choice(CARGOS),
            random.choice(MODALIDAD), random.choice(TIPO_CONTRATO), estado,
            random.choice(["alto", "medio", "bajo"]), random.choice(["alto", "medio", "bajo"]),
            eid, str(dni_seq), random.choice([14, 14, 21, 28, 35]),
            "{" + random.choice(CARGOS) + "}",              # roles text[]
            random.choice(SEXOS), random.choice(PROVINCIAS),
            random.choice([f"Calle {random.randint(100, 9999)}"]),
            random.choice(TURNOS), random.choice([None, 6, 8, 8, 8, 4]),
            random.choice(SENIORITY), random.random() < 0.12, motivo,
        ])
copia("empleados", [
    "id", "legajo", "nombre", "apellido", "email_corporativo", "fecha_nacimiento",
    "fecha_ingreso", "fecha_egreso", "area_id", "cargo", "modalidad_trabajo",
    "tipo_contrato", "estado", "potencial", "desempeno", "empresa_id", "dni",
    "dias_vacaciones_asignados", "roles", "sexo", "domicilio_provincia", "domicilio_calle",
    "turno", "horas_contrato", "seniority", "es_lider", "motivo_baja",
], filas)

# manager_id en una segunda pasada: el jefe tiene que existir y ser de la MISMA empresa
# (lo exige trg_emp_empleados). Se resuelve por UPDATE, no dentro del COPY.
w("-- manager_id: segunda pasada. El superior es de la misma empresa (trg_emp_empleados).")
for eid in empresas:
    gente = emp_por_empresa[eid]
    if len(gente) < 4:
        continue
    jefes = gente[:max(1, len(gente) // 8)]
    for pid in gente:
        if pid in jefes or random.random() > 0.85:
            continue
        w(f"UPDATE empleados SET manager_id = '{random.choice(jefes)}' WHERE id = '{pid}';")
w()

# responsable de area: un empleado de la misma empresa (lo exige trg_emp_areas)
for eid in empresas:
    for aid in areas_por_empresa[eid]:
        if emp_por_empresa[eid] and random.random() < 0.7:
            w(f"UPDATE areas SET responsable_id = '{random.choice(emp_por_empresa[eid])}' "
              f"WHERE id = '{aid}';")
w()

# ── clientes (catalogo GLOBAL, sin empresa) ───────────────────────────────────
clientes = []
filas = []
for nom in CLIENTES:
    cid = u()
    clientes.append(cid)
    filas.append([cid, nom, random.random() < 0.85])
copia("clientes", ["id", "nombre", "activo"], filas)

# ── proyectos ─────────────────────────────────────────────────────────────────
proyectos = []                 # (id, empresa_id)
filas = []
for idx, eid in enumerate(empresas):
    n = max(2, REPARTO[idx] // 40)
    for j in range(n):
        pid = u()
        proyectos.append((pid, eid))
        ini = dia(date(2023, 1, 1), date(2026, 3, 1))
        filas.append([pid, eid, f"Proyecto {AREAS_BASE[j % len(AREAS_BASE)]} {j + 1}",
                      random.choices(["activo", "pausado", "cerrado", "cancelado"],
                                     weights=[6, 1, 2, 1])[0],
                      ini, ini + timedelta(days=random.randint(90, 900)),
                      random.randint(500, 90000) * 1000])
copia("proyectos", ["id", "empresa_id", "nombre", "estado", "fecha_inicio", "fecha_fin",
                    "presupuesto"], filas)

# ── proyecto_asignaciones (~1.4 por colaborador) ──────────────────────────────
asignaciones = []              # (id, proyecto_id, empleado_id, empresa_id)
filas = []
proy_por_empresa = {}
for pid, eid in proyectos:
    proy_por_empresa.setdefault(eid, []).append(pid)
vistos = set()
for pid, eid, aid, estado, ing in empleados:
    if eid not in proy_por_empresa:
        continue
    for _ in range(random.choices([0, 1, 2, 3], weights=[2, 5, 3, 1])[0]):
        proy = random.choice(proy_por_empresa[eid])
        if (proy, pid) in vistos:
            continue
        vistos.add((proy, pid))
        aid2 = u()
        asignaciones.append((aid2, proy, pid, eid))
        filas.append([aid2, proy, pid, eid, random.choice(CARGOS),
                      random.randint(2000, 30000), random.random() < 0.8])
copia("proyecto_asignaciones", ["id", "proyecto_id", "empleado_id", "empleado_empresa_id",
                                "rol", "valor_hora", "activo"], filas)

# ── solicitudes_vacaciones (~3000 en 3 anios) ─────────────────────────────────
filas = []
for _ in range(3000):
    pid, eid, aid, estado, ing = random.choice(empleados)
    desde = dia(date(2023, 9, 1), date(2026, 8, 1))
    dias = random.choice([1, 2, 3, 5, 7, 10, 14, 14, 21])
    filas.append([u(), eid, pid, desde, desde + timedelta(days=dias - 1), dias,
                  random.random() < 0.06,
                  random.choices(["vacaciones", "semana_free", "dia_free", "permiso_especial"],
                                 weights=[8, 1, 1, 1])[0],
                  desde.year, 0])
copia("solicitudes_vacaciones", ["id", "empresa_id", "empleado_id", "fecha_desde",
                                 "fecha_hasta", "dias", "cancelada", "tipo", "periodo",
                                 "dias_liquidados"], filas)

# ── solicitudes_ausencia (~2000) ──────────────────────────────────────────────
# `tipo_id` se referencia con los UUID FIJOS del seed base, no con un lookup: son literales
# de produccion y no cambian. "Injustificada" queda fuera del reparto porque esta `activo=false`.
TIPOS_ACTIVOS = [t[0] for t in TIPOS_AUSENCIA if t[3]]
filas = []
for _ in range(2000):
    pid, eid, aid, estado, ing = random.choice(empleados)
    desde = dia(date(2023, 9, 1), date(2026, 8, 1))
    dias = random.choices([1, 2, 3, 5, 10, 20], weights=[10, 6, 4, 3, 1, 1])[0]
    filas.append([u(), eid, pid, random.choice(TIPOS_ACTIVOS), desde,
                  desde + timedelta(days=dias - 1), dias, random.random() < 0.72,
                  random.choice(["Certificado medico", "Tramite personal", "Familiar", None])])
copia("solicitudes_ausencia", ["id", "empresa_id", "empleado_id", "tipo_id", "fecha_desde",
                               "fecha_hasta", "dias", "justificada", "motivo"], filas)

# ── vacaciones_pendientes ─────────────────────────────────────────────────────
filas = []
vistos = set()
for _ in range(900):
    pid, eid, aid, estado, ing = random.choice(empleados)
    per = random.choice([2023, 2024, 2025])
    if (pid, per) in vistos:
        continue
    vistos.add((pid, per))
    filas.append([u(), eid, pid, per, random.randint(1, 14), 0])
copia("vacaciones_pendientes", ["id", "empresa_id", "empleado_id", "periodo", "dias",
                                "dias_liquidados"], filas)

# ── vacantes (~200) + candidatos ──────────────────────────────────────────────
vacantes = []
filas = []
for i in range(200):
    eid = random.choices(empresas, weights=REPARTO)[0]
    vid = u()
    vacantes.append((vid, eid))
    ap = dia(date(2025, 1, 1), HOY)
    lo = random.randint(600, 3000) * 1000
    filas.append([vid, f"{random.choice(CARGOS)} de {random.choice(AREAS_BASE)}",
                  random.choice(areas_por_empresa[eid]),
                  random.choice(MODALIDAD), random.choice(TIPO_CONTRATO),
                  random.choice(["junior", "semi_senior", "senior", "lider", "manager"]),
                  lo, lo + random.randint(200, 2000) * 1000,
                  random.randint(1, 3),
                  random.choices(["nueva", "en_proceso", "con_candidatos", "cerrada"],
                                 weights=[2, 3, 3, 4])[0],
                  random.choice(["baja", "media", "alta", "urgente"]),
                  ap, random.choice([None, ap + timedelta(days=random.randint(20, 120))]),
                  random.choice(users), eid])
copia("vacantes", ["id", "titulo", "area_id", "modalidad", "tipo_contrato", "nivel",
                   "rango_salarial_min", "rango_salarial_max", "cantidad_puestos", "estado",
                   "prioridad", "fecha_apertura", "fecha_cierre", "responsable_id",
                   "empresa_id"], filas)

filas = []
for i in range(1000):
    vid, eid = random.choice(vacantes)
    nom, ape = random.choice(NOMBRES), random.choice(APELLIDOS)
    filas.append([u(), vid if random.random() < 0.9 else None, nom, ape,
                  f"{nom.lower()}.{ape.lower()}{i}@mail.com",
                  random.choice(["linkedin", "referido", "web", "consultora", "espontanea",
                                 "gmail"]),
                  random.choices(["postulado", "assessment", "entrevista_rrhh",
                                  "entrevista_tecnica", "oferta"],
                                 weights=[8, 3, 3, 2, 1])[0],
                  random.choices(["activo", "descartado", "contratado", "en_espera"],
                                 weights=[5, 5, 1, 2])[0],
                  random.choice([None, random.randint(1, 10)]),
                  dia(date(2025, 1, 1), HOY), eid,
                  random.choice([None, "relevante", "dudoso", "no_relevante"])])
copia("candidatos", ["id", "vacante_id", "nombre", "apellido", "email", "fuente", "etapa",
                     "estado", "puntuacion", "fecha_postulacion", "empresa_id",
                     "clasificacion_ia"], filas)

# ── objetivos (responsable_id -> users, por decision de producto) ──────────────
objetivos = []
filas = []
for i in range(300):
    eid = random.choice(empresas)
    oid = u()
    objetivos.append(oid)
    filas.append([oid, eid, random.choice(users), None,
                  f"Objetivo {i + 1}: {random.choice(AREAS_BASE)}",
                  random.choice(["baja", "media", "alta"]),
                  random.choices(["por_hacer", "haciendo", "terminado"],
                                 weights=[4, 3, 3])[0],
                  dia(date(2026, 1, 1), date(2026, 12, 31)),
                  random.choice(["", "mensual", "trimestral", "anual"])])
copia("objetivos", ["id", "empresa_id", "responsable_id", "parent_id", "titulo", "prioridad",
                    "estado", "fecha_entrega", "periodicidad"], filas)
# subobjetivos: ~120 colgados de un padre
filas = []
for i in range(120):
    padre = random.choice(objetivos)
    filas.append([u(), random.choice(empresas), random.choice(users), padre,
                  f"Subobjetivo {i + 1}", random.choice(["baja", "media", "alta"]),
                  random.choice(["por_hacer", "haciendo", "terminado"]),
                  dia(date(2026, 1, 1), date(2026, 12, 31)), ""])
w("-- subobjetivos: parent_id ya existente (el arbol se arma en 2 niveles)")
copia("objetivos", ["id", "empresa_id", "responsable_id", "parent_id", "titulo", "prioridad",
                    "estado", "fecha_entrega", "periodicidad"], filas)

# ── capacitaciones + asignaciones ─────────────────────────────────────────────
caps = []
filas = []
for eid in empresas:
    for nom in CAPACITACIONES[:random.randint(4, 8)]:
        cid = u()
        caps.append((cid, eid))
        filas.append([cid, eid, nom, random.choice(["tecnica", "blanda", "normativa"]),
                      random.randint(2, 40), random.random() < 0.4, True])
copia("capacitaciones", ["id", "empresa_id", "nombre", "categoria", "duracion_horas",
                         "obligatoria", "activo"], filas)

caps_por_empresa = {}
for cid, eid in caps:
    caps_por_empresa.setdefault(eid, []).append(cid)
filas = []
vistos = set()
for pid, eid, aid, estado, ing in empleados:
    for _ in range(random.choices([0, 1, 2, 3, 4], weights=[2, 4, 4, 2, 1])[0]):
        cid = random.choice(caps_por_empresa[eid])
        if (cid, pid) in vistos:
            continue
        vistos.add((cid, pid))
        est = random.choices(["pendiente", "en_curso", "completado"], weights=[3, 2, 5])[0]
        asig = dia(date(2024, 1, 1), HOY)
        filas.append([u(), eid, cid, pid, est, asig, asig + timedelta(days=90),
                      asig + timedelta(days=random.randint(5, 85)) if est == "completado"
                      else None])
copia("empleado_capacitacion", ["id", "empresa_id", "capacitacion_id", "empleado_id", "estado",
                                "fecha_asignacion", "fecha_limite", "fecha_completado"], filas)

# ── inventario ────────────────────────────────────────────────────────────────
items = []
filas = []
for idx, eid in enumerate(empresas):
    for j in range(max(5, int(REPARTO[idx] * 1.3))):
        iid = u()
        items.append((iid, eid))
        filas.append([iid, eid, f"{random.choice(ITEMS_TIPO).title()} {j + 1}",
                      random.choice(ITEMS_TIPO), f"SN{random.randint(10**7, 10**8)}",
                      random.choices(["disponible", "asignado", "en_reparacion", "baja"],
                                     weights=[3, 6, 1, 1])[0],
                      dia(date(2020, 1, 1), HOY), random.randint(50, 3000) * 1000])
copia("inventario_items", ["id", "empresa_id", "nombre", "tipo", "numero_serie", "estado",
                           "fecha_alta", "costo"], filas)

items_por_empresa = {}
for iid, eid in items:
    items_por_empresa.setdefault(eid, []).append(iid)
filas = []
usados = set()
for pid, eid, aid, estado, ing in empleados:
    for _ in range(random.choices([0, 1, 2], weights=[3, 5, 2])[0]):
        iid = random.choice(items_por_empresa[eid])
        if iid in usados:
            continue
        usados.add(iid)
        fa = dia(date(2022, 1, 1), HOY)
        dev = random.random() < 0.25
        filas.append([u(), eid, iid, pid, fa,
                      fa + timedelta(days=random.randint(30, 700)) if dev else None,
                      random.choice(["ok", "con_daño"]) if dev else None])
copia("inventario_asignaciones", ["id", "empresa_id", "item_id", "empleado_id",
                                  "fecha_asignacion", "fecha_devolucion",
                                  "estado_devolucion"], filas)

# ── costos_nomina: 24 meses por colaborador (~24k filas) ──────────────────────
# Es la tabla que sostiene masa salarial, historial salarial y el reporte anual.
filas = []
periodos = []
a, m = 2024, 9
for _ in range(24):
    periodos.append((a, m))
    m += 1
    if m > 12:
        a, m = a + 1, 1
for pid, eid, aid, estado, ing in empleados:
    base = random.randint(700, 6000) * 1000
    for k, (anio, mes) in enumerate(periodos):
        if date(anio, mes, 28) < ing:
            continue
        bruto = int(base * (1 + 0.028 * k))
        filas.append([u(), pid, anio, mes, bruto, int(bruto * 0.28),
                      int(bruto * random.choice([0, 0, 0, 0.1, 0.25])), 0, eid,
                      random.choice(users)])
copia("costos_nomina", ["id", "empleado_id", "anio", "mes", "salario_bruto", "cargas_sociales",
                        "bonos", "otros_costos", "empresa_id", "created_by"], filas)

# ── presupuesto_areas ─────────────────────────────────────────────────────────
filas = []
for eid in empresas:
    for aid in areas_por_empresa[eid]:
        for mes in range(1, 13):
            for tipo in ("nomina", "total"):
                pres = random.randint(2000, 60000) * 1000
                filas.append([u(), aid, 2026, mes, tipo, pres,
                              int(pres * random.uniform(0.6, 1.15)), eid,
                              random.choice(users)])
copia("presupuesto_areas", ["id", "area_id", "anio", "mes", "tipo_costo",
                            "monto_presupuestado", "monto_ejecutado", "empresa_id",
                            "created_by"], filas)

# ── horas_proyecto ────────────────────────────────────────────────────────────
filas = []
for _ in range(6000):
    aid2, proy, pid, eid = random.choice(asignaciones)
    filas.append([u(), aid2, proy, eid, eid, dia(date(2025, 1, 1), HOY),
                  random.choice([2, 4, 6, 8, 8, 8]), random.randint(2000, 30000),
                  random.choice(clientes), pid,
                  f"Proyecto {random.randint(1, 20)}", f"Tarea {random.randint(1, 50)}",
                  random.choice(users)])
copia("horas_proyecto", ["id", "asignacion_id", "proyecto_id", "empresa_id",
                         "empleado_empresa_id", "fecha", "horas", "valor_hora_snapshot",
                         "cliente_id", "empleado_id", "proyecto_texto", "tarea_texto",
                         "cargado_por"], filas)

# ── adjuntos ──────────────────────────────────────────────────────────────────
filas = []
for i in range(900):
    pid, eid, aid, estado, ing = random.choice(empleados)
    filas.append([u(), "empleado", pid, eid, "documentos", f"empleado/{pid}/doc{i}.pdf",
                  f"documento_{i}.pdf", "application/pdf", random.randint(20000, 4000000),
                  random.choice(["contrato", "dni", "titulo", "certificado"]), "activo",
                  random.choice(users),
                  random.choice([None, dia(HOY, date(2027, 6, 30))])])
copia("adjuntos", ["id", "entidad", "entidad_id", "empresa_id", "bucket", "storage_path",
                   "nombre_archivo", "mime_type", "tamano_bytes", "categoria", "estado",
                   "subido_por", "fecha_vencimiento"], filas)

# ── auditoria: ~20000 eventos. Es la tabla que mas crece. ─────────────────────
ENTIDADES = [("empleado", ["alta_empleado", "edicion_empleado", "baja_empleado"]),
             ("vacacion", ["alta_vacacion", "cancelacion_vacacion"]),
             ("ausencia", ["alta_ausencia", "edicion_ausencia"]),
             ("nomina", ["carga_nomina", "importacion_costos"]),
             ("vacante", ["alta_vacante", "cierre_vacante"]),
             ("candidato", ["alta_candidato", "baja_candidato"]),
             ("objetivo", ["alta_objetivo", "edicion_objetivo"]),
             ("inventario", ["asignacion_item", "devolucion_item"])]
filas = []
for _ in range(20000):
    ent, eventos = random.choice(ENTIDADES)
    pid, eid, aid, estado, ing = random.choice(empleados)
    acc = random.choices(["INSERT", "UPDATE", "DELETE"], weights=[4, 5, 1])[0]
    ts = dia(date(2025, 1, 1), HOY)
    filas.append([u(), ent, pid, acc,
                  r'{"campo": "valor_anterior"}' if acc != "INSERT" else None,
                  r'{"campo": "valor_nuevo"}' if acc != "DELETE" else None,
                  random.choice(users), f"186.{random.randint(0,255)}."
                  f"{random.randint(0,255)}.{random.randint(1,254)}",
                  "Mozilla/5.0", f"{ts} {random.randint(8,19)}:{random.randint(0,59):02d}:00-03",
                  eid, ent, random.choice(eventos)])
copia("auditoria", ["id", "tabla", "registro_id", "accion", "datos_anteriores", "datos_nuevos",
                    "usuario_id", "ip", "user_agent", "created_at", "empresa_id", "entidad",
                    "evento"], filas)

w("COMMIT;")
w("ANALYZE;")
w()
w("""SELECT 'empresas' t, count(*) FROM empresas
UNION ALL SELECT 'empleados', count(*) FROM empleados
UNION ALL SELECT 'areas', count(*) FROM areas
UNION ALL SELECT 'proyectos', count(*) FROM proyectos
UNION ALL SELECT 'proyecto_asignaciones', count(*) FROM proyecto_asignaciones
UNION ALL SELECT 'solicitudes_vacaciones', count(*) FROM solicitudes_vacaciones
UNION ALL SELECT 'solicitudes_ausencia', count(*) FROM solicitudes_ausencia
UNION ALL SELECT 'vacantes', count(*) FROM vacantes
UNION ALL SELECT 'candidatos', count(*) FROM candidatos
UNION ALL SELECT 'objetivos', count(*) FROM objetivos
UNION ALL SELECT 'capacitaciones', count(*) FROM capacitaciones
UNION ALL SELECT 'empleado_capacitacion', count(*) FROM empleado_capacitacion
UNION ALL SELECT 'inventario_items', count(*) FROM inventario_items
UNION ALL SELECT 'inventario_asignaciones', count(*) FROM inventario_asignaciones
UNION ALL SELECT 'costos_nomina', count(*) FROM costos_nomina
UNION ALL SELECT 'presupuesto_areas', count(*) FROM presupuesto_areas
UNION ALL SELECT 'horas_proyecto', count(*) FROM horas_proyecto
UNION ALL SELECT 'adjuntos', count(*) FROM adjuntos
UNION ALL SELECT 'auditoria', count(*) FROM auditoria
ORDER BY 1;""")

# UTF-8 explicito: en Windows stdout sale en cp1252 por default y la 'ñ' de 'con_daño'
# —que exige el CHECK de inventario_asignaciones— llegaria como 0xF1 y psql la rechazaria
# con "secuencia de bytes no valida para codificacion UTF8".
sys.stdout.reconfigure(encoding="utf-8", newline="\n")
sys.stdout.write("\n".join(OUT) + "\n")
