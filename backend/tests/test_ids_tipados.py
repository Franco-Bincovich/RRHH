"""
BARRIDO ESTRUCTURAL — todo campo id tipado `str` en `schemas/` está DECLARADO, con su razón y con
su dirección. Ninguno puede quedarse en el medio.

## Por qué hizo falta

"IDs tipados `UUID`, nunca `str`" es la regla #1 del porteo a asyncpg, y el control que la vigilaba
era un grep: `grep -rn ": str" backend/schemas/ | grep _id`. Ese grep **veía 38 de 92 campos**.

  · `": str"` no matchea `Optional[str]` → **26 campos invisibles**.
  · `grep _id` descarta el `id` pelado: la línea es `    id: str` y no contiene la subcadena
    `_id` → **25 campos más invisibles**, entre ellos los cuatro de `ObjetivoResponse` que la
    auditoría del 19/8 encontró leyendo código.

Es el cuarto control ciego del mes, después de `_validar_columna` (cortaba con `return` al ver
`*`), del barrido de estado que no veía `ESTADOS_EN_PLANTILLA` y del que no veía
`EmpleadoCreate(**campos)`. **El patrón es siempre el mismo: el control busca una FORMA de
escribir la cosa, no la cosa.** Por eso este barrido importa los módulos y mira los modelos.

## 🔴 La distinción que un grep no puede hacer: entrada vs salida

No todos los 92 pesan igual, y tratarlos como una sola bolsa es lo que hace que la lista no se
mire nunca.

  · **salida** (`*Response`, `*Item`, y los row models internos): **NO rompe el porteo.** Se
    llenan desde la base, y el mapper ya castea el `UUID` que devuelve asyncpg a `str`. Es deuda
    cosmética: el tipo miente sobre lo que la columna es, pero nada explota.
  · **entrada** (`*Create`, `*Update`, `*Request`, `*Filtros`): **SÍ rompe.** El valor viaja hacia
    la base, y asyncpg es estricto: un `str` contra una columna `uuid` es un error de query, no
    una coerción silenciosa como la que hacía PostgREST por HTTP.

Hoy son **6 de entrada** (4 reales + 2 ids externos) contra 86 de salida. Esa proporción es la
noticia: el riesgo real de porteo por este concepto es chico y está acotado a cuatro campos, y
hasta que este barrido existió eso no se podía afirmar — sólo se sabía que "había ~30".

## Qué NO hace

**No arregla nada, y no es una lista de tareas con fecha.** Convierte deuda invisible en deuda con
dueño: el día que alguien agregue un `_id: str` nuevo, este test lo obliga a decidir de qué lado
está antes de mergear. Los 92 de hoy se arreglan cuando se decida, no acá.

## Guardas contra el falso verde

`MINIMO_CAMPOS`/`MINIMO_CLASES`: si `inventario()` dejara de importar los módulos o
`model_fields` dejara de resolverse, el conjunto quedaría vacío y **todas las comparaciones
pasarían sin haber comparado nada**. Y `test_ninguna_declaracion_esta_muerta` cierra la
contracara: una entrada que apunta a un campo ya arreglado es ruido que tapa el próximo caso.
"""
from typing import Dict, FrozenSet

from tests._ids_tipados import direccion_de, es_id_str, inventario

# Guardas contra el falso verde. Hoy son 92 campos en 42 clases; los mínimos van holgados para no
# ser ruido cada vez que alguien agrega o arregla uno.
MINIMO_CAMPOS = 80
MINIMO_CLASES = 35


# ── 1 · IDs EXTERNOS — correctos como `str` para siempre, en cualquier dirección ──────────────
# No son UUIDs nuestros: son identificadores que emite un tercero y que nosotros guardamos tal
# cual. Tipearlos `UUID` sería un error, no una mejora — el valor no tiene esa forma.
# Se declaran POR NOMBRE DE CAMPO (no por clave completa) a propósito: el mismo id externo
# aparece en varias clases y la razón es idéntica en todas.
EXTERNOS: Dict[str, str] = {
    "message_id":
        "id de mensaje de Gmail (`AsignarMailRequest`, `IngestaMailItem`, `MailPendienteItem`). "
        "Lo emite Google, tiene formato propio y nunca es un UUID nuestro: es la clave con la que "
        "la ingesta de CVs dedupe contra la casilla.",
    "email_id":
        "ídem message_id, del lado de vacantes (`CandidatoDesdeEmailRequest`, "
        "`EmailCandidatoResponse`). Es el id que devuelve la API de Gmail al listar la casilla.",
    "post_id":
        "id del post publicado en LinkedIn vía Zernio (`PublicarLinkedinResponse`). Lo emite "
        "LinkedIn; el sistema sólo lo guarda para poder linkear el aviso.",
    "linkedin_post_id":
        "la misma id de LinkedIn, persistida en la vacante (`VacanteResponse`). Estaba fuera de "
        "los 'tres de Gmail y LinkedIn' que el checklist declaraba: son CUATRO nombres, no tres.",
}


