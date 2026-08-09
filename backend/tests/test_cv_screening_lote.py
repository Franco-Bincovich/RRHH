"""
La corrida completa del clasificador: presupuesto, CVs sin texto, errores y barrera de empresa.

🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS PUEDAN FALLAR?

  · `_VacanteRepo` **modela DOS empresas** y devuelve `None` cuando el `empresa_id` no coincide.
    Un fake que aceptara el parámetro y lo ignorara daría verde con la barrera borrada — el caso
    #1 de "Un test solo prueba lo que el fake puede desmentir".
  · `_ScreeningRepo` **construye la respuesta a partir de lo que recibe** (guarda las tuplas que
    le mandan) en vez de devolver un objeto prefabricado, y **filtra por `clasificacion_ia IS
    NULL`** como el WHERE real: sin eso, el test de reintento estaría afirmando algo sobre su
    propia constante.
  · `_FakeAnthropic` **cuenta las llamadas**, que es lo único capaz de desmentir "un CV con
    warning no gasta llamada".
  · El presupuesto recibe un **reloj inyectado**, así el corte es determinista y no depende de
    que el modelo tarde.
"""
from types import SimpleNamespace

from services.cv_screening_service import TOPE_POR_CORRIDA, CvScreeningService
from tests._vacante_fake import vacante_completa
from utils.errors import AppError

import pytest

E1, E2 = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"
VAC = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_CV = "Contadora pública con cinco años de experiencia en estudios contables. " * 5


def _fila(cid: str, *, texto=_CV, warning=None, clasificacion=None, motivo=None) -> dict:
    return {"id": cid, "nombre": f"N{cid}", "apellido": "Ape", "cv_texto": texto,
            "screening_warning": warning, "clasificacion_ia": clasificacion,
            "clasificacion_motivo": motivo, "clasificacion_origen": None}


class _VacanteRepo:
    """Modela DOS empresas: la vacante es de E1 y una consulta desde E2 no la encuentra."""

    def __init__(self, empresa=E1) -> None:
        self.empresa = empresa

    def find_by_id(self, vacante_id, empresa_id=None):
        if vacante_id != VAC:
            return None
        if empresa_id and str(empresa_id) != self.empresa:
            return None  # 🔴 HONRA el parámetro. Sin esto la barrera no se puede desmentir.
        # 🔴 Los SIETE campos cargados. Antes este fake devolvía solo título y descripción —
        # o sea, reproducía el bug: el prompt leía dos campos y el fake le pasaba esos dos.
        return vacante_completa(id=VAC, empresa_id=self.empresa)


class _ScreeningRepo:
    """Filtra por 'sin clasificar' como el WHERE real y guarda lo que le mandan."""

    def __init__(self, filas) -> None:
        self.filas = filas
        self.guardados: list = []
        self.fallos: list = []
        self.empresas_recibidas: list = []

    def find_para_clasificar(self, vacante_id, empresa_id=None):
        self.empresas_recibidas.append(empresa_id)
        return [f for f in self.filas if f.get("clasificacion_ia") is None]

    def set_clasificacion(self, candidato_id, clasificacion, motivo, empresa_id=None):
        self.guardados.append((candidato_id, clasificacion, motivo, empresa_id))
        self._aplicar(candidato_id, clasificacion, motivo, "modelo")

    def set_fallo(self, candidato_id, motivo, empresa_id=None):
        """🔴 Deja `clasificacion_ia` en NULL como el repo real: es lo que hace que la fila
        siga siendo reintentable. Un fake que la marcara acá volvería vacuo el test de
        reintento — pasaría igual con el repo escribiendo una clasificación falsa."""
        self.fallos.append((candidato_id, motivo, empresa_id))
        self._aplicar(candidato_id, None, motivo, None)

    def _aplicar(self, candidato_id, clasificacion, motivo, origen):
        for f in self.filas:
            if f["id"] == candidato_id:
                f["clasificacion_ia"] = clasificacion
                f["clasificacion_motivo"] = motivo
                f["clasificacion_origen"] = origen


class _FakeAnthropic:
    """Cuenta llamadas. Es lo único que puede desmentir 'no gasta llamada'."""

    def __init__(self, respuestas=None) -> None:
        self.cola = list(respuestas or [])
        self.llamadas = 0
        self.messages = self

    def create(self, *, model, max_tokens, system, messages):
        self.llamadas += 1
        texto = self.cola.pop(0) if self.cola else '{"clasificacion": "dudoso", "motivo": "ok"}'
        if isinstance(texto, Exception):
            raise texto
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)])


