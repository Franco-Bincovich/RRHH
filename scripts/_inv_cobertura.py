"""
LA COLUMNA QUE DECIDE TODO: ¿esta fila se puede probar automáticamente, y si no, por qué?

🔴 EL VEREDICTO SE DERIVA DE LA DEPENDENCIA EXTERNA, NO DE UNA LISTA DE ENDPOINTS. Una lista se
desactualiza en la primera tanda; una regla sobre "sube un archivo", "el path cuelga de la casilla
de Gmail" o "el router está gateado por flag" clasifica sola al endpoint que se agregue mañana.
Por eso `SUBE_ARCHIVO` sale de `route.dependant.body_params` (¿hay un `UploadFile` en la firma?)
y no de escribir a mano cuáles son los imports.

🔴 TRES VEREDICTOS, NO DOS, y el del medio es el que evita la mentira más cara. "Destructivo"
NO es lo mismo que "no automatizable": borrar un cliente sembrado es perfectamente automatizable
—`docs/SEMILLA-SMOKE.md` existe para eso—, lo que no se puede es borrar un cliente de RRHH. Meter
los dos en la misma celda haría que el inventario declare intestables 60 filas que sí se prueban,
y un inventario que exagera lo que no se puede se deja de leer igual que uno que exagera lo que sí.

⚠️ LO QUE ESTA COLUMNA NO DICE: que la prueba EXISTA. Dice si se puede escribir. La única
afirmación sobre cobertura real que este inventario hace hoy es la del smoke de lectura
(`docs/SMOKE-TEST.md`), y está acotada a los GET.
"""
import re
from functools import lru_cache
from typing import NamedTuple, Optional, Set, Tuple

from _inv_backend import _crudo
from _inv_destructivo import es_destructivo

AUTOMATIZABLE = "sí"
CON_RESERVA = "sí, sólo sobre datos sembrados"
NO = "no"


class Veredicto(NamedTuple):
    automatizable: str
    motivo: str


@lru_cache(maxsize=1)
def sube_archivo() -> Set[Tuple[str, str]]:
    """(MÉTODO, path) de las rutas con un `UploadFile` en la firma. Introspección, no lista."""
    todas, _, _ = _crudo()
    out: Set[Tuple[str, str]] = set()
    for clave, route in todas.items():
        tipos = [getattr(f.type_, "__name__", "") for f in route.dependant.body_params]
        if any(t == "UploadFile" for t in tipos):
            out.add(clave)
    return out


@lru_cache(maxsize=1)
def _previews_con_archivo() -> Set[str]:
    """Prefijos de los `/preview` que suben un archivo. Derivados de dónde está el `UploadFile`,
    no de una lista de módulos: el import que se agregue mañana entra solo."""
    return {p[:-len("/preview")] for _m, p in sube_archivo() if p.endswith("/preview")}


def _es_import(path: str) -> bool:
    """El upload de un import, o el `/confirmar` HERMANO de un `/preview` que sube archivo — su
    body es la salida de ese preview, que sólo existe si alguien subió la planilla.

    ⚠️ Es hermandad de path, no "el path dice importación": `GET /api/importacion/
    superiores-pendientes` y su `/resolver` cuelgan del mismo router y NO necesitan ningún
    archivo (son la cola de revisión de la segunda pasada, que se resuelve a mano desde la UI).
    Una regla por prefijo los marcaba intestables siendo dos de los más fáciles de probar.
    """
    if any((m, path) in sube_archivo() for m in ("POST", "PUT", "PATCH")):
        return "/importa" in path
    return path.endswith("/confirmar") and path[:-len("/confirmar")] in _previews_con_archivo()


def veredicto(metodo: str, path: str, solo_con_flag: bool,
              apagada_por_front: Optional[str] = None) -> Veredicto:
    """El veredicto de una fila. El orden de las reglas ES la decisión: la primera que matchea
    gana, y las de arriba son las que impiden que la prueba corra siquiera."""
    if solo_con_flag:
        return Veredicto(NO, "el router no se monta: el módulo está apagado por flag del backend")
    if apagada_por_front:
        return Veredicto(NO, f"pantalla apagada: {apagada_por_front}. El backend sí responde: "
                             "lo que queda sin probar es el recorrido por navegador, no el endpoint")
    if path.startswith("/api/vacantes/casilla") or path.startswith("/api/integraciones/google"):
        return Veredicto(NO, "depende de una casilla de Gmail viva y de un token OAuth vigente")
    if path == "/api/plantillas/enviar":
        return Veredicto(NO, "manda un mail real desde la casilla del sistema; no se puede desenviar")
    # 🔴 NO TODO UPLOAD ES IGUAL, y meterlos en la misma celda declararía intestables cuatro
    # endpoints que sí se prueban. Un adjunto, un logo o un certificado aceptan CUALQUIER archivo:
    # se genera uno de dos kilobytes y listo. Un IMPORT no: parsea columnas con nombre, encoding y
    # separador propios, y de vacaciones/ausencias RRHH todavía no entregó el Excel real, así que
    # el parser ni siquiera está definido. La diferencia es el PREFIJO del path, no el UploadFile.
    if _es_import(path):
        return Veredicto(NO, "necesita el archivo real de RRHH: el parser depende de los nombres "
                             "de columna, el encoding y el separador de SU planilla")
    if (metodo, path) in sube_archivo():
        return Veredicto(AUTOMATIZABLE, "")
    if "zernio" in path or path.endswith("publicar-linkedin"):
        return Veredicto(NO, "depende de un servicio externo (LinkedIn / Zernio)")
    if path.startswith("/api/screening") or path == "/api/reportes/generar" \
            or path.endswith("/anthropic"):
        return Veredicto(NO, "llama a Claude: cuesta plata por request y la respuesta no es "
                             "determinista, así que la aserción no puede ser sobre el contenido")
    destructivo, razon = es_destructivo(metodo, path)
    if destructivo:
        return Veredicto(CON_RESERVA, "sólo sobre las filas sembradas por "
                                      "docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH")
    return Veredicto(AUTOMATIZABLE, "")


