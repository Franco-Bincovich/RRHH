"""
La AUDITORÍA del módulo de objetivos: que las cuatro escrituras emitan su evento, y que el diff
diga la verdad.

Archivo propio y no dentro de `test_objetivos.py` (1169 líneas, el más grande del repo): el
criterio del repo es **un archivo de test cubre UNA cosa**, y aquél cubre las reglas de negocio
del módulo —validaciones, jerarquía, filtros, export—. Esto es otra unidad: qué queda escrito en
`auditoria` cuando alguien toca un objetivo. Molde: los cuatro archivos del puente
candidato→empleado.

🔴 POR QUÉ EXISTE. Hasta el 24/8/2026 el CRUD de objetivos no emitía un solo evento, y un
objetivo real de Karstec desapareció entre el 17/8 y el 24/8 sin que se pueda saber quién ni
cuándo. El borrado es FÍSICO y arrastra los subobjetivos por CASCADE, así que no quedó ni una
fila de la que reconstruirlo.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 **EL FAKE DE ESCRITURA DEVUELVE ALGO DISTINTO DE LO QUE DEVOLVIÓ `find_by_id`.** Es la
     condición de todo el archivo: si `update` devolviera la MISMA instancia que el `prior`, el
     diff saldría vacío SIEMPRE y "el diff registra el cambio" pasaría con el diff roto. Por eso
     `_Repo.update` construye la fila nueva A PARTIR del patch recibido (regla del repo: un fake
     de escritura nunca devuelve un objeto prefabricado).

  2. 🔴 **LOS CAMPOS DERIVADOS CAMBIAN DE VALOR ENTRE EL `prior` Y EL `nuevo`.** El fake pone
     `empresa_nombre`, `responsable_nombre` y `parent_titulo` DISTINTOS en los dos lados, a
     propósito y de forma que en producción no pasaría. Es lo único que puede desmentir la regla
     que este módulo tiene que cumplir: si `_DERIVADOS_OBJETIVO` dejara de excluirlos, el diff
     los traería y `test_el_diff_no_registra_campos_derivados` rojea. Con los dos lados iguales
     —que es lo que hace producción hoy, porque `update` termina en `find_by_id`— borrar la
     exclusión entera quedaría en VERDE, y sería el caso #2 del manual: el fake no modelaría la
     única diferencia que importa. Los 93 eventos fantasma de empleados nacieron justo así.

  3. 🔴 **`tiene_hijos` NO ES CONSTANTE**: devuelve True para el padre y False para la hoja. Con
     un valor fijo, "el evento avisa del CASCADE" y "el evento miente sobre el CASCADE" darían
     el mismo resultado.

  4. 🔴 **EL ESPÍA GUARDA LOS KWARGS ENTEROS**, no un contador de llamadas. Un espía que solo
     contara dejaría pasar un evento con la entidad, la acción o la empresa equivocadas — que es
     exactamente el bug que dejó la auditoría de nómina en silencio durante meses (`registro_id`
     con un literal en vez de un uuid: el insert fallaba y `registrar` se lo tragaba).

  5. El `AuditService` real NO se usa: tragaría cualquier error de armado del payload y los
     tests pasarían sobre eventos que en producción no se escriben. Acá el espía es tonto y
     guarda lo que le den, así que un payload mal armado se ve.
"""
import os

_TEST_ENV: dict[str, str] = {
    "SUPABASE_URL": "https://test-project.supabase.co",
    "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.anon",
    "SUPABASE_SERVICE_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.service",
    "JWT_SECRET": "test-secret-for-unit-tests-only-minimum-32-chars!!",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "RESEND_API_KEY": "re_test",
}
for _k, _v in _TEST_ENV.items():
    os.environ.setdefault(_k, _v)

from datetime import date, datetime  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

import services.objetivo_service as svc_mod  # noqa: E402
from schemas.objetivo import (  # noqa: E402
    CambiarEstadoRequest, ObjetivoCreate, ObjetivoResponse, ObjetivoUpdate, ResponsableItem,
)
from services.objetivo_service import ObjetivoService  # noqa: E402

EMPRESA_A = uuid4()
USER = str(uuid4())
OTRO_USER = str(uuid4())
OPERADOR = str(uuid4())


