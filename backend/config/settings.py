"""
Única fuente de configuración y variables de entorno del proyecto.
El resto del código importa `settings` desde acá — nunca os.environ directamente.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_env: str = "development"

    # 🔴 EL NOMBRE DE LA PLATAFORMA, EN UN SOLO LUGAR (bloque N9, 25/8/2026).
    # Estaba escrito literal en el título de la API (`main.py`) y en el metadato `author` de todo
    # PDF exportado; del lado del front, en seis archivos (ver `frontend/lib/marca.ts`, que es su
    # espejo con el MISMO default).
    #
    # ✅ EL NOMBRE YA ESTÁ CONFIRMADO: **Core RH**, definido por Capital Humano el 27/8/2026.
    # Ésta es la primera vez que el default cambia, y la centralización se pagó sola: el renombre
    # fue este renglón, su espejo del front y el literal del barrido nº 52 — no un
    # buscar-y-reemplazar sobre un repo que menciona el nombre viejo en decenas de comentarios.
    #
    # ⚠️ «Core RH» dice **RH**, y el vocabulario de §4 prohíbe «RRHH» y «Recursos Humanos».
    # NO hay conflicto y no hace falta ninguna excepción: los dos barridos de vocabulario buscan
    # `\bRRHH\b` (cuatro letras) y `\bRecursos Humanos\b`, y ninguno matchea «RH». Además el
    # nombre lo eligió Capital Humano — es un nombre propio, no un texto de pantalla que estemos
    # redactando nosotros, así que §4 no le aplica aunque el patrón lo rozara.
    #
    # ⚠️ QUÉ **NO** GOBIERNA ESTA VARIABLE, para no prometer de más:
    #   · El DOMINIO `hrkarstec.site`. Es una compra y una config de DNS, no un string: cambiarlo
    #     es comprar otro, apuntarlo, sumarlo a `ALLOWED_ORIGINS` y reemitir el certificado.
    #   · El nombre del LOGGER (`utils/logger.py` usa `"hrkarstec"`). Es un identificador de
    #     jerarquía de logging, no texto de pantalla: renombrarlo rompe cualquier filtro o alerta
    #     que ya apunte a él, y no lo ve ningún usuario. 🔴 SE DEJA ASÍ A PROPÓSITO el 27/8/2026,
    #     con el nombre ya cambiado a «Core RH»: es DECISIÓN DEL DEV DE INFRA, porque el costo lo
    #     paga él y no avisa — una alerta que filtre por `hrkarstec` queda MUDA, no rota, así que
    #     el síntoma es que nunca más suena. Ver `docs/handoff-aws/HANDOFF.md`.
    #   · Los DATOS que ya están en la base: nombres de empresa, las plantillas de mail que
    #     escribe Capital Humano (son contenido editable, no código) y el template de onboarding
    #     que sembró la migración 027.
    #   · Las MIGRACIONES ya corridas. Son historia; no se reescriben.
    #   · La casilla REMITENTE de los mails, que sale de `integraciones` en la base.
    #   · Las RAZONES SOCIALES de las dos empresas ni los mails `@karstec.com.ar`: son datos del
    #     cliente, no de la plataforma. La plataforma se llama Core RH; el cliente sigue siendo
    #     Karstec.
    marca: str = "Core RH"

    # Módulos desactivables
    # Assessment está APAGADO por decisión de producto. Apagarlo saca del app el módulo
    # ENTERO, incluidas sus 2 rutas públicas sin auth (/api/assessment/evaluacion/{token}
    # y .../submit). No se borró una línea de código: services, repos, schemas, migraciones
    # y tests quedan intactos.
    # PARA REACTIVARLO: ASSESSMENT_ENABLED=true en el entorno. Nada más — cero cambios de código.
    # Los dos puntos que leen este flag son main.py (montaje del router) y
    # middleware/auth.py (qué rutas se consideran públicas).
    assessment_enabled: bool = False

    # 🔴 LA QUINTA RUTA PÚBLICA DEL SISTEMA, y la más débil de las cinco POR DISEÑO.
    # Enciende el link público de carga de horas, donde un empleado se identifica SOLO con su
    # DNI. El DNI es un identificador enumerable, no un secreto: no hay autenticador propio ni
    # nonce con TTL, que son las dos condiciones que las otras cuatro rutas públicas sí cumplen.
    # Es una decisión de producto cerrada (la empresa no le da credenciales a los empleados).
    #
    # Nace en False y se entrega apagado. Apagado NO es "el módulo responde 403": el router no
    # se monta y la ruta no es pública, así que se comporta como cualquier path inexistente.
    # Los DOS puntos que leen este flag son `main.py` (montaje) y `middleware/auth.py`
    # (`_is_public`). Gatear uno solo delataría el módulo — ver la nota de ASSESSMENT_ENABLED.
    #
    # PARA ENCENDERLO: HORAS_PUBLICO_ENABLED=true en el entorno. Nada más, cero cambios de código.
    # ⚠️ Antes de encenderlo, leer `docs/BITACORA-CAMBIOS.md`: el rate limit por IP y por DNI es
    # la ÚNICA defensa real de esta ruta, y con `RATE_LIMIT_STORAGE_URI=memory://` es por proceso.
    horas_publico_enabled: bool = False

    # Presupuesto de tiempo del import de nómina, en segundos. Cuando se agota, el import
    # PARA ENTRE FILAS y devuelve el reporte de lo que hizo, en vez de morir en un timeout sin
    # decir nada. Reintentar con el mismo archivo continúa donde quedó (dedup por DNI).
    #
    # EL TECHO ESTÁ VERIFICADO (docs de Vercel al 1/7/2026): con **fluid compute** —habilitado
    # por defecto en proyectos creados después de abril 2025, y este es de 2026— el plan Hobby
    # tiene **300 s de default Y de máximo**.
    # ⚠️ En Hobby los 300 s son también el MÁXIMO: no se puede subir. Un presupuesto > 300 no
    # compra nada — el request muere antes de que el import pueda cortar solo, que es justamente
    # lo que esto vino a evitar.
    # 280 deja 20 s de margen para serializar la respuesta y emitir el evento de auditoría del
    # corte, que son las dos cosas que pasan DESPUÉS de la última fila.
    #
    # El `maxDuration: 300` que `backend/vercel.json` declara dentro de `builds[].config` está
    # en el lugar equivocado (formato legacy; va en la clave `functions` de nivel superior), pero
    # es INOCUO: el default de la plataforma ya es 300 s.
    #
    # En AWS el techo lo pone otra cosa (ALB / Lambda / ECS) → REVISAR este valor en el cutover.
    import_presupuesto_segundos: float = 280.0

    # Presupuesto de tiempo de un envío MASIVO de mails, en segundos. MÁS CHICO que el del
    # import a propósito: acá cada unidad es una llamada de red externa con su propio timeout,
    # no una escritura a nuestra base. Al agotarse, el envío para ENTRE MAILS y devuelve el
    # reporte de lo que salió; la idempotencia del log hace que el reintento no duplique.
    # Ver services/_lote_mails.py.
    mail_presupuesto_segundos: float = 120.0

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

    # (Resend se sacó el 2/8/2026: los mails salen por Gmail, reusando el OAuth que ya existe.
    # `resend_api_key` era OBLIGATORIA sin default y NINGÚN service la importaba, así que lo
    # único que podía hacer era tumbar el arranque entero —ni /health respondía— si faltaba en
    # el entorno. Ver services/mailer/. NO reponerla "por las dudas".)

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
