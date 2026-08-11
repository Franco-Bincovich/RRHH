"""
El paso 2 del link público: cargar horas o una licencia.

## 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO EN LOS FAKES PARA QUE ESTOS TESTS FALLEN?

**1. 🔴 `_HorasFalso` tendría que devolver 0 horas previas siempre.** Es el punto entero del tope:
con un fake que no trae cargas anteriores, "valida la SUMA del día" y "valida solo esta carga"
dan idéntico y el test no prueba lo que dice su nombre. `_HorasFalso.previas` se precarga por día
y `total_horas_del_dia` lee de ahí, así que sacarle la suma al service rojea.

**2. 🔴 La sesión tendría que resolver al mismo empleado que el body.** El body de carga NO TIENE
`empleado_id` —el schema no lo declara— así que la suplantación se prueba por el único camino que
queda: mandar campos extra en el dict y verificar que el request los IGNORA y que lo guardado
lleva el empleado de la SESIÓN. La sesión resuelve a `EMPLEADO_SESION` y el body intenta
`EMPLEADO_IMPOSTOR`, que son distintos: si el service leyera el body, la fila guardada lo diría.

**3. `hoy` tendría que salir del reloj.** Se inyecta, así que los bordes de la ventana de 30 días
se prueban en el día exacto y no dependen de cuándo corre la suite.

**4. `_AusenciasFalso` tendría que devolver una fila prefabricada.** Guarda los argumentos que
recibió y arma la respuesta con ellos, así que un service que mande `justificada=True` o el tipo
equivocado se ve.
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

import hashlib  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402

from schemas.horas_publico import CargaHorasRequest, CargaLicenciaRequest  # noqa: E402
from services._carga_licencia import (  # noqa: E402
    HORAS_POR_DIA_POR_DEFECTO, TIPO_LICENCIA_ID,
)
from services._carga_reglas import DIAS_HACIA_ATRAS, MAX_HORAS_DIA  # noqa: E402
from services.carga_horas_service import CargaHorasService  # noqa: E402
from utils.errors import AppError  # noqa: E402

HOY = date(2026, 8, 9)
EMPLEADO_SESION, EMPRESA_SESION = str(uuid4()), str(uuid4())
EMPLEADO_IMPOSTOR, EMPRESA_IMPOSTORA = str(uuid4()), str(uuid4())
CLIENTE_OK, CLIENTE_BAJA, CLIENTE_INEXISTENTE = str(uuid4()), str(uuid4()), str(uuid4())
# 🔴 El catálogo es GLOBAL (mig 108): estos clientes no cuelgan de ninguna empresa, y en
# particular NO de `EMPRESA_SESION`. Que la sesión sea de una empresa y el catálogo de ninguna es
# lo que hace falsable "el empleado ve clientes que no son de su sociedad".
TOKEN = "t" * 43


class _SesionesFalso:
    """Resuelve el token a UNA identidad. Es la única fuente del empleado del paso 2."""

    def buscar_vigente(self, token_hash: str, ahora: str):
        if token_hash != hashlib.sha256(TOKEN.encode()).hexdigest():
            return None
        return {"empleado_id": EMPLEADO_SESION, "empresa_id": EMPRESA_SESION}


class _HorasFalso:
    """Guarda lo que recibe y RESPONDE CON CARGAS PREVIAS. Ver el punto 1 del encabezado."""

    def __init__(self, previas: dict | None = None) -> None:
        self.previas = previas or {}          # {"2026-08-09": 8.0}
        self.guardadas: list[dict] = []

    def total_horas_del_dia(self, empleado_id: str, fecha: str) -> float:
        return float(self.previas.get((empleado_id, fecha), 0.0))

    def buscar_por_idempotencia(self, idem: str):
        for g in self.guardadas:
            if g.get("idempotencia") == idem:
                return _fila(g)
        return None

    def save(self, **kw):
        self.guardadas.append(kw)
        return _fila(kw)


def _fila(kw: dict):
    """Respuesta armada A PARTIR de lo guardado, nunca de una constante del test."""
    return SimpleNamespace(
        id=uuid4(), fecha=date.fromisoformat(kw["fecha"]), horas=kw["horas"],
        modalidad=kw.get("modalidad"), cliente_nombre="Acme",
        proyecto_texto=kw.get("proyecto_texto"), tarea_texto=kw.get("tarea_texto"),
        empleado_id=kw.get("empleado_id"), empresa_id=kw.get("empresa_id"),
    )


class _ClientesFalso:
    """Catálogo GLOBAL, sin empresa. Devuelve conjuntos DISTINTOS según `incluir_inactivos` y
    REGISTRA cada llamada a `find_all` con su argumento.

    🔴 Las dos cosas son lo que permite desmentir el bug de `carga_horas_service:117`: si el
    service volviera a pasar un posicional, ligaría contra `incluir_inactivos`, un UUID es truthy
    y el listado incluiría al dado de baja. `llamadas_find_all` lo prueba de frente y el conjunto
    devuelto lo prueba por su efecto — con un fake que devolviera SIEMPRE la misma lista, ninguno
    de los dos tests podría fallar."""

    def __init__(self) -> None:
        self.llamadas_find_all: list = []

    def find_all(self, incluir_inactivos: bool = False):
        self.llamadas_find_all.append(incluir_inactivos)
        activos = [SimpleNamespace(id=CLIENTE_OK, nombre="Acme", activo=True)]
        if incluir_inactivos:
            activos.append(SimpleNamespace(id=CLIENTE_BAJA, nombre="Vieja SA", activo=False))
        return activos

    def find_by_id(self, cliente_id: str):
        if cliente_id not in (CLIENTE_OK, CLIENTE_BAJA):
            return None
        return SimpleNamespace(id=cliente_id, nombre="Acme", activo=cliente_id != CLIENTE_BAJA)


class _AusenciasFalso:
    def __init__(self, explota: bool = False) -> None:
        self.explota, self.guardadas = explota, []

    def save(self, empleado_id, empresa_id, tipo_id, desde, hasta, dias, justificada, motivo):
        if self.explota:
            raise RuntimeError("duplicate key value violates unique constraint")
        kw = dict(empleado_id=empleado_id, empresa_id=empresa_id, tipo_id=tipo_id,
                  fecha_desde=desde, fecha_hasta=hasta, dias=dias,
                  justificada=justificada, motivo=motivo)
        self.guardadas.append(kw)
        return SimpleNamespace(id=uuid4(), **kw)


class _DatosFalso:
    def __init__(self, horas=None) -> None:
        self.horas = horas

    def horas_contrato(self, empleado_id: str):
        return self.horas


def _svc(horas=None, ausencias=None, datos=None) -> CargaHorasService:
    return CargaHorasService(sesiones=_SesionesFalso(), horas=horas or _HorasFalso(),
                             clientes=_ClientesFalso(), ausencias=ausencias or _AusenciasFalso(),
                             datos=datos or _DatosFalso(8))


def _req(**kw) -> CargaHorasRequest:
    base = {"token": TOKEN, "fecha": HOY, "horas": 4.0, "modalidad": "home_office",
            "cliente_id": CLIENTE_OK}
    return CargaHorasRequest(**{**base, **kw})


def _error(fn) -> AppError:
    with pytest.raises(AppError) as exc:
        fn()
    return exc.value


# ── El select público: catálogo global ────────────────────────────────────────


class TestClientesDisponibles:
    """🔴 EL BLOQUE QUE MOTIVA TODO L2-L4, medido en producción: los 3 clientes cargados son
    todos de UNA de las dos sociedades. Hasta la 107 el empleado de la otra veía un select vacío
    (y de hecho ni llegaba: el gate lo rechazaba antes).

    ¿Qué tendría que ser distinto en el fake para que estos tests fallen? Que `_ClientesFalso`
    devolviera siempre la misma lista. Devuelve conjuntos DISTINTOS según `incluir_inactivos` y
    guarda cada llamada, así que las dos regresiones posibles —volver a filtrar por empresa, y
    volver a pasar un posicional— se ven por separado.
    """

    def _svc_con(self, clientes: _ClientesFalso) -> CargaHorasService:
        return CargaHorasService(sesiones=_SesionesFalso(), horas=_HorasFalso(),
                                 clientes=clientes, ausencias=_AusenciasFalso(),
                                 datos=_DatosFalso(8))

    def test_el_empleado_ve_clientes_que_no_son_de_su_empresa(self) -> None:
        """La sesión es de `EMPRESA_SESION`; el catálogo no cuelga de ninguna empresa. Antes esto
        devolvía vacío para todo el padrón de la sociedad sin clientes propios."""
        clientes = _ClientesFalso()
        r = self._svc_con(clientes).clientes_disponibles(TOKEN)
        assert [str(c.id) for c in r.items] == [CLIENTE_OK]

    def test_y_puede_imputar_horas_contra_ese_cliente(self) -> None:
        """Verlo no alcanza: el circuito completo es ver + imputar. Si `_verificar_cliente`
        volviera a exigir empresa, esto rojea aunque el select siga andando."""
        horas = _HorasFalso()
        svc = CargaHorasService(sesiones=_SesionesFalso(), horas=horas,
                                clientes=_ClientesFalso(), ausencias=_AusenciasFalso(),
                                datos=_DatosFalso(8))
        svc.cargar_horas(_req(cliente_id=CLIENTE_OK), hoy=HOY)
        assert horas.guardadas[0]["cliente_id"] == CLIENTE_OK

    def test_un_cliente_dado_de_baja_no_aparece_en_el_select(self) -> None:
        """🔴 EL BUG DE `:117`, por su EFECTO. Si el service pasa un posicional, liga contra
        `incluir_inactivos`, un UUID es truthy y el dado de baja entra en la lista — sin ningún
        error, y el usuario se entera recién con un CLIENTE_INVALIDO al final del formulario."""
        clientes = _ClientesFalso()
        r = self._svc_con(clientes).clientes_disponibles(TOKEN)
        assert CLIENTE_BAJA not in [str(c.id) for c in r.items]

    def test_find_all_se_llama_sin_argumentos(self) -> None:
        """El mismo bug, de frente. Los dos tests hacen falta: éste se rompe con CUALQUIER
        posicional, aunque el fake decidiera devolver lo mismo igual."""
        clientes = _ClientesFalso()
        self._svc_con(clientes).clientes_disponibles(TOKEN)
        assert clientes.llamadas_find_all == [False], "se le pasó algo a find_all()"

    def test_un_token_invalido_no_lista_nada(self) -> None:
        """`resolver` sigue siendo la autenticación aunque ya no se use su empresa."""
        clientes = _ClientesFalso()
        with pytest.raises(AppError) as exc:
            self._svc_con(clientes).clientes_disponibles("x" * 43)
        assert exc.value.code == "SESION_INVALIDA"
        assert clientes.llamadas_find_all == []


# ── El caso normal ────────────────────────────────────────────────────────────


class TestCargaNormal:
    def test_sin_proyecto_ni_tarea_funciona(self) -> None:
        """🔴 ES EL CASO NORMAL, no el borde: proyecto y tarea son texto libre y OPCIONALES."""
        horas = _HorasFalso()
        resp = _svc(horas).cargar_horas(_req(), hoy=HOY)
        assert (resp.horas, resp.modalidad) == (4.0, "home_office")
        assert resp.proyecto_texto is None and resp.tarea_texto is None
        # El service los pasa en None y es el REPO el que decide no mandarlos al INSERT
        # (`_OPCIONALES` + `is not None`). Afirmarlo acá sería mirar la capa equivocada: que la
        # clave no llegue al payload está cubierto en `test_horas_carga_directa`.
        assert horas.guardadas[0]["proyecto_texto"] is None
        assert horas.guardadas[0]["tarea_texto"] is None

    def test_con_proyecto_y_tarea_los_guarda(self) -> None:
        horas = _HorasFalso()
        _svc(horas).cargar_horas(_req(proyecto_texto="Migración", tarea_texto="Reunión"), hoy=HOY)
        assert horas.guardadas[0]["proyecto_texto"] == "Migración"
        assert horas.guardadas[0]["tarea_texto"] == "Reunión"

    def test_varias_cargas_el_mismo_dia_estan_permitidas(self) -> None:
        """Es una decisión de producto: la persona detalla distintas tareas."""
        horas = _HorasFalso()
        svc = _svc(horas)
        svc.cargar_horas(_req(horas=4.0), hoy=HOY)
        horas.previas[(EMPLEADO_SESION, str(HOY))] = 4.0
        svc.cargar_horas(_req(horas=3.0, tarea_texto="Otra"), hoy=HOY)
        assert len(horas.guardadas) == 2

    def test_no_escribe_asignacion_ni_proyecto_ni_snapshot(self) -> None:
        """La fila tiene que quedar en la FORMA de carga directa, o el CHECK
        `horas_proyecto_forma_check` la rechaza en la base."""
        horas = _HorasFalso()
        _svc(horas).cargar_horas(_req(), hoy=HOY)
        assert not {"asignacion_id", "proyecto_id", "valor_hora_snapshot"} & set(horas.guardadas[0])


# ── La identidad ──────────────────────────────────────────────────────────────


class TestLaIdentidadSaleDeLaSesion:
    def test_el_empleado_guardado_es_el_de_la_sesion(self) -> None:
        horas = _HorasFalso()
        _svc(horas).cargar_horas(_req(), hoy=HOY)
        g = horas.guardadas[0]
        assert g["empleado_id"] == EMPLEADO_SESION
        assert g["empresa_id"] == EMPRESA_SESION == g["empleado_empresa_id"]

    def test_el_body_no_puede_traer_empleado_id(self) -> None:
        """🔴 LA SUPLANTACIÓN. El schema ni siquiera declara el campo, así que un body que lo
        mande lo pierde en la validación — y aunque llegara, el service lee la sesión.

        Sin este test, "la identidad sale de la sesión" sería una afirmación del docstring: acá
        se manda un empleado DISTINTO al de la sesión y se verifica que lo guardado es el de la
        sesión. Si el service leyera el body, la fila diría EMPLEADO_IMPOSTOR.
        """
        cuerpo = _req().model_dump()
        cuerpo.update(empleado_id=EMPLEADO_IMPOSTOR, empresa_id=EMPRESA_IMPOSTORA)
        req = CargaHorasRequest(**cuerpo)
        assert not hasattr(req, "empleado_id"), "el schema aceptó un empleado_id del cliente"

        horas = _HorasFalso()
        _svc(horas).cargar_horas(req, hoy=HOY)
        assert horas.guardadas[0]["empleado_id"] == EMPLEADO_SESION
        assert EMPLEADO_IMPOSTOR not in str(horas.guardadas[0])

    def test_un_token_invalido_no_escribe_nada(self) -> None:
        horas = _HorasFalso()
        err = _error(lambda: _svc(horas).cargar_horas(_req(token="x" * 43), hoy=HOY))
        assert (err.code, err.status_code) == ("SESION_INVALIDA", 401)
        assert horas.guardadas == []

    def test_un_cliente_inexistente_no_es_elegible(self) -> None:
        """Reemplaza a `test_el_cliente_se_valida_contra_la_empresa_de_la_sesion`: con el catálogo
        global ya no hay "cliente ajeno", pero sigue habiendo "no existe" y sale por el mismo
        error. Sin este caso, un `_verificar_cliente` que aceptara cualquier id pasaría."""
        err = _error(lambda: _svc().cargar_horas(_req(cliente_id=CLIENTE_INEXISTENTE), hoy=HOY))
        assert (err.code, err.status_code) == ("CLIENTE_INVALIDO", 422)

    def test_un_cliente_dado_de_baja_no_es_elegible(self) -> None:
        err = _error(lambda: _svc().cargar_horas(_req(cliente_id=CLIENTE_BAJA), hoy=HOY))
        assert err.code == "CLIENTE_INVALIDO"


# ── El tope de 12 ─────────────────────────────────────────────────────────────


class TestTopeDeHoras:
    """🔴 El fake trae CARGAS PREVIAS. Sin eso, "suma lo que ya existe" y "valida solo esta
    carga" son indistinguibles — que es exactamente el bug que este bloque persigue."""

    def test_suma_las_cargas_que_ya_existen(self) -> None:
        horas = _HorasFalso({(EMPLEADO_SESION, str(HOY)): 8.0})
        err = _error(lambda: _svc(horas).cargar_horas(_req(horas=5.0), hoy=HOY))
        assert (err.code, err.status_code) == ("TOPE_HORAS_DIA", 422)
        assert horas.guardadas == []

    def test_el_borde_exacto_entra(self) -> None:
        """8 + 4 = 12 tiene que pasar. Sin este contraste, un service que rechaza todo pasaría."""
        horas = _HorasFalso({(EMPLEADO_SESION, str(HOY)): 8.0})
        assert _svc(horas).cargar_horas(_req(horas=4.0), hoy=HOY).horas == 4.0

    def test_un_minuto_mas_que_el_borde_no_entra(self) -> None:
        horas = _HorasFalso({(EMPLEADO_SESION, str(HOY)): 8.0})
        assert _error(lambda: _svc(horas).cargar_horas(_req(horas=4.5), hoy=HOY)).code \
            == "TOPE_HORAS_DIA"

    def test_el_mensaje_dice_cuanto_queda(self) -> None:
        """Alguien con 10 cargadas que intenta 4 tiene que saber que puede pedir 2."""
        horas = _HorasFalso({(EMPLEADO_SESION, str(HOY)): 10.0})
        msg = _error(lambda: _svc(horas).cargar_horas(_req(horas=4.0), hoy=HOY)).message
        assert "10" in msg and "2" in msg

    def test_las_previas_son_del_dia_de_la_carga_y_no_de_otro(self) -> None:
        """Si el service consultara el día equivocado, un día lleno bloquearía a uno vacío."""
        ayer = HOY - timedelta(days=1)
        horas = _HorasFalso({(EMPLEADO_SESION, str(ayer)): 12.0})
        assert _svc(horas).cargar_horas(_req(fecha=HOY, horas=8.0), hoy=HOY).horas == 8.0

    def test_el_schema_ya_corta_una_carga_mayor_al_tope(self) -> None:
        with pytest.raises(Exception):
            _req(horas=MAX_HORAS_DIA + 1)