def _fila(titulo="Migrar nómina", estado="por_hacer", prioridad="alta", parent=None,
          resp=USER, extras=(), *, derivados="viejos") -> ObjetivoResponse:
    """Una fila de objetivo. `derivados` decide qué valor toman los campos de JOIN — ver el
    punto 2 del encabezado: es la palanca que hace falseable la regla del diff."""
    sufijo = "" if derivados == "viejos" else " (releído)"
    return ObjetivoResponse(
        id="11111111-1111-1111-1111-111111111111",
        empresa_id=str(EMPRESA_A), empresa_nombre=f"Karstec{sufijo}",
        responsable_id=resp, responsable_nombre=f"Ana Gómez{sufijo}",
        titulo=titulo, descripcion=None, prioridad=prioridad, estado=estado,
        fecha_entrega=date(2026, 6, 30),
        created_at=datetime(2026, 1, 5, 9, 0, 0), updated_at=datetime(2026, 2, 1, 12, 0, 0),
        parent_id=parent, parent_titulo=f"Padre{sufijo}" if parent else None,
        tipo="anual", periodicidad="", areas_involucradas=["Sistemas"],
        responsables=[ResponsableItem(id=resp, nombre="Ana Gómez"),
                      *[ResponsableItem(id=u, nombre="Beto Pérez") for u in extras]],
    )


class _Audit:
    """Punto 4: guarda los kwargs ENTEROS de cada evento, no un contador."""

    def __init__(self) -> None:
        self.eventos: list[dict] = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)

    @property
    def solo(self) -> dict:
        assert len(self.eventos) == 1, f"se esperaba UN evento, hubo {len(self.eventos)}"
        return self.eventos[0]


class _Repo:
    """Repo falso que HONRA la empresa y construye las escrituras a partir de lo recibido.

    🔴 `find_by_id` devuelve la fila con los derivados "viejos" y las ESCRITURAS la devuelven con
    los derivados "releídos" (punto 2). En producción los dos lados se leen igual —`update` y
    `set_estado` terminan los dos en `find_by_id`—, así que esta asimetría es DELIBERADAMENTE
    peor que la realidad: es la única forma de que el test pueda distinguir un diff que excluye
    los derivados de uno que no.
    """

    def __init__(self, fila: ObjetivoResponse, con_hijos: bool = False) -> None:
        self.fila = fila
        self.con_hijos = con_hijos
        self.borrados: list[str] = []

    def find_by_id(self, id, empresa_id=None):
        if id != self.fila.id:
            return None
        if empresa_id is not None and str(empresa_id) != self.fila.empresa_id:
            return None
        return self.fila

    def tiene_hijos(self, id, empresa_id=None) -> bool:
        return self.con_hijos                      # punto 3: distinto por instancia

    def save(self, data: ObjetivoCreate) -> ObjetivoResponse:
        return _fila(titulo=data.titulo, prioridad=data.prioridad,
                     resp=str(data.responsable_id), derivados="releidos")

    def update(self, id, data: ObjetivoUpdate, empresa_id=None) -> ObjetivoResponse:
        patch = data.model_dump(exclude_none=True)
        return _fila(titulo=patch.get("titulo", self.fila.titulo),
                     estado=self.fila.estado,
                     prioridad=patch.get("prioridad", self.fila.prioridad),
                     resp=str(patch.get("responsable_id", self.fila.responsable_id)),
                     extras=tuple(str(u) for u in patch.get("responsables", [])),
                     derivados="releidos")

    def set_estado(self, id, estado, empresa_id=None) -> ObjetivoResponse:
        return _fila(titulo=self.fila.titulo, estado=estado,
                     prioridad=self.fila.prioridad, derivados="releidos")

    def delete(self, id, empresa_id=None) -> bool:
        self.borrados.append(id)
        return True


@pytest.fixture(autouse=True)
def _sin_users_reales(monkeypatch):
    """`ensure_responsable_valido` pega contra `users`. Acá no se está probando eso."""
    monkeypatch.setattr(svc_mod, "ensure_responsable_valido", lambda *_a, **_k: None)
    monkeypatch.setattr(svc_mod, "ensure_responsables_validos", lambda *_a, **_k: None)
    monkeypatch.setattr(svc_mod, "ensure_padre_valido", lambda *_a, **_k: None)
    monkeypatch.setattr(svc_mod, "ensure_no_tiene_hijos", lambda *_a, **_k: None)


def _servicio(fila=None, con_hijos=False):
    repo = _Repo(fila or _fila(), con_hijos)
    audit = _Audit()
    return ObjetivoService(repo=repo, audit=audit), repo, audit


