"""
T2 — `PlantillasService.guardar` y `.borrar`: el alta, la edición y la baja de una plantilla.

QUÉ HABÍA ANTES. `test_plantillas_permisos.py` cubre los GATES (quién puede) y
`test_mail_variables.py` cubre el RENDER y `variables_invalidas` **como función suelta**. Nadie
verificaba el camino de guardado: que `guardar` LLAME a esa validación, que persista con la
empresa correcta, ni que editar una plantilla no toque otra. La función estaba probada; su uso no.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO EN EL FAKE PARA QUE ESTOS TESTS PUEDAN FALLAR?

  1. 🔴 EL FAKE TIENE TRES FILAS: dos plantillas PROPIAS de la empresa y una GLOBAL con la MISMA
     clave que una de ellas. Con una sola, "editó la correcta" y "editó cualquiera" dan el mismo
     resultado; sin la global, el caso que destapó el bug del envío consolidado —una global y una
     propia compartiendo clave— no se puede expresar. Cada test que afirma sobre una fila afirma
     ADEMÁS que las otras quedaron intactas.
  2. 🔴 EL FAKE DE ESCRITURA CONSTRUYE LA RESPUESTA A PARTIR DE LO QUE RECIBE, nunca devuelve un
     objeto prefabricado. Si devolviera una constante, el test estaría afirmando algo sobre su
     propia constante y no sobre lo que el service mandó a persistir (regla del repo; ver el
     encabezado de `test_domicilio_desglosado.py`).
  3. 🔴 EL FAKE HONRA `empresa_id` EN `borrar`, igual que el repo real: una global (empresa NULL)
     NO se borra desde una empresa. Un fake que ignorara el parámetro daría verde con la guarda
     borrada — el caso #1 de "un test solo prueba lo que el fake puede desmentir".
  4. Los rechazos afirman ADEMÁS que NO se persistió nada (`repo.guardadas == []`). Sin eso, un
     service que guardara y DESPUÉS validara pasaría el test del error igual.
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

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.plantillas import PlantillaUpsert  # noqa: E402
from services.plantillas_service import PlantillasService  # noqa: E402
from utils.errors import AppError  # noqa: E402

EMPRESA = uuid4()
OTRA_EMPRESA = uuid4()

ID_BIENVENIDA = str(uuid4())
ID_AVISO = str(uuid4())
ID_GLOBAL = str(uuid4())


def _fila(id_, empresa, clave, asunto):
    return {"id": id_, "empresa_id": empresa, "clave": clave, "contexto": "empleado",
            "asunto": asunto, "cuerpo": "cuerpo de " + clave, "activa": True}


class _Repo:
    """Fake de `PlantillaMailRepo`. Modela TRES filas y honra `empresa_id` en el borrado.

    La global comparte la clave `bienvenida` con una propia a propósito: es la forma en la que el
    repo real resuelve precedencia, y sin las dos no se puede afirmar que una no pisa a la otra.
    """

    def __init__(self) -> None:
        self.filas = {
            ID_BIENVENIDA: _fila(ID_BIENVENIDA, str(EMPRESA), "bienvenida", "Propia"),
            ID_AVISO: _fila(ID_AVISO, str(EMPRESA), "aviso", "Aviso"),
            ID_GLOBAL: _fila(ID_GLOBAL, None, "bienvenida", "Global"),
        }
        self.guardadas: list = []
        self.borrados: list = []
        self.devolver_none = False

    def guardar(self, fila: dict):
        self.guardadas.append(dict(fila))
        if self.devolver_none:      # modela el insert que no devuelve nada (500 del service)
            return None
        id_ = fila.get("id") or str(uuid4())
        # 🔴 La respuesta se ARMA con lo recibido: un objeto prefabricado haría que el test
        # afirme sobre su propia constante en vez de sobre lo que el service mandó.
        nueva = {**self.filas.get(id_, {}), **fila, "id": id_}
        self.filas[id_] = nueva
        return nueva

    def borrar(self, id_, empresa_id=None):
        """Devuelve LA FILA BORRADA, como el repo real (PostgREST retorna lo borrado en `.data`).

        🔴 No devuelve `True`: el service audita la baja con esta fila, y un fake que devolviera
        un booleano dejaría el evento —que es el ÚNICO respaldo del cuerpo que RRHH escribió,
        porque la tabla no tiene versionado— sin nada que fotografiar. Un fake que no modela la
        forma real del retorno no puede desmentir que el payload esté vacío.
        """
        fila = self.filas.get(str(id_))
        # Igual que el repo real: con `empresa_id` provisto, el WHERE lleva las DOS condiciones,
        # así que una global (empresa NULL) nunca cae.
        if not fila or (empresa_id and fila.get("empresa_id") != str(empresa_id)):
            return None
        del self.filas[str(id_)]
        self.borrados.append(str(id_))
        return fila

    def find_by_id(self, id_):
        """El prior del diff de auditoría. Por ID, no por clave: la global comparte `bienvenida`
        con la propia, así que resolver por clave devolvería la fila equivocada — que es
        justamente lo que este fake, con sus tres filas, puede desmentir."""
        return self.filas.get(str(id_))

    def listar(self, empresa_id=None):
        return list(self.filas.values())


def _svc():
    repo = _Repo()
    return PlantillasService(repo=repo), repo


def _upsert(**kw) -> PlantillaUpsert:
    base = {"clave": "nueva", "contexto": "empleado", "asunto": "Hola", "cuerpo": "Texto"}
    return PlantillaUpsert(**{**base, **kw})


# ── 0. El guardián del fake ───────────────────────────────────────────────────

def test_el_fake_tiene_dos_propias_y_una_global_con_clave_repetida() -> None:
    """Sin esto, "editó la correcta" y "no pisó la global" pasarían sin comparar nada."""
    _, repo = _svc()
    assert len(repo.filas) == 3
    assert repo.filas[ID_GLOBAL]["empresa_id"] is None
    assert repo.filas[ID_GLOBAL]["clave"] == repo.filas[ID_BIENVENIDA]["clave"] == "bienvenida"
    assert repo.filas[ID_BIENVENIDA]["empresa_id"] == str(EMPRESA)


# ── 1. ALTA ───────────────────────────────────────────────────────────────────

class TestElAlta:

    def test_persiste_con_la_empresa_que_recibe_el_service(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(clave="corte_luz", contexto="ninguno"), EMPRESA)

        assert repo.guardadas[0]["empresa_id"] == str(EMPRESA)

    def test_con_OTRA_empresa_persiste_esa_otra(self) -> None:
        """Contrapeso: sin esto, un `empresa_id` hardcodeado pasaría el test de arriba."""
        svc, repo = _svc()

        svc.guardar(_upsert(clave="corte_luz", contexto="ninguno"), OTRA_EMPRESA)

        assert repo.guardadas[0]["empresa_id"] == str(OTRA_EMPRESA)

    def test_un_alta_NO_manda_id(self) -> None:
        """Con un `id` en el payload, el upsert del repo real actualizaría una fila existente en
        vez de crear una."""
        svc, repo = _svc()

        svc.guardar(_upsert(clave="corte_luz", contexto="ninguno"), EMPRESA)

        assert "id" not in repo.guardadas[0]

    def test_persiste_los_campos_tal_cual_vinieron(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(clave="k", contexto="ninguno", asunto="A", cuerpo="C"), EMPRESA)

        fila = repo.guardadas[0]
        assert (fila["clave"], fila["contexto"], fila["asunto"], fila["cuerpo"]) == \
            ("k", "ninguno", "A", "C")

    def test_la_respuesta_marca_es_global_en_False(self) -> None:
        """Se calcula desde `empresa_id`, que el service acaba de setear: una propia nunca es
        global, por construcción."""
        svc, _ = _svc()

        out = svc.guardar(_upsert(clave="k", contexto="ninguno"), EMPRESA)

        assert out.es_global is False and str(out.empresa_id) == str(EMPRESA)

    def test_un_insert_que_no_devuelve_nada_es_un_500_explicito(self) -> None:
        svc, repo = _svc()
        repo.devolver_none = True

        with pytest.raises(AppError) as exc:
            svc.guardar(_upsert(clave="k", contexto="ninguno"), EMPRESA)

        assert exc.value.code == "PLANTILLA_SAVE_ERROR" and exc.value.status_code == 500


# ── 2. EDICIÓN ────────────────────────────────────────────────────────────────

class TestLaEdicion:

    def test_actualiza_LA_QUE_SE_PIDE(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(id=ID_BIENVENIDA, clave="bienvenida", asunto="Editado"), EMPRESA)

        assert repo.guardadas[0]["id"] == ID_BIENVENIDA
        assert repo.filas[ID_BIENVENIDA]["asunto"] == "Editado"

    def test_y_NO_toca_la_otra_plantilla_de_la_empresa(self) -> None:
        """🔴 El motivo por el que el fake tiene DOS: con una sola, "editó la correcta" y "editó
        cualquiera" serían el mismo markup."""
        svc, repo = _svc()

        svc.guardar(_upsert(id=ID_BIENVENIDA, clave="bienvenida", asunto="Editado"), EMPRESA)

        assert repo.filas[ID_AVISO]["asunto"] == "Aviso"

    def test_una_edicion_SIEMPRE_escribe_la_empresa_del_request(self) -> None:
        """Ni la del body (el schema no la tiene) ni la de la fila que se está editando."""
        svc, repo = _svc()

        svc.guardar(_upsert(id=ID_BIENVENIDA, clave="bienvenida"), OTRA_EMPRESA)

        assert repo.guardadas[0]["empresa_id"] == str(OTRA_EMPRESA)