# ── La ventana de 30 días ─────────────────────────────────────────────────────


class TestVentanaDeFechas:
    def test_hoy_entra(self) -> None:
        assert _svc().cargar_horas(_req(fecha=HOY), hoy=HOY).fecha == HOY

    def test_el_borde_de_30_dias_atras_entra(self) -> None:
        borde = HOY - timedelta(days=DIAS_HACIA_ATRAS)
        assert _svc().cargar_horas(_req(fecha=borde), hoy=HOY).fecha == borde

    def test_un_dia_mas_viejo_que_el_borde_no_entra(self) -> None:
        """El borde exacto de un lado y del otro: sin los dos, un `<` en vez de `<=` no se ve."""
        viejo = HOY - timedelta(days=DIAS_HACIA_ATRAS + 1)
        assert _error(lambda: _svc().cargar_horas(_req(fecha=viejo), hoy=HOY)).code \
            == "FECHA_MUY_VIEJA"

    def test_el_futuro_se_rechaza(self) -> None:
        manana = HOY + timedelta(days=1)
        err = _error(lambda: _svc().cargar_horas(_req(fecha=manana), hoy=HOY))
        assert (err.code, err.status_code) == ("FECHA_FUTURA", 422)

    def test_futuro_y_viejo_dan_errores_distintos(self) -> None:
        """Acá NO hay rechazo único, al revés que en la identificación: el que pregunta ya está
        autenticado por su sesión y necesita saber cuál de los dos límites tocó."""
        futuro = _error(lambda: _svc().cargar_horas(_req(fecha=HOY + timedelta(days=1)), hoy=HOY))
        viejo = _error(lambda: _svc().cargar_horas(
            _req(fecha=HOY - timedelta(days=99)), hoy=HOY))
        assert futuro.code != viejo.code


