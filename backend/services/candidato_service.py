"""
Servicio de lectura de candidatos para la sección Candidatos.
Resuelve el "nombre del grupo" de cada candidato: título vivo de su vacante, o el
nombre congelado si la búsqueda fue borrada (vacante_id NULL).
Flujo: router → service → repository.
"""
from typing import List, Optional
from uuid import UUID

from integrations import storage
from repositories.candidato_repo import CandidatoRepo
from repositories.vacante_repo import VacanteRepo
from schemas.candidato import CandidatoGrupoResponse, CandidatoResponse, CandidatosPaginaResponse
from services import _candidato_acciones as _acciones
from services._candidatos_export import construir_filas_export
from services._limite_export import LIMITE_FILAS_EXPORT, verificar_limite_export
from services._paginacion import cantidad_paginas
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger



def _grupo_vivo(titulo: str, area_nombre: Optional[str]) -> str:
    """Arma 'Título — Área' de una vacante viva (omite el área si no existe)."""
    return f"{titulo} — {area_nombre}" if area_nombre else titulo


def _contar_grupos(claves: list[dict], titulos: dict) -> dict[str, int]:
    """Cuántos candidatos tiene cada búsqueda EN TODO EL FILTRO, no en la página.

    🔴 ES LO QUE SOSTIENE EL ENCABEZADO DE CADA GRUPO. El listado se pagina plano y la pantalla
    agrupa dentro de la página; si el encabezado contara lo que tiene a la vista, diría
    "Analista SSR (4)" sobre una búsqueda de 40. Un número plausible y falso.

    `claves` viene de UNA query de dos columnas sobre el conjunto filtrado entero — no de un
    count por búsqueda, que serían 200 round trips (ver `_candidato_listado_repo`).

    🔑 LA CLAVE SE ARMA CON LA MISMA REGLA QUE `grupo_nombre` DE CADA FILA, y por eso mira los
    mismos dos campos en el mismo orden: si la vacante sigue viva manda su título; si se cerró,
    el `busqueda_congelada` que quedó guardado en el candidato. Dos reglas que se separen darían
    un encabezado que no le corresponde a ningún grupo de la pantalla.

    ⚠️ El `"Sin búsqueda"` literal es el MISMO que usa `agruparCandidatos` en el front para los
    huérfanos. Está duplicado entre las dos puntas y no hay test que lo ate: si cambia de un
    lado, ese grupo se queda sin conteo (cae en `undefined` y la pantalla no muestra número).
    """
    conteo: dict[str, int] = {}
    for k in claves:
        vid = k.get("vacante_id")
        nombre = titulos.get(vid) if vid in titulos else k.get("busqueda_congelada")
        conteo[nombre or "Sin búsqueda"] = conteo.get(nombre or "Sin búsqueda", 0) + 1
    return conteo


