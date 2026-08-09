"""
La corrección manual de una clasificación, y el fallo del clasificador persistido.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · `_CandidatoRepo` **arranca con el candidato YA CLASIFICADO POR EL MODELO**
    (`clasificacion_ia="no_relevante"`, `clasificacion_origen="modelo"`). Con uno sin clasificar,
    "corrigió" y "clasificó por primera vez" serían indistinguibles: cualquier implementación que
    escribiera la etiqueta pasaría, aunque perdiera el veredicto anterior o no marcara el origen.
  · `_CandidatoRepo` **construye la respuesta a partir de lo que el repo de screening escribió**
    —no devuelve un objeto prefabricado—, así que el test afirma sobre lo que el código guardó y
    no sobre su propia constante.
  · `_CandidatoRepo` **modela DOS empresas** y devuelve `None` cuando el `empresa_id` no coincide.
    Un fake que aceptara el parámetro y lo ignorara daría verde con la barrera borrada.
  · `_ScreeningRepo` mantiene los **TRES estados** —nunca clasificado, clasificado OK, fallado— y
    aplica `set_fallo` dejando `clasificacion_ia` en NULL como el repo real. Si lo marcara, el
    test de "una corrida posterior lo vuelve a tomar" pasaría con el repo escribiendo cualquier
    cosa.
"""
from types import SimpleNamespace

import pytest

from schemas.screening import ClasificacionUpdate
from schemas.vacante import CandidatoResponse
from services._screening_candidato import PREFIJO_FALLO
from services.cv_screening_service import CvScreeningService
from services.screening_correccion_service import ScreeningCorreccionService
from utils.errors import AppError

E1, E2 = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
CID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
VAC = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class _CandidatoRepo:
    """El candidato YA viene clasificado POR EL MODELO. Ver el encabezado."""

    def __init__(self, empresa=E1, clasificacion="no_relevante", motivo="Perfil en gastronomía.",
                 origen="modelo") -> None:
        self.empresa = empresa
        self.estado = {"clasificacion_ia": clasificacion, "clasificacion_motivo": motivo,
                       "clasificacion_origen": origen}

    def find_by_id(self, candidato_id, empresa_id=None):
        if candidato_id != CID:
            return None
        if empresa_id and str(empresa_id) != self.empresa:
            return None  # 🔴 HONRA el parámetro. Sin esto la barrera no se puede desmentir.
        return CandidatoResponse(
            id=CID, vacante_id=VAC, empresa_id=self.empresa, nombre="Ana", apellido="Gómez",
            email="a@e.com", etapa_pipeline="postulado", created_at="2026-08-09T00:00:00Z",
            **self.estado)


class _ScreeningRepo:
    """Escribe sobre el estado del repo de candidatos: la respuesta sale de lo que se guardó."""

    def __init__(self, candidatos: _CandidatoRepo) -> None:
        self._c = candidatos
        self.correcciones: list = []
        self.empresas_recibidas: list = []

    def set_correccion(self, candidato_id, clasificacion, motivo, empresa_id=None):
        self.correcciones.append((candidato_id, clasificacion, motivo, empresa_id))
        self.empresas_recibidas.append(empresa_id)
        self._c.estado = {"clasificacion_ia": clasificacion, "clasificacion_motivo": motivo,
                          "clasificacion_origen": "humano"}


class _Audit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _svc(empresa=E1, **kw):
    cand = _CandidatoRepo(empresa=empresa, **kw)
    repo, audit = _ScreeningRepo(cand), _Audit()
    return ScreeningCorreccionService(candidato_repo=cand, screening_repo=repo,
                                      audit=audit), repo, audit


def _body(clasificacion="relevante", motivo="Trabajó dos años en un estudio contable."):
    return ClasificacionUpdate(clasificacion=clasificacion, motivo=motivo)


class TestLaCorreccionSePersisteYQuedaMarcadaComoHumana:

    def test_pisa_la_clasificacion_del_modelo(self) -> None:
        svc, repo, _ = _svc()
        r = svc.corregir(CID, _body(), E1, "u1")
        assert repo.correcciones[0][1] == "relevante"
        assert r.clasificacion_ia == "relevante"
        assert r.clasificacion_motivo == "Trabajó dos años en un estudio contable."

    def test_queda_marcada_como_HUMANA_y_no_como_modelo(self) -> None:
        """El candidato entró con `origen='modelo'`: si el código no lo cambiara, esto falla."""
        svc, _, _ = _svc()
        assert svc.corregir(CID, _body(), E1, "u1").clasificacion_origen == "humano"

    def test_el_motivo_es_obligatorio(self) -> None:
        """Sin él la ficha diría 'Relevante' con la explicación del 'No relevante' anterior."""
        with pytest.raises(Exception):
            ClasificacionUpdate(clasificacion="relevante", motivo="   ".strip())

    def test_no_se_puede_volver_a_sin_clasificar(self) -> None:
        with pytest.raises(Exception):
            ClasificacionUpdate(clasificacion=None, motivo="x")  # type: ignore[arg-type]


