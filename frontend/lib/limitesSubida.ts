/**
 * Límite de tamaño de las subidas, para la validación de CLIENTE.
 *
 * 🔴 ESPEJO MANUAL de `backend/utils/files.py`. El backend es la fuente de verdad y el único que
 * ENFORZA: esto existe solo para dar feedback antes de gastar la subida, así que una divergencia
 * degrada a "el usuario se enteró un segundo más tarde", nunca a un archivo que entra sin control.
 *
 * Vive en UN archivo y no repetido en cada componente porque antes de esto había dos números
 * distintos y los dos estaban mal: `FileUpload` decía 10 MB y `CvField` 5 MB, cuando la
 * plataforma rechaza cualquier request > 4,5 MB con un 413 que el usuario no puede interpretar.
 *
 * Al cambiar el techo (migración a AWS) hay que tocar el backend Y este número. Es el mismo
 * patrón de espejo manual que `services/permisos.ts` ↔ `utils/permisos.py`, con el mismo riesgo
 * conocido: no hay test que los compare.
 */
export const MAX_SUBIDA_MB = 4.2

/** Mensaje de error del cliente. Mismo texto que produce el backend, para que no haya dos voces. */
export function mensajeSuperaTamano(quePesa: string): string {
  return `El ${quePesa} supera el tamaño máximo de ${MAX_SUBIDA_MB} MB`
}
