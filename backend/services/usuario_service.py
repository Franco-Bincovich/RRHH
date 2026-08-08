"""
Servicio de alta de usuarios del sistema (rol asignable: los 3 roles válidos).
Flujo: router → service → repository. La identidad va a Supabase Auth (auth.users);
el perfil, a public.users. Ambos pasos van juntos o se revierten (rollback del auth user).
"""
from typing import Optional

from integrations.supabase_client import supabase_admin, supabase_client
from repositories.integracion_remitente_repo import IntegracionRemitenteRepo
from repositories.usuario_repo import UsuarioRepo
from schemas.usuario import CrearUsuarioRequest, CrearUsuarioResponse
from services._audit_payloads_usuarios import payload_baja_usuario, payload_cambio_password
from services._limite_export import verificar_limite_export
from services._usuario_alta import crear as _crear_usuario
from services._usuario_remitente import ensure_no_es_remitente as _ensure_no_es_remitente
from services._usuarios_export import construir_filas_export
from services.audit_service import AuditService
from services.export import Descarga, build_export
from utils.errors import AppError
from utils.logger import logger
from utils.usuario_estado import invalidar_estado

# 100 años. GoTrue no tiene "ban para siempre": toma una duración, y "none" la levanta.
_BAN_PERMANENTE = "876000h"


