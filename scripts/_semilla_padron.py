"""
EL PADRÓN INVENTADO de la semilla de smoke: los 9 colaboradores nuevos y sus recategorizaciones.
Datos puros, sin I/O. Los catálogos (perfiles, agenda, formación, objetivos, vacantes) viven en
`_semilla_catalogo.py`: el corte es gente por un lado y catálogos por el otro, no una división
por líneas — los consumen fases distintas del sembrador.

🔴 ESTE ARCHIVO ES TAMBIÉN EL ÍNDICE DE LO QUE HAY QUE BORRAR. `limpiar_semilla.py` reconstruye
la lista de filas sembradas a partir de estas constantes cuando el manifiesto no está: los
nombres son la CLAVE NATURAL de cada fila. Cambiar un nombre después de sembrar deja esa fila
huérfana del limpiador — si hay que cambiarlo, se limpia primero y se siembra de nuevo.

🔴 POR QUÉ NOMBRES ARGENTINOS VEROSÍMILES Y NO "Test 1". El recorrido con Capital Humano se hace
sobre estos datos: una pantalla llena de "Prueba 2" no se puede leer como el sistema real, y lo
que se mira en ese recorrido es justamente si la pantalla se entiende. Ninguno de estos nombres
existe entre los 31 colaboradores reales.

⚠️ LA MARCA DE AGUA ESTÁ EN EL LEGAJO Y EN EL MAIL, no en el nombre: `SMK-xx` y el dominio
`@semilla.hrkarstec.site`. Son los dos campos donde un marcador no molesta a quien lee la
pantalla, y los dos tienen unicidad en la base — o sea que una segunda corrida choca 409 en vez
de duplicar. El nombre queda limpio a propósito.
"""
MARCA = "SMK"
DOMINIO = "semilla.hrkarstec.site"

# ── Colaboradores nuevos ──────────────────────────────────────────────────────
# `dias` = fecha_ingreso relativa a hoy (negativo = pasado). `grupo` decide qué fase lo usa.
PERSONAS = [
    # 4 preingresos. La ventana del panel "Requiere tu atención" es de 7 días y NO tiene piso,
    # así que el de -6 días (el que debía entrar y nadie activó) aparece igual. El de +20 solo
    # entra en el KPI de 30 días. Ver `services/_dashboard_atencion_calculadas.py`.
    dict(grupo="preingreso", legajo="SMK-01", nombre="Bruno", apellido="Vitale", dias=3,
         seniority="semi_senior", categoria="C3", rol="Analista de Sistemas"),
    dict(grupo="preingreso", legajo="SMK-02", nombre="Malena", apellido="Iriarte", dias=20,
         seniority="junior", categoria="C2", rol="Asistente de Administración"),
    dict(grupo="preingreso", legajo="SMK-03", nombre="Tobías", apellido="Quiroga", dias=0,
         seniority="senior", categoria="C4", rol="Coordinador Comercial"),
    dict(grupo="preingreso", legajo="SMK-04", nombre="Rocío", apellido="Bevilacqua", dias=-6,
         seniority="junior", categoria="C1", rol="Analista de Calidad"),
    # 3 bajas. Ingresan hace años para que `fecha_egreso >= fecha_ingreso` se cumpla con holgura
    # (lo valida `_offboarding_efectivizar`). `egreso_dias` lo consume la fase de offboarding:
    # -61 y -305 caen dentro de los 12 meses de la rotación y -396 queda afuera, así que el KPI
    # tiene que contar DOS y no tres.
    dict(grupo="baja", legajo="SMK-05", nombre="Gastón", apellido="Peralta", dias=-1580,
         seniority="senior", categoria="C4", rol="Jefe de Operaciones",
         motivo="renuncia", egreso_dias=-61),
    dict(grupo="baja", legajo="SMK-06", nombre="Ludmila", apellido="Sarquís", dias=-1150,
         seniority="semi_senior", categoria="C3", rol="Analista de Compras",
         motivo="despido", egreso_dias=-305),
    dict(grupo="baja", legajo="SMK-07", nombre="Emiliano", apellido="Roldán", dias=-2100,
         seniority="senior", categoria="C5", rol="Responsable de Mantenimiento",
         motivo="fin_contrato", egreso_dias=-396),
    # 2 offboarding abiertos: se crea la instancia y NO se efectiviza. Siguen activos.
    dict(grupo="offboarding", legajo="SMK-08", nombre="Carla", apellido="Zabaleta", dias=-980,
         seniority="senior", categoria="C4", rol="Especialista en Marketing",
         motivo="acuerdo_mutuo", ultimo_dia=25),
    dict(grupo="offboarding", legajo="SMK-09", nombre="Nahuel", apellido="Otamendi", dias=-3200,
         seniority="lider", categoria="C6", rol="Supervisor de Producción",
         motivo="jubilacion", ultimo_dia=45),
]

# ── Recategorizaciones ────────────────────────────────────────────────────────
# `legajo` apunta a PERSONAS. 🔴 VAN SOBRE COLABORADORES SEMBRADOS Y NO SOBRE LOS 31 REALES, y la
# razón es que crear una recategorización PISA al colaborador (rol/seniority/categoría — ver
# `_recategorizaciones_write.aplicar_al_empleado`) y el módulo NO TIENE DELETE: sobre alguien
# real sería una mutación que la limpieza no puede deshacer sin inventarle valores anteriores.
# Las dos de SMK-05 son la misma persona en dos fechas: la más nueva queda "Vigente".
RECATEGORIZACIONES = [
    dict(legajo="SMK-05", dias=-540, rol="Coordinador de Operaciones", seniority="semi_senior",
         categoria="C3", impacto=None, motivo="Ascenso por concurso interno"),
    dict(legajo="SMK-05", dias=-190, rol=None, seniority="senior", categoria=None,
         impacto=None, motivo="Cambio de seniority por evaluación anual"),
    dict(legajo="SMK-08", dias=-270, rol="Especialista Senior en Marketing", seniority=None,
         categoria="C5", impacto=310000,
         motivo="Recategorización por convenio y ampliación de tareas"),
    dict(legajo="SMK-09", dias=-95, rol=None, seniority=None, categoria="C7",
         impacto=185000, motivo="Pase a categoría 7 por antigüedad"),
    dict(legajo="SMK-06", dias=-430, rol="Analista Senior de Compras", seniority="senior",
         categoria="C4", impacto=240000,
         motivo="Promoción tras cubrir la jefatura interinamente"),
]

