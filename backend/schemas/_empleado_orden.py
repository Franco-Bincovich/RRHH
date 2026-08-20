"""
El vocabulario de ORDEN del listado de empleados: los dos órdenes que se pueden pedir por API.

Vive en `schemas/` y no en `repositories/` porque es la parte del orden que mira hacia AFUERA:
son los valores que el router acepta y que salen publicados en `/docs`. La traducción a columnas
—qué campo y en qué dirección— es cosa del repo y vive en `repositories/_empleado_orden.py`.
`tests/test_empleado_orden.py` verifica que las dos mitades no se separen.
Molde: `schemas/_provincias.py`, la otra lista cerrada que el schema publica y otra capa consume.

🔴 ES UN VOCABULARIO CERRADO Y NO UN PAR `campo` + `direccion`, Y ES LA DECISIÓN DEL ARCHIVO.
Dos parámetros libres se multiplican en órdenes que nadie pidió (`?campo=dni&direccion=desc`),
dejan pedir orden por una columna que no tiene índice —o que ni siquiera existe— y convierten un
422 de validación en un 400 crudo de PostgREST. Y sobre todo: **la dirección es parte del
significado, no una preferencia del que mira**. "Próximos ingresos" es quién entra PRIMERO y
"Bajas" es quién se fue ÚLTIMO; una pantalla de próximos ingresos ordenada al revés no es la
misma pantalla con otro gusto, es una pantalla que no contesta su pregunta. Por eso el nombre
del valor lleva la dirección adentro y no se puede pedir la contraria.

🔴 EL DEFAULT NO ESTÁ EN LA LISTA, A PROPÓSITO. Ausencia de `orden` = el orden de siempre
(apellido, nombre, id), que es el de las ~37 pantallas que ya usan este listado. Darle un nombre
—`"apellido_asc"`— invitaría a mandarlo explícito desde el front, y ahí el default pasaría a
estar escrito en DOS lugares: acá y en `ordenado()`. El día que uno de los dos cambie, las
pantallas que lo mandan explícito y las que no dejan de coincidir, sin ningún error.

⚠️ Es `Literal` y no un `str` con validación en el service, por el mismo motivo que
`utils/estados_empleado.EstadoEmpleado`: Pydantic lo corta en la frontera y devuelve un **422**
por el camino normal —con el contrato `{error, message, code}` que el front ya entiende— en vez
de que un valor cualquiera viaje hasta la query. Y los valores válidos quedan publicados en
`/docs` sin que nadie los escriba dos veces.
"""
from typing import Literal

# Los dos órdenes que hoy tienen una pantalla que los pide. Agregar uno es agregar el valor acá
# Y su columna en `repositories/_empleado_orden.ORDENES`; el test estructural del par no deja
# que uno avance sin el otro.
OrdenEmpleados = Literal["fecha_ingreso_asc", "fecha_egreso_desc"]
