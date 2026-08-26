# Storage — qué hay hoy y qué cambia el día del cutover

> **Escrito el 12/8/2026, sesión 0.7.** Antes de esta sesión, los tres buckets estaban
> hardcodeados en 6 services y el SDK se llamaba desde 7. Ahora hay **un solo punto de contacto**,
> que es lo que hace que este documento pueda ser corto.

---

## Los tres buckets que usa el código

| Bucket | Qué guarda | Acceso | Quién escribe | Path | Objetos (26/8) |
|---|---|---|---|---|---|
| `documentos` | Adjuntos polimórficos (empleado, vacación, ausencia, vacante, offboarding) **y** certificados de capacitación | **Privado** — se lee por URL firmada de 3600 s | `adjunto_service`, `asignacion_service` | `adjuntos/{entidad}/{entidad_id}/{uuid}.{ext}` · `certificados/{asignacion_id}/{uuid}.{ext}` | 1 |
| `cvs` | CVs de candidatos (subidos a mano o bajados de la casilla de Gmail) | **Privado** — URL firmada de 3600 s | `cv_service` | `{empresa_id}/{candidato_id}/{uuid}.{ext}` · `sin_empresa/...` si no hay empresa | 4 |
| `avatars` | Logos de empresa | 🔴 **PÚBLICO** — URL permanente, sin firmar | `_empresa_logo` | `logos/{empresa_id}/{uuid}.{ext}` | 0 |

### 🔴 Pero en el proyecto hay CUATRO, y el cuarto no lo crea Terraform

Existe además un bucket **`reportes`**, **vacío (0 objetos)** y con **cero callers**: no aparece en
`integrations/storage.py`, ningún service lo nombra, y el barrido nº 12 —que prohíbe nombrar un
bucket fuera de ese archivo— no lo puede ver justamente porque nadie lo nombra. Es un resto de
cuando se pensó guardar los PDF exportados; hoy los exports se devuelven en la respuesta HTTP y no
se persisten.

**Qué hacer con él al portear: nada.** Se crean **tres** buckets en Terraform y `reportes` no se
replica. Está escrito acá para que no aparezca como sorpresa al comparar la consola de Supabase
contra el `.tf` y no haya que averiguar si falta algo. *(Medido contra `storage.buckets` el
26/8/2026.)*

🔴 **`avatars` es el único público del sistema.** Su URL se **persiste** en `empresas.logo_url`, así
que si el dominio del bucket cambia en AWS, esas filas quedan apuntando al viejo. Los otros dos
guardan solo la **key** (`adjuntos.storage_path`, `candidatos.cv_storage_path`) y la URL se firma
en cada request — esos no tienen ese problema.

---

## 🔴 El día del cutover: qué se toca y qué NO

### Se toca UN archivo

**`backend/integrations/storage.py`** (94 líneas). Es el único que habla con el proveedor. Expone
cuatro verbos y tres constantes, y su API es **neutral al proveedor a propósito**: afuera no se ve
`from_()`, ni `file_options`, ni la clave `signedURL` del dict que devuelve Supabase.

```python
DOCUMENTOS = "documentos" · CVS = "cvs" · AVATARS = "avatars"

subir(bucket, path, content, content_type) -> None
url_firmada(bucket, path, expires_in=3600) -> str   # devuelve el STRING, no el dict
url_publica(bucket, path) -> str
borrar(bucket, paths: list[str]) -> None
```

El mapeo a S3 es directo: `put_object` · `generate_presigned_url` · la URL pública del bucket ·
`delete_objects`. **Si las cuatro firmas se respetan, no hay que tocar nada más.**

### NO se tocan

- **Los 7 services** que usan Storage (`adjunto_service`, `asignacion_service`, `candidato_service`,
  `cv_service`, `_candidato_acciones`, `_empresa_logo`, `_adjuntos_masivo`). Ninguno nombra un
  bucket ni llama al SDK.
- **Los paths.** Los arma cada service según su convención, y son independientes del proveedor.
- **La validación de tipo y tamaño** (`utils/files.py`) ni el manejo de errores.
- **El schema.** `adjuntos.bucket` sigue siendo una columna `text` con `DEFAULT 'documentos'`.

> ✅ **Hay un test que lo mantiene así:** `backend/tests/test_storage_punto_unico.py` recorre
> `services/` y `repositories/` por AST y rojea si alguien vuelve a nombrar un bucket o a llamar al
> SDK. Si al portar aparece un módulo nuevo que habla con S3 directo, salta ahí y no en producción.

---

## Lo que hay que saber antes de portar

### 1. 🔴 `adjuntos.bucket` está grabado en la base, no solo en el código

La columna tiene `DEFAULT 'documentos'` y las filas de producción ya lo tienen escrito. **Dos
caminos leen el bucket DE LA FILA**, no de una constante:

- `adjunto_service.url_descarga` — firma la URL con `adj.bucket`.
- `_adjuntos_masivo.eliminar_todos` — borra con `adj.bucket`.

Por eso `storage.py` recibe el bucket como **`str` y no como Enum**: tiene que poder operar sobre
un valor que llega de la base, incluido uno viejo o inesperado. Si en AWS los buckets se renombran,
**hay que migrar esa columna** o mapear los nombres viejos dentro del módulo. Es la decisión que
este documento existe para que no se descubra tarde.

### 2. El borrado es best-effort, y es una decisión de negocio

Los dos borrados (`_adjuntos_masivo` y `_candidato_acciones`) envuelven la llamada en `try/except`
con un log propio: **si Storage falla, la fila se borra igual y el objeto queda huérfano**. Esa
decisión vive en los services a propósito, no en el módulo. Al portar, conservarla: cambiar eso
haría que un fallo de S3 bloquee bajas que hoy pasan.

**Consecuencia conocida:** en Supabase ya puede haber objetos huérfanos. No hay proceso de limpieza.

### 3. El E2E de adjuntos nunca se ejecutó

Está anotado desde hace meses: los 11 tests de adjuntos son unitarios con el SDK falseado, y el
E2E real **nunca corrió** porque apuntaba al bucket de producción. **El cutover a S3 es el momento
de escribirlo**, con un bucket de prueba. Es la única superficie de Storage sin verificación real.

### 4. Ningún test funcional afirma el NOMBRE del bucket

Hallazgo de esta sesión, medido con una mutación: si el módulo apunta a un bucket equivocado, **los
tests funcionales de adjuntos, CVs y logo pasan igual**. Sus fakes reciben el bucket en `from_()` y
lo descartan sin mirarlo. Lo único que caza esa mutación hoy es el barrido estructural, que fija
los tres valores como literales.

**Para el porteo importa:** un typo en el nombre de un bucket de S3 no lo va a detener un test
funcional. Verificarlo contra el bucket real.

### 5. Un techo que no es de Storage

El límite de subida efectivo lo pone la plataforma (Vercel hoy), no el bucket: **4,5 MB**. Está en
`utils/files.py` y en `docs/DEPLOY.md` §3. En ECS ese techo cambia, y conviene revisar los mensajes
de error que lo citan.