# ── 2 · ENTRADA — 🔴 lo que SÍ rompe el porteo. Cuatro campos, cada uno con su razón ──────────
DEUDA_ENTRADA: Dict[str, str] = {
    "costo.PresupuestoCreate.area_id":
        "🔴 EL MÁS CARO DE LOS CUATRO: es el único que viaja a un INSERT real de una tabla viva "
        "(`presupuesto_area`). Con asyncpg, un `str` contra la columna `uuid` es error de query. "
        "Se arregla junto con el resto de costos, no suelto: `PresupuestoResponse` lo espeja.",
    "objetivo_filtros.ObjetivosFiltros.responsable_id":
        "va a un WHERE, no a un INSERT, así que rompe la LECTURA y no la escritura. Es parte del "
        "mismo paquete de objetivos que ya tiene declarada la deuda de paginación y auditoría en "
        "docs/DEUDA-TECNICA.md: se toca cuando se toque ese módulo, no antes.",
    "assessment.CampanaCreate.area_id":
        "módulo APAGADO por `ASSESSMENT_ENABLED=false`: el router no se monta, así que hoy no hay "
        "camino por el que este payload llegue a la base. Se arregla si el módulo se enciende — y "
        "esa decisión está antes que este arreglo.",
    "assessment.LinkCreate.empleado_id":
        "ídem CampanaCreate.area_id, mismo módulo apagado y misma condición para arreglarlo.",
}


# ── 3 · SALIDA — deuda cosmética, no rompe el porteo. El inventario completo ──────────────────
# Se listan una por una y no por clase o por módulo: una lista agregada esconde exactamente el
# caso que este barrido existe para hacer visible (un campo nuevo que se cuela en una clase que
# ya estaba declarada). El archivo es un `test_*.py` y está exento del límite de 200 líneas.
DEUDA_SALIDA: FrozenSet[str] = frozenset({
    # adjunto.py — `Adjunto` es el row model interno (repo/service), no un payload de entrada
    "adjunto.Adjunto.empresa_id",
    "adjunto.Adjunto.entidad_id",
    "adjunto.Adjunto.id",
    "adjunto.AdjuntoResponse.entidad_id",
    "adjunto.AdjuntoResponse.id",
    # area.py
    "area.AreaResponse.empresa_id",
    "area.AreaResponse.id",
    "area.AreaResponse.responsable_id",
    # auditoria.py
    "auditoria.AuditLogResponse.empresa_id",
    "auditoria.AuditLogResponse.id",
    "auditoria.AuditLogResponse.registro_id",
    "auditoria.AuditLogResponse.usuario_id",
    # ausencias.py
    "ausencias.AusenciaResponse.area_id",
    "ausencias.AusenciaResponse.empleado_id",
    "ausencias.AusenciaResponse.empresa_id",
    "ausencias.AusenciaResponse.id",
    "ausencias.AusenciaResponse.tipo_id",
    "ausencias.TipoAusenciaResponse.empresa_id",
    "ausencias.TipoAusenciaResponse.id",
    "ausencias.TipoAusenciaResponse.padre_id",
    # candidato.py
    "candidato.CandidatoGrupoResponse.empresa_id",
    "candidato.CandidatoGrupoResponse.id",
    "candidato.CandidatoGrupoResponse.vacante_id",
    "candidato.CandidatoResponse.empresa_id",
    "candidato.CandidatoResponse.id",
    "candidato.CandidatoResponse.vacante_id",
    # capacitacion.py — el módulo de Formación
    "capacitacion.AsignacionResponse.area_id",
    "capacitacion.AsignacionResponse.capacitacion_id",
    "capacitacion.AsignacionResponse.empleado_id",
    "capacitacion.AsignacionResponse.empresa_id",
    "capacitacion.AsignacionResponse.id",
    "capacitacion.CapacitacionResponse.empresa_id",
    "capacitacion.CapacitacionResponse.id",
    # cesion.py
    "cesion.CesionResponse.empleado_id",
    "cesion.CesionResponse.empresa_id",
    "cesion.CesionResponse.id",
    # costo.py
    "costo.NominaResponse.empleado_id",
    "costo.NominaResponse.empresa_id",
    "costo.NominaResponse.id",
    "costo.PresupuestoResponse.area_id",
    "costo.PresupuestoResponse.empresa_id",
    "costo.PresupuestoResponse.id",
    # cv_ingesta.py
    "cv_ingesta.AsignacionResponse.vacante_id",
    # dashboard.py
    "dashboard.HeadcountAreaResponse.area_id",
    # empleado_out.py
    "empleado_out.EmpleadoResponse.area_id",
    "empleado_out.EmpleadoResponse.empresa_id",
    "empleado_out.EmpleadoResponse.id",
    "empleado_out.EmpleadoResponse.manager_id",
    "empleado_out.EmpleadoSeleccionable.id",
    # empresa.py
    "empresa.EmpresaResponse.id",
    # evaluacion_reportes.py
    "evaluacion_reportes.BrechaItem.empleado_id",
    "evaluacion_reportes.EvaluadoListadoItem.empleado_id",
    "evaluacion_reportes.EvaluadoListadoItem.id",
    # inventario.py
    "inventario.AsignacionResponse.empleado_id",
    "inventario.AsignacionResponse.empresa_id",
    "inventario.AsignacionResponse.id",
    "inventario.AsignacionResponse.item_id",
    "inventario.ItemResponse.empresa_id",
    "inventario.ItemResponse.id",
    # objetivo.py — los cuatro que la auditoría del 19/8 encontró leyendo, no grepeando
    "objetivo.ObjetivoResponse.empresa_id",
    "objetivo.ObjetivoResponse.id",
    "objetivo.ObjetivoResponse.parent_id",
    "objetivo.ObjetivoResponse.responsable_id",
    "objetivo.ResponsableItem.id",
    # periodo.py
    "periodo.PeriodoResponse.empresa_id",
    "periodo.PeriodoResponse.id",
    # screening.py
    "screening.CandidatoClasificado.candidato_id",
    # superiores_pendientes.py
    "superiores_pendientes.SuperiorPendienteItem.empleado_id",
    # usuario.py
    "usuario.CrearUsuarioResponse.id",
    # vacaciones.py
    "vacaciones.SaldoVacacionesResponse.empleado_id",
    "vacaciones.SolicitudVacacionesResponse.area_id",
    "vacaciones.SolicitudVacacionesResponse.empleado_id",
    "vacaciones.SolicitudVacacionesResponse.empresa_id",
    "vacaciones.SolicitudVacacionesResponse.id",
    # vacaciones_pendientes.py
    "vacaciones_pendientes.VacacionPendienteResponse.area_id",
    "vacaciones_pendientes.VacacionPendienteResponse.empleado_id",
    "vacaciones_pendientes.VacacionPendienteResponse.empresa_id",
    "vacaciones_pendientes.VacacionPendienteResponse.id",
    # vacante.py
    "vacante.VacanteResponse.area_id",
    "vacante.VacanteResponse.empresa_id",
    "vacante.VacanteResponse.id",
})


