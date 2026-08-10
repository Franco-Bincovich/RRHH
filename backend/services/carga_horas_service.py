"""
El paso 2 del link público: cargar horas o una licencia.
Flujo: router (sin auth, con token de sesión) → service → repository → DB

🔴 LA IDENTIDAD NUNCA SALE DEL BODY. `empleado_id` y `empresa_id` se resuelven contra
`sesiones_horas` a partir del token, y los schemas de request NO tienen esos campos — así que no
es una validación que alguien pueda aflojar, es un dato que no existe en el request. Es la
condición #3 de las rutas públicas y lo que mantiene acotado el daño de toda la feature: adivinar
un DNI no alcanza para escribir, hace falta además un token de 256 bits vigente.

Las reglas duras (ventana de 30 días, tope de 12 h sumando lo ya cargado) viven en
`_carga_reglas.py` y la licencia en `_carga_licencia.py`; este service las orquesta.

🔴 EL DOBLE TAP DE HORAS se cierra con `idempotencia` + su índice único parcial (migración 106).
La carrera que NO se cierra —dos cargas DISTINTAS enviadas a la vez— está declarada como límite
conocido, con su motivo y su disparador, en el encabezado de esa migración. No se esconde.
"""
from datetime import date, datetime
from typing import Optional

from repositories.ausencias_repo import AusenciasRepo
from repositories.cliente_repo import ClienteRepo
from repositories.horas_repo import HorasRepo
from repositories.sesion_horas_repo import SesionHorasRepo
from repositories import _semana_publica_repo, identificacion_repo
from schemas.horas_publico import (
    CargaHorasRequest, CargaHorasResponse, CargaLicenciaRequest, CargaLicenciaResponse,
    ClientePublico, ClientesPublicosResponse, SemanaResponse,
)
from services import _carga_licencia, _semana_publica
from services._carga_reglas import verificar_tope, verificar_ventana
from services._sesion_horas import resolver
from utils.errors import AppError
from utils.logger import logger

_CLIENTE_INVALIDO = ("Ese cliente ya no está disponible. Elegí otro de la lista.",
                     "CLIENTE_INVALIDO", 422)


