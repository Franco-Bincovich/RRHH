"""
Helper del import de nómina: engancha "Apellido Superior" + "Nombre Superior" con el matcheo.

Molde: `_nomina_proyectos` / `_nomina_cesiones` — un colaborador que el service construye en
`__init__` y usa en una línea. El MATCHEO en sí no vive acá: vive en `_superiores_matcher`,
compartido con el botón "resolver pendientes", para que no haya dos resoluciones que diverjan.
Acá queda lo que es propio del import: qué se anota, cuándo, y qué se persiste después.

🔴 CORRE EN UNA SEGUNDA PASADA, DESPUÉS DEL LOOP — NO fila por fila. Por qué:
el jefe puede estar en una fila POSTERIOR a la de su subordinado. En el archivo real el único
jefe presente (Libertelli, 13 subordinados) está en la fila 11, o sea que 10 de sus subordinados
se procesan ANTES que él. Resolviendo dentro del loop, esos 10 quedarían sin superior y los 3
posteriores sí lo tendrían: un resultado que depende del ORDEN DE LAS FILAS DEL EXCEL, que es la
clase de bug que después nadie reproduce. Con la segunda pasada, para cuando se resuelve, todo el
archivo ya está escrito y el orden deja de importar.

🔴 SOLO SOBRE FILAS EFECTIVAMENTE PROCESADAS. `registrar` se llama desde `_procesar_fila`, o sea
únicamente para filas que SE ESCRIBIERON. Si el presupuesto de tiempo corta el import a la mitad
(`LoteNomina.filas_con_margen`), las filas que no se procesaron nunca se registraron y no tienen
superior que resolver — resolverlo sería escribir sobre datos que no entraron. El reintento las
procesa y las registra entonces.

## Lo que no se resuelve NO SE PIERDE
Los pendientes se PERSISTEN en `empleado_superior_pendiente` (migración 086) además de salir en
el resultado del import. Es lo que permite que el día que RRHH dé de alta al jefe que faltaba, un
botón lo resuelva sin re-subir el CSV — que es el caso real: 5 de los 6 jefes del archivo no están
cargados como empleados. Y lo que SÍ se resuelve se borra de esa tabla: un pendiente resuelto en
un re-import deja de ser pendiente.
"""
from typing import List, Optional, Tuple

from repositories.empleado_repo import EmpleadoRepo
from repositories.empleado_superior_pendiente_repo import EmpleadoSuperiorPendienteRepo
from schemas.importacion_nomina_empleados import SuperiorPendiente
from services import _superiores_matcher as matcher
from utils.logger import logger


class NominaSuperiores:
    def __init__(self, repo: Optional[EmpleadoRepo] = None,
                 pendientes_repo: Optional[EmpleadoSuperiorPendienteRepo] = None) -> None:
        self._repo = repo or EmpleadoRepo()
        self._pendientes_repo = pendientes_repo or EmpleadoSuperiorPendienteRepo()
        self._anotados: List[dict] = []   # una entrada por fila escrita CON superior en el CSV

    def registrar(self, fila: int, empleado_id: str, empresa_id: str, f: dict) -> None:
        """Anota el superior CRUDO de una fila ya escrita. No resuelve ni consulta nada.

        Una fila sin superior en el CSV no se anota: no hay nada pendiente que reportar (es
        "sin jefe", no "no lo encontramos").

        Args:
            fila: nº de fila del CSV (el encabezado es la 1), para el reporte de pendientes.
            empleado_id: el empleado que el import acaba de crear o actualizar.
            empresa_id: su empresa (la que el import acaba de escribir, no la del header).
            f: la fila ya parseada por `tx.parsear_fila`.
        """
        apellido, nombre = f.get("_superior_apellido"), f.get("_superior_nombre")
        if not (apellido or nombre):
            return
        self._anotados.append({
            "fila": fila, "empleado_id": str(empleado_id), "empresa_id": str(empresa_id),
            "empleado": f"{f['apellido']}, {f['nombre']}",
            "apellido_csv": apellido, "nombre_csv": nombre,
            "superior": ", ".join(x for x in (apellido, nombre) if x),
            "clave": matcher.clave(apellido, nombre),
        })

    def resolver(self) -> Tuple[int, List[SuperiorPendiente]]:
        """Segunda pasada: resuelve todos los superiores anotados, escribe y persiste el resto.

        Returns:
            `(resueltos, pendientes)` — el conteo de `manager_id` escritos y el detalle de los que
            quedaron sin resolver, con motivo, para el reporte que ve quien importó.
        """
        if not self._anotados:
            return 0, []

        resueltos, pendientes = matcher.resolver(self._anotados, self._repo)
        self._persistir(resueltos, pendientes)
        return len(resueltos), [SuperiorPendiente(fila=p["fila"], empleado=p["empleado"],
                                                  superior=p["superior"], motivo=p["motivo"])
                                for p in pendientes]

    def _persistir(self, resueltos: List[str], pendientes: List[dict]) -> None:
        """Guarda los pendientes y limpia los que se resolvieron. Best-effort: no rompe el import.

        El borrado de los resueltos importa tanto como el alta de los pendientes: un empleado que
        quedó pendiente en un import anterior y AHORA se resolvió tiene que salir de la tabla, o
        el botón lo seguiría ofreciendo para siempre.

        Si esto falla, el import ya hizo lo suyo —los empleados están cargados y los `manager_id`
        escritos— y el resultado que ve el usuario igual lista los pendientes. Lo único que se
        pierde es poder resolverlos después sin re-subir el archivo. No justifica tumbar el lote.
        """
        try:
            self._pendientes_repo.borrar_muchos(resueltos)
            self._pendientes_repo.upsert_muchos([{
                "empleado_id": p["empleado_id"], "empresa_id": p["empresa_id"],
                "apellido_csv": p["apellido_csv"], "nombre_csv": p["nombre_csv"],
                "motivo": p["motivo"],
            } for p in pendientes])
        except Exception as exc:  # noqa: BLE001 — el import ya está hecho; esto es la cola
            logger.warning("No se pudieron persistir los superiores pendientes",
                           extra={"pendientes": len(pendientes), "error": str(exc)})
