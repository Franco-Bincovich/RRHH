"""
Las 24 jurisdicciones argentinas: 23 provincias + la Ciudad Autónoma de Buenos Aires.

FUENTE. Nombres oficiales del IGN, obtenidos de la API Georef del Estado argentino
(https://apis.datos.gob.ar/georef/api/provincias). No están escritos de memoria: los acentos y
la forma larga de Tierra del Fuego son los oficiales, y son lo que hace que el valor sirva como
clave de agrupación.

POR QUÉ UNA CONSTANTE Y NO UNA TABLA. Son 24 valores que no cambian —la última modificación
del mapa político argentino fue en 1990—. Una tabla compraría un join en cada lectura, una
migración de seed y un ABM que nadie va a usar, a cambio de nada.

POR QUÉ TAMPOCO UN CHECK EN LA BASE. Sería una segunda copia de la lista, y dos copias se
separan: es exactamente el problema documentado de `permisos.ts` como espejo manual de
`permisos.py`. La validación vive acá y la base guarda texto.

🔴 EL ESPEJO DEL FRONTEND. `frontend/services/provincias.ts` necesita la misma lista para armar
el select. En vez de confiar en que dos listas escritas a mano se mantengan iguales, el
backend la EXPONE por `GET /api/empleados/catalogos/provincias` y el front la consume. Si aun
así alguien la duplica, `tests/test_provincias.py` compara ambos archivos y falla — leer la
explicación completa allá.
"""
from typing import Literal, get_args

# Orden alfabético, que es como se muestra en un select. CABA va primero por ser la capital y
# el caso más frecuente en el padrón.
Provincia = Literal[
    "Ciudad Autónoma de Buenos Aires",
    "Buenos Aires",
    "Catamarca",
    "Chaco",
    "Chubut",
    "Córdoba",
    "Corrientes",
    "Entre Ríos",
    "Formosa",
    "Jujuy",
    "La Pampa",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquén",
    "Río Negro",
    "Salta",
    "San Juan",
    "San Luis",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
    "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
    "Tucumán",
]

# Tupla para iterar (el endpoint de catálogo y los tests). `Literal` es lo que valida.
PROVINCIAS: tuple[str, ...] = get_args(Provincia)
