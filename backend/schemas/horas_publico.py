"""
Schemas del link PÚBLICO de carga de horas (sin autenticación).

🔴 LA RESPUESTA ES DELIBERADAMENTE MÍNIMA: solo el NOMBRE DE PILA.
Lo único que el empleado necesita es confirmar que tecleó bien SU dni. Todo lo demás que el
mockup mostraba se sacó, y cada omisión tiene su motivo:

  · APELLIDO   → publicaría el par (dni, apellido) de un tercero a cualquiera que acierte un dni.
                 El nombre de pila alcanza para confirmar; el apellido no agrega confirmación.
  · CARGO      → no aporta a la confirmación (el empleado sabe qué hace) y describe la
                 organización. Además NO EXISTE: `empleados.cargo` está NULL en 31/31.
  · EMPRESA    → es el peor de los tres. Al empleado no le sirve —ya sabe dónde trabaja— y a
                 alguien enumerando le dice de qué sociedad del grupo cobra cada dni que acierta,
                 o sea le arma el mapa de la organización dni por dni.

⚠️ EL `empleado_id` NO VIAJA EN LA RESPUESTA, y no es un olvido. La identidad se resuelve
server-side desde la fila que el dni matcheó y NO puede volver por el request en el paso
siguiente: si el front pudiera mandar un `empleado_id`, adivinar un dni dejaría de ser el techo
del daño y pasaría a ser el piso — cualquiera cargaría horas a nombre de cualquiera sin siquiera
adivinar. Cómo se sostiene la identidad entre este paso y la carga es la decisión abierta de la
sesión que siga; lo que este schema fija es que NO se resuelve devolviéndola.
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.horas import Modalidad
from services._carga_reglas import MAX_HORAS_DIA


class IdentificacionRequest(BaseModel):
    """El dni viaja en el BODY, nunca en el path.

    Un `POST /identificar/{dni}` habría hecho el rate limit por dni más simple (se lee de
    `path_params`), y aun así se descartó: un dni en la URL queda en los access logs del edge,
    en los del proxy, en el historial del navegador y en el header `Referer` de cualquier
    recurso que la página cargue después. Es un identificador personal; no va en una URL.

    `max_length` acota la superficie antes de que el valor toque la base o el log. No se valida
    el FORMATO (solo dígitos, longitud exacta): un dni mal formado tiene que salir por el MISMO
    rechazo genérico que uno inexistente, y un 422 de Pydantic sería un status distinto — o sea
    un oráculo que dice "esto ni siquiera parece un dni", que es información que no hace falta dar.
    """
    dni: str = Field(..., min_length=1, max_length=32)


class IdentificacionResponse(BaseModel):
    """Nombre de pila + el token de la sesión. Ver el encabezado antes de agregarle un campo.

    🔴 EL `token` NO VIOLA LA REGLA DEL PAYLOAD MÍNIMO, y conviene entender por qué. Esa regla
    es sobre DATOS DE LA PERSONA: cada campo que se devuelve es algo que alguien que adivinó un
    DNI aprende sobre un tercero. El token no dice nada de nadie — es una capacidad opaca de 256
    bits que este mismo request acaba de crear. Y es lo que permite que el paso 2 NO reciba un
    `empleado_id` por el body, que es la condición que mantiene acotado el daño de toda la
    feature. Sin token, la alternativa era devolver el `empleado_id`; con él, no se devuelve nada.
    """
    nombre: str
    token: str
    expira_en: datetime


# ── Paso 2: la carga ──────────────────────────────────────────────────────────
#
# 🔴 SON DOS REQUESTS DISJUNTOS Y DOS ENDPOINTS, NO UNO CON UN `tipo`.
# La regla de producto es "al elegir licencia, la carga de horas se desactiva: solo se piden
# desde, hasta y observaciones". Un solo body con `tipo: "horas" | "licencia"` y todos los campos
# opcionales dejaría esa regla como una validación cruzada que hay que acordarse de escribir —y
# que un día alguien afloja—. Con dos schemas disjuntos, mandar `horas` en una licencia no es un
# error de negocio: es un campo que no existe. La regla queda expresada en el TIPO.
#
# 🔴 NINGUNO DE LOS DOS LLEVA `empleado_id` NI `empresa_id`, y no es un olvido. Los dos salen de
# la sesión (ver `services/_sesion_horas.py`). Si estuvieran acá, adivinar un DNI dejaría de ser
# el techo del daño: cualquiera escribiría a nombre de cualquiera. Es la condición #3 de las
# rutas públicas, y es lo único que mantiene el daño de esta feature acotado.


class CargaHorasRequest(BaseModel):
    """Obligatorios: fecha, horas, modalidad y cliente. Proyecto, tarea y descripción son texto
    libre y opcionales — no hay tabla de tareas ni cascada."""
    token: str = Field(..., min_length=1, max_length=128)
    fecha: date
    horas: float = Field(..., gt=0, le=MAX_HORAS_DIA)
    modalidad: Modalidad
    cliente_id: UUID
    proyecto_texto: Optional[str] = Field(default=None, max_length=200)
    tarea_texto: Optional[str] = Field(default=None, max_length=200)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    # Identificador POR INTENTO DE ENVÍO que genera el cliente. Es lo que cierra el doble tap
    # (índice único parcial, migración 106). Opcional para no romper a un cliente que no lo mande
    # todavía; sin él simplemente no hay protección contra el doble tap para ESA carga.
    idempotencia: Optional[str] = Field(default=None, max_length=64)


class CargaLicenciaRequest(BaseModel):
    """Una licencia: desde, hasta y observaciones. NADA de horas — ver la nota de arriba."""
    token: str = Field(..., min_length=1, max_length=128)
    fecha_desde: date
    fecha_hasta: date
    observaciones: Optional[str] = Field(default=None, max_length=1000)


class CargaHorasResponse(BaseModel):
    """Lo mínimo para que la pantalla confirme y arme la tabla de la semana."""
    id: UUID
    fecha: date
    horas: float
    modalidad: Modalidad
    cliente_nombre: Optional[str] = None
    proyecto_texto: Optional[str] = None
    tarea_texto: Optional[str] = None


class CargaLicenciaResponse(BaseModel):
    id: UUID
    fecha_desde: date
    fecha_hasta: date
    dias: int
    # Horas equivalentes = dias × horas por día del empleado.
    horas_equivalentes: float
    # 🔴 True cuando `empleados.horas_contrato` estaba vacío y se asumieron 8. Viaja al cliente a
    # propósito: la pantalla tiene que poder decir "se asumieron 8 h/día" en vez de afirmar un
    # número inventado como si fuera dato. Ver `services/_carga_licencia.py`.
    horas_por_dia_estimadas: bool = False


# ── Paso 3: lo que cargaste esta semana ───────────────────────────────────────


class CargaDeLaSemana(BaseModel):
    """Una fila de la tabla de solo lectura. LO MÍNIMO: fecha, cliente, proyecto, tarea y horas.

    🔴 NO lleva `id`, y es deliberado: el empleado NO puede editar ni borrar sus cargas (decisión
    de producto), así que un id no le sirve para nada y lo único que haría es publicar la clave
    de una fila en una ruta pública. Las correcciones las hace RRHH desde la pantalla interna,
    que sí trae el id porque sí puede borrar.

    Tampoco lleva `empleado_id` ni `empresa_id`: el que pregunta ya sabe quién es —tiene la
    sesión— y devolvérselos no agrega nada.
    """
    fecha: date
    cliente_nombre: Optional[str] = None
    proyecto_texto: Optional[str] = None
    tarea_texto: Optional[str] = None
    horas: float
    modalidad: Optional[Modalidad] = None


class LicenciaDeLaSemana(BaseModel):
    """Una licencia que toca el período. El mockup las muestra junto a las horas."""
    fecha_desde: date
    fecha_hasta: date
    dias: int
    observaciones: Optional[str] = None


class SemanaResponse(BaseModel):
    """La semana EN CURSO del empleado de la sesión.

    `desde`/`hasta` viajan para que la pantalla pueda titular el período sin recalcularlo —y sin
    poder equivocarse: el lunes lo decide el backend, que es el que conoce la regla.
    """
    desde: date
    hasta: date
    total_horas: float
    cargas: List[CargaDeLaSemana]
    licencias: List[LicenciaDeLaSemana]


class ClientePublico(BaseModel):
    """Un cliente elegible en el formulario. SOLO id y nombre.

    🔴 NO se reusa `ClienteResponse`: ese trae `empresa_id`, `activo`, `created_at` y
    `updated_at`, y ninguno le sirve al empleado. `empresa_id` en particular es el dato que la
    identificación se cuida de no devolver — devolverlo acá lo reintroduciría por la ventana.
    """
    id: UUID
    nombre: str


class ClientesPublicosResponse(BaseModel):
    items: List[ClientePublico]
