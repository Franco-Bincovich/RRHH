"""
El pool de áreas ya usadas en objetivos, para el desplegable del filtro.

🔴 POR QUÉ NO SE REUSA `EmpleadoRolesRepo.get_valores_conocidos`, QUE HACE "LO MISMO".
El mecanismo es el mismo —traer una columna, aplanar, deduplicar, ordenar— pero la
implementación está atada a `empleados` en tres puntos y tocarla tiene dos costos declarados:

  · `EmpleadoRolesRepo._TABLE = "empleados"` es constante de MÓDULO, y `get_valores_conocidos`
    hace `.select(campo)` sobre ella. Parametrizar la tabla convierte un repo de una entidad en
    un repo genérico de dos.
  · `tests/test_selects_repos.py:100` declara ese archivo con `(1, "select(campo): UNA columna de
    la whitelist CAMPOS_AUTOCOMPLETABLES")` y **el barrido cuenta selects dinámicos por archivo**:
    un segundo lo rojea. Y `tests/test_critical_flows.py:246` afirma que
    `CAMPOS_AUTOCOMPLETABLES` tiene exactamente 9 campos.

O sea: reusar costaba dos tests estructurales y un repo más genérico de lo que nadie pidió, para
ahorrar quince líneas. Se escribe aparte, y las dos implementaciones quedan simples.

🔴 Y LA DIFERENCIA DE FONDO, QUE ES LA QUE JUSTIFICA QUE ESTE ARCHIVO EXISTA: allá la columna es
un `text` y el "pool" son sus valores distintos. Acá es un **`text[]`**, así que el pool sale de
APLANAR los arrays — y eso es exactamente lo que se ganó con la migración 119. Con la columna en
texto, una celda "Sistemas; Legales" habría entrado al desplegable como UNA opción: el selector
habría ofrecido COMBINACIONES en vez de áreas, y filtrar por "Legales" no habría estado
disponible nunca. Es el mismo argumento que el del filtro, del otro lado de la pantalla.

El molde del aplanado es `EmpleadoRolesRepo.get_roles_conocidos`, que ya hace esto sobre
`empleados.roles` (el otro `text[]` del modelo): `unnest` no es expresable vía PostgREST, así que
se traen las listas y se aplanan en Python. Aceptable por volumen — `objetivos` es el tablero de
un equipo de 3 personas, no el padrón.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

_T = "objetivos"


class ObjetivoAreasRepo:
    def get_areas_conocidas(self, empresa_id: Optional[UUID] = None) -> List[str]:
        """Áreas distintas ya usadas, ordenadas. None = consolidado (todas las empresas).

        🔴 ACOTA POR EMPRESA, al revés que el pool de `empleados`, que es compartido A PROPÓSITO.
        La diferencia es para qué sirve cada uno: aquél alimenta el AUTOCOMPLETADO de un
        formulario, donde ofrecer un valor que otra empresa ya escribió es justamente lo que evita
        que se inventen tres grafías del mismo sector. Éste alimenta el DESPLEGABLE DE UN FILTRO,
        y un filtro que ofrece opciones que no pueden dar resultado en la vista actual es un
        filtro que devuelve vacío sin explicar por qué. El desplegable tiene que ofrecer lo que
        esta vista puede encontrar.
        ⚠️ Si algún día el FORMULARIO quiere sugerir áreas al escribir, eso pide el pool global —
        o sea otro parámetro, no cambiarle la semántica a éste.

        Ordena con `casefold` y no con el orden de bytes: sin eso, "legales" cae después de
        "Sistemas" y el desplegable se lee al azar. **No deduplica por mayúsculas**: "Sistemas" y
        "sistemas" son dos strings distintos en la base y el filtro los distingue, así que
        colapsarlos acá ofrecería una opción que encuentra la mitad de las filas.

        Args:
            empresa_id: empresa del request. None = consolidado, no restringe.

        Returns:
            Las áreas distintas, sin vacíos, ordenadas alfabéticamente sin distinguir mayúsculas.
        """
        q = supabase_admin.table(_T).select("areas_involucradas")
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        filas = q.execute().data or []
        # 🔴 EL DOBLE `for` ES EL APLANADO, y es todo el punto del módulo: se itera CADA ELEMENTO
        # de cada array, no cada fila. Un `.add(fila["areas_involucradas"])` metería la lista
        # entera y el desplegable ofrecería combinaciones.
        # `or []` porque la columna es NOT NULL DEFAULT '{}' pero un select sobre una fila vieja
        # de un entorno sin la migración devolvería None: sin áreas no aporta nada al pool.
        unicas = {
            area.strip()
            for fila in filas
            for area in (fila.get("areas_involucradas") or [])
            if area and area.strip()
        }
        return sorted(unicas, key=str.casefold)