class TestLaGlobalNoSePisa:
    """🔴 Es el mismo par —global y propia con la misma clave— que destapó el bug del envío en
    modo consolidado. Acá se fija la mitad de escritura de esa regla."""

    def test_guardar_una_propia_con_la_clave_de_una_global_NO_toca_la_global(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(clave="bienvenida", asunto="Version de la empresa"), EMPRESA)

        assert repo.filas[ID_GLOBAL]["asunto"] == "Global"
        assert repo.filas[ID_GLOBAL]["empresa_id"] is None

    def test_lo_que_se_persiste_es_una_fila_NUEVA_de_la_empresa(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(clave="bienvenida", asunto="Version de la empresa"), EMPRESA)

        assert "id" not in repo.guardadas[0]          # no apunta a la global
        assert repo.guardadas[0]["empresa_id"] == str(EMPRESA)

    def test_la_global_sigue_existiendo_despues_de_guardar(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(clave="bienvenida"), EMPRESA)

        assert ID_GLOBAL in repo.filas

    def test_el_listado_marca_es_global_solo_en_la_que_no_tiene_empresa(self) -> None:
        """La bandera sale de `empresa_id is None`, no de un flag guardado que pueda mentir."""
        svc, _ = _svc()

        por_id = {str(p.id): p for p in svc.listar(EMPRESA).items}

        assert por_id[ID_GLOBAL].es_global is True
        assert por_id[ID_BIENVENIDA].es_global is False