# ── El doble tap ──────────────────────────────────────────────────────────────


class TestDobleTap:
    def test_el_reenvio_devuelve_la_carga_ya_creada_y_no_duplica(self) -> None:
        horas = _HorasFalso()
        svc = _svc(horas)
        primera = svc.cargar_horas(_req(idempotencia="abc"), hoy=HOY)
        segunda = svc.cargar_horas(_req(idempotencia="abc"), hoy=HOY)
        assert len(horas.guardadas) == 1
        assert (primera.horas, segunda.horas) == (4.0, 4.0)

    def test_el_reenvio_no_se_cae_por_el_tope(self) -> None:
        """🔴 El corte por idempotencia va ANTES de validar. Si fuera después, un doble tap sobre
        la ÚLTIMA carga del día daría TOPE_HORAS_DIA — un error, cuando la carga ya está hecha."""
        horas = _HorasFalso()
        svc = _svc(horas)
        svc.cargar_horas(_req(horas=12.0, idempotencia="abc"), hoy=HOY)
        horas.previas[(EMPLEADO_SESION, str(HOY))] = 12.0
        assert svc.cargar_horas(_req(horas=12.0, idempotencia="abc"), hoy=HOY).horas == 12.0

    def test_sin_idempotencia_no_hay_proteccion_y_eso_es_visible(self) -> None:
        """El campo es opcional; sin él el doble tap crea dos filas. Queda declarado en el test
        para que nadie crea que la protección es automática."""
        horas = _HorasFalso()
        svc = _svc(horas)
        svc.cargar_horas(_req(), hoy=HOY)
        svc.cargar_horas(_req(), hoy=HOY)
        assert len(horas.guardadas) == 2


