"""
Servicio de autenticación. Lógica de login, refresh y logout usando Supabase Auth.
"""
from schemas.auth import LoginResponse, RefreshResponse, UserInfo
from integrations.supabase_client import supabase_admin, supabase_client
from repositories.usuario_repo import UsuarioRepo
from utils.errors import AppError
from utils.logger import logger
from utils.usuario_estado import invalidar_estado


class AuthService:
    def login(self, username: str, password: str) -> LoginResponse:
        """
        Autentica al usuario con username y contraseña.

        Primero resuelve el username (case-insensitive) a un email buscando en
        public.users con el cliente admin (bypasea RLS, el token aún no existe).
        Luego usa ese email para autenticar contra Supabase Auth.

        El mensaje de error es genérico en ambos casos de fallo para no revelar
        si el username existe o no en el sistema.

        Args:
            username: Nombre de usuario registrado (case-insensitive).
            password: Contraseña en texto plano (case-sensitive, Supabase Auth la valida).

        Returns:
            LoginResponse con access_token, refresh_token y datos del usuario.

        Raises:
            AppError: INVALID_CREDENTIALS (401) si el username no existe o la contraseña es incorrecta.
        """
        # Paso 1: resolver username → perfil completo (case-insensitive via ilike sin wildcards)
        profile = UsuarioRepo().find_by_username(username)
        if not profile:
            logger.warning("Login fallido — username no encontrado", extra={"username": username})
            raise AppError("Usuario o contraseña incorrectos", "INVALID_CREDENTIALS", 401)

        # Paso 2: autenticar contra Supabase Auth usando el email resuelto
        try:
            auth_resp = supabase_client.auth.sign_in_with_password(
                {"email": profile["email"], "password": password}
            )
        except Exception:
            logger.warning("Login fallido — contraseña incorrecta", extra={"username": username})
            raise AppError("Usuario o contraseña incorrectos", "INVALID_CREDENTIALS", 401)

        session = auth_resp.session

        # 🔴 Sellar acá NO es cosmética: sin esto, alguien que estuvo 9 horas sin entrar se
        # loguearía bien y el PRIMER request de su sesión nueva moriría con SESION_EXPIRADA,
        # porque el middleware compara contra un `ultimo_acceso` de ayer. Quedaría en un loop
        # de login → 401 → login sin ninguna forma de salir. `/api/auth/login` es pública y no
        # pasa por el middleware, así que este es el único lugar donde puede pasar.
        # Best-effort: un fallo de esta escritura no puede tumbar un login válido.
        try:
            UsuarioRepo().tocar_ultimo_acceso(profile["id"])
            invalidar_estado(profile["id"])
        except Exception:
            logger.warning("No se pudo sellar ultimo_acceso en el login",
                           extra={"user_id": profile["id"]})

        logger.info("Login exitoso", extra={"user_id": profile["id"], "username": username})

        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=UserInfo(
                id=profile["id"],
                email=profile["email"],
                username=profile["username"],
                rol=profile["rol"],
                nombre=profile["nombre"],
                apellido=profile["apellido"],
                must_change_password=profile.get("must_change_password", False),
            ),
        )

    def refresh_token(self, token: str) -> RefreshResponse:
        """
        Genera nuevos tokens a partir de un refresh token válido.

        Supabase rota el refresh token en cada llamada: el token usado
        queda invalidado y se emite uno nuevo.

        Args:
            token: Refresh token vigente emitido en el login o refresh anterior.

        Returns:
            RefreshResponse con el nuevo access_token y el refresh_token rotado.

        Raises:
            AppError: INVALID_REFRESH_TOKEN (401) si el token expiró o fue revocado.
        """
        try:
            resp = supabase_client.auth.refresh_session(refresh_token=token)
        except Exception:
            raise AppError("Token de refresco inválido o expirado", "INVALID_REFRESH_TOKEN", 401)

        session = resp.session
        return RefreshResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
        )

    def logout(self, user_id: str, access_token: str) -> None:
        """
        Cierra la sesión del usuario invalidando todos sus tokens activos en Supabase.

        La invalidación es best-effort: si Supabase falla, se loguea el error
        pero no se lanza excepción para no bloquear el flujo del cliente.

        Args:
            user_id: UUID del usuario que cierra sesión (para trazabilidad).
            access_token: JWT activo del usuario, identifica la sesión en Supabase.
        """
        try:
            supabase_admin.auth.admin.sign_out(access_token)
        except Exception as exc:
            logger.warning(
                "Error al invalidar token en logout",
                extra={"user_id": user_id, "error": str(exc)},
            )
        logger.info("Logout exitoso", extra={"user_id": user_id})