class CargaHorasService:
    def __init__(self, sesiones=None, horas=None, clientes=None,
                 ausencias=None, datos=None, semana=None) -> None:
        self._semana = semana or _semana_publica_repo
        self._sesiones = sesiones or SesionHorasRepo()
        self._horas = horas or HorasRepo()
        self._clientes = clientes or ClienteRepo()
        self._ausencias = ausencias or AusenciasRepo()
        self._datos = datos or identificacion_repo

    def cargar_horas(self, data: CargaHorasRequest,
                     hoy: Optional[date] = None) -> CargaHorasResponse:
        """Registra una carga de horas.

        Raises:
            AppError: SESION_INVALIDA (401), FECHA_FUTURA / FECHA_MUY_VIEJA / CLIENTE_INVALIDO /
                TOPE_HORAS_DIA (422).
        """
        empleado_id, empresa_id = resolver(self._sesiones, data.token)
        hoy = hoy or datetime.now().date()

        # El corte por idempotencia va PRIMERO: un reenvío tiene que devolver lo que ya se creó
        # sin volver a validar nada. Si validara antes, un doble tap sobre la última carga del día
        # daría TOPE_HORAS_DIA — un error, cuando en realidad la carga ya está hecha y bien.
        if data.idempotencia:
            ya = self._horas.buscar_por_idempotencia(data.idempotencia)
            if ya:
                return self._respuesta(ya)

        verificar_ventana(data.fecha, hoy)
        self._verificar_cliente(str(data.cliente_id), empresa_id)
        verificar_tope(data.horas, self._horas.total_horas_del_dia(empleado_id, str(data.fecha)))

        row = self._horas.save(
            empresa_id=empresa_id, empleado_empresa_id=empresa_id,
            fecha=str(data.fecha), horas=data.horas, descripcion=data.descripcion,
            empleado_id=empleado_id, cliente_id=str(data.cliente_id),
            modalidad=data.modalidad, proyecto_texto=data.proyecto_texto,
            tarea_texto=data.tarea_texto, idempotencia=data.idempotencia,
        )
        logger.info("Horas cargadas desde el link público",
                    extra={"empleado_id": empleado_id, "fecha": str(data.fecha),
                           "horas": data.horas})
        return self._respuesta(row)

    def cargar_licencia(self, data: CargaLicenciaRequest,
                        hoy: Optional[date] = None) -> CargaLicenciaResponse:
        """Registra una licencia en `solicitudes_ausencia`. Ver `_carga_licencia.py`."""
        empleado_id, empresa_id = resolver(self._sesiones, data.token)
        return _carga_licencia.crear(self._ausencias, self._datos, empleado_id, empresa_id,
                                     data, hoy or datetime.now().date())

    def ver_semana(self, token: str, hoy: Optional[date] = None) -> SemanaResponse:
        """Lo que el empleado cargó en la semana en curso. Es la ÚNICA lectura del link público.

        🔴 Autenticada por el TOKEN, no por el dni. Leer con el dni sería volver a la parte débil
        del flujo —un identificador enumerable— para devolver datos de una persona: el peor
        intercambio posible. Con el token hace falta un secreto de 256 bits vigente.
        """
        empleado_id, _ = resolver(self._sesiones, token)
        return _semana_publica.armar(self._semana, empleado_id, hoy or datetime.now().date())

    def clientes_disponibles(self, token: str) -> ClientesPublicosResponse:
        """Los clientes ACTIVOS de la empresa del empleado, para el select del formulario.

        🔴 EXISTE PORQUE EL FORMULARIO NO SE PUEDE COMPLETAR SIN ÉL: `cliente_id` es obligatorio
        y `GET /api/clientes` exige JWT + Seccion.CLIENTES, que un empleado sin cuenta no tiene.
        Sin esta ruta el select nace vacío y la pantalla es decorativa.

        Autenticada por el TOKEN y acotada a la empresa de la SESIÓN: un empleado ve los clientes
        de SU sociedad y de ninguna otra. `incluir_inactivos` queda en False —el default— porque
        un cliente dado de baja no es elegible, y ofrecerlo terminaría en un CLIENTE_INVALIDO
        después de que la persona completó todo el formulario.
        """
        _, empresa_id = resolver(self._sesiones, token)
        return ClientesPublicosResponse(items=[
            ClientePublico(id=c.id, nombre=c.nombre)
            for c in self._clientes.find_all(empresa_id)
        ])

    def _verificar_cliente(self, cliente_id: str, empresa_id: str) -> None:
        """El cliente tiene que ser de LA EMPRESA DE LA SESIÓN y estar activo.

        🔴 La empresa sale de la sesión, no del request: sin esto alguien podría imputarle horas
        al cliente de otra sociedad del grupo. `ClienteRepo.find_by_id` mete el `empresa_id` en el
        WHERE, así que la barrera viaja en la query y no se compara acá.

        "No existe", "es de otra empresa" y "está dado de baja" salen por el MISMO error: los tres
        significan lo mismo para quien está cargando —ese cliente no es elegible— y distinguirlos
        confirmaría la existencia de clientes de otras empresas.
        """
        cliente = self._clientes.find_by_id(cliente_id, empresa_id)
        if not cliente or not cliente.activo:
            raise AppError(*_CLIENTE_INVALIDO)

    @staticmethod
    def _respuesta(row) -> CargaHorasResponse:
        """Proyecta la fila guardada a la respuesta. NO devuelve `empleado_id` ni `empresa_id`:
        el cliente no los necesita —los tiene la sesión— y no hay motivo para publicarlos."""
        return CargaHorasResponse(
            id=row.id, fecha=row.fecha, horas=row.horas, modalidad=row.modalidad,
            cliente_nombre=row.cliente_nombre, proyecto_texto=row.proyecto_texto,
            tarea_texto=row.tarea_texto,
        )