class UsuarioService:
    def __init__(
        self, repo: Optional[UsuarioRepo] = None, audit: Optional[AuditService] = None,
        remitente_repo: Optional[IntegracionRemitenteRepo] = None,
    ) -> None:
        self._repo = repo or UsuarioRepo()
        self._audit = audit or AuditService()
        self._remitente = remitente_repo or IntegracionRemitenteRepo()

    def listar(self) -> dict:
        """Usuarios activos del sistema, para la pantalla de ABM y los selectores."""
        items = self._repo.listar_activos()
        return {"items": items, "total": len(items)}

    def exportar(self, formato: str = "excel") -> Descarga:
        """Exporta el listado de usuarios con columnas legibles (sin ids ni credenciales).

        Va por el MISMO `listar_activos` que el listado, así que el archivo no puede traer
        filas que la pantalla no muestre. El listado no tiene filtros: no hay ninguno que se
        pueda perder entre las dos puntas. Qué columnas salen y por qué, en _usuarios_export.
        """
        items = self._repo.listar_activos()
        verificar_limite_export(len(items))
        datos = {"Usuarios": construir_filas_export(items)}
        return build_export(nombre="Usuarios", datos=datos, filename_base="usuarios", formato=formato)

    def crear_usuario(self, data: CrearUsuarioRequest, creado_por: Optional[str]) -> CrearUsuarioResponse:
        """Crea identidad + perfil con rollback. Ver services/_usuario_alta.crear."""
        return _crear_usuario(self._repo, self._audit, data, creado_por)

    def cambiar_password(self, user_id: str, password_actual: str, password_nueva: str) -> None:
        """
        Cambia la contraseña del usuario autenticado (self-service). Cubre los dos casos
        con el mismo flujo: cambio obligatorio (must_change_password) y cambio voluntario.

        Reautentica con la contraseña actual (sign_in_with_password) ANTES de cambiar:
        si falla, corta con INVALID_CREDENTIALS 401 genérico (no revela el detalle). Luego
        actualiza la credencial vía Supabase admin y baja must_change_password a false.
        Nunca loguea ninguna de las dos contraseñas.

        Args:
            user_id: id del usuario, SIEMPRE del token (nunca del body → evita IDOR).
            password_actual: contraseña vigente, a verificar por reautenticación.
            password_nueva: nueva contraseña (largo/distinción ya validados por el schema).

        Raises:
            AppError: USUARIO_NOT_FOUND (404), INVALID_CREDENTIALS (401),
                      PASSWORD_UPDATE_ERROR (502).
        """
        email = self._repo.get_email(user_id)
        if not email:
            raise AppError("Usuario no encontrado", "USUARIO_NOT_FOUND", 404)
        try:
            supabase_client.auth.sign_in_with_password({"email": email, "password": password_actual})
        except Exception as exc:
            raise AppError("Contraseña actual incorrecta", "INVALID_CREDENTIALS", 401) from exc
        try:
            supabase_admin.auth.admin.update_user_by_id(user_id, {"password": password_nueva})
        except Exception as exc:
            raise AppError("No se pudo actualizar la contraseña", "PASSWORD_UPDATE_ERROR", 502) from exc

        self._repo.bajar_flag_password(user_id)
        self._audit.registrar(**payload_cambio_password(user_id))
        logger.info("Cambio de contraseña", extra={"user_id": user_id})

    def eliminar_usuario(self, user_id: str, ejecutor_id: Optional[str]) -> None:
        """Da de baja un usuario. Es una baja BLANDA y REVERSIBLE, no un DELETE.

        Antes borraba `auth.users` y el CASCADE se llevaba `public.users`. Eso tenía dos costos
        que no se pagan más: el `ON DELETE SET NULL` de `empleados.user_id` **desvinculaba al
        empleado** de su usuario, y la auditoría vieja quedaba apuntando a un id que ya no
        resolvía a ningún nombre. La identidad se conserva; lo que se corta es el acceso.

        Las dos mitades hacen falta y son distintas:
          1. `activo=false` — lo hace regir. El middleware lo lee en cada request y responde 403.
          2. el ban en Supabase Auth — `/api/auth/refresh` es PÚBLICA y no pasa por el
             middleware, así que sin el ban el usuario sigue renovando tokens para siempre.

        El orden no es casual: primero la baja en nuestra base, que es la que corta de verdad, y
        recién después el ban. Si fallara el ban, el usuario ya está afuera de la API y lo único
        pendiente es dejar de emitirle tokens que no le sirven para nada; al revés, un ban
        exitoso con la baja fallida lo dejaría con acceso pleno hasta que expire su token.

        Reversión (a mano, ver docs/DEPLOY.md): `activo=true` + `ban_duration: "none"`.

        🔴 NO SE PUEDE DAR DE BAJA AL USUARIO QUE SOSTIENE LA CASILLA DEL SISTEMA (409). Ver
        `_ensure_no_es_remitente`. El chequeo va ANTES de tocar nada: desactivar y después
        avisar dejaría el envío de mails caído durante la ventana entre las dos cosas.

        Raises: AppError AUTOELIMINACION (400), USUARIO_NOT_FOUND (404),
                USUARIO_ES_REMITENTE_SISTEMA (409), USUARIO_DELETE_ERROR (502).
        """
        if ejecutor_id and str(ejecutor_id) == str(user_id):
            raise AppError("No podés eliminar tu propio usuario", "AUTOELIMINACION", 400)
        perfil = self._repo.get_perfil(user_id)
        if not perfil:
            raise AppError("Usuario no encontrado", "USUARIO_NOT_FOUND", 404)
        self._ensure_no_es_remitente(user_id)

        self._repo.set_activo(user_id, False)
        invalidar_estado(user_id)  # que rija en el acto, sin esperar el TTL
        self._audit.registrar(**payload_baja_usuario(user_id, perfil.get("username"), ejecutor_id))
        logger.info("Usuario dado de baja", extra={"user_id": user_id, "eliminado_por": ejecutor_id})

        try:
            supabase_admin.auth.admin.update_user_by_id(user_id, {"ban_duration": _BAN_PERMANENTE})
        except Exception as exc:
            # La baja YA rige (el 403 sale del middleware). Lo que queda sin cerrar es la
            # canilla de tokens nuevos, así que se avisa fuerte para reintentar, pero no se
            # revierte nada: revertir dejaría al usuario adentro, que es peor.
            logger.error("Baja aplicada pero el ban de Auth falló", extra={"user_id": user_id})
            raise AppError("El usuario quedó desactivado, pero no se pudo revocar su sesión. Reintentá.",
                           "USUARIO_DELETE_ERROR", 502) from exc

    def _ensure_no_es_remitente(self, user_id: str) -> None:
        """Bloquea con 409 la baja del usuario que sostiene la casilla del sistema.
        Ver services/_usuario_remitente.ensure_no_es_remitente (extraído por límite de líneas)."""
        _ensure_no_es_remitente(self._remitente, user_id)
