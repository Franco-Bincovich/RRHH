"""
Única fuente de configuración y variables de entorno del proyecto.
El resto del código importa `settings` desde acá — nunca os.environ directamente.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_env: str = "development"

    # Módulos desactivables
    # Assessment está APAGADO por decisión de producto. Apagarlo saca del app el módulo
    # ENTERO, incluidas sus 2 rutas públicas sin auth (/api/assessment/evaluacion/{token}
    # y .../submit). No se borró una línea de código: services, repos, schemas, migraciones
    # y tests quedan intactos.
    # PARA REACTIVARLO: ASSESSMENT_ENABLED=true en el entorno. Nada más — cero cambios de código.
    # Los dos puntos que leen este flag son main.py (montaje del router) y
    # middleware/auth.py (qué rutas se consideran públicas).
    assessment_enabled: bool = False

    # Presupuesto de tiempo del import de nómina, en segundos. Cuando se agota, el import
    # PARA ENTRE FILAS y devuelve el reporte de lo que hizo, en vez de morir en un timeout sin
    # decir nada. Reintentar con el mismo archivo continúa donde quedó (dedup por DNI).
    #
    # 🔴 EL DEFAULT ES CONSERVADOR A PROPÓSITO, y hay que ajustarlo en cada entorno.
    # El techo real de esta app NO ESTÁ VERIFICADO: `backend/vercel.json` declara
    # `maxDuration: 300`, pero lo hace dentro de `builds[].config`, que es el formato legacy —
    # la duración de una función se configura en la clave `functions` de nivel superior, que ese
    # archivo no tiene. O sea que muy probablemente esté IGNORADO y el backend corra con el
    # default del plan (que en el más bajo son 10 s).
    # 8 s asume ese peor caso y deja margen para serializar la respuesta. Un presupuesto MAYOR
    # que el techo real no sirve de nada: el request muere antes de que el import pueda cortar
    # solo, que es justamente lo que esto vino a evitar.
    # En AWS el techo es otro (ALB/Lambda/ECS) → REVISAR este valor en el cutover.
    import_presupuesto_segundos: float = 8.0

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    supabase_timeout: int = 30  # timeout httpx (s) de postgrest/storage/functions

    # Auth
    jwt_secret: str
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30

    # Anthropic
    anthropic_api_key: str

    # Resend
    resend_api_key: str
    resend_from_email: str = "noreply@hrkarstec.com"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/integraciones/google/callback"

    # Frontend URL (para redirects OAuth)
    frontend_url: str = "http://localhost:3000"

    # Rate limiting
    # Cuántas capas de proxy CONFIABLES hay delante del app. Define qué entrada de
    # X-Forwarded-For es la IP real del cliente: se toma hops[-trusted_proxy_hops], contando
    # desde la derecha, porque esas entradas las escribió nuestra infraestructura y las de la
    # izquierda las puede falsificar el cliente (ver utils/rate_limit.py::client_ip).
    #   1 → Vercel: su edge termina TLS y agrega la IP del cliente antes de invocar la función.
    #   0 → sin proxy (local): se ignora el header y se usa la IP de la conexión.
    #   AWS: 1 con ALB solo; 2 si además hay CloudFront adelante.
    # ⚠️ Un valor de más colapsa todo el tráfico en un único contador y deja al equipo afuera.
    trusted_proxy_hops: int = 1
    # Store de los contadores. "memory://" es POR PROCESO: en serverless cada cold start
    # arranca en cero y con N instancias el límite efectivo es N×. Para que los límites sean
    # reales hace falta un store compartido (redis://...). Enchufe listo, decisión de infra.
    rate_limit_storage_uri: str = "memory://"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
