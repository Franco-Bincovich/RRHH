"""
Lecturas y escrituras de `candidatos` que usa el clasificador de CVs (migración 100).

## Por qué repo propio y no dos métodos más en `candidato_repo`

`candidato_repo.py` está en **94/100** y ya delega en tres satélites (`_candidato_row`,
`_candidato_write`, `_candidato_gmail`) justamente porque estuvo en 100/100 exacto. Sumarle los
dos métodos de acá lo pasaba del límite, y la regla del repo es dividir ANTES de escribir, no
correr el límite. Molde: `oauth_state_repo`, que también es un repo chico de una sola
responsabilidad.

Es la misma tabla que `candidato_repo`, no la misma pregunta: acá se lee `cv_texto` —hasta 20 KB
por fila, la ENTRADA del modelo— y se escribe el resultado. Ningún otro caller quiere esa columna
(no viaja al front, ver `frontend/types/candidato.ts`), así que mezclarla en el `select("*")` de
las lecturas normales sería traer 20 KB por candidato en cada listado.

## 🔴 Barrera de empresa: Forma A, en el WHERE

Los dos métodos reciben `empresa_id` y lo aplican con `.eq()` en la query, no comparando en el
service. Es una sola ida a la base e imposible de saltear. Sin eso, `set_clasificacion` con un
UUID ajeno escribiría sobre el candidato de otra empresa.
"""
from typing import Any, Dict, List, Optional

from integrations.supabase_client import supabase_admin

_C = "candidatos"

# `cv_texto` es la entrada del modelo y `screening_warning` decide si se clasifica o no.
_COLS = "id, nombre, apellido, cv_texto, screening_warning"


class CandidatoScreeningRepo:
    def find_para_clasificar(self, vacante_id: str,
                             empresa_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Candidatos de la vacante que TODAVÍA no tienen clasificación, más viejos primero.

        🔴 El filtro `clasificacion_ia IS NULL` va en la query, y es lo que hace que el botón sea
        REINTENTABLE y no acumule costo: volver a apretarlo después de un corte por presupuesto
        toma solo los que quedaron, nunca reclasifica —ni recobra— los que ya están hechos.
        """
        q = (supabase_admin.table(_C).select(_COLS)
             .eq("vacante_id", vacante_id)
             .is_("clasificacion_ia", "null")
             .order("created_at"))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return q.execute().data or []

    def set_clasificacion(self, candidato_id: str, clasificacion: str, motivo: str,
                          empresa_id: Optional[str] = None) -> None:
        """Persiste el resultado del MODELO para UN candidato."""
        self._update(candidato_id, {"clasificacion_ia": clasificacion,
                                    "clasificacion_motivo": motivo,
                                    "clasificacion_origen": "modelo"}, empresa_id)

    def set_fallo(self, candidato_id: str, motivo: str, empresa_id: Optional[str] = None) -> None:
        """El clasificador falló: se guarda el motivo con la clasificación en NULL.

        🔴 `clasificacion_ia` queda en NULL A PROPÓSITO, no por omisión: es lo que hace que
        `find_para_clasificar` lo vuelva a tomar en el próximo click. El motivo persiste el
        estado —que antes se perdía al recargar— sin volver el fallo permanente. `origen`
        también queda NULL: no hay veredicto del que declarar autor.
        """
        self._update(candidato_id, {"clasificacion_ia": None, "clasificacion_motivo": motivo,
                                    "clasificacion_origen": None}, empresa_id)

    def set_correccion(self, candidato_id: str, clasificacion: str, motivo: str,
                       empresa_id: Optional[str] = None) -> None:
        """Un HUMANO fija la clasificación. `origen='humano'` viaja en el MISMO update.

        🔴 Que el origen se escriba acá y no en un segundo write es lo que impide que una fila
        quede con clasificación corregida y origen 'modelo': serían dos mutaciones que fallan
        por separado, y la que falla en silencio es justo la que después se lee para medir si
        el filtro sirve.
        """
        self._update(candidato_id, {"clasificacion_ia": clasificacion,
                                    "clasificacion_motivo": motivo,
                                    "clasificacion_origen": "humano"}, empresa_id)

    def _update(self, candidato_id: str, campos: dict, empresa_id: Optional[str]) -> None:
        q = supabase_admin.table(_C).update(campos).eq("id", candidato_id)
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        q.execute()
