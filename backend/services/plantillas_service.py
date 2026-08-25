"""
Plantillas de mail: listar, guardar, borrar y PREVISUALIZAR.

El envío vive en `mail_envio_service.py`: son dos responsabilidades y juntas no entran en 150.

## 🔴 EL PREVIEW USA EL MISMO RENDERER QUE EL ENVÍO
`_render.render` es uno solo y no sabe si lo que devuelve se va a mandar o a mostrar. Si fueran
dos, divergen — es la lección de los filtros duplicados front/back, que este repo ya pagó.

## 🔴 AUDITA SUS DOS ESCRITURAS (25/8/2026)
El disparador fue la baja (barrido nº 42: "el texto que RRHH escribió desaparece y no hay versión
anterior de la que sacarlo"), y el barrido nº 8 obliga a que el guardado también. Ver
`_audit_payloads_plantillas_mail`.

## Preview con datos REALES, ejemplo como fallback
Con datos inventados los huecos reales —el empleado sin área cargada, `manager_id` en 0/19— NO SE
VEN, y son justamente el problema que hoy existe. Por eso el default es elegir un empleado. El
ejemplo queda para el contexto 'ninguno' y para cuando todavía no hay empleados cargados.

⚠️ El preview con datos reales LEE datos de un empleado, así que el router lo gatea también por
lectura de EMPLEADOS: quien puede editar plantillas pero no ver empleados no debe sacar datos
por esta puerta.

## Guardar valida las variables (momento 1 de los tres)
Es la única barrera con un humano mirando la pantalla que puede corregir un typo. Ver `_render`.
"""
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from repositories.plantilla_mail_repo import PlantillaMailRepo
from schemas.plantillas import (
    PlantillaResponse, PlantillasListResponse, PlantillaUpsert, PreviewRequest, PreviewResponse,
)
from services._envio_libre import plantilla_usa_variables
from services._plantillas_write import borrar as _borrar
from services._plantillas_write import guardar as _guardar
from services.mailer._markdown import a_html
from services.mailer._render import datos_de_ejemplo, render
from services.mailer._variables import CONTEXTOS
from services.audit_service import AuditService
from utils.errors import AppError
from utils.logger import logger


class PlantillasService:
    def __init__(self, repo: Optional[PlantillaMailRepo] = None,
                 empleado_repo: Optional[EmpleadoRepo] = None,
                 audit: Optional[AuditService] = None) -> None:
        self._repo = repo or PlantillaMailRepo()
        self._empleados = empleado_repo or EmpleadoRepo()
        self._audit = audit or AuditService()

    def listar(self, empresa_id: Optional[UUID] = None) -> PlantillasListResponse:
        """Las plantillas visibles: las de la empresa + las globales que no pisó.

        Devuelve además el catálogo de contextos → variables, para que la UI ofrezca solo las
        válidas. Viaja acá y no en un endpoint aparte: es un dict chico y constante, y un request
        más por abrir una pantalla no compra nada."""
        items = [_a_response(f) for f in self._repo.listar(empresa_id)]
        return PlantillasListResponse(items=items, contextos={k: list(v) for k, v in CONTEXTOS.items()})

    def guardar(self, data: PlantillaUpsert, empresa_id: UUID,
                usuario_id: Optional[str] = None) -> PlantillaResponse:
        """Crea o edita una plantilla de la empresa. Ver `_plantillas_write.guardar`."""
        return _guardar(self._repo, self._audit, data, empresa_id, _a_response, usuario_id)

    def borrar(self, id_: UUID, empresa_id: UUID, usuario_id: Optional[str] = None) -> None:
        """Borra una plantilla de la empresa. Ver `_plantillas_write.borrar`."""
        _borrar(self._repo, self._audit, id_, empresa_id, usuario_id)

    def preview(self, data: PreviewRequest, empresa_id: Optional[UUID] = None) -> PreviewResponse:
        """Renderiza sin enviar. Con el empleado elegido, o con datos de ejemplo.

        Un `empleado_id` que no exista (o de otra empresa) NO es un error: cae al ejemplo y lo
        informa en `con_datos_reales`. Cortar con un 404 obligaría a RRHH a resolver un problema
        de datos para poder mirar un texto.
        """
        datos, reales = self._datos(data.empleado_id, empresa_id, data.contexto)
        asunto, cuerpo, faltantes = render(data.contexto, data.asunto, data.cuerpo, datos)
        return PreviewResponse(asunto=asunto, cuerpo_html=a_html(cuerpo),
                               faltantes=faltantes, con_datos_reales=reales)

    def _datos(self, empleado_id, empresa_id, contexto: str) -> tuple:
        """Arma el payload del render desde un empleado real, o el de ejemplo."""
        if not empleado_id:
            return datos_de_ejemplo(contexto), False
        emp = self._empleados.find_by_id(str(empleado_id), empresa_id)
        if not emp:
            return datos_de_ejemplo(contexto), False
        return {"empresa": {"nombre": getattr(emp, "empresa_nombre", None)},
                "empleado": datos_empleado(emp)}, True


def datos_empleado(emp) -> dict:
    """Traduce un EmpleadoResponse al dict que el catálogo de variables espera.

    🔴 Enumera SOLO los campos que el catálogo declara. Pasar el `model_dump()` entero sería
    exactamente el "todo menos" que `_variables` prohíbe: cada columna nueva de empleados
    quedaría disponible para una plantilla sin que nadie lo decida.
    """
    return {
        "nombre": emp.nombre, "apellido": emp.apellido,
        "_nombre_completo": f"{emp.nombre} {emp.apellido}".strip(),
        "email_corporativo": emp.email_corporativo,
        "area_nombre": getattr(emp, "area_nombre", None),
        "fecha_ingreso": emp.fecha_ingreso,
        "tipo_contrato": getattr(emp, "tipo_contrato", None),
        "seniority": getattr(emp, "seniority", None),
        "manager_nombre": getattr(emp, "manager_nombre", None),
    }


def _a_response(fila: dict) -> PlantillaResponse:
    # `usa_variables` se calcula acá, del lado del backend, y viaja en el listado: es lo que hace
    # que la pantalla pueda deshabilitar el envío a direcciones sueltas SIN reimplementar la
    # detección. Ver la nota en el schema y `services/_envio_libre.py`.
    return PlantillaResponse(
        id=fila["id"], empresa_id=fila.get("empresa_id"), clave=fila["clave"],
        contexto=fila["contexto"], asunto=fila["asunto"], cuerpo=fila["cuerpo"],
        activa=bool(fila.get("activa", True)), es_global=fila.get("empresa_id") is None,
        usa_variables=plantilla_usa_variables(fila))