# ── 3. 🔴 EL RECHAZO DE VARIABLES, POR EL CAMINO DE GUARDADO ──────────────────

class TestElGuardadoValidaLasVariables:
    """`test_mail_variables.py` prueba `variables_invalidas` COMO FUNCIÓN. Lo que se fija acá es
    que `guardar` la USE: que el 422 salga y que no se persista nada.

    Sin estos tests, borrar el `if malas: raise` de `plantillas_service` dejaba la suite entera
    en verde — la función seguía probada, y la plantilla rota se guardaba igual."""

    def test_una_variable_inventada_se_rechaza_con_422(self) -> None:
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.guardar(_upsert(cuerpo="Hola {{nombre_emplado}}"), EMPRESA)

        assert exc.value.code == "PLANTILLA_VARIABLES_INVALIDAS"
        assert exc.value.status_code == 422

    def test_y_NO_se_persiste_nada(self) -> None:
        """Si el service guardara y validara después, el test de arriba pasaría igual y la
        plantilla rota quedaría en la base."""
        svc, repo = _svc()

        with pytest.raises(AppError):
            svc.guardar(_upsert(cuerpo="Hola {{nombre_emplado}}"), EMPRESA)

        assert repo.guardadas == []

    def test_el_mensaje_dice_CUAL_variable_esta_mal(self) -> None:
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.guardar(_upsert(cuerpo="{{nombre_emplado}}"), EMPRESA)

        assert "nombre_emplado" in exc.value.message

    def test_una_variable_de_OTRO_contexto_tambien_se_rechaza(self) -> None:
        """`{{fecha_desde}}` vale en 'vacacion' y no en 'empleado'. Es el caso central del diseño
        de contextos, y hasta ahora nadie lo probaba por el camino real."""
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.guardar(_upsert(contexto="empleado", cuerpo="Desde {{fecha_desde}}"), EMPRESA)

        assert exc.value.code == "PLANTILLA_VARIABLES_INVALIDAS" and repo.guardadas == []

    def test_esa_MISMA_plantilla_en_su_contexto_SI_se_guarda(self) -> None:
        """🔴 EL CONTRAPESO. Sin esto, una validación que rechace SIEMPRE pasaría todo lo de
        arriba y dejaría el módulo inusable — nadie podría guardar una plantilla."""
        svc, repo = _svc()

        svc.guardar(_upsert(contexto="vacacion", cuerpo="Desde {{fecha_desde}}"), EMPRESA)

        assert len(repo.guardadas) == 1
        assert repo.guardadas[0]["cuerpo"] == "Desde {{fecha_desde}}"

    def test_una_plantilla_sin_variables_se_guarda(self) -> None:
        svc, repo = _svc()

        svc.guardar(_upsert(contexto="ninguno", cuerpo="Sin variables."), EMPRESA)

        assert len(repo.guardadas) == 1

    def test_un_contexto_inexistente_se_rechaza_ANTES_que_las_variables(self) -> None:
        """El orden importa: con un contexto desconocido, TODA variable sería inválida y el
        mensaje hablaría de las variables en vez del problema real."""
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.guardar(_upsert(contexto="inventado", cuerpo="{{nombre_empleado}}"), EMPRESA)

        assert exc.value.code == "PLANTILLA_CONTEXTO_INVALIDO" and repo.guardadas == []