def _declarado(campo) -> bool:
    """¿Este campo está cubierto por alguna de las tres declaraciones?"""
    return (
        campo.campo in EXTERNOS
        or campo.clave in DEUDA_ENTRADA
        or campo.clave in DEUDA_SALIDA
    )


# ── Guardas ───────────────────────────────────────────────────────────────────────────────────

def test_la_derivacion_encuentra_algo() -> None:
    """GUARDA CONTRA EL FALSO VERDE: sin esto, un inventario vacío pasaría todos los tests.

    ¿Qué tendría que ser distinto para que falle? Que `inventario()` dejara de importar los
    módulos de `schemas/` (un import roto, un rename del paquete) o que `model_fields` dejara de
    resolverse — que es exactamente cuando los tests de abajo dejan de mirar nada.
    """
    filas = inventario()
    clases = {(f.modulo, f.clase) for f in filas}
    assert len(filas) >= MINIMO_CAMPOS, (
        f"Sólo {len(filas)} campos id tipados str (mínimo {MINIMO_CAMPOS}). La introspección de "
        "schemas/ se rompió: sin esto el barrido pasa en el vacío."
    )
    assert len(clases) >= MINIMO_CLASES, (
        f"Sólo {len(clases)} clases con campos id str (mínimo {MINIMO_CLASES})."
    )


def test_el_detector_de_str_distingue_de_verdad() -> None:
    """ANCLA del detector, con valores literales: si `es_id_str` se rompiera y devolviera siempre
    True (o siempre False), el barrido entero mediría cualquier cosa y seguiría en verde.

    Es el mismo criterio con el que `contrasteTokens.test.ts` ancla la fórmula de contraste con
    blanco/negro antes de medir la paleta real.
    """
    from typing import List, Optional
    from uuid import UUID

    assert es_id_str(str) is True
    assert es_id_str(Optional[str]) is True
    assert es_id_str(List[str]) is True
    assert es_id_str(UUID) is False
    assert es_id_str(Optional[UUID]) is False
    assert es_id_str(int) is False


