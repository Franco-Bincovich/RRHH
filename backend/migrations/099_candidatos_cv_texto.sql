-- 099_candidatos_cv_texto.sql
--
-- QUÉ HACE: `candidatos.cv_texto` (el texto extraído del CV) y `candidatos.screening_warning`
-- (por qué NO se pudo extraer). Las dos nullable.
--
-- NO ES DESTRUCTIVA: agrega dos columnas. Ninguna fila existente cambia.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 EL TEXTO SE PERSISTE, NO SE EXTRAE AL VUELO
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- La alternativa era extraerlo cada vez que el clasificador corre. Eso obliga, por cada
-- clasificación, a: pedirle a Storage una signed URL, bajar el archivo, y volver a parsearlo. El
-- CV no cambia nunca después de entrar —es un adjunto de un mail— así que ese trabajo daría
-- SIEMPRE el mismo resultado. Se hace una vez, al persistir el candidato.
--
-- Como efecto secundario buscado, también deja de importar que el archivo siga estando: si
-- alguien limpia el bucket, el texto sobrevive y el candidato se puede seguir clasificando.
--
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- 🔴 `screening_warning` ES TEXTO Y NO UN BOOLEANO — es la decisión que da valor a la columna
-- ═════════════════════════════════════════════════════════════════════════════════════════
-- Un flag `cv_ilegible = true` obliga a abrir el archivo para saber qué pasó, que es exactamente
-- el trabajo que esto viene a evitar. Los motivos NO son intercambiables para quien lo lee:
--
--   · "PDF sin texto extraíble"       → es un escaneo. Se le pide el CV en otro formato.
--   · "formato .doc no soportado"     → se le pide que lo reexporte a PDF o DOCX.
--   · "el archivo está protegido con contraseña" → se le pide la contraseña, o el archivo abierto.
--   · "PDF corrupto o ilegible"       → el archivo llegó roto; se le pide de nuevo.
--
-- Cada uno tiene una acción distinta. El booleano las colapsa todas en "abrí el archivo y fijate".
--
-- ⚠️ SON DOS COLUMNAS INDEPENDIENTES Y PUEDEN CONVIVIR. Un PDF de 40 páginas produce texto
-- (truncado al tope) Y un warning que dice que se truncó: el clasificador tiene con qué trabajar
-- y RRHH sabe que no vio el archivo entero. Modelarlo como "o texto o warning" habría escondido
-- justo ese caso.
--
-- ⚠️ NO SE INDEXAN. `cv_texto` es un blob de hasta ~20 KB por fila que nadie filtra ni ordena: lo
-- lee el clasificador por `id`. Un índice de texto completo (GIN/tsvector) es otra decisión, para
-- cuando exista la búsqueda por contenido — hoy no existe y el índice solo costaría escritura.
--
-- ⚠️ Sin backfill: los candidatos que ya existen no tienen CV que leer (`candidatos` está en 0 en
-- producción). Los que entren por la ingesta traen el texto desde su INSERT.

BEGIN;

-- El texto plano del CV, ya truncado al tope que define `services/_cv_texto.py`.
ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS cv_texto TEXT;

-- POR QUÉ no se pudo procesar (o qué se perdió). Legible por una persona, no un código.
ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS screening_warning TEXT;

COMMIT;
