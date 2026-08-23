"""
LOS CATÁLOGOS INVENTADOS de la semilla de smoke: perfiles de puesto, agenda, formación,
objetivos, vacantes y candidatos. Datos puros, sin I/O. Hermano de `_semilla_padron.py`, que
tiene a las personas; el corte es ése —gente por un lado, catálogos por el otro— y no una
división por líneas: los dos archivos los consumen fases distintas del sembrador.

🔴 IGUAL QUE SU HERMANO, ESTE ARCHIVO ES EL ÍNDICE DE LO QUE HAY QUE BORRAR. `limpiar_semilla.py`
reconstruye la lista de filas sembradas a partir de estos nombres y títulos cuando el manifiesto
no está: son la CLAVE NATURAL de cada fila. Cambiar un título después de sembrar deja esa fila
huérfana del limpiador — si hay que cambiarlo, se limpia primero y se siembra de nuevo.
"""
# ── Perfiles de puesto ────────────────────────────────────────────────────────
# Los 12 campos llenos en los 6. El primero es de texto CORTO y el segundo de texto LARGO a
# propósito: son los dos extremos que la tarjeta del listado tiene que poder mostrar (uno que
# entra entero y uno que corta). `baja=True` en el último: se le pega el DELETE —que en este
# módulo es baja LÓGICA— para ver el chip de inactivo y el botón Reactivar.
_LARGO = (
    "Liderar el ciclo completo de la operación logística de la sucursal, coordinando el equipo "
    "de depósito, la flota propia y los proveedores de última milla, con foco en el cumplimiento "
    "de los plazos comprometidos con el cliente interno y en la trazabilidad de cada envío desde "
    "que se genera la orden hasta que se confirma la entrega. Incluye la gestión del presupuesto "
    "del sector, la negociación anual con transportistas y la mejora continua de los indicadores "
    "de servicio, calidad y costo por unidad despachada."
)
PERFILES = [
    dict(nombre="Analista de Sistemas",
         descripcion="Soporte y desarrollo de las aplicaciones internas.",
         funciones="Relevar requerimientos, desarrollar y documentar.",
         experiencia="2 años en posiciones similares.",
         formacion="Estudiante avanzado de Sistemas.",
         conocimientos_tecnicos="SQL, Python, Git.",
         requisitos="Disponibilidad full time.",
         ofrecemos="Obra social y capacitación continua.",
         modalidad="hibrido", tipo_contrato="efectivo", nivel="semi_senior", jornada="Full time"),
    dict(nombre="Jefe de Logística", descripcion=_LARGO,
         funciones="Coordinar depósito, flota y última milla; gestionar el presupuesto del sector.",
         experiencia="5 años conduciendo equipos de logística o distribución.",
         formacion="Graduado en Logística, Ingeniería Industrial o afines.",
         conocimientos_tecnicos="WMS, TMS, Excel avanzado, tableros de control.",
         requisitos="Movilidad propia y disponibilidad para viajar a las sucursales del interior.",
         ofrecemos="Vehículo de la empresa, bono anual por objetivos y plan de carrera.",
         modalidad="presencial", tipo_contrato="efectivo", nivel="manager", jornada="Full time"),
    dict(nombre="Asistente de Administración",
         descripcion="Apoyo administrativo al área de Finanzas.",
         funciones="Carga de comprobantes, conciliaciones y archivo.",
         experiencia="1 año en tareas administrativas.", formacion="Secundario completo.",
         conocimientos_tecnicos="Excel, Tango.", requisitos="Residir en la zona.",
         ofrecemos="Horario flexible.",
         modalidad="presencial", tipo_contrato="plazo_fijo", nivel="junior",
         jornada="Part time 6 hs"),
    dict(nombre="Responsable de Calidad",
         descripcion="Sostiene el sistema de gestión de calidad de la planta.",
         funciones="Auditorías internas, no conformidades y acciones correctivas.",
         experiencia="4 años en calidad de procesos industriales.",
         formacion="Ingeniería en Alimentos o afín.",
         conocimientos_tecnicos="ISO 9001, HACCP, estadística aplicada.",
         requisitos="Experiencia comprobable en auditorías externas.",
         ofrecemos="Cobertura médica familiar.",
         modalidad="presencial", tipo_contrato="efectivo", nivel="senior", jornada="Full time"),
    dict(nombre="Ejecutivo Comercial",
         descripcion="Desarrollo de cartera de clientes corporativos.",
         funciones="Prospección, visitas y cierre de acuerdos anuales.",
         experiencia="3 años en venta consultiva B2B.",
         formacion="Estudios universitarios en curso.",
         conocimientos_tecnicos="CRM, Google Workspace.",
         requisitos="Carnet de conducir vigente.", ofrecemos="Comisiones sin techo.",
         modalidad="hibrido", tipo_contrato="contratado", nivel="semi_senior",
         jornada="Full time"),
    dict(nombre="Pasante de Recursos Humanos",
         descripcion="Acompaña al equipo de Capital Humano en tareas de legajo.",
         funciones="Armado de legajos, carga de novedades y apoyo en búsquedas.",
         experiencia="Sin experiencia previa requerida.",
         formacion="Estudiante de RRHH o Psicología.",
         conocimientos_tecnicos="Paquete Office.",
         requisitos="Convenio de pasantía vigente con la facultad.",
         ofrecemos="Tutoría y posibilidad de efectivización.",
         modalidad="presencial", tipo_contrato="pasantia", nivel="junior",
         jornada="Part time 4 hs", baja=True),
]