class CandidatoService:
    def __init__(
        self, candidato_repo: Optional[CandidatoRepo] = None, vacante_repo: Optional[VacanteRepo] = None,
        audit: Optional[AuditService] = None,
    ) -> None:
        self._candidato_repo = candidato_repo or CandidatoRepo()
        self._vacante_repo = vacante_repo or VacanteRepo()
        self._audit = audit or AuditService()

    def exportar(self, empresa_id: Optional[UUID] = None, formato: str = "excel",
                 sin_vacante: bool = False, clasificacion: Optional[str] = None) -> Descarga:
        """Exporta los candidatos por el MISMO camino que el listado (columnas legibles, sin
        UUIDs), así el archivo no puede traer filas que la pantalla no muestre. El motor
        genérico no se toca.

        🔴 `sin_vacante` viaja hasta el repo, igual que en el listado: si el filtro se aplicara
        acá y no en el WHERE, el archivo saldría con más filas de las que se ven en pantalla."""
        pagina = self.listar_todos_candidatos(empresa_id, sin_vacante, clasificacion,
                                              1, LIMITE_FILAS_EXPORT)
        verificar_limite_export(pagina.total)  # total exacto (count="exact"), respeta los filtros
        datos = {"Candidatos": construir_filas_export(pagina.items)}
        return build_export(nombre="Candidatos", datos=datos, filename_base="candidatos", formato=formato)

    def listar_todos_candidatos(self, empresa_id: Optional[UUID] = None,
                                sin_vacante: bool = False, clasificacion: Optional[str] = None,
                                page: int = 1, page_size: int = 20) -> CandidatosPaginaResponse:
        """
        Lista todos los candidatos de la empresa (con y sin vacante), resolviendo el nombre
        del grupo y si la búsqueda sigue activa.

        N+1 evitado: se juntan los vacante_id distintos y se traen las vacantes vivas en UNA
        sola query (find_by_ids); el resto se resuelve en memoria.

        Args:
            empresa_id: filtra por empresa. None = todas (vista consolidada).
            sin_vacante: solo los huérfanos. Se resuelve EN EL WHERE del repo, no acá.
            clasificacion: relevante | dudoso | no_relevante | sin_clasificar. También en el
                WHERE, y el export lo acepta igual: si viviera acá o en el cliente, el archivo
                saldría con más filas de las que muestra la pantalla, sin error y sin aviso.
        """
        candidatos, total = self._candidato_repo.find_pagina(
            empresa_id, sin_vacante, clasificacion, page, page_size)
        claves = self._candidato_repo.claves_de_grupo(empresa_id, sin_vacante, clasificacion)
        # UNA query de vacantes para la página Y para el conteo: los ids de las dos se juntan
        # antes de pedir. Pedirlas dos veces sería el N+1 que este método ya evitaba, con otra cara.
        ids_vivos = {c.vacante_id for c in candidatos if c.vacante_id}
        ids_vivos |= {k["vacante_id"] for k in claves if k.get("vacante_id")}
        titulos = {
            v.id: _grupo_vivo(v.titulo, v.area_nombre)
            for v in self._vacante_repo.find_by_ids(list(ids_vivos))
        }
        items = []
        for c in candidatos:
            activa = bool(c.vacante_id) and c.vacante_id in titulos
            grupo = titulos.get(c.vacante_id) if activa else c.busqueda_congelada
            items.append(
                CandidatoGrupoResponse(**c.model_dump(), grupo_nombre=grupo, busqueda_activa=activa)
            )
        return CandidatosPaginaResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=cantidad_paginas(total, page_size),
            conteo_por_grupo=_contar_grupos(claves, titulos),
        )

    def cv_signed_url(self, candidato_id: str, empresa_id: Optional[UUID] = None) -> str:
        """Signed URL temporal (3600 s) del CV del candidato, sobre el bucket privado 'cvs'.

        Raises: CANDIDATO_NOT_FOUND (404) si no existe o es de otra empresa (fail-closed);
        CV_NOT_FOUND (404) si el candidato no tiene CV cargado.
        """
        candidato = self._candidato_repo.find_by_id(candidato_id, empresa_id)
        if not candidato:
            raise AppError("Candidato no encontrado", "CANDIDATO_NOT_FOUND", 404)
        if not candidato.cv_storage_path:
            raise AppError("El candidato no tiene CV cargado", "CV_NOT_FOUND", 404)
        return storage.url_firmada(storage.CVS, candidato.cv_storage_path)

    def delete_candidato(self, candidato_id: str, empresa_id: Optional[UUID] = None,
                         usuario_id: Optional[str] = None) -> None:
        """Baja de un candidato huérfano. Delegado a _candidato_acciones.borrar."""
        _acciones.borrar(self._candidato_repo, self._audit, candidato_id, empresa_id, usuario_id)

    def asignar_vacante(self, candidato_id: str, vacante_id: str,
                        empresa_id: Optional[UUID] = None,
                        usuario_id: Optional[str] = None) -> CandidatoResponse:
        """Asigna una vacante a un candidato huérfano. Delegado a _candidato_acciones."""
        return _acciones.asignar_vacante(self._candidato_repo, self._vacante_repo, self._audit,
                                         candidato_id, vacante_id, empresa_id, usuario_id)