class TestLasCuatroEscriturasEmitenSuEvento:
    """La regla que el módulo no cumplía. Cada acto deja UNA fila en `auditoria`."""

    def test_el_alta_emite_alta_objetivo(self) -> None:
        svc, _, audit = _servicio()
        svc.create(ObjetivoCreate(empresa_id=EMPRESA_A, responsable_id=USER,
                                  titulo="Migrar nómina", prioridad="alta"), OPERADOR)
        ev = audit.solo
        assert ev["evento"] == "alta_objetivo"
        assert ev["accion"] == "INSERT"
        assert ev["entidad"] == "objetivo"
        assert ev["usuario_id"] == OPERADOR
        assert ev["datos_nuevos"]["titulo"] == "Migrar nómina"
        assert ev["datos_anteriores"] is None

    def test_la_edicion_emite_update_objetivo(self) -> None:
        svc, _, audit = _servicio()
        svc.update(uuid4().__class__(_fila().id), ObjetivoUpdate(titulo="Migrar nómina v2"),
                   EMPRESA_A, OPERADOR)
        ev = audit.solo
        assert ev["evento"] == "update_objetivo"
        assert ev["accion"] == "UPDATE"
        assert ev["usuario_id"] == OPERADOR

    def test_el_cambio_de_estado_emite_su_propio_evento(self) -> None:
        """EVENTO PROPIO y no `update_objetivo`: mover una tarjeta es el acto más frecuente del
        tablero y tiene endpoint propio. Con un evento compartido, el filtro de `/auditoria`
        mezclaría "lo reescribieron" con "lo movieron de columna"."""
        svc, _, audit = _servicio()
        svc.cambiar_estado(uuid4().__class__(_fila().id), CambiarEstadoRequest(estado="haciendo"),
                           EMPRESA_A, OPERADOR)
        ev = audit.solo
        assert ev["evento"] == "cambio_estado_objetivo"
        assert ev["evento"] != "update_objetivo"
        assert ev["datos_anteriores"]["estado"] == "por_hacer"
        assert ev["datos_nuevos"]["estado"] == "haciendo"

    def test_la_baja_emite_baja_objetivo_con_la_foto_de_lo_borrado(self) -> None:
        """El borrado es FÍSICO: este evento es lo ÚNICO que va a quedar del objetivo."""
        svc, repo, audit = _servicio()
        svc.delete(uuid4().__class__(_fila().id), EMPRESA_A, OPERADOR)
        ev = audit.solo
        assert ev["evento"] == "baja_objetivo"
        assert ev["accion"] == "DELETE"
        assert ev["datos_nuevos"] is None
        assert ev["datos_anteriores"]["titulo"] == "Migrar nómina"
        assert repo.borrados == [_fila().id]


class TestElEventoDiceDeQuienEsYQuienLoHizo:

    def test_la_empresa_sale_de_la_entidad_y_no_del_header(self) -> None:
        """Vista vs Acción: el sidebar decide qué se MIRA, la entidad de quién es lo que se HACE.

        Se pasa `empresa_id=None` (modo consolidado) a propósito: si el payload tomara la
        empresa del header, este evento saldría sin empresa y quedaría fuera del filtro por
        empresa de `/auditoria`, que es la pantalla donde esto se busca."""
        svc, _, audit = _servicio()
        svc.delete(uuid4().__class__(_fila().id), None, OPERADOR)
        assert audit.solo["empresa_id"] == str(EMPRESA_A)

    def test_los_cuatro_eventos_llevan_el_operador(self) -> None:
        """Un evento sin `usuario_id` no contesta la única pregunta por la que existe."""
        for accion in ("crear", "update", "estado", "delete"):
            svc, _, audit = _servicio()
            oid = uuid4().__class__(_fila().id)
            if accion == "crear":
                svc.create(ObjetivoCreate(empresa_id=EMPRESA_A, responsable_id=USER,
                                          titulo="T", prioridad="alta"), OPERADOR)
            elif accion == "update":
                svc.update(oid, ObjetivoUpdate(titulo="T2"), EMPRESA_A, OPERADOR)
            elif accion == "estado":
                svc.cambiar_estado(oid, CambiarEstadoRequest(estado="haciendo"), EMPRESA_A, OPERADOR)
            else:
                svc.delete(oid, EMPRESA_A, OPERADOR)
            assert audit.solo["usuario_id"] == OPERADOR, f"{accion} perdió el operador"