def test_la_direccion_se_deriva_bien() -> None:
    """ANCLA del clasificador entrada/salida, que es lo que decide la gravedad de cada campo.

    Sin esto, un cambio en `ENTRADA_SUFIJOS` podría mandar los 6 de entrada a la bolsa de salida
    y el barrido seguiría verde habiendo perdido justo la distinción que lo hace útil.
    """
    assert direccion_de("PresupuestoCreate") == "entrada"
    assert direccion_de("EmpleadoUpdate") == "entrada"
    assert direccion_de("AsignarMailRequest") == "entrada"
    assert direccion_de("ObjetivosFiltros") == "entrada"
    assert direccion_de("VacanteResponse") == "salida"
    assert direccion_de("BrechaItem") == "salida"


# ── El barrido, en las dos direcciones ────────────────────────────────────────────────────────

def test_todo_id_str_esta_declarado() -> None:
    """🔴 EL BARRIDO. Ningún campo id tipado `str` puede quedar sin decisión.

    ¿Qué tendría que ser distinto para que falle? Nada del test: falla solo en cuanto alguien
    agrega un `_id: str` (o un `id: str`) nuevo en cualquier schema. Verificado a mano el 19/8
    agregando un campo de prueba y viéndolo rojear.
    """
    huerfanos = sorted(f.clave for f in inventario() if not _declarado(f))
    assert not huerfanos, (
        "Campos id tipados `str` que nadie declaró:\n  "
        + "\n  ".join(huerfanos)
        + "\n\nTipalo `UUID` (es lo correcto salvo que sea un id externo), o declaralo: en "
          "EXTERNOS si lo emite un tercero, en DEUDA_ENTRADA si viaja HACIA la base (y entonces "
          "rompe el porteo), o en DEUDA_SALIDA si sólo sale."
    )


def test_ninguna_declaracion_esta_muerta() -> None:
    """La dirección contraria: una declaración que apunta a un campo que ya no existe.

    No es simetría de adorno. Un campo que se arregló a `UUID` y quedó declarado como deuda hace
    que la lista mienta hacia arriba, y una lista con ruido es una lista que nadie mira — que es
    exactamente cómo se llegó a tener ~30 ids mal tipados sin que nadie los inventariara.

    Molde: la misma guarda de `test_paridad_list_export` sobre `_EXPORTS_SIN_LISTADO`.
    """
    vivas = {f.clave for f in inventario()}
    muertas = sorted((set(DEUDA_ENTRADA) | DEUDA_SALIDA) - vivas)
    assert not muertas, (
        "Declaraciones que apuntan a campos que ya no están tipados `str` (¿se arreglaron?):\n  "
        + "\n  ".join(muertas)
        + "\nSacalas de la lista: una entrada muerta tapa el próximo caso."
    )


def test_no_hay_entrada_nueva_sin_declarar() -> None:
    """🔴 EL CASO QUE MÁS IMPORTA, con mensaje propio: un payload de ENTRADA nuevo mal tipado.

    Lo cubre también el barrido general, pero merece su propia aserción porque la consecuencia es
    distinta: los de salida son cosméticos y éste **rompe la query** contra asyncpg. Si algún día
    alguien silencia el barrido general, este test sigue custodiando lo caro.
    """
    sin_declarar = sorted(
        f.clave for f in inventario()
        if f.direccion == "entrada" and f.campo not in EXTERNOS
        and f.clave not in DEUDA_ENTRADA
    )
    assert not sin_declarar, (
        "🔴 Payload(s) de ENTRADA con id tipado `str` sin declarar:\n  "
        + "\n  ".join(sin_declarar)
        + "\n\nEsto NO es deuda cosmética: el valor viaja hacia la base y asyncpg no coacciona "
          "`str` a `uuid`. Tipalo `UUID` o declaralo en DEUDA_ENTRADA con por qué puede esperar."
    )


def test_las_razones_explican_algo() -> None:
    """La razón es el contenido del inventario, no un campo a completar con cualquier cosa.

    Sin el porqué, la próxima persona borra una entrada porque "no se usa" o la arregla sin
    entender que el id es externo y tipearlo `UUID` lo rompe.
    """
    flojas = sorted(
        k for k, r in list(EXTERNOS.items()) + list(DEUDA_ENTRADA.items())
        if len(r.strip()) < 40
    )
    assert not flojas, f"Estas declaraciones no explican nada: {flojas}"


def test_los_externos_existen_de_verdad() -> None:
    """Un id externo declarado que ya no aparece en ningún schema es ruido.

    Contracara de `EXTERNOS`, que se declara por NOMBRE de campo y por eso no lo cubre
    `test_ninguna_declaracion_esta_muerta` (que compara claves completas).
    """
    nombres_vivos = {f.campo for f in inventario()}
    muertos = sorted(set(EXTERNOS) - nombres_vivos)
    assert not muertos, f"IDs externos declarados que ya no existen en schemas/: {muertos}"