# ── 4. BORRADO ────────────────────────────────────────────────────────────────

class TestElBorrado:

    def test_borra_la_que_se_pide(self) -> None:
        svc, repo = _svc()

        svc.borrar(ID_AVISO, EMPRESA)

        assert ID_AVISO not in repo.filas and repo.borrados == [ID_AVISO]

    def test_y_SOLO_esa(self) -> None:
        svc, repo = _svc()

        svc.borrar(ID_AVISO, EMPRESA)

        assert ID_BIENVENIDA in repo.filas and ID_GLOBAL in repo.filas

    def test_una_plantilla_de_OTRA_empresa_no_se_borra_y_da_404(self) -> None:
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.borrar(ID_AVISO, OTRA_EMPRESA)

        assert exc.value.code == "PLANTILLA_NOT_FOUND" and exc.value.status_code == 404
        assert ID_AVISO in repo.filas

    def test_una_GLOBAL_no_se_puede_borrar_desde_una_empresa(self) -> None:
        """🔴 Borrarla la sacaría para TODAS las demás empresas. La guarda vive en el WHERE del
        repo; el fake la modela, así que este test la puede desmentir."""
        svc, repo = _svc()

        with pytest.raises(AppError) as exc:
            svc.borrar(ID_GLOBAL, EMPRESA)

        assert exc.value.code == "PLANTILLA_NOT_FOUND"
        assert ID_GLOBAL in repo.filas

    def test_una_plantilla_inexistente_da_404_y_no_rompe(self) -> None:
        svc, _ = _svc()

        with pytest.raises(AppError) as exc:
            svc.borrar(uuid4(), EMPRESA)

        assert exc.value.code == "PLANTILLA_NOT_FOUND"

    def test_el_404_de_inexistente_y_el_de_otra_empresa_son_IDENTICOS(self) -> None:
        """Patrón de barrera de empresa: mismo status, mismo code, mismo mensaje. Un 403 o un
        texto distinto confirmaría que la plantilla existe y es de otro."""
        svc, _ = _svc()
        svc2, _ = _svc()

        with pytest.raises(AppError) as ajena:
            svc.borrar(ID_AVISO, OTRA_EMPRESA)
        with pytest.raises(AppError) as inexistente:
            svc2.borrar(uuid4(), EMPRESA)

        assert (ajena.value.code, ajena.value.status_code, ajena.value.message) == \
               (inexistente.value.code, inexistente.value.status_code, inexistente.value.message)