class TestElDiffDiceLaVerdad:
    """La otra mitad del trabajo: que el evento no afirme cambios que no ocurrieron."""

    def test_el_diff_no_registra_campos_derivados_de_joins(self) -> None:
        """🔴 EL TEST QUE JUSTIFICA `_DERIVADOS_OBJETIVO`.

        El fake devuelve `empresa_nombre`, `responsable_nombre` y `parent_titulo` DISTINTOS entre
        el prior y el nuevo (punto 2 del encabezado). Si el diff se armara sobre el response
        completo, esos tres aparecerían como cambios — y serían exactamente los 93 eventos
        fantasma que este repo ya se comió una vez, afirmándole al usuario que el área y la
        empresa de un empleado se habían vaciado.
        """
        svc, _, audit = _servicio(_fila(parent="99999999-9999-9999-9999-999999999999"))
        svc.update(uuid4().__class__(_fila().id), ObjetivoUpdate(titulo="Migrar nómina v2"),
                   EMPRESA_A, OPERADOR)
        ev = audit.solo
        for derivado in ("empresa_nombre", "responsable_nombre", "parent_titulo", "hijos"):
            assert derivado not in ev["datos_anteriores"], f"{derivado} entró al diff"
            assert derivado not in ev["datos_nuevos"], f"{derivado} entró al diff"

    def test_el_diff_si_registra_el_campo_que_cambio(self) -> None:
        """La contracara del anterior: sin esto, excluir TODO también pasaría."""
        svc, _, audit = _servicio()
        svc.update(uuid4().__class__(_fila().id), ObjetivoUpdate(titulo="Migrar nómina v2"),
                   EMPRESA_A, OPERADOR)
        ev = audit.solo
        assert ev["datos_anteriores"]["titulo"] == "Migrar nómina"
        assert ev["datos_nuevos"]["titulo"] == "Migrar nómina v2"

    def test_el_diff_registra_los_responsables_por_id_y_no_por_nombre(self) -> None:
        """La puente es un dato de negocio real, pero llega con los nombres resueltos por join.
        Se registra la MEMBRESÍA (ids), que es lo que la base tiene."""
        svc, _, audit = _servicio()
        svc.update(uuid4().__class__(_fila().id), ObjetivoUpdate(responsables=[OTRO_USER]),
                   EMPRESA_A, OPERADOR)
        ev = audit.solo
        assert OTRO_USER in ev["datos_nuevos"]["responsables"]
        assert OTRO_USER not in ev["datos_anteriores"]["responsables"]
        assert "Beto Pérez" not in str(ev["datos_nuevos"]["responsables"])

    def test_updated_at_no_cuenta_como_cambio(self) -> None:
        """Lo escribe la base en TODO update. Adentro del diff, ninguna edición podría ser
        'sin cambios' y el descarte de `_es_update_sin_cambios` no funcionaría nunca."""
        svc, _, audit = _servicio()
        svc.update(uuid4().__class__(_fila().id), ObjetivoUpdate(titulo="Migrar nómina v2"),
                   EMPRESA_A, OPERADOR)
        assert "updated_at" not in audit.solo["datos_nuevos"]


class TestLaBajaAvisaDelCascade:
    """`parent_id` es ON DELETE CASCADE: borrar un padre se lleva a los hijos, y de ESOS no queda
    ni un evento —el CASCADE lo ejecuta la base, sin triggers de auditoría desde la mig 058."""

    def test_borrar_un_padre_deja_escrito_que_arrastro_hijos(self) -> None:
        svc, _, audit = _servicio(con_hijos=True)
        svc.delete(uuid4().__class__(_fila().id), EMPRESA_A, OPERADOR)
        assert audit.solo["datos_anteriores"]["arrastro_subobjetivos_por_cascade"] is True

    def test_borrar_una_hoja_deja_escrito_que_no_arrastro_nada(self) -> None:
        """La contracara (punto 3): con un `tiene_hijos` constante, el aviso no probaría nada."""
        svc, _, audit = _servicio(con_hijos=False)
        svc.delete(uuid4().__class__(_fila().id), EMPRESA_A, OPERADOR)
        assert audit.solo["datos_anteriores"]["arrastro_subobjetivos_por_cascade"] is False


class TestNoSeAuditaLoQueNoOcurrio:

    def test_un_objetivo_de_otra_empresa_no_emite_ningun_evento(self) -> None:
        """La barrera de empresa corre ANTES de escribir: un 404 no deja rastro de auditoría.
        Un evento acá sería peor que inútil — diría que alguien borró algo que sigue existiendo."""
        svc, repo, audit = _servicio()
        with pytest.raises(Exception):
            svc.delete(uuid4().__class__(_fila().id), uuid4(), OPERADOR)
        assert audit.eventos == []
        assert repo.borrados == []

    def test_un_estado_invalido_no_emite_ningun_evento(self) -> None:
        svc, _, audit = _servicio()
        with pytest.raises(Exception):
            svc.cambiar_estado(uuid4().__class__(_fila().id),
                               CambiarEstadoRequest(estado="inventado"), EMPRESA_A, OPERADOR)
        assert audit.eventos == []
