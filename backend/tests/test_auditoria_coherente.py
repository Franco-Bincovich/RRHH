"""
🔴 BARRIDO ESTRUCTURAL — un módulo que ya audita alguna operación tiene que auditarlas TODAS.

POR QUÉ ESTA REGLA Y NO "TODO LO QUE ESCRIBE AUDITA". No existe una fuente de verdad de qué
entidades deben auditarse: es una definición de producto que todavía no se tomó. Con la regla
amplia, 44 métodos quedarían en un limbo que el código no resuelve, y la lista de excepciones
diría "no sé" — que es basura que nadie limpia y que tapa el próximo caso.
Esta regla, en cambio, SÍ tiene fuente de verdad, y es el propio módulo: si un service audita el
alta y no la edición, eso es olvido, no criterio. Es la clase que ya se cerró a mano tres veces
(baja de vacante sin alta, subir adjunto sin marcar principal, alta de empresa sin logo).

🚩 ALCANCE, Y CÓMO **NO** HAY QUE LEER EL VERDE DE ESTE ARCHIVO.
Solo se miran los módulos que YA emiten al menos un evento. Los **44 métodos de escritura en
módulos sin ninguna auditoría** —objetivos, áreas, capacitaciones, proyectos, inventario,
onboarding_templates, horas, asignaciones, tipos_ausencia, configuración, plantillas— quedan
FUERA POR CONSTRUCCIÓN, no por estar exentos. Este test en verde significa "ningún módulo audita
a medias", NUNCA "todo lo que escribe audita". Esos 44 esperan la definición de producto.

⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
  · El descubrimiento es por AST con resolución de tipos y propagación ascendente; no hay lista
    escrita a mano de qué mirar. Un módulo nuevo que audite queda barrido solo.
  · Los siete falsos positivos medidos en el diagnóstico están cubiertos y explicados uno por uno
    en `tests/_barrido_auditoria.py`.
  · Las tres guardas de mínimo corren ANTES de comparar: si el descubrimiento se rompe, esto
    falla en vez de pasar habiendo mirado cero escrituras.

🔴 LÍMITE CONOCIDO, DECLARADO A PROPÓSITO — UN ANCESTRO QUE AUDITA OTRA COSA DA POR CUBIERTA LA
ESCRITURA. La cobertura se resuelve por el grafo de llamadas: si alguna función del camino emite
un evento, la escritura cuenta como auditada. El barrido NO compara la entidad del evento contra
la tabla escrita, porque el payload no siempre la nombra. Es generoso en la dirección peligrosa
(sub-reporta) y es exactamente el modo de falla que dejó pasar el import de costos, que escribía
sueldos dentro de un flujo que sí emitía otros eventos. No tiene solución automática: cerrarlo
pide que el payload declare la tabla, que hoy no hace. Mientras tanto, este test cubre la
omisión TOTAL de eventos en un módulo, no la omisión de UNO dentro de un flujo que emite otros.
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

from tests._barrido_auditoria import (  # noqa: E402
    escrituras_del_alcance, modulos_que_auditan, sin_auditar, total_escritores,
)

# ── Escrituras sin evento, declaradas ─────────────────────────────────────────
# La clave es `archivo::funcion` y el valor su motivo. Las dos que hay son DEUDA, no criterio:
# el barrido las encontró el día que nació y no se arreglaron acá porque los dos archivos están
# sin margen de líneas (150/150 y 147/150) y tocarlos exige otra división — que es una tarea
# propia, no un efecto colateral de escribir un test.
_SIN_EVENTO_DECLARADAS: dict[str, str] = {
    "services/_vacaciones_write.py::crear":
        "🔴 DEUDA, NO INTENCIONAL. El ALTA de una solicitud de vacaciones no emite evento, "
        "mientras `cancel` y `actualizar` del mismo archivo sí, y su módulo hermano "
        "`_ausencias_write.crear` también. No existe ningún `payload_alta_vacacion` en el repo. "
        "Bloqueado por líneas: _vacaciones_write.py está en 150/150.",

    "services/empresa_service.py::EmpresaService.update_empresa":
        "🔴 DEUDA, NO INTENCIONAL. La edición genérica de empresa no emite evento, mientras el "
        "alta, el toggle de activa y el cambio de logo sí. Bloqueado por líneas: "
        "empresa_service.py está en 147/150 y el evento no entra sin dividir.",
}

# ── Guardas de mínimo ─────────────────────────────────────────────────────────
# Criterio: ~25% por debajo del real del 7/8/2026 (24 módulos que auditan, 125 métodos de
# escritura en repositories/, 50 escrituras dentro del alcance). Igual que en
# `test_callers_huerfanos` y `test_selects_repos`. El margen absorbe la baja normal del repo
# —que borra código muerto y parte archivos seguido— pero no una ROTURA del descubrimiento, que
# no baja un 25%: colapsa. Si el mapa de atributos deja de resolverse, si `app`/los árboles no
# se parsean o si cambia la estructura de directorios, los tres conteos se van al piso.
_MINIMO_MODULOS_QUE_AUDITAN = 18
_MINIMO_METODOS_DE_ESCRITURA = 93
_MINIMO_ESCRITURAS_EN_ALCANCE = 37


class TestElBarridoEstaMirandoAlgo:
    """Sin esto, todo lo de abajo pasa en el vacío."""

    def test_descubre_modulos_que_auditan(self) -> None:
        n = len(modulos_que_auditan())
        assert n >= _MINIMO_MODULOS_QUE_AUDITAN, (
            f"solo {n} módulos con auditoría (mínimo {_MINIMO_MODULOS_QUE_AUDITAN}). No es que "
            "se borró auditoría: es que la detección de `registrar` se rompió.")

    def test_descubre_metodos_de_escritura(self) -> None:
        n = total_escritores()
        assert n >= _MINIMO_METODOS_DE_ESCRITURA, (
            f"solo {n} métodos de escritura en repositories/ (mínimo "
            f"{_MINIMO_METODOS_DE_ESCRITURA}): se rompió la detección de insert/update/delete.")

    def test_descubre_escrituras_dentro_del_alcance(self) -> None:
        """La guarda que más importa: es el conjunto que el test de abajo compara. Si la
        resolución de `self._repo` → clase se rompe, este conteo cae y los otros dos no."""
        n = len(escrituras_del_alcance())
        assert n >= _MINIMO_ESCRITURAS_EN_ALCANCE, (
            f"solo {n} escrituras alcanzadas (mínimo {_MINIMO_ESCRITURAS_EN_ALCANCE}): la "
            "resolución de tipos del `__init__` dejó de mapear atributos a repos.")


class TestCoherenciaDeAuditoria:

    def test_ningun_modulo_audita_a_medias(self) -> None:
        """LA REGLA. Un módulo que ya emite eventos no puede tener escrituras mudas."""
        nuevas = [f"{arch}::{qual}" for arch, qual, _ in sin_auditar()
                  if f"{arch}::{qual}" not in _SIN_EVENTO_DECLARADAS]
        assert not nuevas, (
            f"Escrituras sin evento en módulos que SÍ auditan: {nuevas}.\n"
            "El módulo ya decidió que esto se audita — la operación que falta es un olvido, no "
            "un criterio. Agregá el evento copiando el payload del hermano, o declaralo en "
            "_SIN_EVENTO_DECLARADAS CON su razón.")

    def test_las_declaradas_siguen_sin_evento(self) -> None:
        """Dirección inversa: una declaración que ya no corresponde (porque se le agregó el
        evento, o porque la función se borró o se renombró) es ruido que tapa el próximo caso."""
        vigentes = {f"{arch}::{qual}" for arch, qual, _ in sin_auditar()}
        obsoletas = [k for k in _SIN_EVENTO_DECLARADAS if k not in vigentes]
        assert not obsoletas, (
            f"Declaraciones que ya no corresponden: {obsoletas}. O se auditó (sacala de la "
            "lista) o la función se movió (actualizá la clave).")

    def test_toda_declaracion_tiene_razon_escrita(self) -> None:
        """Una lista pelada no se puede auditar: en seis meses nadie sabe por qué está cada una."""
        sin_razon = [k for k, v in _SIN_EVENTO_DECLARADAS.items() if len(v.strip()) < 20]
        assert not sin_razon, f"Declaraciones sin razón escrita: {sin_razon}"
