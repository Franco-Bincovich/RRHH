"""
Alta de un ÁREA ENTERA a un proyecto — sin red.

  1. Un área con varios empleados: se crean todas las asignaciones.
  2. 🔴 Un área con la mitad ya asignada: las nuevas en `asignados`, las viejas en
     `ya_asignados`, CERO en `errores`.
  3. Un área vacía: mensaje propio, no un 200 mudo.
  4. 🔴 Un área de OTRA empresa: 404 de `ensure_area_valida`, NO una lista vacía silenciosa.
  5. 🔴 Modo consolidado: asignar un área de B a un proyecto de A funciona — es el cruce que
     `empleado_empresa_id` existe para soportar.
  6. Un empleado en baja va a `errores`, no a `ya_asignados`.
  7. Una asignación con horas cargadas no se toca.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

🔴 EL PUNTO MÁS IMPORTANTE: **EL FAKE MODELA DOS EMPRESAS.** En producción hay UNA SOLA, y las 9
áreas son todas suyas: el caso cruzado —que es el que la barrera compuesta viene a resolver— no
existe en los datos reales y **vive solo acá hasta que haya una segunda empresa**. Un fake de una
empresa no podría desmentir nada: "validé el área contra el header" y "no validé nada" darían el
mismo verde.

  · `_Areas.find_by_id` HONRA `empresa_id` (devuelve None si no coincide) → sin eso, (4) pasa con
    la barrera puesta o sacada. Es el caso #1 de la regla del repo.
  · `_empleados_de_area` REGISTRA con qué `empresa_id` se lo llamó → es lo único que distingue
    "se resolvió sin filtro" de "se resolvió con filtro y por casualidad dio lo mismo". Sin esa
    captura, el filtro redundante-y-silencioso volvería sin que ningún test se entere.
  · `_asignar_uno` levanta `ASIGNACION_DUPLICADA` solo para los ya asignados y `EMPLEADO_INACTIVO`
    solo para los de baja: dos AppError DISTINTOS. Si levantara el mismo, (2) y (6) no podrían
    distinguirse y la clasificación en tres grupos sería indemostrable.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import services._asignaciones_bulk as mod
from schemas.proyectos import AsignacionAreaCreate, AsignacionBulkCreate, AsignacionResponse
from services.asignaciones_service import AsignacionesService
from utils.errors import AppError

EMPRESA_A, EMPRESA_B = uuid4(), uuid4()
PROYECTO_A = uuid4()          # proyecto de la empresa A
AREA_A, AREA_B, AREA_VACIA = uuid4(), uuid4(), uuid4()

# Empleados: 3 en el área de A (uno ya asignado, uno de baja) y 2 en el área de B.
E1, E2, E3 = (str(UUID(int=i)) for i in (1, 2, 3))      # área A
B1, B2 = (str(UUID(int=i)) for i in (11, 12))           # área B


class _Proyectos:
    """HONRA empresa_id: el proyecto de A no se alcanza con el header de B."""

    def find_by_id(self, id, empresa_id=None):
        if str(id) != str(PROYECTO_A):
            return None
        if empresa_id and str(empresa_id) != str(EMPRESA_A):
            return None
        return SimpleNamespace(id=str(id), empresa_id=str(EMPRESA_A))


class _Areas:
    """🔴 HONRA empresa_id. Sin esto, el test del área ajena pasaría con la barrera sacada."""

    _DE = {str(AREA_A): EMPRESA_A, str(AREA_B): EMPRESA_B, str(AREA_VACIA): EMPRESA_A}

    def find_by_id(self, id, empresa_id=None):
        duena = self._DE.get(str(id))
        if not duena or (empresa_id and str(duena) != str(empresa_id)):
            return None
        return SimpleNamespace(id=str(id), empresa_id=str(duena))


class _Asignador:
    """Reemplaza a `_asignar_uno`. Levanta DOS AppError distintos: sin esa diferencia, la
    clasificación en tres grupos no se podría demostrar."""

    def __init__(self, ya_asignados=(), de_baja=()) -> None:
        self._ya = {str(e) for e in ya_asignados}
        self._baja = {str(e) for e in de_baja}
        self.creadas: list = []

    def __call__(self, proyecto_id, empleado_id, rol, valor_hora, fecha_desde, fecha_hasta):
        eid = str(empleado_id)
        if eid in self._ya:
            raise AppError("El empleado ya está asignado a este proyecto", "ASIGNACION_DUPLICADA", 409)
        if eid in self._baja:
            raise AppError("No se puede asignar un empleado dado de baja", "EMPLEADO_INACTIVO", 422)
        self.creadas.append(eid)
        # Se devuelve el schema REAL y no un doble suelto: el service arma un
        # AsignacionBulkResult, así que un SimpleNamespace ni llegaría a la aserción.
        # 🔑 `empleado_empresa_id` es la del EMPLEADO, no la del proyecto — es la columna que
        # hace posible el cruce entre empresas del test de modo consolidado.
        return AsignacionResponse.model_validate({
            "id": str(UUID(int=abs(hash(eid)) % (2**128))), "proyecto_id": str(proyecto_id),
            "empleado_id": eid, "empleado_empresa_id": str(self._empresa_de(eid)),
            "rol": rol, "valor_hora": valor_hora, "activo": True,
            "created_at": "2026-01-01T00:00:00Z"})

    @staticmethod
    def _empresa_de(eid: str):
        """Los E* son de la empresa A y los B* de la B, igual que sus áreas."""
        return EMPRESA_B if eid in {B1, B2} else EMPRESA_A


class _Empleados:
    """Resuelve los empleados de un área y REGISTRA con qué empresa se lo llamó.

    Esa captura es lo único que distingue "se resolvió sin filtro de empresa" de "se resolvió
    con filtro y por casualidad dio el mismo resultado" — que con una sola empresa en producción
    es indistinguible en los datos reales."""

    _DE = {str(AREA_A): [E1, E2, E3], str(AREA_B): [B1, B2], str(AREA_VACIA): []}

    def __init__(self) -> None:
        self.empresas_recibidas: list = []

    def __call__(self, area_id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        return list(self._DE.get(str(area_id), []))


def _armar(monkeypatch, *, ya_asignados=(), de_baja=()):
    empleados = _Empleados()
    monkeypatch.setattr(mod, "empleados_de_area", empleados)
    asignador = _Asignador(ya_asignados, de_baja)
    svc = AsignacionesService(proyectos_repo=_Proyectos(), areas_repo=_Areas())
    svc._asignar_uno = asignador          # el único colaborador que no entra por constructor
    return svc, asignador, empleados


def _pedido(area_id=AREA_A) -> AsignacionAreaCreate:
    return AsignacionAreaCreate(area_id=area_id, rol="Analista", valor_hora=0)


def _ids(grupo) -> set:
    return {str(g.empleado_id) for g in grupo}


# ── 1. El caso feliz ──────────────────────────────────────────────────────────

def test_un_area_con_varios_crea_todas_las_asignaciones(monkeypatch) -> None:
    svc, asignador, _ = _armar(monkeypatch)
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert len(out.asignados) == 3 and out.ya_asignados == [] and out.errores == []
    assert set(asignador.creadas) == {E1, E2, E3}


def test_los_datos_compartidos_viajan_a_cada_asignacion(monkeypatch) -> None:
    """rol/valor_hora se piden UNA vez para todos (el caso particular se ajusta con el PUT)."""
    svc, _, _ = _armar(monkeypatch)
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert all(a.rol == "Analista" for a in out.asignados)


# ── 2. 🔴 La mitad ya asignada ────────────────────────────────────────────────

def test_los_ya_asignados_NO_van_a_errores(monkeypatch) -> None:
    """🔴 EL MOTIVO DEL GRUPO NUEVO. Asignando un área entera lo normal es que la mitad ya esté;
    reportarlos como errores se lee como un fallo masivo.

    Para que falle: borrar el `if exc.code == "ASIGNACION_DUPLICADA"` de `clasificar` — todo
    volvería a caer en `errores`, que es el estado anterior a este commit."""
    svc, asignador, _ = _armar(monkeypatch, ya_asignados=[E1, E2])
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert _ids(out.asignados) == {E3}
    assert _ids(out.ya_asignados) == {E1, E2}
    assert out.errores == [], "un duplicado se reportó como error"
    assert asignador.creadas == [E3], "se reintentó crear una asignación que ya existía"


def test_un_area_entera_ya_asignada_no_es_un_fallo(monkeypatch) -> None:
    """El caso extremo: reasignar la misma área dos veces. Cero creadas, cero errores."""
    svc, _, _ = _armar(monkeypatch, ya_asignados=[E1, E2, E3])
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert (out.asignados, out.errores) == ([], [])
    assert len(out.ya_asignados) == 3


# ── 3. Área vacía ─────────────────────────────────────────────────────────────

def test_un_area_vacia_da_un_mensaje_propio(monkeypatch) -> None:
    """🔴 No un 200 con tres listas vacías: eso se lee como "no hizo nada" o como un fallo
    silencioso, cuando es un dato faltante que el usuario puede arreglar."""
    svc, asignador, _ = _armar(monkeypatch)
    with pytest.raises(AppError) as exc:
        svc.asignar_area(PROYECTO_A, _pedido(AREA_VACIA), EMPRESA_A)
    assert exc.value.code == "AREA_SIN_EMPLEADOS" and exc.value.status_code == 422
    assert "área no tiene colaboradores" in exc.value.message
    assert asignador.creadas == []


# ── 4. 🔴 Área de otra empresa ────────────────────────────────────────────────

def test_un_area_de_OTRA_empresa_es_404_y_no_una_lista_vacia(monkeypatch) -> None:
    """🔴 LA RAZÓN DE LA BARRERA COMPUESTA. Si en vez de validar el área se le pasara el
    `empresa_id` a `empleados_de_area`, esto devolvería una LISTA VACÍA y el endpoint
    respondería "0 asignados, 0 errores" sin decir nada — el patrón de filtro que falla en
    silencio que este repo ya corrigió dos veces.

    Para que falle: sacar el `ensure_area_valida`. Sin él, el área de B pasaría y se asignarían
    sus empleados a un proyecto de A desde un header de A, salteando la barrera."""
    svc, asignador, _ = _armar(monkeypatch)
    with pytest.raises(AppError) as exc:
        svc.asignar_area(PROYECTO_A, _pedido(AREA_B), EMPRESA_A)
    assert exc.value.code == "AREA_NOT_FOUND" and exc.value.status_code == 404
    assert asignador.creadas == []


def test_el_area_ajena_NO_devuelve_un_resultado_vacio(monkeypatch) -> None:
    """El contrapeso explícito del anterior: lo que NO puede pasar es un 200 mudo."""
    svc, _, _ = _armar(monkeypatch)
    with pytest.raises(AppError):
        svc.asignar_area(PROYECTO_A, _pedido(AREA_B), EMPRESA_A)


def test_los_empleados_se_resuelven_SIN_filtro_de_empresa(monkeypatch) -> None:
    """🔴 El segundo paso de la barrera. Un filtro acá sería redundante (los empleados de un área
    son de la empresa del área por construcción) y silencioso si algo no coincidiera.

    Para que falle: pasarle `empresa_id` a `empleados_de_area` "para que no falte el filtro"."""
    svc, _, empleados = _armar(monkeypatch)
    svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert empleados.empresas_recibidas == [None], \
        "se le pasó un empresa_id a empleados_de_area: volvió el filtro redundante"


# ── 5. 🔴 El cruce entre empresas, en modo consolidado ────────────────────────

def test_consolidado_permite_asignar_un_area_de_B_a_un_proyecto_de_A(monkeypatch) -> None:
    """🔴 ESTE CASO NO EXISTE EN PRODUCCIÓN —hay una sola empresa— y vive acá hasta que haya una
    segunda. Es el cruce que `proyecto_asignaciones.empleado_empresa_id` existe para soportar:
    la asignación guarda la empresa del EMPLEADO, no la del proyecto.

    `empresa_id=None` es la vista consolidada: no restringe, y eso es correcto."""
    svc, asignador, _ = _armar(monkeypatch)
    out = svc.asignar_area(PROYECTO_A, _pedido(AREA_B), None)
    assert len(out.asignados) == 2 and set(asignador.creadas) == {B1, B2}


def test_pero_el_proyecto_sigue_gateado_por_su_empresa(monkeypatch) -> None:
    """El consolidado afloja el ÁREA, no el proyecto: con el header de B, un proyecto de A
    sigue dando 404. Sin este test, "no restringe nada" y "no restringe el área" se confunden."""
    svc, _, _ = _armar(monkeypatch)
    with pytest.raises(AppError) as exc:
        svc.asignar_area(PROYECTO_A, _pedido(AREA_B), EMPRESA_B)
    assert exc.value.code == "PROYECTO_NOT_FOUND"


# ── 6. Un empleado en baja ────────────────────────────────────────────────────

def test_un_empleado_en_baja_va_a_errores_no_a_ya_asignados(monkeypatch) -> None:
    """Los tres grupos son tres cosas distintas: uno estaba, otro no se puede. Para que falle:
    clasificar por el texto del mensaje en vez de por el `code`."""
    svc, _, _ = _armar(monkeypatch, ya_asignados=[E1], de_baja=[E2])
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert _ids(out.asignados) == {E3}
    assert _ids(out.ya_asignados) == {E1}
    assert _ids(out.errores) == {E2}
    assert "baja" in out.errores[0].motivo


def test_un_fallo_no_corta_el_area(monkeypatch) -> None:
    """Éxito parcial: castigar a los otros por un empleado en baja sería la peor opción."""
    svc, asignador, _ = _armar(monkeypatch, de_baja=[E1])
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert len(out.asignados) == 2 and len(out.errores) == 1
    assert set(asignador.creadas) == {E2, E3}


# ── 7. Las horas cargadas ─────────────────────────────────────────────────────

def test_el_alta_por_area_NUNCA_borra_una_asignacion(monkeypatch) -> None:
    """🔴 ES LO QUE HACE QUE ESTO SEA UNA FOTO Y NO UN VÍNCULO VIVO.

    El alta por área SOLO CREA: no toca ni borra asignaciones existentes, así que una con horas
    cargadas queda intacta por construcción. Un vínculo vivo —el proyecto atado al área— sí la
    borraría al sacar a alguien del área, y ahí chocaría con `ASIGNACION_CON_HORAS` (409), que es
    el guard que hoy protege esas horas.

    Para que falle: que el alta por área intente "sincronizar" el área con el proyecto
    (crear las que faltan Y quitar las que sobran), que es la lectura natural de "asignar el
    área" y la que hay que NO implementar."""
    svc, asignador, _ = _armar(monkeypatch, ya_asignados=[E1])
    out = svc.asignar_area(PROYECTO_A, _pedido(), EMPRESA_A)
    assert _ids(out.ya_asignados) == {E1}
    assert not hasattr(asignador, "borradas"), "el alta por área intentó borrar algo"
    assert asignador.creadas == [E2, E3]


# ── El bulk manual comparte la clasificación ──────────────────────────────────

def test_el_bulk_manual_tambien_separa_los_ya_asignados(monkeypatch) -> None:
    """La clasificación es UNA sola: lo que vale para el área vale para la selección manual.
    Para que falle: que el alta por área tenga su propia clasificación en vez de reusar
    `clasificar` — ahí este test seguiría verde con `errores` mezclado en el bulk."""
    svc, _, _ = _armar(monkeypatch, ya_asignados=[E1])
    out = svc.asignar_bulk(
        PROYECTO_A,
        AsignacionBulkCreate(empleado_ids=[UUID(E1), UUID(E2)], rol="Analista", valor_hora=0),
        EMPRESA_A)
    assert _ids(out.asignados) == {E2} and _ids(out.ya_asignados) == {E1} and out.errores == []
