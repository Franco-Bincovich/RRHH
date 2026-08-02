"""
Barrera de acceso sobre la plantilla de onboarding TARGET de una operación (helper transversal).

🔴 POR QUÉ ES UN HELPER Y NO UN MÉTODO DE OnboardingTemplatesService.
Porque tres de los caminos que leen una plantilla por id NO pasan por esa clase, y un gate que
vive adentro de ella quedaría incompleto POR CONSTRUCCIÓN:

  1. `OnboardingTemplatesService.add_tarea` llamaba a `self._repo.get_template(...)` directo,
     salteando el `get_template` de su propio service — cuatro de los cinco endpoints de
     escritura lo usaban, uno no.
  2. `services/_onboarding_iniciar.iniciar` es una función libre (el service de onboarding la
     delega) y resuelve el template con `templates_repo.get_template(...)`.
  3. `OnboardingRepo.get_default_template` elige la plantilla por defecto sin pasar por ningún
     service de templates.

Es el mismo aprendizaje que "el router pasando empresa_id NO prueba nada": hay que seguir el
parámetro hasta la query, uno por uno. Como helper libre que recibe el repo —molde de
`_empleado_scope.ensure_empleado_de_empresa`— los tres caminos pueden usar el MISMO gate sin
depender de en qué clase viven.

DOS EJES, SE COMPONEN POR INTERSECCIÓN Y EN ESTE ORDEN:
  - empresa     → de qué organización es la plantilla. Aplica a TODO. Va en el WHERE (Forma A).
  - visibilidad → dentro de mi empresa, cuáles alcanzo. `es_publica OR created_by = yo OR
                  created_by IS NULL`.
La visibilidad NUNCA reemplaza a la empresa: ser el autor de una plantilla no abre la puerta de
otra empresa.

⚠️ `gerencia_lectura` NO ES UNA EXCEPCIÓN — ve todo, incluidas las privadas de los demás. El
bypass está en `_onboarding_templates_filtros.with_visibilidad` (por eso este helper recibe `rol`
además de `user_id`, igual que `_empleado_scope.ensure_empleado_visible`). Es una decisión de
producto: "privada" acá significa privacidad ENTRE PARES DE RRHH (un borrador que no quiero
que aparezca en la lista de mis compañeros), no confidencialidad. Ocultárselas a gerencia sería
la PRIMERA excepción row-level al modelo de roles —donde "lectura en todo" hoy significa
literalmente todo— y no se abre esa puerta por un caso que hoy es teórico (los cuatro usuarios
de producción son admin_rrhh). Si más adelante hace falta, se agrega ahí; al revés no.
"""
from typing import Optional
from uuid import UUID

from schemas.onboarding import TemplateResponse
from utils.errors import AppError

# Literal canónico del módulo. No duplicar: los tres motivos de rechazo salen por acá.
MENSAJE_404 = "Template no encontrado"
CODE_404 = "TEMPLATE_NOT_FOUND"


def template_or_404(tmpl: Optional[TemplateResponse]) -> TemplateResponse:
    """Devuelve la plantilla o levanta el 404 canónico del módulo.

    Existe para que el mensaje y el code tengan UNA sola fuente, igual que
    `_empleados_utils.empleado_or_404`. Los callers que ya tienen la fila lo reusan en vez de
    re-lanzar el AppError por su cuenta.
    """
    if tmpl is None:
        raise AppError(MENSAJE_404, CODE_404, 404)
    return tmpl


def ensure_autor(tmpl: TemplateResponse, user_id: Optional[str]) -> None:
    """Exige que `user_id` sea el autor de la plantilla. Para cambiar SU VISIBILIDAD.

    🔴 POR QUÉ HACE FALTA, si el gate de acceso ya corrió. Porque el gate responde "¿podés
    tocar esta plantilla?" y acá la pregunta es otra: "¿es tuya?". Sin esto, cualquiera puede
    volver PRIVADA la plantilla PÚBLICA de otro — y como `created_by` sigue siendo del autor
    original, quien la volvió privada pierde el acceso en el mismo movimiento. Es una acción
    de un solo sentido y sin dueño claro; el resto de la edición (nombre, descripción, tareas)
    sigue siendo colaborativa entre pares de RRHH, que es como funciona el módulo.

    UN 403 Y NO UN 404, a diferencia de todo lo demás en este archivo: acá no hay nada que
    ocultar. Para llegar a este punto la plantilla ya te resultó visible, así que negarte con
    un código propio no confirma ninguna existencia que no supieras. El 404 uniforme protege
    contra la ENUMERACIÓN; este caso no es enumerable.

    Una plantilla sin autor (`created_by IS NULL`, FK ON DELETE SET NULL) la puede volver
    privada cualquiera: es la contracara de la regla de huérfanas —se comporta como pública—
    y no hay a quién preguntarle.

    Raises:
        AppError: TEMPLATE_NO_SOS_AUTOR (403) si la plantilla tiene autor y no sos vos.
    """
    if tmpl.created_by is None or str(tmpl.created_by) == str(user_id):
        return
    raise AppError(
        "Solo quien creó la plantilla puede cambiar si es compartida o privada.",
        "TEMPLATE_NO_SOS_AUTOR", 403,
    )


def ensure_template_accesible(repo, template_id, empresa_id: Optional[UUID],
                              user_id: Optional[str], rol: Optional[str] = None) -> TemplateResponse:
    """Carga la plantilla validando empresa ∩ visibilidad. La devuelve para reusar la fila.

    🔴 EL 404 ES IDÉNTICO EN LOS TRES CASOS —no existe · es de otra empresa · es privada de
    otro—: mismo status, mismo code y mismo mensaje. Nunca un 403 ni un texto distinto. Un
    mensaje propio para "es privada" confirmaría que la plantilla existe y de quién es, que es
    exactamente el oráculo de enumeración que cerró la Fase 2.

    Devuelve la fila (no un bool) para que el caller no la consulte dos veces — es de donde
    después sale `template.empresa_id` en `add_tarea` y en el alta de onboarding.

    `empresa_id=None` es la vista consolidada y NO restringe (semántica de `get_empresa_id`).
    Ahí la visibilidad queda como único filtro, que es justo donde más fácil se colaría una
    plantilla ajena — por eso el filtro va en la query y no depende del modo.

    Args:
        repo: OnboardingTemplatesRepo (o doble de test). Su `get_template` aplica los dos ejes.
        template_id: plantilla objetivo de la operación (UUID o str).
        empresa_id: empresa activa del request. None = consolidado, no restringe.
        user_id: usuario que mira, sujeto de la visibilidad.
        rol: rol de ese usuario. `gerencia_lectura` ve todo (ver `with_visibilidad`).

    Returns:
        TemplateResponse validado por ambos ejes.

    Raises:
        AppError: TEMPLATE_NOT_FOUND (404) si no existe, es de otra empresa o es privada de otro.
    """
    return template_or_404(repo.get_template(str(template_id), empresa_id, user_id, rol))
