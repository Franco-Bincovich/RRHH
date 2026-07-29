"""
Importación de nómina de empleados (CSV 27 columnas, ';', latin1).

Idempotente y tolerante: dedup por DNI (crea si es nuevo, actualiza si ya existe), y clasifica
cada fila en 3 grupos — cargados OK · cargados con faltantes (email) · no cargados (falta un
obligatorio o falló la creación). Reusa Empresa/Area/EmpleadoService (validaciones + audit).
No aborta ante error de fila. Flujo: router → service → services.

AUDITORÍA: UN evento por lote para las ALTAS (con la lista de ids creados) y un evento
individual con diff por cada UPDATE. Ver `_audit_payloads_import.payload_importacion_nomina`:
un alta es una fotografía y el id alcanza para reconstruirla; un update responde "qué cambió"
y eso no se puede reconstruir desde un id.
"""
import csv
import io
from typing import Optional
from uuid import UUID

from repositories.empleado_repo import EmpleadoRepo
from schemas.importacion_nomina_empleados import (
    ImportacionNominaEmpleadosResult, build_create, build_update,
)
from services import _nomina_empleados_transforms as tx
from services._nomina_parsers import email_valido
from services._audit_payloads_import import payload_importacion_nomina
from services._nomina_catalogos import NominaCatalogos
from services._nomina_lote import LoteNomina, resultado_headers_invalidos
from services._nomina_cesiones import NominaCesiones
from services._nomina_proyectos import NominaProyectos
from services.audit_service import AuditService
from services.empleado_service import EmpleadoService
from utils.logger import logger


