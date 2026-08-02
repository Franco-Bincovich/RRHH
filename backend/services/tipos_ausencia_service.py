"""
Servicio del catálogo de tipos de ausencia.
Flujo: router → service → repository → DB

Desde la migración 085 el catálogo es global + por empresa: los 4 tipos base son globales y
cada empresa puede sumar los suyos. Las lecturas devuelven los globales más los propios.

🔴 NO EXISTE BAJA FÍSICA, Y NO ES UN DESCUIDO. solicitudes_ausencia.tipo_id es una FK sin
ON DELETE: borrar un tipo en uso falla, y si algún día no fallara se llevaría el historial de
ausencias con él. La baja es `activo=False`: saca el tipo de los selects y deja intactas las
ausencias que ya lo usan, que siguen mostrando su nombre. Por eso el router expone PATCH y
NO expone DELETE.
"""
from typing import Optional
from uuid import UUID

from repositories.tipos_ausencia_repo import TiposAusenciaRepo
from services._tipos_jerarquia import ensure_no_ciclo_tipo, ensure_padre_valido
from schemas.ausencias import (
    TipoAusenciaCreate, TipoAusenciaListResponse, TipoAusenciaResponse,
)
from schemas.configuracion import TipoAusenciaUpdate
from utils.errors import AppError


class TiposAusenciaService:
    def __init__(self, repo: Optional[TiposAusenciaRepo] = None) -> None:
        self._repo = repo or TiposAusenciaRepo()

    def get_tipos(
        self, empresa_id: Optional[UUID] = None, incluir_inactivos: bool = False,
    ) -> TipoAusenciaListResponse:
        """Tipos visibles para la empresa activa: los globales más los suyos."""
        items = self._repo.find_all(str(empresa_id) if empresa_id else None, incluir_inactivos)
        return TipoAusenciaListResponse(items=items, total=len(items))

    def create_tipo(
        self, data: TipoAusenciaCreate, empresa_id: Optional[UUID] = None,
    ) -> TipoAusenciaResponse:
        """
        Crea un tipo para la empresa activa (o global si no hay empresa en el contexto).

        Con `padre_id` crea un SUBTIPO. 🔴 `cuenta_ausentismo` se PRECARGA con el del padre —
        ver `_cuenta_del_padre`, donde está escrito por qué es un default y no una herencia.

        Raises:
            AppError: TIPO_NOMBRE_VACIO (422) si el nombre está en blanco.
            AppError: TIPO_PADRE_NOT_FOUND (404) · TIPO_JERARQUIA_PROFUNDA (422) si el padre no sirve.
            AppError: TIPO_DUPLICADO (422) si el nombre ya existe en ese alcance.
        """
        if not data.nombre.strip():
            raise AppError("El nombre del tipo no puede estar vacío", "TIPO_NOMBRE_VACIO", 422)
        padre = ensure_padre_valido(self._repo, data.padre_id)
        try:
            return self._repo.create(
                data.nombre.strip(), str(empresa_id) if empresa_id else None,
                str(data.padre_id) if data.padre_id else None, _cuenta_del_padre(padre))
        except AppError:
            raise
        except Exception:
            raise AppError("El tipo de ausencia ya existe", "TIPO_DUPLICADO", 422)

    def update_tipo(
        self, tipo_id: UUID, data: TipoAusenciaUpdate, empresa_id: Optional[UUID],
    ) -> TipoAusenciaResponse:
        """
        Edita un tipo: nombre, alta/baja lógica y si computa como ausentismo.

        Barrera de empresa: un tipo PROPIO de otra empresa da el mismo 404 que uno inexistente.
        Los globales sí se pueden editar desde cualquier empresa — son de todas, y esa es la
        decisión: hoy hay un solo equipo de RRHH operando todas las empresas.

        Raises:
            AppError: TIPO_NOT_FOUND (404) si no existe o es de otra empresa.
            AppError: TIPO_BASE_NO_DESACTIVABLE (422) al intentar dar de baja un tipo base.
            AppError: TIPO_NOMBRE_VACIO (422) si el nombre nuevo está en blanco.
        """
        actual = self._repo.find_by_id(str(tipo_id))
        propietaria = actual.get("empresa_id") if actual else None
        if not actual or (propietaria and propietaria != str(empresa_id)):
            raise AppError("Tipo de ausencia no encontrado", "TIPO_NOT_FOUND", 404)

        cambios = data.model_dump(exclude_unset=True)
        if cambios.get("activo") is False and actual.get("es_base"):
            # Los 4 base son el vocabulario mínimo con el que se cargó todo el histórico.
            # Sin ellos el formulario de ausencias podría quedar sin una sola opción.
            raise AppError(
                "Los tipos base no se pueden desactivar", "TIPO_BASE_NO_DESACTIVABLE", 422,
            )
        if "padre_id" in cambios:
            # Las dos guardas, en el orden que importa: primero que el padre EXISTA y no sea ya
            # un hijo (profundidad 2), después que no se cierre un circuito. Al revés, el
            # recorrido de ciclos saldría a caminar sobre un padre que no existe.
            ensure_padre_valido(self._repo, cambios["padre_id"], str(tipo_id))
            ensure_no_ciclo_tipo(self._repo, tipo_id, cambios["padre_id"])
            cambios["padre_id"] = str(cambios["padre_id"]) if cambios["padre_id"] else None
        if "nombre" in cambios:
            if not cambios["nombre"].strip():
                raise AppError("El nombre del tipo no puede estar vacío", "TIPO_NOMBRE_VACIO", 422)
            cambios["nombre"] = cambios["nombre"].strip()
        if not cambios:
            return TipoAusenciaResponse.model_validate(actual)
        return self._repo.update(str(tipo_id), cambios)


def _cuenta_del_padre(padre: Optional[dict]) -> Optional[bool]:
    """El `cuenta_ausentismo` con el que nace un subtipo: el del padre.

    🔴 ES UN DEFAULT DE ALTA, NO UNA HERENCIA — y la diferencia es toda la decisión. Se copia UNA
    VEZ, al crear, y a partir de ahí el hijo es independiente: editar el padre NO toca a sus
    hijos, y un hijo puede computar aunque su padre no.

    Por qué no vive en el padre y se lee desde el hijo: dentro de un mismo padre puede haber
    subtipos que computan y otros que no (una licencia por estudio vs. una por maternidad). Si la
    política viviera en el padre, RRHH no podría distinguirlos sin crear un padre nuevo — que es
    justo lo que la jerarquía vino a evitar.

    Por qué no vive en los dos: serían DOS FUENTES para el mismo hecho. Un padre en False con un
    hijo en True no tiene respuesta correcta, y quien la resuelva va a inventar una regla
    (¿gana el hijo? ¿el más restrictivo?) que después nadie recuerda. La ausencia se carga contra
    UN tipo concreto y ESE tipo decide: `_reporte_ausentismo` no cambia una línea.

    None (tipo de primer nivel) deja el default de la tabla.
    """
    return None if padre is None else bool(padre.get("cuenta_ausentismo", True))