# ── Agenda ────────────────────────────────────────────────────────────────────
# `dias` = fecha del evento relativa a hoy. Un evento entra en "Requiere tu atención" cuando
# `fecha - dias_aviso <= hoy`: los dos primeros están dentro de su ventana y los dos siguientes
# no. El último se crea y se resuelve en la misma corrida, para que la pantalla tenga un
# resuelto que mostrar (y para ejercitar `PUT /{id}/resuelta`, que es el único que sabe escribir
# las tres columnas de forma coherente con su CHECK).
EVENTOS = [
    dict(nombre="Vencimiento de la ART de planta", dias=4, dias_aviso=15, es_publica=True,
         descripcion="Renovar la póliza con el broker antes del vencimiento."),
    dict(nombre="Cierre de la encuesta de clima", dias=6, dias_aviso=7, es_publica=True,
         descripcion="Recordar por mail a quienes todavía no la completaron."),
    dict(nombre="Auditoría externa de calidad", dias=62, dias_aviso=10, es_publica=True,
         descripcion="Preparar legajos de capacitación del personal de planta."),
    dict(nombre="Revisión anual de convenio", dias=95, dias_aviso=20, es_publica=False,
         descripcion="Reunión con el estudio laboral para revisar escalas."),
    dict(nombre="Entrega de indumentaria de invierno", dias=9, dias_aviso=30, es_publica=True,
         descripcion="Ya se entregó en todas las sucursales.", resuelta=True),
]

# ── Formación ─────────────────────────────────────────────────────────────────
CAPACITACIONES = [
    dict(nombre="Seguridad e Higiene en Planta", categoria="Obligatoria", duracion_horas=8,
         entidad_capacitadora="Instituto Argentino de Seguridad", modalidad="Presencial",
         tipo="Técnica", obligatoria=True,
         descripcion="Uso de EPP, riesgos eléctricos y procedimientos de emergencia."),
    dict(nombre="Excel Avanzado para Gestión", categoria="Herramientas", duracion_horas=16,
         entidad_capacitadora="Centro de Formación Profesional", modalidad="Virtual",
         tipo="Técnica", obligatoria=False,
         descripcion="Tablas dinámicas, Power Query y tableros de control."),
    dict(nombre="Liderazgo de Equipos", categoria="Habilidades", duracion_horas=12,
         entidad_capacitadora="Consultora Vía Directa", modalidad="Híbrida",
         tipo="Blanda", obligatoria=False,
         descripcion="Conducción, delegación y conversaciones difíciles."),
]

# Los tres nombres del Excel de formación que NO están en el padrón: entran como `nombre_libre`,
# que es el caso que la pantalla distingue y que el alta por formulario NO puede producir
# (`AsignacionCreate.empleado_id` es obligatorio). Solo el import los crea.
NOMBRES_LIBRES = ["Mariela Ancarola", "Federico Bugallo", "Vanina Terzaghi"]