class NominaEmpleadosImportService:
    def __init__(self, usuario_id: str) -> None:
        self._usuario_id = usuario_id
        self._catalogos = NominaCatalogos(usuario_id)  # empresa/area con cache primado
        self._empleados = EmpleadoService()
        self._emp_repo = EmpleadoRepo()
        self._audit = AuditService()
        self._seen_dni: set[tuple] = set()
        # 🔴 Simétrico con _seen_dni, y por el mismo motivo: `ensure_legajo_unico` valida contra
        # la BASE, no contra el archivo. Dos filas del mismo CSV con el mismo legajo pasan las
        # dos (ninguna está en la base todavía) y la segunda revienta en el INSERT con el error
        # de `empleados_legajo_empresa_key`, que llega al usuario como texto de Postgres en vez
        # de un motivo legible. Este set lo convierte en un "no cargado" con explicación.
        self._seen_legajo: set[tuple] = set()
        self._proyectos = NominaProyectos()  # proyecto por gerencia + asignación
        self._cesiones = NominaCesiones(usuario_id)  # cesión por Fecha Ingreso Reconocida

    def importar(self, contenido: str, archivo: str,
                 presupuesto: Optional[float] = None) -> ImportacionNominaEmpleadosResult:
        """Procesa el CSV. Reporta cada fila en su grupo; no aborta por errores.

        Si se agota el PRESUPUESTO DE TIEMPO, para ENTRE FILAS y devuelve el reporte de lo hecho
        con `parcial=True`. Reintentar con el mismo archivo continúa donde quedó: el dedup por
        (empresa_id, dni) manda las ya cargadas por la rama de update. No hay estado que limpiar.

        `presupuesto` en segundos; None → `settings.import_presupuesto_segundos`. Solo los tests
        lo pasan explícito."""
        reader = csv.DictReader(io.StringIO(contenido), delimiter=";")
        error_headers = tx.validar_headers(reader.fieldnames)
        if error_headers:
            return resultado_headers_invalidos(error_headers)

        lote = LoteNomina(presupuesto)
        for n, raw in lote.filas_con_margen(list(reader)):
            try:
                nuevo, faltan, empleado_id = self._procesar_fila(raw, n)
            except Exception as exc:  # noqa: BLE001 — el lote no aborta por una fila
                lote.registrar_fallo(n, tx.identificador(raw), str(exc))
                continue
            lote.registrar_cargada(n, tx.identificador(raw), nuevo, faltan, empleado_id)

        # 🔴 EL EVENTO DE LOTE SE EMITE SIEMPRE, TAMBIÉN EN EL CORTE PARCIAL, y no es un detalle:
        # las altas ya NO emiten evento individual (se consolidaron acá, `auditar=False`), así que
        # este evento es el ÚNICO registro de que alguien importó algo. Si se emitiera solo al
        # terminar el archivo completo, un corte dejaría N empleados creados sin una sola línea
        # en `auditoria`. Los updates sí conservan el suyo, así que quedaría un rastro asimétrico
        # y engañoso: los modificados auditados, los creados invisibles.
        self._audit.registrar(**payload_importacion_nomina(
            archivo, lote.creados, lote.actualizados, len(lote.con_faltantes),
            len(lote.no_cargados), self._usuario_id, lote.ids_creados, lote.parcial))
        # El tiempo se loguea SIEMPRE, no solo en el corte: es la única medición de duración de
        # todo el repo, y sin ella el presupuesto se calibra a ojo en vez de con datos reales.
        logger.info("Import nómina empleados", extra={
            "archivo": archivo, "creados": lote.creados, "actualizados": lote.actualizados,
            "con_faltantes": len(lote.con_faltantes), "no_cargados": len(lote.no_cargados),
            "segundos": lote.segundos(), "parcial": lote.parcial,
            "filas_sin_procesar": lote.filas_sin_procesar})
        return lote.resultado()

    def _procesar_fila(self, raw: dict, fila: int) -> tuple[bool, list, str]:
        """Crea o actualiza (dedup DNI) el empleado de una fila.
        Devuelve (es_nuevo, faltantes, empleado_id) — el id nomina el alta en el evento de lote.
        Lanza ValueError con motivo si falta un obligatorio o el DNI está duplicado en el archivo."""
        f = tx.parsear_fila(raw)
        faltan_oblig = tx.obligatorios_faltantes(f)
        if faltan_oblig:
            raise ValueError(f"falta {', '.join(faltan_oblig)}")

        empresa_id = self._catalogos.empresa_id(f["_empresa"])
        area_id = self._catalogos.area_id(empresa_id, f["_area"])
        clave = (empresa_id, f["dni"])
        if clave in self._seen_dni:
            raise ValueError("DNI duplicado dentro del archivo (fila previa ya procesada)")
        self._seen_dni.add(clave)

        if f["legajo"]:
            clave_legajo = (empresa_id, f["legajo"])
            if clave_legajo in self._seen_legajo:
                raise ValueError("Legajo duplicado dentro del archivo (fila previa ya procesada)")
            self._seen_legajo.add(clave_legajo)

        email = f["email_corporativo"] if email_valido(f["email_corporativo"]) else None
        faltan = [] if email else ["email"]

        # `areas_validadas` y `prior` ahorran una query cada uno POR FILA: el área la acabó de
        # resolver `_catalogos` contra esta misma empresa, y `existente` ES la fila anterior que
        # el diff de auditoría necesita (viene del mismo SELECT con joins que find_by_id).
        validadas = self._catalogos.areas_validadas()
        existente = self._emp_repo.find_by_dni(f["dni"], UUID(empresa_id))
        if existente:
            self._empleados.update_empleado(
                UUID(existente.id), build_update(f, UUID(area_id), email), UUID(empresa_id),
                self._usuario_id, areas_validadas=validadas, prior=existente)
            empleado_id, nuevo = existente.id, False
        else:
            # auditar=False: las altas se consolidan en el evento de lote (ver `importar`).
            empleado = self._empleados.create_empleado(
                build_create(f, UUID(empresa_id), UUID(area_id), email), self._usuario_id,
                UUID(empresa_id), areas_validadas=validadas, auditar=False)
            empleado_id, nuevo = empleado.id, True

        if f["fecha_baja"]:
            self._emp_repo.dar_de_baja(empleado_id, f["fecha_baja"], UUID(empresa_id))
        # Gerencia → proyecto (crear/reusar) + asignar el empleado (no si está de baja).
        # empresa_id del empleado: es la que acabamos de escribir, no hace falta consultarla.
        self._proyectos.resolver_y_asignar(
            empresa_id, f["gerencia"], empleado_id, f["roles"][0], bool(f["fecha_baja"]),
            empresa_id)
        # Fecha Ingreso Reconocida → cesión (idempotente por fecha, best-effort).
        self._cesiones.crear_si_falta(empleado_id, empresa_id, f["fecha_ingreso_reconocida"])
        return nuevo, faltan, empleado_id
