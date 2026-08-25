"""
Plantillas de mail (migración 087).

🔴 LA LECTURA RESUELVE `COALESCE(la de mi empresa, la global)` — mismo patrón que
`configuracion_repo` con `parametros_empresa` (migración 085), y por el mismo motivo: se siembran
las plantillas base UNA vez con `empresa_id NULL` y cada empresa pisa solo las que quiera cambiar.

⚠️ El fallback es POR CLAVE, no por tabla: una empresa puede tener su propia "bienvenida" y usar
la global de "aviso_vacaciones" al mismo tiempo. Resolverlo con un "si la empresa tiene alguna
plantilla, usar solo las suyas" —que es como funciona la escala de vacaciones de la 085— sería
incorrecto acá: allá la escala es UNA LISTA que se reemplaza entera, y esto son plantillas
independientes entre sí.
"""
from typing import List, Optional
from uuid import UUID

from integrations.supabase_client import supabase_admin

_TABLE = "plantillas_mail"


class PlantillaMailRepo:
    def find(self, clave: str, empresa_id: Optional[UUID] = None) -> Optional[dict]:
        """La plantilla activa de `clave`: la de la empresa si existe, si no la global.

        Dos queries y no un `or_()` con ordenamiento: la precedencia queda explícita en el código
        en vez de escondida en un `order` que alguien puede "simplificar" sin notar que ahí vivía
        la regla. Y la segunda solo corre si la primera no encontró nada, así que el caso normal
        —empresa con plantilla propia— paga una sola.
        """
        if empresa_id:
            propia = (supabase_admin.table(_TABLE).select("*")
                      .eq("clave", clave).eq("empresa_id", str(empresa_id)).eq("activa", True)
                      .maybe_single().execute())
            if propia and propia.data:
                return propia.data
        glob = (supabase_admin.table(_TABLE).select("*")
                .eq("clave", clave).is_("empresa_id", "null").eq("activa", True)
                .maybe_single().execute())
        return glob.data if glob else None

    def find_by_id(self, id_: UUID) -> Optional[dict]:
        """La plantilla de ese id, o None.

        🔑 NO se resuelve con `find(clave, empresa_id)`: aquélla busca por CLAVE y cae a la
        global si la empresa no tiene la suya, así que al editar una propia devolvería la GLOBAL
        como "estado anterior" y el diff de auditoría mostraría cambios que nadie hizo. El upsert
        va por `id`, y el prior tiene que salir del mismo id."""
        res = supabase_admin.table(_TABLE).select("*").eq("id", str(id_)).maybe_single().execute()
        return res.data if (res and res.data) else None

    def listar(self, empresa_id: Optional[UUID] = None) -> List[dict]:
        """Las plantillas visibles para una empresa: las suyas + las globales que no pisó.

        El dedup por clave se hace en Python y no en SQL: son unas pocas decenas de filas, y un
        `DISTINCT ON` acá sería una query que nadie puede leer para ahorrar nada."""
        q = supabase_admin.table(_TABLE).select("*").order("clave")
        if empresa_id:
            q = q.or_(f"empresa_id.eq.{empresa_id},empresa_id.is.null")
        filas = q.execute().data or []
        por_clave: dict = {}
        for f in filas:
            # La propia (empresa_id no nulo) gana sobre la global, sin importar el orden que
            # devuelva la query: se pisa solo si la que llega tiene empresa.
            if f["clave"] not in por_clave or f.get("empresa_id"):
                por_clave[f["clave"]] = f
        return list(por_clave.values())

    def guardar(self, fila: dict) -> Optional[dict]:
        """Crea o actualiza una plantilla. El upsert va por `id` cuando ya existe.

        No usa `on_conflict` sobre (empresa_id, clave): esa unicidad la garantizan DOS índices
        únicos PARCIALES (uno para las de empresa y otro para las globales, porque en SQL
        NULL <> NULL), y PostgREST no puede apuntar `on_conflict` a un índice parcial.
        """
        res = supabase_admin.table(_TABLE).upsert(fila).execute()
        return (res.data or [None])[0]

    def borrar(self, id_: UUID, empresa_id: Optional[UUID] = None) -> Optional[dict]:
        """Borra una plantilla DE LA EMPRESA y DEVUELVE LA FILA BORRADA (None si no borró nada).
        Con `empresa_id` provisto nunca toca una global: borrar la global desde una empresa la
        sacaría para todas las demás.

        🔑 DEVUELVE LA FILA Y NO UN BOOL: `plantillas_mail` no tiene versionado, así que el
        cuerpo que RRHH escribió no sobrevive en ningún otro lado — el evento de auditoría de la
        baja es el único respaldo. PostgREST ya retorna lo borrado en `.data`, así que la foto
        sale gratis y sin ventana entre leer y borrar. Sigue siendo falsy cuando no borra nada,
        que es como lo lee el service."""
        q = supabase_admin.table(_TABLE).delete().eq("id", str(id_))
        if empresa_id:
            q = q.eq("empresa_id", str(empresa_id))
        return (q.execute().data or [None])[0]
