"""
Resolutor de identidad → empleado_id (fase 3). De identidad cruda del CSV a un candidato con
nivel de confianza (estado), SIN persistir. Invariante: se busca SIEMPRE dentro de la empresa
del lote (las tablas hijas de evaluación no llevan empresa_id → única barandilla; nunca global).

Orden de señales: (0) equivalencia confirmada previa → 'resuelto' directo · (1) apellido+nombre
normalizado · (2) superior inmediato contra manager_id · (3) gerencia como color secundario.
Sin matcheo difuso por similitud: un apellido parecido le asignaría notas a la persona equivocada.
"""
from typing import Dict, List, Optional
from uuid import UUID

from repositories.evaluacion_matcheo_repo import EvaluacionMatcheoRepo
from schemas.evaluacion_import import EmpleadoCandidato, ResolucionIdentidad
from services import _evaluacion_import_transforms as tx


class ResolutorIdentidad:
    def __init__(self, repo: Optional[EvaluacionMatcheoRepo] = None) -> None:
        self._repo = repo or EvaluacionMatcheoRepo()

    def resolver(self, empresa_id: UUID, apellido_csv: str, nombre_csv: str,
                 apellido_superior: Optional[str] = None, nombre_superior: Optional[str] = None,
                 ) -> ResolucionIdentidad:
        """Resuelve una identidad a 'resuelto' / 'ambiguo' / 'sin_candidato' dentro de la empresa."""
        base = {"apellido_csv": apellido_csv, "nombre_csv": nombre_csv}
        emp = str(empresa_id)

        equiv = self._repo.find_equivalencia(emp, tx.normalizar_campo(apellido_csv), tx.normalizar_campo(nombre_csv))
        if equiv:
            return ResolucionIdentidad(**base, estado="resuelto", empleado_id=equiv, fuente="equivalencia")

        todos = self._repo.find_empleados_empresa(emp)
        objetivo = tx.clave_identidad(apellido_csv, nombre_csv)
        candidatos = [c for c in todos if tx.clave_identidad(c.apellido, c.nombre) == objetivo]
        if not candidatos:
            return ResolucionIdentidad(**base, estado="sin_candidato",
                                       motivo="ningún colaborador con ese nombre en la empresa")

        by_id = {str(c.empleado_id): c for c in todos}
        for c in candidatos:
            self._anotar_superior(c, by_id, apellido_superior, nombre_superior)

        if len(candidatos) > 1:
            return ResolucionIdentidad(**base, estado="ambiguo", candidatos=candidatos,
                                       motivo="más de un empleado con ese nombre")

        unico = candidatos[0]
        if unico.superior_coincide is False:  # tiene manager conocido y NO coincide con el del CSV
            return ResolucionIdentidad(**base, estado="ambiguo", candidatos=candidatos,
                                       motivo="el nombre coincide pero el superior no")
        # superior coincide, o no es evaluable (candidato sin manager / CSV sin superior)
        return ResolucionIdentidad(**base, estado="resuelto",
                                   empleado_id=unico.empleado_id, fuente="nombre+superior")

    @staticmethod
    def _anotar_superior(c: EmpleadoCandidato, by_id: Dict[str, EmpleadoCandidato],
                         apellido_superior: Optional[str], nombre_superior: Optional[str]) -> None:
        """Completa manager_* y superior_coincide (True/False/None) sobre el candidato."""
        if c.manager_id:
            mgr = by_id.get(str(c.manager_id))
            if mgr:
                c.manager_apellido, c.manager_nombre = mgr.apellido, mgr.nombre
        c.superior_coincide = _superior_coincide(c, apellido_superior, nombre_superior)


def _superior_coincide(c: EmpleadoCandidato, apellido_superior: Optional[str],
                       nombre_superior: Optional[str]) -> Optional[bool]:
    """True/False si se puede comparar; None si no (candidato sin manager, o CSV sin superior)."""
    if not c.manager_id or not c.manager_apellido:
        return None
    if not (apellido_superior or nombre_superior):
        return None
    return tx.clave_identidad(c.manager_apellido, c.manager_nombre or "") == \
        tx.clave_identidad(apellido_superior or "", nombre_superior or "")