# ── Objetivos ─────────────────────────────────────────────────────────────────
# 4 anuales y 4 operativos, repartidos en los tres estados del CHECK. `padre` referencia el
# título de otro de la lista: es el subobjetivo que el árbol tiene que poder anidar (profundidad
# máxima 2, migración 095).
OBJETIVOS = [
    dict(titulo="Reducir la rotación voluntaria al 8% anual", tipo="anual", prioridad="alta",
         estado="haciendo", dias=150, periodicidad="",
         descripcion="Medida sobre la dotación promedio del ejercicio."),
    dict(titulo="Digitalizar el 100% de los legajos", tipo="anual", prioridad="media",
         estado="haciendo", dias=210, periodicidad="",
         descripcion="Incluye la carga histórica de los últimos cinco años."),
    dict(titulo="Certificar la norma de calidad en las dos plantas", tipo="anual",
         prioridad="alta", estado="por_hacer", dias=300, periodicidad="",
         descripcion="Auditoría de certificación prevista para el último trimestre."),
    dict(titulo="Cerrar el plan de capacitación obligatoria", tipo="anual", prioridad="media",
         estado="terminado", dias=-30, periodicidad="",
         descripcion="Todo el personal de planta con seguridad e higiene al día."),
    dict(titulo="Publicar el tablero de ausentismo mensual", tipo="operativo", prioridad="media",
         estado="haciendo", dias=20, periodicidad="primer lunes de cada mes",
         descripcion="Con el corte por área y el acumulado del trimestre."),
    dict(titulo="Actualizar las descripciones de puesto de Operaciones", tipo="operativo",
         prioridad="baja", estado="por_hacer", dias=45, periodicidad="tercera semana del mes",
         descripcion="Arranca por las posiciones con búsqueda abierta."),
    dict(titulo="Relevar las descripciones del turno noche", tipo="operativo", prioridad="baja",
         estado="por_hacer", dias=40, periodicidad="",
         descripcion="Subobjetivo del relevamiento de Operaciones.",
         padre="Actualizar las descripciones de puesto de Operaciones"),
    dict(titulo="Cerrar la liquidación de agosto sin ajustes posteriores", tipo="operativo",
         prioridad="alta", estado="terminado", dias=-5, periodicidad="mensual",
         descripcion="Control cruzado con el reporte de novedades antes del envío."),
]

# ── Vacantes y candidatos ─────────────────────────────────────────────────────
# `candidatos` son los que cuelgan de esa búsqueda. `etapa` mueve al candidato después del alta
# (nacen todos en 'postulado'). El de `oferta` es el que habilita el botón Contratar, que exige
# etapa `oferta` Y estado `activo` — ver `frontend/types/candidato.ts`.
VACANTES = [
    dict(titulo="Analista de Sistemas Semi Senior", tipo_contrato="efectivo", modalidad="hibrido",
         ubicacion="Mar del Plata", jornada="Full time", prioridad="alta",
         descripcion="Se incorpora al equipo de aplicaciones internas.",
         requisitos="2 años de experiencia, SQL y Python.",
         candidatos=[
             dict(nombre="Ignacio", apellido="Bermúdez", cargo="Analista funcional",
                  empresa="Sistemas del Sur", etapa="oferta"),
             dict(nombre="Priscila", apellido="Manzur", cargo="Desarrolladora backend",
                  empresa="Nodo Digital", etapa="entrevista_tecnica"),
             dict(nombre="Alan", apellido="Recalde", cargo="Soporte técnico",
                  empresa="Cooperativa Andina", etapa="postulado"),
         ]),
    dict(titulo="Jefe de Logística", tipo_contrato="efectivo", modalidad="presencial",
         ubicacion="Batán", jornada="Full time", prioridad="urgente",
         descripcion="Conduce depósito, flota y última milla.",
         requisitos="5 años conduciendo equipos, movilidad propia.",
         candidatos=[
             dict(nombre="Verónica", apellido="Lastra", cargo="Jefa de depósito",
                  empresa="Distribuidora Pampeana", etapa="entrevista_rrhh"),
             dict(nombre="Damián", apellido="Cocucci", cargo="Coordinador de flota",
                  empresa="Transporte Litoral", etapa="postulado"),
         ]),
    dict(titulo="Asistente de Administración", tipo_contrato="plazo_fijo", modalidad="presencial",
         ubicacion="Mar del Plata", jornada="Part time 6 hs", prioridad="media",
         descripcion="Apoyo al área de Finanzas durante el pico de cierre.",
         requisitos="Excel y experiencia en carga de comprobantes.",
         candidatos=[
             dict(nombre="Julieta", apellido="Nocera", cargo="Administrativa",
                  empresa="Estudio Contable Riera", etapa="entrevista_rrhh"),
             dict(nombre="Matías", apellido="Ferreyra", cargo="Auxiliar contable",
                  empresa="Grupo Rioja", etapa="postulado"),
         ]),
    dict(titulo="Ejecutivo Comercial", tipo_contrato="contratado", modalidad="hibrido",
         ubicacion="Buenos Aires", jornada="Full time", prioridad="baja",
         descripcion="Desarrollo de cartera corporativa en AMBA.",
         requisitos="Venta consultiva B2B y carnet de conducir.",
         candidatos=[
             dict(nombre="Sebastián", apellido="Videla", cargo="Ejecutivo de cuentas",
                  empresa="Editorial Pampa", etapa="assessment"),
             dict(nombre="Guadalupe", apellido="Etchart", cargo="Vendedora corporativa",
                  empresa="Farmacias Unidas", etapa="postulado"),
         ]),
]