class _Config:
    def get_criterio(self, empresa_id=None):
        return SimpleNamespace(def_relevante="a", def_dudoso="b", def_no_relevante="c",
                               instrucciones="")


class _Audit:
    def __init__(self) -> None:
        self.eventos: list = []

    def registrar(self, **kw) -> None:
        self.eventos.append(kw)


def _svc(filas, cliente=None, empresa=E1, audit=None):
    repo = _ScreeningRepo(filas)
    return CvScreeningService(vacante_repo=_VacanteRepo(empresa), screening_repo=repo,
                              config=_Config(), audit=audit or _Audit(),
                              cliente=cliente or _FakeAnthropic()), repo


class TestLasTresCategoriasSePersisten:
    def test_cada_resultado_llega_a_la_base_con_su_motivo(self) -> None:
        cli = _FakeAnthropic([
            '{"clasificacion": "relevante", "motivo": "Es contadora."}',
            '{"clasificacion": "dudoso", "motivo": "No se entiende el CV."}',
            '{"clasificacion": "no_relevante", "motivo": "Perfil en gastronomía."}',
        ])
        svc, repo = _svc([_fila("c1"), _fila("c2"), _fila("c3")], cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.clasificados == 3 and r.errores == 0 and r.sin_texto == 0
        assert [g[1] for g in repo.guardados] == ["relevante", "dudoso", "no_relevante"]
        assert repo.guardados[2][2] == "Perfil en gastronomía."


class TestSalidaInvalida:
    def test_un_valor_desconocido_NO_se_persiste_como_clasificacion(self) -> None:
        """No se interpreta ni se cae a `dudoso`: la clasificación queda en NULL."""
        cli = _FakeAnthropic(['{"clasificacion": "tal vez", "motivo": "x"}'])
        svc, repo = _svc([_fila("c1")], cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.errores == 1 and r.clasificados == 0
        assert repo.guardados == []
        assert repo.filas[0]["clasificacion_ia"] is None

    def test_un_CV_roto_NO_corta_el_lote(self) -> None:
        """Dos CVs, el primero explota: el segundo se clasifica igual."""
        cli = _FakeAnthropic([RuntimeError("timeout"), '{"clasificacion": "relevante", "motivo": "ok"}'])
        svc, repo = _svc([_fila("c1"), _fila("c2")], cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.errores == 1 and r.clasificados == 1
        assert [g[0] for g in repo.guardados] == ["c2"]


class TestCvSinTextoNoGastaLlamada:
    def test_con_warning_no_se_clasifica_ni_se_llama_al_modelo(self) -> None:
        cli = _FakeAnthropic()
        svc, repo = _svc([_fila("c1", texto=None, warning="El archivo está protegido.")], cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert cli.llamadas == 0                 # 🔴 lo que el fake puede desmentir
        assert r.sin_texto == 1 and r.clasificados == 0 and r.errores == 0
        assert repo.guardados == []

    def test_sin_texto_NO_es_un_error_del_lote(self) -> None:
        """Va a revisión manual: son cuentas distintas y la pantalla las muestra distinto."""
        svc, _ = _svc([_fila("c1", texto="", warning=None), _fila("c2")])
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.sin_texto == 1 and r.errores == 0 and r.clasificados == 1

    def test_el_lote_mezclado_gasta_una_llamada_por_CV_legible(self) -> None:
        cli = _FakeAnthropic()
        svc, _ = _svc([_fila("c1"), _fila("c2", warning="roto"), _fila("c3")], cliente=cli)
        svc.clasificar_pendientes(VAC, E1)
        assert cli.llamadas == 2


class TestBarreraDeEmpresa:
    def test_una_vacante_de_otra_empresa_da_404_y_no_llama_al_modelo(self) -> None:
        cli = _FakeAnthropic()
        svc, repo = _svc([_fila("c1")], cliente=cli, empresa=E1)
        with pytest.raises(AppError) as exc:
            svc.clasificar_pendientes(VAC, E2)
        assert exc.value.code == "VACANTE_NOT_FOUND" and exc.value.status_code == 404
        assert cli.llamadas == 0

    def test_el_404_es_IDENTICO_al_de_una_vacante_inexistente(self) -> None:
        """Un código distinto confirmaría que la vacante ajena existe."""
        svc, _ = _svc([_fila("c1")])
        with pytest.raises(AppError) as ajena:
            svc.clasificar_pendientes(VAC, E2)
        with pytest.raises(AppError) as inexistente:
            svc.clasificar_pendientes("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", E1)
        assert (ajena.value.code, ajena.value.message) == (inexistente.value.code,
                                                           inexistente.value.message)

    def test_la_escritura_lleva_la_empresa_de_la_VACANTE_no_la_del_header(self) -> None:
        """Vista vs Acción: en consolidado el header es None y la vacante sí tiene empresa."""
        svc, repo = _svc([_fila("c1")])
        svc.clasificar_pendientes(VAC, None)          # modo consolidado
        assert repo.guardados[0][3] == E1
        assert repo.empresas_recibidas == [E1]


class TestPresupuesto:
    def test_corta_y_REPORTA_cuantos_quedaron(self, monkeypatch) -> None:
        """Reloj inyectado: el corte es determinista, no depende de cuánto tarde el modelo.

        🔴 El parche va sobre `cv_screening_service.Presupuesto`, NO sobre `_presupuesto`: el
        service hace `from ... import Presupuesto`, así que ya tiene su propia referencia y
        parchear el módulo de origen no lo alcanzaría — el test pasaría con el presupuesto real
        y nunca cortaría.
        """
        import services.cv_screening_service as mod

        # Reloj falso que avanza 10 s por consulta contra un presupuesto de 25 s: entran los
        # primeros y el resto queda sin procesar.
        pasos = iter([i * 10.0 for i in range(60)])
        real = mod.Presupuesto
        monkeypatch.setattr(mod, "Presupuesto",
                            lambda *a, **k: real(25.0, reloj=lambda: next(pasos)))

        svc, _ = _svc([_fila(f"c{i}") for i in range(5)], cliente=_FakeAnthropic())
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.parcial is True
        assert r.sin_procesar > 0
        assert r.clasificados + r.sin_texto + r.errores + r.sin_procesar == 5

    def test_lo_que_quedo_sin_procesar_es_REINTENTABLE(self) -> None:
        """El repo pide `clasificacion_ia IS NULL`: la segunda corrida toma solo el resto."""
        filas = [_fila("c1", clasificacion="relevante"), _fila("c2")]
        cli = _FakeAnthropic()
        svc, repo = _svc(filas, cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert cli.llamadas == 1 and r.clasificados == 1
        assert [g[0] for g in repo.guardados] == ["c2"]

    def test_una_segunda_corrida_sobre_todo_clasificado_cuesta_CERO(self) -> None:
        cli = _FakeAnthropic()
        svc, _ = _svc([_fila("c1", clasificacion="dudoso")], cliente=cli)
        r = svc.clasificar_pendientes(VAC, E1)
        assert cli.llamadas == 0 and r.clasificados == 0 and r.sin_procesar == 0


class TestTopePorCorrida:
    def test_el_tope_se_AVISA_en_vez_de_truncar_en_silencio(self) -> None:
        """Un tope silencioso se leería como 'ya está todo clasificado'."""
        filas = [_fila(f"c{i}") for i in range(TOPE_POR_CORRIDA + 3)]
        svc, _ = _svc(filas)
        r = svc.clasificar_pendientes(VAC, E1)
        assert r.tope_alcanzado is True
        assert r.sin_procesar >= 3

    def test_sin_excedente_no_se_marca_el_tope(self) -> None:
        svc, _ = _svc([_fila("c1")])
        assert svc.clasificar_pendientes(VAC, E1).tope_alcanzado is False


class TestAuditoria:
    def test_UN_evento_por_lote_y_no_uno_por_CV(self) -> None:
        audit = _Audit()
        svc, _ = _svc([_fila("c1"), _fila("c2"), _fila("c3")], audit=audit)
        svc.clasificar_pendientes(VAC, E1)
        assert len(audit.eventos) == 1
        assert audit.eventos[0]["evento"] == "screening_cv"

    def test_el_evento_lleva_la_empresa_de_la_vacante_y_los_conteos(self) -> None:
        audit = _Audit()
        svc, _ = _svc([_fila("c1"), _fila("c2", warning="roto")], audit=audit)
        svc.clasificar_pendientes(VAC, None)   # header en consolidado
        evento = audit.eventos[0]
        assert evento["empresa_id"] == E1
        assert evento["datos_nuevos"]["clasificados"] == 1
        assert evento["datos_nuevos"]["sin_texto"] == 1
        assert evento["datos_nuevos"]["vacante_id"] == VAC
