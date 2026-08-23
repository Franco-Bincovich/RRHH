"""
LOS TRES USUARIOS DE PRUEBA del smoke, uno por rol. Datos puros, sin I/O.

🔴 POR QUÉ HACEN FALTA. Hoy solo hay credenciales del admin de Franco, así que el smoke entra
siempre con el rol más ancho y **las restricciones de los otros dos nunca se ejercitan en
runtime**. `docs/SMOKE-TEST.md` ya lo declara como su límite más grande: *"los 4 usuarios de
producción son admin_rrhh, así que todo el modelo de permisos se ejercita desde el rol más
amplio"*. Estos tres cierran eso sin tocar una sola credencial real — que además no se puede:
no sabemos sus contraseñas y resetearlas es intervenir la cuenta de una persona.

🔴 EL DE `mandos_medios` NECESITA GENTE A CARGO, Y LA CADENA TIENE TRES ESLABONES.
`ownership.ids_empleados_visibles` devuelve **su propio empleado + los subordinados directos**,
y para llegar ahí hace falta:
    users.id  →  empleados.user_id  →  ese empleado.id  →  el manager_id de los demás
O sea que el usuario tiene que estar VINCULADO a un colaborador (`empleado_id` en el alta, que
setea `empleados.user_id`) y ese colaborador tiene que ser el `manager_id` de los otros. Un
mando medio sin vínculo devuelve `[]` —fail-closed— y el smoke vería todas las pantallas vacías
**sin poder distinguir "el permiso funciona" de "la pantalla está rota"**, que es exactamente el
resultado inútil que estos usuarios existen para evitar.

🔴 LOS CUATRO A CARGO SON DE LA MISMA EMPRESA QUE EL JEFE, Y NO ES UNA PREFERENCIA: ES LO
ÚNICO QUE LA BASE ACEPTA. Medido el 23/8/2026 sembrando: `PUT /api/empleados/{id}` con un
`manager_id` de OTRA empresa devuelve **500**. Lo rechaza el trigger `trg_emp_empleados`, que
corre `fn_misma_empresa('area_id','areas','manager_id','empleados')` (migración 094) y levanta
excepción cuando el padre es de otra sociedad.
⚠️ **Eso CONTRADICE la decisión de producto que documenta `services/_alcance_mandos.py`** —"un
empleado puede tener superior de OTRA empresa del grupo, y para mandos_medios el `manager_id`
REEMPLAZA al filtro de empresa"—: la app está escrita para ese caso y la base no deja crearlo.
No se toca acá; está reportado. Lo que sí se hace es sembrar lo que la base permite.

🔴 TRES DE LOS CINCO CON LICENCIAS QUEDAN AFUERA, Y ES LA MITAD QUE HACE ÚTIL LA PRUEBA. Los
cinco con licencias sembradas son SMK-05, 06, 07, 08 y 09, y de esos solo 06 y 08 comparten
empresa con el jefe. Así el mando medio tiene que ver **2 de las 5 ausencias, no 5**: si viera
las cinco, el filtro de ownership no estaría haciendo nada y el test pasaría igual. Los otros dos
a cargo son preingresos (SMK-02 y SMK-04), que suman gente sin sumar licencias — sirven para
verificar que el ownership también recorta el PADRÓN, no solo las licencias.

⚠️ EL JEFE ES SMK-10 Y ES UN COLABORADOR NUEVO, no uno de los nueve. Entre los nueve no había
candidato posible: SMK-01 a 04 son preingresos (nadie que todavía no entró puede tener gente a
cargo), SMK-05 a 07 terminan dados de baja, y los dos que quedan activos —SMK-08 y 09— tienen un
offboarding abierto, así que un recorrido con Capital Humano vería a alguien que se está yendo
como jefe de cuatro personas. SMK-10 nace activo y sin proceso encima.
"""

# El colaborador (de `_semilla_padron.PERSONAS`) al que se vincula el usuario `mandos_medios`.
JEFE = "SMK-10"

# Los cuatro a cargo. 🔴 TIENEN QUE SER DE LA MISMA EMPRESA QUE `JEFE` — leer el bloque de
# arriba antes de tocar esta lista: uno de otra empresa hace que el alta devuelva 500.
# La siembra reparte alternando, así que los índices IMPARES de `PERSONAS` caen en la segunda
# empresa junto con SMK-10. `_asignar_a_cargo` lo verifica igual en runtime en vez de confiar
# en que el reparto no cambie.
A_CARGO = ["SMK-02", "SMK-04", "SMK-06", "SMK-08"]

# 🔴 El dominio es el MISMO que usa el limpiador para reconocer lo suyo (`_semilla_padron.DOMINIO`).
# Se importa de ahí y no se reescribe: dos copias que se separen dejarían usuarios huérfanos de
# la limpieza, que es la peor forma de basura que puede dejar esta semilla — un acceso al sistema
# que nadie recuerda haber creado.
from _semilla_padron import DOMINIO  # noqa: E402

# Nombres argentinos verosímiles, por el mismo motivo que el padrón: el recorrido con Capital
# Humano se hace sobre estos datos y una pantalla con "Test Admin" no se puede leer como el
# sistema real. Ninguno coincide con los 31 colaboradores reales ni con los nueve sembrados.
USUARIOS = [
    dict(clave="admin", rol="admin_rrhh", nombre="Mariano", apellido="Del Valle",
         username="smk.admin", email=f"mariano.delvalle@{DOMINIO}", legajo=None,
         para="el rol que puede todo: es el control contra el que se comparan los otros dos"),
    dict(clave="gerencia", rol="gerencia_lectura", nombre="Silvina", apellido="Achával",
         username="smk.gerencia", email=f"silvina.achaval@{DOMINIO}", legajo=None,
         para="lee todo y no escribe nada: toda escritura tiene que darle 403"),
    dict(clave="mando", rol="mandos_medios", nombre="Verónica", apellido="Ledesma",
         username="smk.mando", email=f"veronica.ledesma@{DOMINIO}", legajo=JEFE,
         para="solo VACACIONES y AUSENCIAS, y solo de los suyos: el resto del sistema, 403"),
]
