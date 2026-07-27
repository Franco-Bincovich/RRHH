"""
Servicio de autenticación con emisión propia de JWT — reemplaza a Supabase Auth (gotrue).

DESTINO: backend/services/auth_service.py (reemplaza el actual, 118 líneas).

QUÉ CAMBIA vs. el auth_service actual
-------------------------------------
Hoy el login es híbrido (services/auth_service.py:33-68):
  1. resuelve username → email contra public.users con el SDK (ilike + single);
  2. valida la contraseña contra Supabase Auth (auth.sign_in_with_password, línea 49).
El paso 1 sobrevive conceptualmente (ahora en SQL). **El paso 2 es el que cambia**: acá la
contraseña se verifica contra `users.password_hash` (migración 075) con bcrypt local. No
hay red, no hay gotrue, y el email deja de ser necesario para autenticar — el username
resuelve directo al perfil con su hash.

⚠️ ASYNC. El auth_service actual es SÍNCRONO (los routers lo llaman sin await:
routers/auth.py:30 `return service.login(...)`). asyncpg es async, así que estos métodos
lo son, y los routers pasan a necesitar `await`. No es opcional: sin el await, FastAPI
devuelve la corrutina sin ejecutar y el login "responde 200" con basura.

BCRYPT DIRECTO, NO PASSLIB. requirements.txt trae `passlib[bcrypt]==1.7.4`, que está ROTO
contra el bcrypt instalado (5.0.0): passlib lee `bcrypt.__about__`, atributo que bcrypt 4.1+
eliminó → AttributeError. Verificado en este repo. Se usa `import bcrypt` directo, que
funciona. No "arreglar" esto volviendo a passlib.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from config.settings import settings
from repositories.token_repo_NEW import UserAuthRepo
from utils.errors import AppError
from utils.logger import logger

# HS256: secreto simétrico (settings.jwt_secret), nosotros firmamos y verificamos. El auth
# actual usa ES256 porque verifica contra el JWKS público de Supabase — asimétrico, ellos
# firman. Al emitir nosotros, HS256 alcanza y evita gestionar un par de claves.
ALGORITHM = "HS256"

# Límite duro de bcrypt: ignora todo lo que pase de 72 BYTES. Truncar explícitamente evita
# el ValueError de las versiones nuevas. Se trunca sobre los BYTES ya encodeados, no sobre
# el str: `password[:72]` en Python son 72 CARACTERES, que en UTF-8 pueden ser hasta 288
# bytes — con acentos (esperables acá) seguiría explotando. Cortar bytes puede partir un
# carácter multibyte al medio, pero bcrypt opera sobre bytes crudos y no le molesta.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt (salt aleatorio por hash).

    Args:
        password: Contraseña en claro.

    Returns:
        El hash como str, listo para guardar en users.password_hash.
    """
    raw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt.

    Nunca levanta: un hash corrupto o vacío devuelve False. Un caller de auth no debe
    distinguir "hash inválido" de "contraseña incorrecta".

    Args:
        password: Contraseña en claro a verificar.
        password_hash: Hash almacenado.

    Returns:
        True si coincide; False si no, o si el hash es inválido/vacío.
    """
    if not password_hash:
        return False
    try:
        raw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, rol: str) -> str:
    """Emite un access token JWT firmado con settings.jwt_secret.

    Campo `rol` (español), NO `role`: es el nombre real en RRHH — columna users.rol, y
    middleware/auth.py:131 arma `request.state.user = {"id":..., "rol":...}`, que leen
    utils/permisos.py y los 142 endpoints gateados. Renombrarlo acá obligaría a tocarlos
    todos.

    Args:
        user_id: UUID del usuario → claim `sub`.
        rol: Rol funcional (admin_rrhh | gerencia_lectura | mandos_medios).

    Returns:
        El JWT como str.
    """
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.jwt_expiration_minutes),
        "type": "access",  # separa access de refresh: un refresh no debe autorizar requests
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """Verifica firma y expiración de un JWT propio y devuelve su payload.

    Fail-closed: cualquier fallo (firma inválida, expirado, malformado) es el MISMO
    AppError 401. El motivo real solo va al log del servidor — nunca al cliente, para no
    dar señal sobre por qué falló. `algorithms=[ALGORITHM]` fija HS256: sin eso, un token
    con `alg: none` se aceptaría (confusión de algoritmo).

    Args:
        token: JWT crudo.

    Returns:
        El payload decodificado.

    Raises:
        AppError: UNAUTHORIZED (401) ante cualquier fallo de verificación.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except Exception as exc:
        logger.warning("Token JWT rechazado", extra={"motivo": type(exc).__name__})
        raise AppError("No autorizado", "UNAUTHORIZED", 401) from exc


class AuthService:
    def __init__(self, repo: Optional[UserAuthRepo] = None) -> None:
        """Inyección por constructor, como el resto de los services de RRHH."""
        self._repo = repo or UserAuthRepo()

    async def authenticate_user(self, username: str, password: str) -> dict:
        """Autentica username + contraseña contra users.password_hash.

        Mensaje genérico e idéntico en los cuatro fallos (usuario inexistente, sin
        credencial local, contraseña incorrecta, usuario inactivo) — SEGURIDAD-PENTEST 2.3:
        no revelar si el username existe. Mantiene el código INVALID_CREDENTIALS del
        auth_service actual para que el frontend no cambie.

        Nota de timing: si el usuario no existe se responde sin correr bcrypt, así que la
        respuesta es más rápida — un atacante puede enumerar usernames midiendo. Mitigado
        de facto por el rate limit de 5/min por IP en el login (routers/auth.py:26). El fix
        real es un checkpw contra un hash dummy en la rama de "no existe".

        Args:
            username: Nombre de usuario (case-insensitive).
            password: Contraseña en claro.

        Returns:
            El perfil como dict (id, email, username, nombre, apellido, rol,
            must_change_password), SIN password_hash.

        Raises:
            AppError: INVALID_CREDENTIALS (401) en cualquier fallo.
        """
        generico = AppError("Usuario o contraseña incorrectos", "INVALID_CREDENTIALS", 401)

        user = await self._repo.find_by_username(username)
        if not user:
            logger.warning("Login fallido — username no encontrado", extra={"username": username})
            raise generico

        # password_hash NULL = perfil sin credencial local (migración 075 no hace backfill:
        # los hashes de Supabase no son legibles). No puede loguear hasta que el ABM le
        # asigne una contraseña temporal.
        if not verify_password(password, user.get("password_hash") or ""):
            logger.warning("Login fallido — credencial inválida", extra={"username": username})
            raise generico

        if not user.get("activo", False):
            logger.warning("Login fallido — usuario inactivo", extra={"username": username})
            raise generico

        logger.info("Login exitoso", extra={"user_id": str(user["id"]), "username": username})
        return {k: v for k, v in user.items() if k != "password_hash"}