class TestAuditoriaIndividual:

    def test_emite_UN_evento_por_correccion_no_por_lote(self) -> None:
        svc, _, audit = _svc()
        svc.corregir(CID, _body(), E1, "u1")
        assert len(audit.eventos) == 1
        assert audit.eventos[0]["evento"] == "correccion_clasificacion"
        assert audit.eventos[0]["registro_id"] == CID  # el candidato, no un uuid de evento

    def test_conserva_el_VEREDICTO_DEL_MODELO_que_la_correccion_pisa(self) -> None:
        """🔴 La columna dice que intervino un humano; solo el evento dice QUÉ había dicho el
        modelo. Sin esto no se puede medir en qué dirección se equivoca el filtro."""
        svc, _, audit = _svc()
        svc.corregir(CID, _body(), E1, "u1")
        previo = audit.eventos[0]["datos_anteriores"]
        assert previo["clasificacion_ia"] == "no_relevante"
        assert previo["clasificacion_motivo"] == "Perfil en gastronomía."
        assert previo["clasificacion_origen"] == "modelo"
        assert audit.eventos[0]["datos_nuevos"]["clasificacion_origen"] == "humano"

    def test_la_empresa_del_evento_sale_del_CANDIDATO_no_del_header(self) -> None:
        """Vista vs Acción: en consolidado el header es None y el candidato sí tiene empresa."""
        svc, repo, audit = _svc()
        svc.corregir(CID, _body(), None, "u1")
        assert audit.eventos[0]["empresa_id"] == E1
        assert repo.empresas_recibidas == [E1]


class TestBarreraDeEmpresa:

    def test_un_candidato_de_otra_empresa_da_404_y_no_escribe(self) -> None:
        svc, repo, audit = _svc(empresa=E1)
        with pytest.raises(AppError) as exc:
            svc.corregir(CID, _body(), E2, "u1")
        assert exc.value.code == "CANDIDATO_NOT_FOUND" and exc.value.status_code == 404
        assert repo.correcciones == [] and audit.eventos == []

    def test_el_404_es_IDENTICO_al_de_un_candidato_inexistente(self) -> None:
        """Un código o mensaje distinto confirmaría que el candidato ajeno existe."""
        svc, _, _ = _svc()
        with pytest.raises(AppError) as ajeno:
            svc.corregir(CID, _body(), E2, "u1")
        with pytest.raises(AppError) as inexistente:
            svc.corregir("dddddddd-dddd-dddd-dddd-dddddddddddd", _body(), E1, "u1")
        assert (ajeno.value.code, ajeno.value.message, ajeno.value.status_code) == \
               (inexistente.value.code, inexistente.value.message, inexistente.value.status_code)


# ── Lo corregido no lo pisa una corrida posterior ─────────────────────────────────────────

class _VacanteRepo:
    def find_by_id(self, vacante_id, empresa_id=None):
        if vacante_id != VAC or (empresa_id and str(empresa_id) != E1):
            return None
        return SimpleNamespace(id=VAC, titulo="Contador", descripcion=None, empresa_id=E1)


class _LoteRepo:
    """Los TRES estados. `find_para_clasificar` filtra por NULL como el WHERE real."""

    def __init__(self, filas) -> None:
        self.filas = filas
        self.tocados: list = []

    def find_para_clasificar(self, vacante_id, empresa_id=None):
        return [f for f in self.filas if f["clasificacion_ia"] is None]

    def set_clasificacion(self, candidato_id, clasificacion, motivo, empresa_id=None):
        self.tocados.append(candidato_id)
        self._set(candidato_id, clasificacion, motivo, "modelo")

    def set_fallo(self, candidato_id, motivo, empresa_id=None):
        self.tocados.append(candidato_id)
        self._set(candidato_id, None, motivo, None)  # 🔴 NULL: sigue siendo reintentable

    def _set(self, cid, clas, motivo, origen):
        for f in self.filas:
            if f["id"] == cid:
                f.update(clasificacion_ia=clas, clasificacion_motivo=motivo,
                         clasificacion_origen=origen)


class _FakeAnthropic:
    def __init__(self, respuestas=None) -> None:
        self.cola = list(respuestas or [])
        self.llamadas = 0
        self.messages = self

    def create(self, *, model, max_tokens, system, messages):
        self.llamadas += 1
        t = self.cola.pop(0) if self.cola else '{"clasificacion": "dudoso", "motivo": "ok"}'
        if isinstance(t, Exception):
            raise t
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=t)])