# ── La licencia ───────────────────────────────────────────────────────────────


def _lic(**kw) -> CargaLicenciaRequest:
    base = {"token": TOKEN, "fecha_desde": HOY - timedelta(days=2), "fecha_hasta": HOY}
    return CargaLicenciaRequest(**{**base, **kw})


class TestLicencia:
    def test_calcula_dias_y_horas_con_la_jornada_del_empleado(self) -> None:
        aus = _AusenciasFalso()
        resp = _svc(ausencias=aus, datos=_DatosFalso(6)).cargar_licencia(_lic(), hoy=HOY)
        assert resp.dias == 3                       # extremos incluidos
        assert resp.horas_equivalentes == 18.0      # 3 × 6
        assert resp.horas_por_dia_estimadas is False

    def test_sin_horas_contrato_asume_8_y_lo_avisa(self) -> None:
        """🔴 `horas_contrato` está en 0/31: NO avisar sería devolver un número inventado como si
        fuera dato. El flag es lo que le permite a la pantalla decir "se asumieron 8 h/día"."""
        resp = _svc(datos=_DatosFalso(None)).cargar_licencia(_lic(), hoy=HOY)
        assert resp.horas_equivalentes == 3.0 * HORAS_POR_DIA_POR_DEFECTO
        assert resp.horas_por_dia_estimadas is True

    def test_usa_el_tipo_licencia_por_id_y_no_por_nombre(self) -> None:
        """Por nombre se rompería el día que RRHH lo renombre desde configuración."""
        aus = _AusenciasFalso()
        _svc(ausencias=aus).cargar_licencia(_lic(), hoy=HOY)
        assert aus.guardadas[0]["tipo_id"] == TIPO_LICENCIA_ID

    def test_justificada_siempre_en_false(self) -> None:
        """Un empleado no puede justificarse a sí mismo: es el juicio que emite RRHH."""
        aus = _AusenciasFalso()
        _svc(ausencias=aus).cargar_licencia(_lic(observaciones="Trámite"), hoy=HOY)
        assert aus.guardadas[0]["justificada"] is False
        assert aus.guardadas[0]["motivo"] == "Trámite"

    def test_la_identidad_tambien_sale_de_la_sesion(self) -> None:
        aus = _AusenciasFalso()
        _svc(ausencias=aus).cargar_licencia(_lic(), hoy=HOY)
        assert aus.guardadas[0]["empleado_id"] == EMPLEADO_SESION
        assert aus.guardadas[0]["empresa_id"] == EMPRESA_SESION

    def test_el_body_de_licencia_no_tiene_campos_de_horas(self) -> None:
        """La regla "al elegir licencia la carga de horas se desactiva" está en el TIPO: no es
        una validación cruzada que alguien pueda aflojar, son campos que no existen."""
        campos = set(CargaLicenciaRequest.model_fields)
        assert not campos & {"horas", "modalidad", "cliente_id", "proyecto_texto", "tarea_texto"}

    def test_un_rango_invertido_se_rechaza(self) -> None:
        err = _error(lambda: _svc().cargar_licencia(
            _lic(fecha_desde=HOY, fecha_hasta=HOY - timedelta(days=3)), hoy=HOY))
        assert (err.code, err.status_code) == ("RANGO_INVALIDO", 422)

    def test_la_ventana_se_valida_en_los_dos_extremos(self) -> None:
        """Validar solo `desde` dejaría pasar un rango que empieza ayer y termina el año que viene."""
        assert _error(lambda: _svc().cargar_licencia(
            _lic(fecha_desde=HOY - timedelta(days=1),
                 fecha_hasta=HOY + timedelta(days=30)), hoy=HOY)).code == "FECHA_FUTURA"
        assert _error(lambda: _svc().cargar_licencia(
            _lic(fecha_desde=HOY - timedelta(days=99), fecha_hasta=HOY), hoy=HOY)).code \
            == "FECHA_MUY_VIEJA"

    def test_el_doble_tap_lo_atrapa_la_base_y_sale_legible(self) -> None:
        """La migración 089 está CORRIDA (verificado contra el catálogo): existe
        `uq_ausencia_empleado_rango_tipo`. Acá solo se traduce ese choque a un mensaje."""
        err = _error(lambda: _svc(ausencias=_AusenciasFalso(explota=True))
                     .cargar_licencia(_lic(), hoy=HOY))
        assert (err.code, err.status_code) == ("LICENCIA_DUPLICADA", 409)


class TestElIdDelTipoEsUnEspejo:
    def test_el_literal_del_codigo_coincide_con_el_de_la_migracion(self) -> None:
        """🔴 `TIPO_LICENCIA_ID` es un espejo del uuid sembrado por SQL, y no hay forma de
        evitarlo. Este test es lo único que impide que se separen en silencio: si divergen, la
        carga de licencias apuntaría a un tipo que no existe y fallaría contra la FK."""
        from pathlib import Path
        mig = (Path(__file__).resolve().parents[1] / "migrations"
               / "107_tipo_ausencia_licencia.sql").read_text(encoding="utf-8")
        assert TIPO_LICENCIA_ID in mig
        assert "'Licencia'" in mig and "true, true, true" in mig.replace(", NULL", "")
