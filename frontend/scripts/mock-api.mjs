/**
 * Backend FALSO para el recorrido visual del front. No habla con Supabase ni con nada: escucha
 * en :8000 —el default de `NEXT_PUBLIC_API_URL` cuando no hay `.env.local`— y le contesta
 * cualquier cosa al front para que las 45 pantallas RENDERICEN sin credenciales.
 *
 * 🔴 PARA QUÉ SIRVE Y PARA QUÉ NO. Sirve para mirar la PANTALLA: densidad, contraste en los dos
 * temas, qué se corta en mobile, qué grilla colapsa mal, qué estado vacío está mal escrito.
 * **No sirve para verificar datos**: los números son inventados y varios campos no coinciden con
 * los del backend real, así que un `$NaN` o un `undefined` en una captura es casi siempre culpa
 * de este archivo y no del front.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 HICIERON FALTA SIETE ITERACIONES, Y ESO ES EL VALOR DE ESTE ARCHIVO — no la comodidad.
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * Cada vez que una pantalla caía en el error boundary, el motivo era el mismo: **la FORMA de la
 * respuesta es un contrato que el front da por sabido y que no se puede adivinar desde afuera.**
 * No hay un patrón único; hay uno por endpoint, y ninguno está escrito en un solo lugar. Los tres
 * ejemplos que costaron una iteración cada uno:
 *
 *   · `GET /api/onboarding` devuelve un **array pelado** → `onboardings.map is not a function`
 *     si le contestás `{items}`.
 *   · `GET /api/candidatos` devuelve **`{items, total, …}`** → `items is not iterable` si le
 *     contestás un array. Los dos son listados de la misma app.
 *   · `GET /api/empleados/{id}/recategorizaciones` devuelve un **array**, y su hermano
 *     `GET /api/empleados/{id}/cesiones` devuelve un **objeto `{items}`**. Misma entidad padre,
 *     misma forma de URL, dos contratos distintos.
 *
 * Es la misma clase de deuda que `services/dashboard.ts` documenta en su encabezado (espejo
 * manual de un schema de Pydantic que `tsc` no puede verificar): acá se ve desde el otro lado.
 * **Si alguna vez se genera el cliente desde el OpenAPI del backend, este archivo sobra.**
 *
 * Criterio de las respuestas, elegido para SOBREVIVIR a cualquier consumidor:
 *   1. Un puñado de endpoints con forma propia (dashboard, atención, procesos, organigrama,
 *      costos) se responden a mano: `objetoPorRuta`.
 *   2. Los que devuelven un array pelado están en la lista `ARRAYS`, que se fue llenando
 *      pantalla por pantalla — es el registro de las siete iteraciones.
 *   3. Todo lo demás recibe el **objeto universal**: `{items, total, page, …}` más ~30 claves de
 *      array con los nombres más usados del repo. Un consumidor que lee `data.items`, otro que
 *      lee `data.alertas` y otro que lee `data.total` sobreviven los tres; las claves de más son
 *      inertes.
 *
 * Cómo se corre: ver `frontend/scripts/README.md`.
 */
import { createServer } from "node:http"