def _fila(cid, *, clasificacion=None, motivo=None, origen=None, texto="CV largo. " * 40):
    return {"id": cid, "nombre": "N", "apellido": "A", "cv_texto": texto,
            "screening_warning": None, "clasificacion_ia": clasificacion,
            "clasificacion_motivo": motivo, "clasificacion_origen": origen}


def _lote(filas, cliente=None):
    repo = _LoteRepo(filas)
    return CvScreeningService(
        vacante_repo=_VacanteRepo(), screening_repo=repo,
        config=SimpleNamespace(get_criterio=lambda e=None: SimpleNamespace(
            def_relevante="a", def_dudoso="b", def_no_relevante="c", instrucciones="")),
        audit=_Audit(), cliente=cliente or _FakeAnthropic()), repo


class TestUnaCorreccionNoLaPisaElClasificador:

    def test_la_corrida_posterior_NO_toca_al_corregido(self) -> None:
        """🔴 La garantía que hace que corregir valga la pena. Si `find_para_clasificar` dejara
        de filtrar por NULL, el modelo empezaría a sobrescribir decisiones humanas en silencio."""
        corregido = _fila("c1", clasificacion="relevante", motivo="Lo revisé yo.", origen="humano")
        cli = _FakeAnthropic()
        svc, repo = _lote([corregido, _fila("c2")], cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert repo.tocados == ["c2"]
        assert cli.llamadas == 1                      # ni siquiera se gastó una llamada en c1
        assert corregido["clasificacion_ia"] == "relevante"
        assert corregido["clasificacion_origen"] == "humano"
        assert r.clasificados == 1

    def test_tampoco_toca_al_que_clasifico_el_modelo(self) -> None:
        ya = _fila("c1", clasificacion="dudoso", motivo="m", origen="modelo")
        svc, repo = _lote([ya])
        assert svc.clasificar_pendientes(VAC, E1).clasificados == 0
        assert repo.tocados == []


class TestElFalloDelClasificadorPersiste:

    def test_queda_guardado_el_motivo_con_la_clasificacion_en_NULL(self) -> None:
        """Antes esto vivía solo en la respuesta del botón y se perdía al recargar."""
        fila = _fila("c1")
        svc, _ = _lote([fila], cliente=_FakeAnthropic([RuntimeError("timeout")]))
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.errores == 1
        assert fila["clasificacion_ia"] is None
        assert fila["clasificacion_motivo"].startswith(PREFIJO_FALLO)
        assert "timeout" in fila["clasificacion_motivo"]

    def test_se_DISTINGUE_de_nunca_clasificado(self) -> None:
        """Los dos tienen `clasificacion_ia` en NULL; lo que los separa es el motivo."""
        fallado, nunca = _fila("c1"), _fila("c2")
        svc, _ = _lote([fallado], cliente=_FakeAnthropic([RuntimeError("boom")]))
        svc.clasificar_pendientes(VAC, E1)
        assert fallado["clasificacion_ia"] is nunca["clasificacion_ia"] is None
        assert fallado["clasificacion_motivo"] and nunca["clasificacion_motivo"] is None

    def test_una_salida_invalida_tambien_persiste_su_motivo(self) -> None:
        fila = _fila("c1")
        svc, _ = _lote([fila], cliente=_FakeAnthropic(['{"clasificacion": "tal vez", "motivo": "x"}']))
        svc.clasificar_pendientes(VAC, E1)
        assert fila["clasificacion_ia"] is None
        assert PREFIJO_FALLO in fila["clasificacion_motivo"]

    def test_el_fallado_SIGUE_siendo_reintentable(self) -> None:
        """🔴 Por eso NO se guarda en `screening_warning`: ahí gatearía el salteo y el fallo se
        volvería permanente. Con la clasificación en NULL, el próximo click lo vuelve a tomar."""
        fila = _fila("c1")
        svc, repo = _lote([fila], cliente=_FakeAnthropic([RuntimeError("boom")]))
        svc.clasificar_pendientes(VAC, E1)
        assert repo.find_para_clasificar(VAC) == [fila]

        cli2 = _FakeAnthropic(['{"clasificacion": "relevante", "motivo": "Ahora sí."}'])
        svc2, _ = _lote([fila], cliente=cli2)
        assert svc2.clasificar_pendientes(VAC, E1).clasificados == 1
        assert fila["clasificacion_ia"] == "relevante"
        assert fila["clasificacion_origen"] == "modelo"

    def test_un_CV_ilegible_NO_escribe_motivo_de_fallo(self) -> None:
        """Nunca llegó al modelo: su motivo ya está en `screening_warning` y dice otra cosa."""
        fila = _fila("c1", texto=None)
        fila["screening_warning"] = "El archivo está protegido con contraseña."
        cli = _FakeAnthropic()
        svc, repo = _lote([fila], cliente=cli)
        svc.clasificar_pendientes(VAC, E1)
        assert cli.llamadas == 0 and repo.tocados == []
        assert fila["clasificacion_motivo"] is None


# ── Un escalón más abajo: lo que tiene que viajar EN LA QUERY ─────────────────────────────

class TestLoQueEscribeElRepoDeVerdad:
    """
    🔴 LOS FAKES DE ARRIBA NO ALCANZAN, Y EL MUTATION CHECK LO MOSTRÓ.

    `_ScreeningRepo` y `_LoteRepo` implementan `set_correccion` / `set_fallo` /
    `find_para_clasificar` a mano, así que fijan el CONTRATO (qué espera el service) pero no
    tocan el repo real. Tres mutaciones sobrevivieron a la suite entera:

      · `set_correccion` escribiendo `origen='modelo'` en vez de `'humano'`,
      · `set_fallo` cayendo a `'dudoso'` en vez de dejar la clasificación en NULL,
      · `find_para_clasificar` SIN el `.is_("clasificacion_ia", "null")`.

    Las tres son exactamente las garantías del módulo, y las tres se decidían en una línea que
    ningún test miraba. Acá se faltea el CLIENTE DE SUPABASE y se captura lo que el repo manda.

    (Mismo molde que `TestElOrdenLoPoneLaQuery` en `test_historial_salarial.py`.)
    """

    def _repo_con_espia(self, monkeypatch):
        import repositories.candidato_screening_repo as mod

        capturado: dict = {"updates": [], "filtros": [], "select": []}

        class _Q:
            def select(self, *a, **k):
                capturado["select"].append(a)
                return self

            def update(self, campos):
                capturado["updates"].append(campos)
                return self

            def eq(self, col, val):
                capturado["filtros"].append(("eq", col, val))
                return self

            def is_(self, col, val):
                capturado["filtros"].append(("is_", col, val))
                return self

            def order(self, *a, **k):
                return self

            def execute(self):
                return SimpleNamespace(data=[])

        monkeypatch.setattr(mod, "supabase_admin", type("C", (), {"table": lambda s, t: _Q()})())
        return mod.CandidatoScreeningRepo(), capturado

    def test_la_correccion_escribe_origen_HUMANO(self, monkeypatch) -> None:
        repo, cap = self._repo_con_espia(monkeypatch)
        repo.set_correccion(CID, "relevante", "Lo revisé yo.", E1)
        assert cap["updates"] == [{"clasificacion_ia": "relevante",
                                   "clasificacion_motivo": "Lo revisé yo.",
                                   "clasificacion_origen": "humano"}]

    def test_el_clasificador_escribe_origen_MODELO(self, monkeypatch) -> None:
        repo, cap = self._repo_con_espia(monkeypatch)
        repo.set_clasificacion(CID, "dudoso", "m", E1)
        assert cap["updates"][0]["clasificacion_origen"] == "modelo"

    def test_el_fallo_deja_la_clasificacion_en_NULL(self, monkeypatch) -> None:
        """🔴 Si cayera a una categoría, el candidato saldría del conjunto reintentable y el
        fallo se volvería un veredicto — atribuido al modelo, que nunca lo dio."""
        repo, cap = self._repo_con_espia(monkeypatch)
        repo.set_fallo(CID, f"{PREFIJO_FALLO}: boom", E1)
        assert cap["updates"] == [{"clasificacion_ia": None,
                                   "clasificacion_motivo": f"{PREFIJO_FALLO}: boom",
                                   "clasificacion_origen": None}]

    def test_las_tres_escrituras_llevan_la_empresa_EN_EL_WHERE(self, monkeypatch) -> None:
        for metodo, args in (("set_correccion", (CID, "dudoso", "m", E1)),
                             ("set_clasificacion", (CID, "dudoso", "m", E1)),
                             ("set_fallo", (CID, "m", E1))):
            repo, cap = self._repo_con_espia(monkeypatch)
            getattr(repo, metodo)(*args)
            assert ("eq", "empresa_id", E1) in cap["filtros"], metodo
            assert ("eq", "id", CID) in cap["filtros"], metodo

    def test_la_corrida_SOLO_pide_los_que_estan_sin_clasificar(self, monkeypatch) -> None:
        """🔴 Este `.is_` es lo único que impide que el modelo pise una corrección humana."""
        repo, cap = self._repo_con_espia(monkeypatch)
        repo.find_para_clasificar(VAC, E1)
        assert ("is_", "clasificacion_ia", "null") in cap["filtros"]
        assert ("eq", "vacante_id", VAC) in cap["filtros"]
        assert ("eq", "empresa_id", E1) in cap["filtros"]
