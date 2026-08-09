"""
La clasificación de UN candidato dentro de una corrida: saltear, clasificar o registrar el fallo.

Extraído de `cv_screening_service.py`, que estaba en **149/150** y no admitía la persistencia del
fallo del clasificador. El corte es por unidad de trabajo: el service de arriba orquesta el lote
(presupuesto, tope, resumen, auditoría) y acá vive lo que le pasa a un candidato.

El movimiento fue VERBATIM salvo por lo que la sesión vino a agregar, que está marcado abajo.

## ⚠️ ESTE MÓDULO ESCRIBE Y NO AUDITA, Y ES LA REGLA DEL REPO

UN EVENTO POR LOTE, NUNCA UNO POR CV: el evento (`screening_cv`) lo emite `_resumen` en
`cv_screening_service`, una vez por corrida y con los cuatro conteos. Emitirlo acá convertiría un
click de RRHH en N filas de `auditoria`. Mismo criterio que `ingesta_cv_gmail` e
`importacion_costos`.

🚩 Al extraer esto de `cv_screening_service` la escritura salió del alcance de
`test_auditoria_coherente` —que solo mira módulos que YA emiten eventos—, así que la excepción
declarada allá se borró. La regla no cambió; lo que se perdió es que un barrido la vigile. La
corrección manual, que sí es individual, audita en `screening_correccion_service`.

## 🔴 EL FALLO DEL CLASIFICADOR SE PERSISTE, Y NO EN `screening_warning`

Antes, un fallo del modelo dejaba `clasificacion_ia = NULL` y nada más: el conteo de errores
vivía solo en la respuesta del botón, así que **al recargar la pantalla un candidato que falló
era indistinguible de uno que nunca pasó por el clasificador**. Son dos estados distintos y
piden acciones distintas (reintentar vs. correr el botón por primera vez).

Se persiste en **`clasificacion_motivo` con `clasificacion_ia` en NULL**, y NO en
`screening_warning`, por dos razones:

  1. **`screening_warning` GATEA EL SALTEO.** La guarda de abajo saltea a todo candidato que lo
     tenga, sin gastar llamada. Escribir el fallo ahí volvería el fallo **permanente e
     irreintentable**: el próximo click saltearía justo a los que hay que reintentar. Una sola
     columna no puede manejar dos decisiones opuestas.
  2. **Significan cosas distintas.** `screening_warning` es "el ARCHIVO no se pudo leer" y la
     acción es pedirle otro CV al candidato. Un fallo del clasificador es "el archivo está bien,
     la llamada falló" y la acción es volver a apretar el botón.

Con `clasificacion_ia` en NULL, `find_para_clasificar` lo sigue tomando: el reintento funciona
solo, sin ninguna regla nueva. Y los dos no pueden colisionar nunca — un candidato con
`screening_warning` no llega jamás a la llamada.
"""
from typing import Optional

from schemas.screening import CandidatoClasificado
from services import _cv_clasificador as clasificador
from utils.logger import logger

# Lo que se guarda en `clasificacion_motivo` cuando la llamada falla. Prefijo fijo para que la
# pantalla y el export puedan distinguirlo de un motivo real sin depender de la clasificación.
PREFIJO_FALLO = "No se pudo clasificar"


def clasificar_uno(fila: dict, vacante, criterio, empresa: Optional[str],
                   *, repo, cliente=None) -> CandidatoClasificado:
    """Un candidato. Cualquier fallo suyo queda contenido acá: el lote sigue."""
    base = {"candidato_id": str(fila["id"]),
            "nombre": f"{fila.get('nombre', '')} {fila.get('apellido', '')}".strip()}
    # 🔴 Un CV con `screening_warning` NO se clasifica y NO gasta llamada: el clasificador no
    # tendría qué leer. No es un error del lote — es un candidato que va a revisión manual, y
    # el warning ya dice qué pedirle (la contraseña, el CV en otro formato).
    if fila.get("screening_warning") or not (fila.get("cv_texto") or "").strip():
        return CandidatoClasificado(**base, error=None)
    try:
        r = clasificador.clasificar(fila["cv_texto"], vacante, criterio, cliente=cliente)
    except Exception as exc:  # noqa: BLE001 — ver el docstring
        logger.error("Fallo al clasificar un CV",
                     extra={"candidato_id": base["candidato_id"], "error": str(exc)})
        # Ver el encabezado: el motivo se persiste con la clasificación en NULL, así el estado
        # sobrevive a un F5 y el candidato sigue siendo reintentable.
        repo.set_fallo(base["candidato_id"], f"{PREFIJO_FALLO}: {exc}", empresa)
        return CandidatoClasificado(**base, error=str(exc))
    repo.set_clasificacion(base["candidato_id"], r.clasificacion, r.motivo, empresa)
    return CandidatoClasificado(**base, clasificacion=r.clasificacion, motivo=r.motivo)