const UUID = (n) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`

const NOMBRES = [
  ["Lucía", "Fernández"], ["Martín", "Gómez"], ["Sofía", "Rodríguez"],
  ["Diego", "Pérez"], ["Valentina", "Sosa"], ["Nicolás", "Álvarez"],
]

function fila(i) {
  const [nombre, apellido] = NOMBRES[i % NOMBRES.length]
  return {
    id: UUID(i + 1), nombre, apellido,
    nombre_completo: `${nombre} ${apellido}`,
    empleado_nombre: `${nombre} ${apellido}`,
    usuario_nombre: `${nombre} ${apellido}`,
    responsable_nombre: `${nombre} ${apellido}`,
    created_by_nombre: `${nombre} ${apellido}`,
    email: `${nombre.toLowerCase()}@karstec.com`,
    email_corporativo: `${nombre.toLowerCase()}@karstec.com`,
    dni: `3${i}111222`, legajo: `L-${100 + i}`,
    cargo: "Analista de sistemas", cargo_anterior: "Analista junior",
    puesto: "Analista de sistemas", rol: "Analista", roles: ["Analista"],
    area_id: UUID(90), area_nombre: "Sistemas",
    empresa_id: UUID(91), empresa_nombre: "Bodegas Tupungato",
    empleado_empresa_id: UUID(91), empleado_empresa_nombre: "Bodegas Tupungato",
    manager_id: null, manager_nombre: "Carla Ledesma",
    seniority: "semi_senior", nivel: "semi_senior", modalidad: "hibrido",
    estado: i % 3 === 0 ? "activo" : i % 3 === 1 ? "pausado" : "cerrado",
    activo: i % 4 !== 3, es_publica: i % 2 === 0, es_global: i % 2 === 0,
    es_lider: i % 5 === 0, cancelada: false, justificada: i % 2 === 0,
    clave: `bienvenida_${i}`, asunto: "Te damos la bienvenida a Karstec",
    titulo: "Reducir el tiempo de contratación", label: "Onboarding",
    descripcion: "Descripción de ejemplo para revisar cómo se corta el texto en la tarjeta.",
    observaciones: "Sin observaciones.",
    motivo: "Renuncia", motivo_egreso: "Renuncia", motivo_baja: "Renuncia",
    tipo: "vacaciones", tipo_id: UUID(80), tipo_nombre: "Licencia por enfermedad",
    capacitacion_nombre: "Seguridad de la información",
    proyecto: "Migración AWS", proyecto_nombre: "Migración AWS",
    cliente_nombre: "Cliente Norte", tarea: "Desarrollo",
    fecha: "2026-08-10", fecha_inicio: "2026-08-01", fecha_fin: "2026-08-31",
    fecha_desde: "2026-08-01", fecha_hasta: "2026-08-12", fecha_ingreso: "2024-03-01",
    fecha_egreso: null, fecha_nacimiento: "1992-06-14", fecha_aplicacion: "2026-08-02",
    created_at: "2026-08-10T14:32:00Z", updated_at: "2026-08-10T14:32:00Z",
    anio: 2026, mes: 8, periodo: "Julio 2026", dias: 12, dias_habiles: 21,
    horas: 8, total_horas: 160, cantidad: 3, total: 12, progreso: 60,
    total_asignados: 4, total_proyectos: 2, tareas_total: 9, totalGrupo: 4,
    salario_bruto: 1850000, salario_neto: 1500000, monto: 1850000,
    presupuesto: 5000000, costo_acumulado: 2100000, valor_hora: 9500,
    prioridad: "alta", perfil: "general", sector: "Sistemas",
    nota_final: 8.4, puntaje: 8.4, competencia: "Comunicación",
    entidad: "empleado", evento: "alta_empleado", accion: "INSERT",
    tabla: "empleados", registro_id: UUID(i + 1), usuario_id: UUID(70),
    ip: "190.0.0.1", user_agent: "Mozilla/5.0",
    datos_anteriores: null, datos_nuevos: { nombre },
    cerrado_at: "2026-08-05T10:00:00Z", reabierto_at: null, cerrado_por: UUID(70), reabierto_por: null,
    fecha_asignacion: "2026-07-01", fecha_devolucion: null, fecha_carga: "2026-08-10",
    fecha_alta: "2026-01-15", fecha_baja: null, fecha_compra: "2025-11-20",
    fecha_entrega: "2026-07-01", fecha_solicitud: "2026-06-28", fecha_prevista: "2026-09-01",
    fecha_resolucion: null, fecha_cierre: null, fecha_publicacion: "2026-08-01",
    checklist: [], pasos: [], mails: [], candidatos: [], brechas: [], series: [], serie: [],
    nombres_adjuntos: [], activos: [{ id: UUID(60), nombre: "Notebook Dell", devuelto: true }, { id: UUID(61), nombre: "Celular", devuelto: false }],
    brecha: [{ competencia: "Comunicación", auto: 8.9, terceros: 7.6, brecha: 1.3, n: 10 }],
    n_lider: 2, n_general: 8,
    competencias: {
      n_lider: 2, n_general: 8,
      lider: [{ competencia: "Conducción de equipos", promedio: 8.0, n: 2 }, { competencia: "Visión estratégica", promedio: 7.4, n: 2 }],
      general: [{ competencia: "Comunicación", promedio: 8.2, n: 8 }, { competencia: "Trabajo en equipo", promedio: 8.6, n: 8 }],
    },
    lider: [{ competencia: "Conducción de equipos", promedio: 8.0, n: 2 }, { competencia: "Visión estratégica", promedio: 7.4, n: 2 }],
    general: [{ competencia: "Comunicación", promedio: 8.2, n: 8 }, { competencia: "Trabajo en equipo", promedio: 8.6, n: 8 }],
    importado_por_nombre: "Ana Molina", evaluados: 10, con_nota_final: 8,
    url: "#", logo_url: null, avatar_url: null, foto_url: null,
    hijos: [], empleados: [], estados: [], items: [], adjuntos: [], tareas: [],
    costeo: { costo_acumulado: 2100000, presupuesto_restante: 2900000, pct_consumido: 42 },
  }
}

const filas = (n) => Array.from({ length: n }, (_, i) => fila(i))

const USUARIO = {
  id: UUID(70), email: "rrhh@karstec.com", username: "rrhh", rol: "admin_rrhh",
  nombre: "Ana", apellido: "Molina", must_change_password: false,
}

const DASHBOARD = {
  kpis: { empleados_activos: 31, ingresos_mes: 2, bajas_mes: 1, onboardings_activos: 3, vacantes_activas: 4 },
  headcount_por_area: [
    { area_id: UUID(90), area: "Sistemas", total: 12 },
    { area_id: UUID(93), area: "Administración", total: 9 },
    { area_id: UUID(94), area: "Operaciones", total: 10 },
  ],
  headcount_por_empresa: [
    { empresa_id: UUID(91), empresa: "Bodegas Tupungato", total: 19 },
    { empresa_id: UUID(92), empresa: "Karstec Servicios", total: 12 },
  ],
  alertas: [
    { tipo: "sin_manager", mensaje: "20 colaboradores no tienen superior asignado.", nivel: "warning", href: "/empleados?sin_manager=true" },
    { tipo: "costos_vacios", mensaje: "No hay costos de nómina cargados: la masa salarial sale en cero.", nivel: "error", href: "/costos" },
    { tipo: "info", mensaje: "El período de vacaciones 2026 está abierto.", nivel: "info", href: null },
  ],
  kpis_extra: {
    ausencias_activas_hoy: 3, ausentismo_mes_pct: 2.8,
    ausentismo_nota: "Sobre una base de 21 días hábiles configurada para agosto.",
    masa_salarial_actual: 58200000, masa_salarial_anterior: 55850000,
    masa_salarial_variacion_pct: 4.2, ingresos_proximos_30: 2, recategorizaciones_mes: 1,
    rotacion_12m_bajas: 2, rotacion_12m_pct: 6.4,
    antiguedad_promedio_anios: 4.2, antiguedad_mediana_anios: 3.1,
    distribucion_seniority: [{ categoria: "Semi senior", total: 12 }, { categoria: "Senior", total: 8 }, { categoria: "Sin especificar", total: 11 }],
    distribucion_modalidad: [{ categoria: "Híbrido", total: 20 }, { categoria: "Presencial", total: 11 }],
    cumpleanos_mes: [{ empleado: "Lucía Fernández", fecha: "24/08" }, { empleado: "Martín Gómez", fecha: "29/08" }],
    aniversarios_mes: [{ empleado: "Sofía Rodríguez", fecha: "30/08" }],
    errores: [],
  },
}

const ATENCION_ALERTAS = [
  { origen: "calculada", tipo: "ingreso_proximo", mensaje: "Sofía Rodríguez ingresa el 25/8 y su legajo sigue en preingreso.", fecha: "2026-08-25", href: "/proximos-ingresos", evento_id: null, creado_por_nombre: null },
  { origen: "manual", tipo: "agenda", mensaje: "Revisar el fin del período de prueba de Diego Pérez.", fecha: "2026-08-27", href: "/empleados", evento_id: "e2", creado_por_nombre: "Ana Molina" },
]
const ATENCION = { alertas: ATENCION_ALERTAS }

const PROCESOS = {
  procesos: [
    { proceso: "onboarding", label: "Onboarding", total: 3, estados: [{ estado: "en_progreso", label: "En progreso", total: 2 }, { estado: "completado", label: "Completado", total: 1 }] },
    { proceso: "offboarding", label: "Offboarding", total: 1, estados: [{ estado: "iniciado", label: "Iniciado", total: 1 }] },
    { proceso: "vacantes", label: "Búsquedas", total: 4, estados: [{ estado: "abierto", label: "Abierta", total: 3 }, { estado: "cerrada", label: "Cerrada", total: 1 }] },
    { proceso: "objetivos", label: "Objetivos", total: 6, estados: [{ estado: "por_hacer", label: "Por hacer", total: 2 }, { estado: "haciendo", label: "Haciendo", total: 3 }, { estado: "terminado", label: "Terminado", total: 1 }] },
  ],
}

const EMPRESAS_ORDEN = [
  { id: UUID(91), nombre: "Bodegas Tupungato" }, { id: UUID(92), nombre: "Karstec Servicios" },
]

const ORG_PROYECTOS = {
  empresas_orden: EMPRESAS_ORDEN,
  proyectos: [0, 1, 2].map((i) => ({
    id: UUID(50 + i), nombre: ["Migración AWS", "Vendimia 2026", "Portal de clientes"][i],
    empresa_id: UUID(91 + (i % 2)), empresa_nombre: EMPRESAS_ORDEN[i % 2].nombre,
    total_asignados: 4,
    empleados: [0, 1, 2, 3].map((j) => ({
      ...fila(j), empleado_empresa_id: UUID(91 + (j % 2)),
      empleado_empresa_nombre: EMPRESAS_ORDEN[j % 2].nombre,
      total_proyectos: j === 0 ? 2 : 1,
    })),
  })),
}

const ORG_EMPRESAS = {
  empresas_orden: EMPRESAS_ORDEN,
  empresas: EMPRESAS_ORDEN.map((e, i) => ({
    ...e, total: 19 - i * 7,
    nodos: [0, 1].map((j) => ({ ...fila(j), subordinados: [fila(j + 2)] })),
    raices: [{ ...fila(i), subordinados: [fila(i + 2), fila(i + 3)] }],
  })),
}

const COSTOS = {
  total_nomina: 58200000, costo_promedio: 1877419, variacion_porcentual: 3.1,
  costos_por_area: [
    { area_id: UUID(90), area: "Sistemas", area_nombre: "Sistemas", total: 24000000, cantidad: 12, empleados: 12 },
    { area_id: UUID(93), area: "Administración", area_nombre: "Administración", total: 18000000, cantidad: 9, empleados: 9 },
  ],
  evolucion_mensual: [
    { anio: 2026, mes: 6, total: 55000000 }, { anio: 2026, mes: 7, total: 56800000 }, { anio: 2026, mes: 8, total: 58200000 },
  ],
}

function objetoPorRuta(path) {
  if (path.includes("/costos/dashboard")) return COSTOS
  if (path.includes("/dashboard/atencion")) return ATENCION
  if (path.includes("/dashboard")) return DASHBOARD
  if (path.includes("/procesos")) return PROCESOS
  if (path.includes("/organigrama/proyectos")) return ORG_PROYECTOS
  if (path.includes("/organigrama")) return ORG_EMPRESAS
  if (path.includes("/costos/dashboard") || path.endsWith("/costos")) return COSTOS
  if (path.includes("/usuarios/me") || path.includes("/vigente")) return USUARIO
  if (path.includes("/auth/me")) return USUARIO
  if (path.includes("/empresas") && !path.includes("?")) return null
  if (path.includes("/provincias")) return ["Mendoza", "Buenos Aires", "Córdoba"]
  // Los que devuelven un array pelado: acá el objeto universal rompe con `.map is not a function`.
  const ARRAYS = [
    "/api/onboarding", "/api/onboarding/templates", "/api/offboarding", "/api/equipo",
    "/api/reportes/historial", "/api/vacantes/casilla/pendientes",
  ]
  if (ARRAYS.includes(path) || /\/vacantes\/[^/]+\/candidatos$/.test(path) || /\/tareas$/.test(path)) return filas(4)
  if (path.includes("/costos/nomina/empleado/")) {
    return filas(4).map((f, i) => ({ ...f, anio: 2026, mes: 5 + i, total: 1800000 + i * 40000, salario_bruto: 1800000 + i * 40000, salario_neto: 1500000 + i * 30000 }))
  }
  if (path.includes("/integraciones")) return []
  // `/api/empleados/{id}/recategorizaciones` y hermanos: sub-listas que vuelven como array pelado.
  if (/\/empleados\/[^/]+\/recategorizaciones$/.test(path)) return filas(3)
  return null
}

const OPCIONES = [
  { valor: "semi_senior", label: "Semi senior", value: "semi_senior", nombre: "Semi senior" },
  { valor: "senior", label: "Senior", value: "senior", nombre: "Senior" },
]

/**
 * El objeto universal: un consumidor que lee `data.items`, uno que lee `data.alertas` y uno que
 * lee `data.total` sobreviven todos. Las claves de más son inertes.
 */
function universal() {
  return {
    ...fila(0),
    items: filas(6), total: 6, page: 1, page_size: 20, total_pages: 1,
    alertas: [], eventos: filas(3), areas: filas(3), empresas: EMPRESAS_ORDEN.map((e, i) => ({ ...fila(i), ...e })),
    empleados: filas(4), clientes: filas(3), proyectos: filas(3), lotes: filas(2),
    resultados: filas(3), evaluados: filas(3), tareas: filas(4), adjuntos: [], hijos: [],
    historial: filas(3), pendientes: [], estados: [], asignaciones: filas(3), plantillas: filas(3),
    reglas: [], tipos: filas(3), grupos: [], secciones: [], semanas: [], detalle: [],
    campos: [
      { clave: "descripcion", nombre: "Descripción", label: "Descripción", tipo: "textarea", placeholder: "" },
      { clave: "funciones", nombre: "Funciones", label: "Funciones", tipo: "textarea", placeholder: "" },
    ],
    nota_requisitos: "Cargá cada requisito en su campo: el aviso se arma por partes.",
    modalidades: OPCIONES, niveles: OPCIONES, tipos_contrato: OPCIONES, jornadas: OPCIONES,
    opciones: OPCIONES, es_propia: true,
    kpis: { horas_totales: 160, empleados_activos: 31, clientes: 3, proyectos: 3, cargas: 24 },
    horas_totales: 160, empleados_con_carga: 4, cantidad_cargas: 24,
    parametros: { es_propia: true, dias_habiles_mes: 21, dias_vacaciones_base: 14, tope_horas_dia: 12 },
    escala: { es_propia: true, niveles: OPCIONES, tramos: [] },
    resumen: { evaluados: 10, con_nota_final: 8, promedio: 7.9, nota_mas_alta: 9.4, nota_mas_baja: 6.1, evaluaciones: 307 },
    sectores: [{ sector: "Sistemas", evaluados: 6, promedio: 8.1 }, { sector: "Administración", evaluados: 4, promedio: 7.6 }],
    brechas: [{ competencia: "Comunicación", auto: 8.9, terceros: 7.6, brecha: 1.3, n: 10 }],
    integraciones: [], mails: [], checklist: [], pasos: [],
    costos_por_area: COSTOS.costos_por_area, evolucion_mensual: COSTOS.evolucion_mensual,
  }
}

const PUERTO = 8000

createServer((req, res) => {
  const [path, query = ""] = req.url.split("?")
  res.setHeader("Access-Control-Allow-Origin", "*")
  res.setHeader("Access-Control-Allow-Headers", "*")
  res.setHeader("Access-Control-Allow-Methods", "*")
  res.setHeader("Content-Type", "application/json; charset=utf-8")
  if (req.method === "OPTIONS") { res.writeHead(204); res.end(); return }

  const propio = objetoPorRuta(path)
  const cuerpo = propio !== null ? propio : universal()

  res.writeHead(200)
  res.end(JSON.stringify(cuerpo))
}).listen(PUERTO, () => console.log(`mock api en http://localhost:${PUERTO}`))
