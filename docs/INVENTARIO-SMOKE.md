# INVENTARIO-SMOKE — todo lo que hay que probar, y qué se puede probar solo

> **GENERADO DESDE EL CÓDIGO. No editar a mano.**
> Se regenera con `backend\venv\Scripts\python.exe scripts/inventario_smoke.py`,
> y `backend/tests/test_inventario_smoke.py` da ROJO si el archivo quedó atrás.
> Última generación: **2026-08-23**.

## Por qué existe

Hay 5.700 tests y 36 barridos estructurales, y **ninguno atraviesa navegador → front →
HTTP → backend → base real**: el backend se prueba contra un doble de Supabase y el
front contra un backend simulado. El pegamento entre las dos mitades no lo mira nadie, y
de ahí salieron el deslogueo de `/vacantes` (once días echando al usuario en cada carga),
los 24 `maybe_single()` que devolvían 500 —con `POST /api/offboarding` inutilizable en
producción sin que nadie lo notara— y los botones cortados en mobile.

🔴 **El objetivo NO es probar todo: es que nada quede sin listar.** Cada fila dice si se
puede probar automáticamente y, si no, por qué. Una fila que dice «no» con su motivo es
un resultado; una fila que falta es el modo de falla que este repo ya pagó cinco veces.

### Qué NO afirma este documento

| No dice | Por qué |
|---|---|
| que la prueba EXISTA | dice si se puede escribir. Lo único que hoy corre de punta a punta es el smoke de LECTURA (`docs/SMOKE-TEST.md`), acotado a los GET |
| que el resultado sea correcto | un endpoint que responde 200 con números equivocados figura igual que uno sano |
| el texto de cada botón | ver la nota de alcance de la sección 3 |

## Resumen

| Lista | Filas | Automatizable | Sólo sobre datos sembrados | No |
|---|---:|---:|---:|---:|
| Endpoints | 265 | 203 | 25 | 37 |
| Pantallas | 46 | 41 | 0 | 5 |
| Acciones de escritura | 139 | 86 | 25 | 28 |

### Los endpoints que no salen automatizables a secas

⚠️ **`sí, sólo sobre datos sembrados` NO es lo mismo que `no`**: esas filas se prueban igual, con la semilla. Van juntas acá porque las dos exigen una decisión antes de escribir la prueba, pero la columna dice cuál es cuál.

| ¿Automatizable? | Motivo | Endpoints |
|---|---|---:|
| sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH | 25 |
| no | el router no se monta: el módulo está apagado por flag del backend | 12 |
| no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla | 9 |
| no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido | 7 |
| no | depende de una casilla de Gmail viva y de un token OAuth vigente | 6 |
| no | depende de un servicio externo (LinkedIn / Zernio) | 2 |
| no | manda un mail real desde la casilla del sistema; no se puede desenviar | 1 |

Y 7 familias de casos declarados (sección 5), que no se descubren recorriendo la superficie.

## 1 — Endpoints

Los **265** que monta la app, por introspección de `app.routes` **con todos los flags encendidos**: un módulo apagado no queda exento de figurar. El gate sale del closure de `require_permission`, no de un grep del router.

La columna **Caller** cruza contra los literales de path del front. `—declarado` significa que `tests/test_callers_huerfanos.py` ya lo tiene declarado sin caller **con su razón o su disparador de salida**, que se transcribe en la última sección.

| # | Método | Path | Gate | Escribe | Caller | ¿Automatizable? | Por qué no |
|---:|---|---|---|:-:|---|---|---|
| 1 | GET | `/api/adjuntos` | dinámico (lo resuelve el service) | 👁️ | sí | sí |  |
| 2 | POST | `/api/adjuntos` | dinámico (lo resuelve el service) | ✍️ | sí | sí |  |
| 3 | DELETE | `/api/adjuntos/{id}` | dinámico (lo resuelve el service) | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 4 | PUT | `/api/adjuntos/{id}/principal` | dinámico (lo resuelve el service) | ✍️ | sí | sí |  |
| 5 | GET | `/api/adjuntos/{id}/url` | dinámico (lo resuelve el service) | 👁️ | sí | sí |  |
| 6 | GET | `/api/areas` | areas · read | 👁️ | sí | sí |  |
| 7 | POST | `/api/areas` | areas · write | ✍️ | sí | sí |  |
| 8 | GET | `/api/areas/exportar` | areas · read | 👁️ | sí | sí |  |
| 9 | GET | `/api/areas/opciones` | areas · read | 👁️ | sí | sí |  |
| 10 | DELETE | `/api/areas/{id}` | areas · write | ✍️ | sí | sí |  |
| 11 | GET | `/api/areas/{id}` | areas · read | 👁️ | sí | sí |  |
| 12 | PUT | `/api/areas/{id}` | areas · write | ✍️ | sí | sí |  |
| 13 | GET | `/api/assessment/campanas` 🚩flag | assessment · read | 👁️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 14 | POST | `/api/assessment/campanas` 🚩flag | assessment · write | ✍️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 15 | POST | `/api/assessment/campanas/{campana_id}/links` 🚩flag | assessment · write | ✍️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 16 | GET | `/api/assessment/evaluacion/{token}` 🚩flag | público (sin auth) | 👁️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 17 | POST | `/api/assessment/evaluacion/{token}/submit` 🚩flag | público (sin auth) | ✍️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 18 | GET | `/api/assessment/resultados` 🚩flag | assessment · read | 👁️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 19 | GET | `/api/assessment/resultados/{resultado_id}` 🚩flag | assessment · read | 👁️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 20 | GET | `/api/auditoria` | auditoria · read | 👁️ | sí | sí |  |
| 21 | GET | `/api/auditoria/exportar` | auditoria · read | 👁️ | sí | sí |  |
| 22 | GET | `/api/ausencias` | ausencias · read | 👁️ | sí | sí |  |
| 23 | POST | `/api/ausencias` | ausencias · write | ✍️ | sí | sí |  |
| 24 | GET | `/api/ausencias/exportar` | ausencias · read | 👁️ | sí | sí |  |
| 25 | GET | `/api/ausencias/tipos` | ausencias · read | 👁️ | sí | sí |  |
| 26 | POST | `/api/ausencias/tipos` | ausencias · write | ✍️ | sí | sí |  |
| 27 | PATCH | `/api/ausencias/tipos/{tipo_id}` | configuracion · write | ✍️ | sí | sí |  |
| 28 | DELETE | `/api/ausencias/{id}` | ausencias · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 29 | GET | `/api/ausencias/{id}` | ausencias · read | 👁️ | **—declarado** | sí |  |
| 30 | PUT | `/api/ausencias/{id}` | ausencias · write | ✍️ | sí | sí |  |
| 31 | POST | `/api/auth/login` | público (sin auth) | ✍️ | sí | sí |  |
| 32 | POST | `/api/auth/logout` | solo auth | ✍️ | sí | sí |  |
| 33 | GET | `/api/auth/me` | solo auth | 👁️ | sí | sí |  |
| 34 | POST | `/api/auth/refresh` | público (sin auth) | ✍️ | sí | sí |  |
| 35 | GET | `/api/candidatos` | candidatos · read | 👁️ | sí | sí |  |
| 36 | GET | `/api/candidatos/exportar` | candidatos · read | 👁️ | sí | sí |  |
| 37 | DELETE | `/api/candidatos/{id}` | candidatos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 38 | POST | `/api/candidatos/{id}/contratar` | candidatos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 39 | GET | `/api/candidatos/{id}/cv-url` | candidatos · read | 👁️ | sí | sí |  |
| 40 | PUT | `/api/candidatos/{id}/etapa` | candidatos · write | ✍️ | sí | sí |  |
| 41 | PUT | `/api/candidatos/{id}/vacante` | candidatos · write | ✍️ | sí | sí |  |
| 42 | GET | `/api/capacitaciones` | capacitaciones · read | 👁️ | sí | sí |  |
| 43 | POST | `/api/capacitaciones` | capacitaciones · write | ✍️ | sí | sí |  |
| 44 | GET | `/api/capacitaciones/asignaciones` | capacitaciones · read | 👁️ | sí | sí |  |
| 45 | POST | `/api/capacitaciones/asignaciones` | capacitaciones · write | ✍️ | sí | sí |  |
| 46 | GET | `/api/capacitaciones/asignaciones/exportar` | capacitaciones · read | 👁️ | sí | sí |  |
| 47 | DELETE | `/api/capacitaciones/asignaciones/{id}` | capacitaciones · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 48 | PUT | `/api/capacitaciones/asignaciones/{id}` | capacitaciones · write | ✍️ | sí | sí |  |
| 49 | GET | `/api/capacitaciones/asignaciones/{id}/certificado` | capacitaciones · read | 👁️ | sí | sí |  |
| 50 | POST | `/api/capacitaciones/asignaciones/{id}/certificado` | capacitaciones · write | ✍️ | sí | sí |  |
| 51 | GET | `/api/capacitaciones/exportar` | capacitaciones · read | 👁️ | sí | sí |  |
| 52 | DELETE | `/api/capacitaciones/{id}` | capacitaciones · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 53 | GET | `/api/capacitaciones/{id}` | capacitaciones · read | 👁️ | **—declarado** | sí |  |
| 54 | PUT | `/api/capacitaciones/{id}` | capacitaciones · write | ✍️ | sí | sí |  |
| 55 | DELETE | `/api/cesiones/{id}` | empleados · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 56 | PUT | `/api/cesiones/{id}` | empleados · write | ✍️ | sí | sí |  |
| 57 | GET | `/api/clientes` | clientes · read | 👁️ | sí | sí |  |
| 58 | POST | `/api/clientes` | clientes · write | ✍️ | sí | sí |  |
| 59 | GET | `/api/clientes/exportar` | clientes · read | 👁️ | sí | sí |  |
| 60 | DELETE | `/api/clientes/{id}` | clientes · write | ✍️ | sí | sí |  |
| 61 | GET | `/api/clientes/{id}` | clientes · read | 👁️ | **—declarado** | sí |  |
| 62 | PUT | `/api/clientes/{id}` | clientes · write | ✍️ | sí | sí |  |
| 63 | GET | `/api/configuracion` | configuracion · read | 👁️ | sí | sí |  |
| 64 | PUT | `/api/configuracion/escala` | configuracion · write | ✍️ | sí | sí |  |
| 65 | PUT | `/api/configuracion/parametros` | configuracion · write | ✍️ | sí | sí |  |
| 66 | GET | `/api/costos/dashboard` | costos · read | 👁️ | sí | sí |  |
| 67 | GET | `/api/costos/nomina` | costos · read | 👁️ | sí | sí |  |
| 68 | POST | `/api/costos/nomina` | costos · write | ✍️ | sí | sí |  |
| 69 | GET | `/api/costos/nomina/empleado/{empleado_id}` | costos · read | 👁️ | sí | sí |  |
| 70 | GET | `/api/costos/nomina/exportar` | costos · read | 👁️ | sí | sí |  |
| 71 | POST | `/api/costos/presupuesto` | costos · write | ✍️ | sí | sí |  |
| 72 | GET | `/api/dashboard` | dashboard · read | 👁️ | sí | sí |  |
| 73 | GET | `/api/dashboard-equipo` | vacaciones · read | 👁️ | sí | sí |  |
| 74 | GET | `/api/dashboard/atencion` | dashboard · read | 👁️ | sí | sí |  |
| 75 | POST | `/api/dashboard/atencion/resolver` | eventos · write | ✍️ | sí | sí |  |
| 76 | GET | `/api/empleados` | empleados · read | 👁️ | sí | sí |  |
| 77 | POST | `/api/empleados` | empleados · write | ✍️ | sí | sí |  |
| 78 | GET | `/api/empleados/exportar` | empleados · read | 👁️ | sí | sí |  |
| 79 | GET | `/api/empleados/provincias` | empleados · read | 👁️ | sí | sí |  |
| 80 | GET | `/api/empleados/roles-conocidos` | empleados · read | 👁️ | sí | sí |  |
| 81 | GET | `/api/empleados/seleccionables` | empleados · read | 👁️ | sí | sí |  |
| 82 | GET | `/api/empleados/valores-conocidos` | empleados · read | 👁️ | sí | sí |  |
| 83 | GET | `/api/empleados/{empleado_id}/cesiones` | empleados · read | 👁️ | sí | sí |  |
| 84 | POST | `/api/empleados/{empleado_id}/cesiones` | empleados · write | ✍️ | sí | sí |  |
| 85 | GET | `/api/empleados/{empleado_id}/recategorizaciones` | recategorizaciones · read | 👁️ | sí | sí |  |
| 86 | GET | `/api/empleados/{id}` | empleados · read | 👁️ | sí | sí |  |
| 87 | PUT | `/api/empleados/{id}` | empleados · write | ✍️ | sí | sí |  |
| 88 | POST | `/api/empleados/{id}/activar` | empleados · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 89 | GET | `/api/empresas` | empresa · read | 👁️ | sí | sí |  |
| 90 | POST | `/api/empresas` | empresa · write | ✍️ | sí | sí |  |
| 91 | GET | `/api/empresas/exportar` | empresa · read | 👁️ | sí | sí |  |
| 92 | GET | `/api/empresas/{id}` | empresa · read | 👁️ | sí | sí |  |
| 93 | PUT | `/api/empresas/{id}` | empresa · write | ✍️ | sí | sí |  |
| 94 | PATCH | `/api/empresas/{id}/activa` | empresa · write | ✍️ | sí | sí |  |
| 95 | POST | `/api/empresas/{id}/logo` | empresa · write | ✍️ | sí | sí |  |
| 96 | GET | `/api/equipo` | vacaciones · read | 👁️ | sí | sí |  |
| 97 | GET | `/api/equipo/exportar` | vacaciones · read | 👁️ | sí | sí |  |
| 98 | POST | `/api/evaluaciones/importar/confirmar` | evaluaciones · write | ✍️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 99 | POST | `/api/evaluaciones/importar/preview` | evaluaciones · write | 👁️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 100 | GET | `/api/evaluaciones/resultados/lotes` | evaluaciones · read | 👁️ | sí | sí |  |
| 101 | POST | `/api/evaluaciones/resultados/lotes/eliminar` | evaluaciones · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 102 | DELETE | `/api/evaluaciones/resultados/lotes/{lote_id}` | evaluaciones · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 103 | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados` | evaluaciones · read | 👁️ | sí | sí |  |
| 104 | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/export` | evaluaciones · read | 👁️ | sí | sí |  |
| 105 | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/evaluados/{evaluado_id}/ficha` | evaluaciones · read | 👁️ | sí | sí |  |
| 106 | GET | `/api/evaluaciones/resultados/lotes/{lote_id}/metricas` | evaluaciones · read | 👁️ | sí | sí |  |
| 107 | GET | `/api/eventos` | eventos · read | 👁️ | sí | sí |  |
| 108 | POST | `/api/eventos` | eventos · write | ✍️ | sí | sí |  |
| 109 | DELETE | `/api/eventos/{id}` | eventos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 110 | GET | `/api/eventos/{id}` | eventos · read | 👁️ | **—declarado** | sí |  |
| 111 | PUT | `/api/eventos/{id}` | eventos · write | ✍️ | sí | sí |  |
| 112 | PUT | `/api/eventos/{id}/resuelta` | eventos · write | ✍️ | sí | sí |  |
| 113 | GET | `/api/horas-cliente` | proyectos · read | 👁️ | sí | sí |  |
| 114 | GET | `/api/horas-cliente/detalle` | proyectos · read | 👁️ | sí | sí |  |
| 115 | GET | `/api/horas-cliente/exportar` | proyectos · read | 👁️ | sí | sí |  |
| 116 | DELETE | `/api/horas-cliente/{hora_id}` | proyectos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 117 | GET | `/api/horas-publico/clientes` 🚩flag | público (sin auth) | 👁️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 118 | POST | `/api/horas-publico/horas` 🚩flag | público (sin auth) | ✍️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 119 | POST | `/api/horas-publico/identificar` 🚩flag | público (sin auth) | ✍️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 120 | POST | `/api/horas-publico/licencia` 🚩flag | público (sin auth) | ✍️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 121 | GET | `/api/horas-publico/semana` 🚩flag | público (sin auth) | 👁️ | sí | no | el router no se monta: el módulo está apagado por flag del backend |
| 122 | POST | `/api/importacion/formacion/confirmar` | importacion · write | ✍️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 123 | POST | `/api/importacion/formacion/preview` | importacion · write | 👁️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 124 | POST | `/api/importacion/nomina-empleados` | importacion · write | ✍️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 125 | POST | `/api/importacion/nomina/confirmar` | importacion · write | ✍️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 126 | POST | `/api/importacion/nomina/preview` | importacion · write | 👁️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 127 | POST | `/api/importacion/objetivos/confirmar` | importacion · write | ✍️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 128 | POST | `/api/importacion/objetivos/preview` | importacion · write | 👁️ | sí | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| 129 | GET | `/api/importacion/superiores-pendientes` | importacion · read | 👁️ | sí | sí |  |
| 130 | POST | `/api/importacion/superiores-pendientes/resolver` | importacion · write | ✍️ | sí | sí |  |
| 131 | GET | `/api/integraciones` | integraciones · read | 👁️ | sí | sí |  |
| 132 | POST | `/api/integraciones/anthropic` | integraciones · write | ✍️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 133 | GET | `/api/integraciones/google/auth` | integraciones · read | 👁️ | sí | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| 134 | GET | `/api/integraciones/google/callback` | público (sin auth) | 👁️ | **—declarado** | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| 135 | POST | `/api/integraciones/google/remitente` | integraciones · write | ✍️ | sí | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| 136 | POST | `/api/integraciones/zernio` | integraciones · write | ✍️ | sí | no | depende de un servicio externo (LinkedIn / Zernio) |
| 137 | DELETE | `/api/integraciones/{tipo}` | integraciones · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 138 | GET | `/api/inventario/asignaciones` | inventario · read | 👁️ | sí | sí |  |
| 139 | POST | `/api/inventario/asignaciones` | inventario · write | ✍️ | sí | sí |  |
| 140 | GET | `/api/inventario/asignaciones/exportar` | inventario · read | 👁️ | sí | sí |  |
| 141 | POST | `/api/inventario/asignaciones/{id}/devolver` | inventario · write | ✍️ | sí | sí |  |
| 142 | GET | `/api/inventario/items` | inventario · read | 👁️ | sí | sí |  |
| 143 | POST | `/api/inventario/items` | inventario · write | ✍️ | sí | sí |  |
| 144 | GET | `/api/inventario/items/exportar` | inventario · read | 👁️ | sí | sí |  |
| 145 | DELETE | `/api/inventario/items/{id}` | inventario · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 146 | GET | `/api/inventario/items/{id}` | inventario · read | 👁️ | sí | sí |  |
| 147 | PUT | `/api/inventario/items/{id}` | inventario · write | ✍️ | sí | sí |  |
| 148 | GET | `/api/inventario/items/{id}/historial` | inventario · read | 👁️ | sí | sí |  |
| 149 | GET | `/api/mails` | configuracion · read | 👁️ | sí | sí |  |
| 150 | GET | `/api/objetivos` | objetivos · read | 👁️ | sí | sí |  |
| 151 | POST | `/api/objetivos` | objetivos · write | ✍️ | sí | sí |  |
| 152 | GET | `/api/objetivos/areas-conocidas` | objetivos · read | 👁️ | **—declarado** | sí |  |
| 153 | GET | `/api/objetivos/campos` | objetivos · read | 👁️ | sí | sí |  |
| 154 | GET | `/api/objetivos/exportar` | objetivos · read | 👁️ | sí | sí |  |
| 155 | DELETE | `/api/objetivos/{id}` | objetivos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 156 | PUT | `/api/objetivos/{id}` | objetivos · write | ✍️ | sí | sí |  |
| 157 | PUT | `/api/objetivos/{id}/estado` | objetivos · write | ✍️ | sí | sí |  |
| 158 | GET | `/api/offboarding` | offboarding · read | 👁️ | sí | sí |  |
| 159 | POST | `/api/offboarding` | offboarding · write | ✍️ | sí | sí |  |
| 160 | GET | `/api/offboarding/exportar` | offboarding · read | 👁️ | sí | sí |  |
| 161 | PUT | `/api/offboarding/{instancia_id}/activos/{activo_id}` | offboarding · write | ✍️ | sí | sí |  |
| 162 | POST | `/api/offboarding/{instancia_id}/efectivizar` | offboarding · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 163 | PUT | `/api/offboarding/{instancia_id}/entrevista` | offboarding · write | ✍️ | sí | sí |  |
| 164 | GET | `/api/onboarding` | onboarding · read | 👁️ | sí | sí |  |
| 165 | GET | `/api/onboarding/exportar` | onboarding · read | 👁️ | sí | sí |  |
| 166 | GET | `/api/onboarding/templates` | onboarding · read | 👁️ | sí | sí |  |
| 167 | POST | `/api/onboarding/templates` | onboarding · write | ✍️ | sí | sí |  |
| 168 | GET | `/api/onboarding/templates/exportar` | onboarding · read | 👁️ | sí | sí |  |
| 169 | DELETE | `/api/onboarding/templates/{template_id}` | onboarding · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 170 | GET | `/api/onboarding/templates/{template_id}` | onboarding · read | 👁️ | sí | sí |  |
| 171 | PUT | `/api/onboarding/templates/{template_id}` | onboarding · write | ✍️ | sí | sí |  |
| 172 | POST | `/api/onboarding/templates/{template_id}/tareas` | onboarding · write | ✍️ | sí | sí |  |
| 173 | DELETE | `/api/onboarding/templates/{template_id}/tareas/{tarea_id}` | onboarding · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 174 | PUT | `/api/onboarding/templates/{template_id}/tareas/{tarea_id}` | onboarding · write | ✍️ | sí | sí |  |
| 175 | GET | `/api/onboarding/{empleado_id}` | onboarding · read | 👁️ | sí | sí |  |
| 176 | POST | `/api/onboarding/{empleado_id}/iniciar` | onboarding · write | ✍️ | sí | sí |  |
| 177 | PUT | `/api/onboarding/{instancia_id}/tareas/{tarea_id}/completar` | onboarding · write | ✍️ | sí | sí |  |
| 178 | GET | `/api/organigrama` | organigrama · read | 👁️ | sí | sí |  |
| 179 | GET | `/api/organigrama/proyectos` | organigrama · read | 👁️ | sí | sí |  |
| 180 | GET | `/api/perfiles-puesto` | perfiles_puesto · read | 👁️ | sí | sí |  |
| 181 | POST | `/api/perfiles-puesto` | perfiles_puesto · write | ✍️ | sí | sí |  |
| 182 | GET | `/api/perfiles-puesto/campos` | perfiles_puesto · read | 👁️ | sí | sí |  |
| 183 | GET | `/api/perfiles-puesto/exportar` | perfiles_puesto · read | 👁️ | sí | sí |  |
| 184 | DELETE | `/api/perfiles-puesto/{id}` | perfiles_puesto · write | ✍️ | sí | sí |  |
| 185 | GET | `/api/perfiles-puesto/{id}` | perfiles_puesto · read | 👁️ | **—declarado** | sí |  |
| 186 | PUT | `/api/perfiles-puesto/{id}` | perfiles_puesto · write | ✍️ | sí | sí |  |
| 187 | GET | `/api/periodos` | periodos · read | 👁️ | sí | sí |  |
| 188 | POST | `/api/periodos` | periodos · write | ✍️ | sí | sí |  |
| 189 | GET | `/api/periodos/exportar` | periodos · read | 👁️ | sí | sí |  |
| 190 | POST | `/api/periodos/{id}/reabrir` | periodos · write | ✍️ | sí | sí |  |
| 191 | GET | `/api/plantillas` | configuracion · read | 👁️ | sí | sí |  |
| 192 | PUT | `/api/plantillas` | configuracion · write | ✍️ | sí | sí |  |
| 193 | POST | `/api/plantillas/enviar` | configuracion · write | ✍️ | sí | no | manda un mail real desde la casilla del sistema; no se puede desenviar |
| 194 | POST | `/api/plantillas/preview` | configuracion · read | 👁️ | sí | sí |  |
| 195 | DELETE | `/api/plantillas/{id}` | configuracion · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 196 | GET | `/api/procesos` | procesos · read | 👁️ | sí | sí |  |
| 197 | GET | `/api/proyectos` | proyectos · read | 👁️ | sí | sí |  |
| 198 | POST | `/api/proyectos` | proyectos · write | ✍️ | sí | sí |  |
| 199 | GET | `/api/proyectos/exportar` | proyectos · read | 👁️ | sí | sí |  |
| 200 | DELETE | `/api/proyectos/{id}` | proyectos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 201 | GET | `/api/proyectos/{id}` | proyectos · read | 👁️ | sí | sí |  |
| 202 | PUT | `/api/proyectos/{id}` | proyectos · write | ✍️ | sí | sí |  |
| 203 | GET | `/api/proyectos/{proyecto_id}/asignaciones` | proyectos · read | 👁️ | sí | sí |  |
| 204 | POST | `/api/proyectos/{proyecto_id}/asignaciones` | proyectos · write | ✍️ | sí | sí |  |
| 205 | POST | `/api/proyectos/{proyecto_id}/asignaciones/area` | proyectos · write | ✍️ | sí | sí |  |
| 206 | POST | `/api/proyectos/{proyecto_id}/asignaciones/bulk` | proyectos · write | ✍️ | sí | sí |  |
| 207 | DELETE | `/api/proyectos/{proyecto_id}/asignaciones/{asig_id}` | proyectos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 208 | PUT | `/api/proyectos/{proyecto_id}/asignaciones/{asig_id}` | proyectos · write | ✍️ | sí | sí |  |
| 209 | GET | `/api/proyectos/{proyecto_id}/horas` | proyectos · read | 👁️ | sí | sí |  |
| 210 | POST | `/api/proyectos/{proyecto_id}/horas` | proyectos · write | ✍️ | sí | sí |  |
| 211 | DELETE | `/api/proyectos/{proyecto_id}/horas/{hora_id}` | proyectos · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 212 | GET | `/api/recategorizaciones` | recategorizaciones · read | 👁️ | sí | sí |  |
| 213 | POST | `/api/recategorizaciones` | recategorizaciones · write | ✍️ | sí | sí |  |
| 214 | GET | `/api/recategorizaciones/exportar` | recategorizaciones · read | 👁️ | sí | sí |  |
| 215 | GET | `/api/recategorizaciones/{id}` | recategorizaciones · read | 👁️ | **—declarado** | sí |  |
| 216 | PUT | `/api/recategorizaciones/{id}` | recategorizaciones · write | ✍️ | sí | sí |  |
| 217 | POST | `/api/reportes/generar` | reportes · write | ✍️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 218 | GET | `/api/reportes/historial` | reportes · read | 👁️ | sí | sí |  |
| 219 | GET | `/api/reportes/{reporte_id}/exportar` | reportes · read | 👁️ | sí | sí |  |
| 220 | PUT | `/api/screening/candidatos/{candidato_id}/clasificacion` | candidatos · write | ✍️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 221 | GET | `/api/screening/criterio` | configuracion · read | 👁️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 222 | PUT | `/api/screening/criterio` | configuracion · write | ✍️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 223 | POST | `/api/screening/criterio/restaurar` | configuracion · write | ✍️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 224 | POST | `/api/screening/vacantes/{vacante_id}` | candidatos · write | ✍️ | sí | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| 225 | GET | `/api/sucesion/analisis` | sucesion · read | 👁️ | sí | sí |  |
| 226 | PUT | `/api/sucesion/hitos/{hito_id}/completar` | sucesion · write | ✍️ | sí | sí |  |
| 227 | GET | `/api/sucesion/mapa` | sucesion · read | 👁️ | sí | sí |  |
| 228 | GET | `/api/sucesion/planes` | sucesion · read | 👁️ | sí | sí |  |
| 229 | POST | `/api/sucesion/planes` | sucesion · write | ✍️ | sí | sí |  |
| 230 | GET | `/api/sucesion/planes/{plan_id}/hitos` | sucesion · read | 👁️ | sí | sí |  |
| 231 | POST | `/api/sucesion/planes/{plan_id}/hitos` | sucesion · write | ✍️ | sí | sí |  |
| 232 | PUT | `/api/sucesion/planes/{plan_id}/readiness` | sucesion · write | ✍️ | sí | sí |  |
| 233 | GET | `/api/usuarios` | usuarios · read | 👁️ | sí | sí |  |
| 234 | POST | `/api/usuarios` | usuarios · write | ✍️ | sí | sí |  |
| 235 | POST | `/api/usuarios/cambiar-password` | solo auth | ✍️ | sí | sí |  |
| 236 | GET | `/api/usuarios/exportar` | usuarios · read | 👁️ | sí | sí |  |
| 237 | DELETE | `/api/usuarios/{user_id}` | usuarios · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 238 | GET | `/api/vacaciones` | vacaciones · read | 👁️ | sí | sí |  |
| 239 | POST | `/api/vacaciones` | vacaciones · write | ✍️ | sí | sí |  |
| 240 | GET | `/api/vacaciones-pendientes` | vacaciones · read | 👁️ | sí | sí |  |
| 241 | POST | `/api/vacaciones-pendientes` | vacaciones · write | ✍️ | sí | sí |  |
| 242 | GET | `/api/vacaciones-pendientes/empleado/{empleado_id}` | vacaciones · read | 👁️ | **—declarado** | sí |  |
| 243 | GET | `/api/vacaciones-pendientes/exportar` | vacaciones · read | 👁️ | sí | sí |  |
| 244 | DELETE | `/api/vacaciones-pendientes/{id}` | vacaciones · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 245 | PUT | `/api/vacaciones-pendientes/{id}` | vacaciones · write | ✍️ | sí | sí |  |
| 246 | GET | `/api/vacaciones/empleado/{empleado_id}` | vacaciones · read | 👁️ | sí | sí |  |
| 247 | GET | `/api/vacaciones/exportar` | vacaciones · read | 👁️ | sí | sí |  |
| 248 | GET | `/api/vacaciones/saldo/{empleado_id}` | vacaciones · read | 👁️ | sí | sí |  |
| 249 | GET | `/api/vacaciones/{id}` | vacaciones · read | 👁️ | sí | sí |  |
| 250 | PUT | `/api/vacaciones/{id}` | vacaciones · write | ✍️ | sí | sí |  |
| 251 | PUT | `/api/vacaciones/{id}/cancelar` | vacaciones · write | ✍️ | sí | sí |  |
| 252 | GET | `/api/vacantes` | vacantes · read | 👁️ | sí | sí |  |
| 253 | POST | `/api/vacantes` | vacantes · write | ✍️ | sí | sí |  |
| 254 | POST | `/api/vacantes/casilla/asignar` | vacantes · write | ✍️ | sí | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| 255 | GET | `/api/vacantes/casilla/pendientes` | vacantes · read | 👁️ | sí | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| 256 | POST | `/api/vacantes/casilla/revisar` | vacantes · write | ✍️ | sí | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| 257 | GET | `/api/vacantes/exportar` | vacantes · read | 👁️ | sí | sí |  |
| 258 | DELETE | `/api/vacantes/{id}` | vacantes · write | ✍️ | sí | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| 259 | GET | `/api/vacantes/{id}` | vacantes · read | 👁️ | sí | sí |  |
| 260 | PUT | `/api/vacantes/{id}` | vacantes · write | ✍️ | sí | sí |  |
| 261 | GET | `/api/vacantes/{id}/aviso` | vacantes · read | 👁️ | sí | sí |  |
| 262 | GET | `/api/vacantes/{id}/candidatos` | vacantes · read | 👁️ | sí | sí |  |
| 263 | POST | `/api/vacantes/{id}/candidatos` | vacantes · write | ✍️ | sí | sí |  |
| 264 | POST | `/api/vacantes/{id}/publicar-linkedin` | vacantes · write | ✍️ | sí | no | depende de un servicio externo (LinkedIn / Zernio) |
| 265 | GET | `/health` | público (sin auth) | 👁️ | **—declarado** | sí |  |

## 2 — Pantallas

Las **46** rutas de `app/`. ⚠️ **La columna GET dice qué endpoints ALCANZA la pantalla por su grafo de imports, no qué dispara exactamente al montar**: adentro caen también los fetch de un modal que quizás no se abra. Es un superconjunto a propósito — un endpoint de más se prueba y se tacha, uno de menos no se descubre nunca.

**Roles** sale de `RUTA_SECCION` (el mapa del AuthGuard) resuelto con `utils.permisos.puede`, que es la fuente canónica: reimplementarlo acá sería un tercer espejo de un modelo que ya tiene dos y ningún test que los compare.

| Ruta | Sección | Roles que la ven | GET | Export | Escrituras | Filtra | Pagina | Apagada | ¿Automatizable? |
|---|---|---|---:|---:|---:|:-:|:-:|---|---|
| `/areas` | areas | admin rrhh, gerencia lectura | 3 | 1 | 3 | sí | sí | — | sí |
| `/assessment/{}` | assessment | admin rrhh, gerencia lectura | 1 | 0 | 0 | — | — | flag del front (la página redirige a /dashboard) | no |
| `/assessment` | assessment | admin rrhh, gerencia lectura | 4 | 0 | 1 | — | — | flag del front (la página redirige a /dashboard) | no |
| `/auditoria` | auditoria | admin rrhh, gerencia lectura | 3 | 1 | 0 | sí | sí | — | sí |
| `/ausencias` | ausencias | todos | 10 | 1 | 6 | sí | sí | — | sí |
| `/bajas` | offboarding | admin rrhh, gerencia lectura | 4 | 0 | 0 | sí | sí | — | sí |
| `/candidatos` | candidatos | admin rrhh, gerencia lectura | 4 | 1 | 4 | sí | sí | — | sí |
| `/capacitaciones` | capacitaciones | admin rrhh, gerencia lectura | 7 | 2 | 9 | sí | sí | — | sí |
| `/clientes` | clientes | admin rrhh, gerencia lectura | 1 | 1 | 3 | sí | — | — | sí |
| `/comunicacion` | configuracion | admin rrhh, gerencia lectura | 3 | 0 | 4 | sí | — | — | sí |
| `/configuracion` | — | todos | 5 | 0 | 13 | — | — | — | sí |
| `/costos` | costos | admin rrhh, gerencia lectura | 4 | 1 | 3 | — | sí | — | sí |
| `/dashboard` | — | todos | 3 | 0 | 1 | — | — | — | sí |
| `/empleados/{}` | empleados | admin rrhh, gerencia lectura | 15 | 0 | 9 | — | sí | — | sí |
| `/empleados` | empleados | admin rrhh, gerencia lectura | 9 | 1 | 4 | sí | sí | — | sí |
| `/empresas/{}` | empresa | admin rrhh, gerencia lectura | 4 | 0 | 6 | — | — | — | sí |
| `/empresas` | empresa | admin rrhh, gerencia lectura | 1 | 1 | 3 | — | — | — | sí |
| `/equipo` | vacaciones | todos | 1 | 1 | 0 | — | — | — | sí |
| `/evaluaciones` | evaluaciones | admin rrhh, gerencia lectura | 7 | 1 | 4 | sí | sí | — | sí |
| `/eventos` | eventos | admin rrhh, gerencia lectura | 1 | 0 | 4 | sí | sí | — | sí |
| `/horas-por-cliente` | proyectos | admin rrhh, gerencia lectura | 2 | 1 | 1 | — | — | — | sí |
| `/inventario` | inventario | admin rrhh, gerencia lectura | 7 | 2 | 5 | sí | sí | — | sí |
| `/objetivos` | objetivos | admin rrhh, gerencia lectura | 4 | 1 | 6 | sí | — | — | sí |
| `/offboarding` | offboarding | admin rrhh, gerencia lectura | 3 | 1 | 5 | — | — | — | sí |
| `/onboarding` | onboarding | admin rrhh, gerencia lectura | 4 | 1 | 2 | — | — | — | sí |
| `/onboarding/templates/{}` | onboarding | admin rrhh, gerencia lectura | 1 | 0 | 4 | — | — | — | sí |
| `/onboarding/templates` | onboarding | admin rrhh, gerencia lectura | 2 | 1 | 2 | — | — | — | sí |
| `/organigrama` | organigrama | admin rrhh, gerencia lectura | 2 | 0 | 0 | — | — | — | sí |
| `/perfiles-puesto` | perfiles_puesto | admin rrhh, gerencia lectura | 2 | 1 | 3 | sí | sí | — | sí |
| `/periodos` | periodos | admin rrhh, gerencia lectura | 3 | 1 | 2 | — | — | — | sí |
| `/procesos` | procesos | admin rrhh, gerencia lectura | 1 | 0 | 0 | — | — | — | sí |
| `/proximos-ingresos` | empleados | admin rrhh, gerencia lectura | 4 | 0 | 1 | sí | sí | — | sí |
| `/proyectos/{}` | proyectos | admin rrhh, gerencia lectura | 6 | 0 | 7 | — | sí | — | sí |
| `/proyectos` | proyectos | admin rrhh, gerencia lectura | 3 | 1 | 2 | sí | sí | — | sí |
| `/recategorizaciones` | recategorizaciones | admin rrhh, gerencia lectura | 3 | 1 | 2 | sí | sí | — | sí |
| `/reportes` | reportes | admin rrhh, gerencia lectura | 3 | 1 | 1 | — | — | — | sí |
| `/sucesion` | sucesion | admin rrhh, gerencia lectura | 6 | 0 | 4 | sí | — | flag del front (la página redirige a /dashboard) | no |
| `/usuarios` | usuarios | admin rrhh, gerencia lectura | 2 | 1 | 2 | — | — | — | sí |
| `/vacaciones` | vacaciones | todos | 11 | 2 | 7 | sí | sí | — | sí |
| `/vacantes/{}` | vacantes | admin rrhh, gerencia lectura | 6 | 0 | 10 | — | — | — | sí |
| `/vacantes` | vacantes | admin rrhh, gerencia lectura | 4 | 1 | 3 | sí | sí | — | sí |
| `/cambiar-password` | — | todos | 0 | 0 | 1 | — | — | — | sí |
| `/evaluacion/{}` | — | todos | 1 | 0 | 1 | — | — | flag del backend (el router no se monta) | no |
| `/horas` | — | todos | 2 | 0 | 3 | — | — | flag del backend (el router no se monta) | no |
| `/login` | — | todos | 0 | 0 | 1 | — | — | — | sí |
| `/` | — | todos | 0 | 0 | 0 | — | — | — | sí |

## 3 — Acciones de escritura

**139** filas. 🔴 **La unidad es «el componente que importa una función de escritura y la invoca», no «el botón»**, y la diferencia importa al leer la lista:

| Se cuenta | Qué pasa |
|---|---|
| dos botones que llaman a la MISMA función en el mismo componente | **una** fila (sub-cuenta — es el único lado por el que esta lista se queda corta) |
| un componente que llama a dos funciones distintas | **dos** filas |
| `onSubmit`, `onChange` de un toggle y `onClick` | indistinguibles: los tres son «el componente llama a la función» |

**Lo que NO se puede derivar del código estático:** el TEXTO del botón (vive en el JSX, muchas veces armado con un ternario sobre el estado), si el control está VISIBLE (casi todos cuelgan de `useCanWrite()`, pero también hay condiciones de estado) y si la acción es idempotente (eso es del backend). La columna dice el COMPONENTE, que es lo que un tester puede abrir y buscar.

**Roles** = los de la pantalla **intersecados con `write`**: `gerencia_lectura` lee todas las pantallas, así que sin esa intersección la tabla diría que ve el botón de borrar — y el backend le contesta 403.

| Pantalla | Componente | Función | Endpoint | Roles | Destructivo | ¿Automatizable? | Por qué |
|---|---|---|---|---|---|---|---|
| (layout) /(dashboard) | `components/layout/UserMenu.tsx` | `logout` | `POST /api/auth/logout` | todos | reversible | sí |  |
| /areas, /empresas/{} | `components/features/areas/guardarArea.ts` | `createArea` | `POST /api/areas` | admin rrhh | reversible | sí |  |
| /areas, /empresas/{} | `components/features/areas/guardarArea.ts` | `updateArea` | `PUT /api/areas/{}` | admin rrhh | reversible | sí |  |
| /areas | `components/features/areas/useAreasAcciones.ts` | `deleteArea` | `DELETE /api/areas/{}` | admin rrhh | reversible | sí |  |
| /assessment | `components/features/assessment/CampanaModal.tsx` | `createCampana` | `POST /api/assessment/campanas` | admin rrhh | reversible | no | el router no se monta: el módulo está apagado por flag del backend |
| /ausencias, /empleados/{}, /offboarding, /vacaciones | `components/features/adjuntos/AdjuntosSection.tsx` | `eliminarAdjunto` | `DELETE /api/adjuntos/{}` | admin rrhh, mandos medios | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /ausencias, /empleados/{}, /offboarding, /vacaciones | `components/features/adjuntos/AdjuntosSection.tsx` | `subirAdjunto` | `POST /api/adjuntos` | admin rrhh, mandos medios | reversible | sí |  |
| /ausencias | `components/features/ausencias/useAusenciaForm.ts` | `crearAusenciaConAdjuntos` | `POST /api/adjuntos`<br>`POST /api/ausencias` | admin rrhh, mandos medios | reversible | sí |  |
| /ausencias | `components/features/ausencias/useAusenciaForm.ts` | `updateAusencia` | `PUT /api/ausencias/{}` | admin rrhh, mandos medios | reversible | sí |  |
| /ausencias | `components/features/ausencias/useListadoAusencias.ts` | `deleteAusencia` | `DELETE /api/ausencias/{}` | admin rrhh, mandos medios | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /ausencias | `components/features/ausencias/useTiposAusencia.ts` | `createTipoAusencia` | `POST /api/ausencias/tipos` | admin rrhh, mandos medios | reversible | sí |  |
| /cambiar-password, /configuracion | `components/features/usuarios/CambiarPasswordForm.tsx` | `cambiarPassword` | `POST /api/usuarios/cambiar-password` | todos | reversible | sí |  |
| /candidatos | `components/features/candidatos/AsignarVacanteCandidato.tsx` | `asignarVacanteACandidato` | `PUT /api/candidatos/{}/vacante` | admin rrhh | reversible | sí |  |
| /candidatos | `components/features/candidatos/ContratarCandidatoButton.tsx` | `contratarCandidato` | `POST /api/candidatos/{}/contratar` | admin rrhh | 🔴 crea el legajo del candidato; no hay des-contratar | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /candidatos | `components/features/candidatos/EliminarCandidatoButton.tsx` | `deleteCandidato` | `DELETE /api/candidatos/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /candidatos, /vacantes/{} | `components/features/screening/CorregirClasificacion.tsx` | `corregirClasificacion` | `PUT /api/screening/candidatos/{}/clasificacion` | admin rrhh | reversible | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| /capacitaciones | `components/features/capacitaciones/AsignacionModal.tsx` | `createAsignacion` | `POST /api/capacitaciones/asignaciones` | admin rrhh | reversible | sí |  |
| /capacitaciones | `components/features/capacitaciones/AsignacionesTab.tsx` | `deleteAsignacion` | `DELETE /api/capacitaciones/asignaciones/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /capacitaciones | `components/features/capacitaciones/CapacitacionModal.tsx` | `createCapacitacion` | `POST /api/capacitaciones` | admin rrhh | reversible | sí |  |
| /capacitaciones | `components/features/capacitaciones/CapacitacionModal.tsx` | `updateCapacitacion` | `PUT /api/capacitaciones/{}` | admin rrhh | reversible | sí |  |
| /capacitaciones | `components/features/capacitaciones/CatalogoTab.tsx` | `deleteCapacitacion` | `DELETE /api/capacitaciones/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /capacitaciones | `components/features/capacitaciones/CertificadoCell.tsx` | `uploadCertificado` | `POST /api/capacitaciones/asignaciones/{}/certificado` | admin rrhh | reversible | sí |  |
| /capacitaciones | `components/features/capacitaciones/EstadoModal.tsx` | `updateAsignacion` | `PUT /api/capacitaciones/asignaciones/{}` | admin rrhh | reversible | sí |  |
| /capacitaciones | `components/features/capacitaciones/ImportarFormacionModal.tsx` | `confirmarFormacion` | `POST /api/importacion/formacion/confirmar` | admin rrhh | 🔴 persiste el lote entero del import; en evaluaciones BORRA el período anterior por CASCADE antes de escribir el nuevo | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /capacitaciones | `components/features/capacitaciones/ImportarFormacionModal.tsx` | `previewFormacion` | `POST /api/importacion/formacion/preview` | admin rrhh | reversible | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /clientes | `app/(dashboard)/clientes/page.tsx` | `deleteCliente` | `DELETE /api/clientes/{}` | admin rrhh | reversible | sí |  |
| /clientes | `components/features/clientes/guardarCliente.ts` | `createCliente` | `POST /api/clientes` | admin rrhh | reversible | sí |  |
| /clientes | `components/features/clientes/guardarCliente.ts` | `updateCliente` | `PUT /api/clientes/{}` | admin rrhh | reversible | sí |  |
| /comunicacion | `components/features/comunicacion/PlantillaModal.tsx` | `guardarPlantilla` | `PUT /api/plantillas` | admin rrhh | reversible | sí |  |
| /comunicacion | `components/features/comunicacion/PlantillaModal.tsx` | `previewPlantilla` | `POST /api/plantillas/preview` | admin rrhh | reversible | sí |  |
| /comunicacion | `components/features/comunicacion/envioAcciones.ts` | `enviarPlantilla` | `POST /api/plantillas/enviar` | admin rrhh | 🔴 sale un mail real a un buzón real; no se puede desenviar | no | manda un mail real desde la casilla del sistema; no se puede desenviar |
| /comunicacion | `components/features/comunicacion/usePlantillas.ts` | `borrarPlantilla` | `DELETE /api/plantillas/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /configuracion | `components/features/configuracion/PerfilSection.tsx` | `logout` | `POST /api/auth/logout` | todos | reversible | sí |  |
| /configuracion | `components/features/configuracion/accionesConfiguracion.ts` | `guardarEscala` | `PUT /api/configuracion/escala` | todos | reversible | sí |  |
| /configuracion | `components/features/configuracion/accionesConfiguracion.ts` | `guardarParametros` | `PUT /api/configuracion/parametros` | todos | reversible | sí |  |
| /configuracion | `components/features/configuracion/accionesIntegracion.ts` | `designarRemitente` | `POST /api/integraciones/google/remitente` | todos | reversible | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| /configuracion | `components/features/configuracion/accionesIntegracion.ts` | `disconnectIntegracion` | `DELETE /api/integraciones/{}` | todos | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /configuracion | `components/features/configuracion/useCriterioScreening.ts` | `restaurarCriterioScreening` | `POST /api/screening/criterio/restaurar` | todos | reversible | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| /configuracion | `components/features/configuracion/useCriterioScreening.ts` | `setCriterioScreening` | `PUT /api/screening/criterio` | todos | reversible | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| /configuracion | `components/features/configuracion/useTiposAusencia.ts` | `createTipoAusencia` | `POST /api/ausencias/tipos` | todos | reversible | sí |  |
| /configuracion | `components/features/configuracion/useTiposAusencia.ts` | `updateTipoAusencia` | `PATCH /api/ausencias/tipos/{}` | todos | reversible | sí |  |
| /costos | `components/features/costos/ImportarNominaCSVModal.tsx` | `confirmarImportacionNomina` | `POST /api/importacion/nomina/confirmar` | admin rrhh | 🔴 persiste el lote entero del import; en evaluaciones BORRA el período anterior por CASCADE antes de escribir el nuevo | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /costos | `components/features/costos/ImportarNominaCSVModal.tsx` | `previewImportacionNominaCSV` | `POST /api/importacion/nomina/preview` | admin rrhh | reversible | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /costos | `components/features/costos/NominaModal.tsx` | `cargarNomina` | `POST /api/costos/nomina` | admin rrhh | reversible | sí |  |
| /costos | `components/features/costos/useEdicionNomina.ts` | `cargarNomina` | `POST /api/costos/nomina` | admin rrhh | reversible | sí |  |
| /dashboard | `components/features/dashboard/DashboardAdmin.tsx` | `resolverAtencion` | `POST /api/dashboard/atencion/resolver` | todos | reversible | sí |  |
| /empleados | `components/features/empleados/ImportarNominaModal.tsx` | `importarNominaEmpleados` | `POST /api/importacion/nomina-empleados` | admin rrhh | reversible | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /empleados | `components/features/empleados/SuperioresPendientesPanel.tsx` | `resolverSuperioresPendientes` | `POST /api/importacion/superiores-pendientes/resolver` | admin rrhh | reversible | sí |  |
| /empleados, /empleados/{} | `components/features/empleados/modal/_guardar.ts` | `createEmpleado` | `POST /api/empleados` | admin rrhh | reversible | sí |  |
| /empleados, /empleados/{} | `components/features/empleados/modal/_guardar.ts` | `updateEmpleado` | `PUT /api/empleados/{}` | admin rrhh | reversible | sí |  |
| /empleados/{} | `components/features/empleados/ficha/CesionModal.tsx` | `actualizarCesion` | `PUT /api/cesiones/{}` | admin rrhh | reversible | sí |  |
| /empleados/{} | `components/features/empleados/ficha/CesionModal.tsx` | `crearCesion` | `POST /api/empleados/{}/cesiones` | admin rrhh | reversible | sí |  |
| /empleados/{} | `components/features/empleados/ficha/CesionesSection.tsx` | `eliminarCesion` | `DELETE /api/cesiones/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /empleados/{} | `components/features/empleados/ficha/OffboardingModal.tsx` | `iniciarOffboarding` | `POST /api/offboarding` | admin rrhh | reversible | sí |  |
| /empleados/{}, /proximos-ingresos | `components/features/empleados/useActivarEmpleado.ts` | `activarEmpleado` | `POST /api/empleados/{}/activar` | admin rrhh | 🔴 convierte un preingreso en activo; no hay endpoint que lo devuelva a preingreso | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /empresas | `app/(dashboard)/empresas/page.tsx` | `toggleEmpresaActiva` | `PATCH /api/empresas/{}/activa` | admin rrhh | reversible | sí |  |
| /empresas, /empresas/{} | `components/features/empresas/EmpresaModal.tsx` | `createEmpresa` | `POST /api/empresas` | admin rrhh | reversible | sí |  |
| /empresas, /empresas/{} | `components/features/empresas/EmpresaModal.tsx` | `updateEmpresa` | `PUT /api/empresas/{}` | admin rrhh | reversible | sí |  |
| /empresas/{} | `components/features/empresas/EmpresaAreasTab.tsx` | `deleteArea` | `DELETE /api/areas/{}` | admin rrhh | reversible | sí |  |
| /empresas/{} | `components/features/empresas/ficha/LogoPanel.tsx` | `uploadLogo` | `POST /api/empresas/{}/logo` | admin rrhh | reversible | sí |  |
| /evaluacion/{} | `app/evaluacion/[token]/page.tsx` | `submitEvaluacion` | `POST /api/assessment/evaluacion/{}/submit` | todos | 🔴 cierra la evaluación del token; el link queda consumido | no | el router no se monta: el módulo está apagado por flag del backend |
| /evaluaciones | `hooks/useHistorialImportaciones.ts` | `deleteLoteEvaluacion` | `DELETE /api/evaluaciones/resultados/lotes/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /evaluaciones | `hooks/useHistorialImportaciones.ts` | `deleteLotesBulk` | `POST /api/evaluaciones/resultados/lotes/eliminar` | admin rrhh | 🔴 baja en LOTE: borra varias filas de una y cada una arrastra sus hijas por CASCADE, así que un clic de más no se deshace fila por fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /evaluaciones | `hooks/useImportarEvaluaciones.ts` | `confirmarImportEvaluaciones` | `POST /api/evaluaciones/importar/confirmar` | admin rrhh | 🔴 persiste el lote entero del import; en evaluaciones BORRA el período anterior por CASCADE antes de escribir el nuevo | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /evaluaciones | `hooks/useImportarEvaluaciones.ts` | `previewImportEvaluaciones` | `POST /api/evaluaciones/importar/preview` | admin rrhh | reversible | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /eventos | `app/(dashboard)/eventos/page.tsx` | `deleteEvento` | `DELETE /api/eventos/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /eventos | `components/features/eventos/guardarEvento.ts` | `createEvento` | `POST /api/eventos` | admin rrhh | reversible | sí |  |
| /eventos | `components/features/eventos/guardarEvento.ts` | `updateEvento` | `PUT /api/eventos/{}` | admin rrhh | reversible | sí |  |
| /eventos | `components/features/eventos/useEventos.ts` | `setEventoResuelta` | `PUT /api/eventos/{}/resuelta` | admin rrhh | reversible | sí |  |
| /horas | `app/horas/page.tsx` | `cargarHoras` | `POST /api/horas-publico/horas` | todos | reversible | no | el router no se monta: el módulo está apagado por flag del backend |
| /horas | `app/horas/page.tsx` | `cargarLicencia` | `POST /api/horas-publico/licencia` | todos | reversible | no | el router no se monta: el módulo está apagado por flag del backend |
| /horas | `app/horas/page.tsx` | `identificar` | `POST /api/horas-publico/identificar` | todos | reversible | no | el router no se monta: el módulo está apagado por flag del backend |
| /horas-por-cliente | `components/features/horasCliente/DetalleEmpleadoModal.tsx` | `deleteCargaHoras` | `DELETE /api/horas-cliente/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /inventario | `components/features/inventario/AsignarModal.tsx` | `asignarItem` | `POST /api/inventario/asignaciones` | admin rrhh | reversible | sí |  |
| /inventario | `components/features/inventario/DevolverModal.tsx` | `devolverItem` | `POST /api/inventario/asignaciones/{}/devolver` | admin rrhh | reversible | sí |  |
| /inventario | `components/features/inventario/ItemModal.tsx` | `createItem` | `POST /api/inventario/items` | admin rrhh | reversible | sí |  |
| /inventario | `components/features/inventario/ItemModal.tsx` | `updateItem` | `PUT /api/inventario/items/{}` | admin rrhh | reversible | sí |  |
| /inventario | `components/features/inventario/ItemsTab.tsx` | `deleteItem` | `DELETE /api/inventario/items/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /login | `components/features/auth/LoginForm.tsx` | `login` | `POST /api/auth/login` | todos | reversible | sí |  |
| /objetivos | `app/(dashboard)/objetivos/page.tsx` | `cambiarEstadoObjetivo` | `PUT /api/objetivos/{}/estado` | admin rrhh | reversible | sí |  |
| /objetivos | `app/(dashboard)/objetivos/page.tsx` | `deleteObjetivo` | `DELETE /api/objetivos/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /objetivos | `components/features/objetivos/ImportarObjetivosModal.tsx` | `confirmarImportObjetivos` | `POST /api/importacion/objetivos/confirmar` | admin rrhh | 🔴 persiste el lote entero del import; en evaluaciones BORRA el período anterior por CASCADE antes de escribir el nuevo | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /objetivos | `components/features/objetivos/ImportarObjetivosModal.tsx` | `previewImportObjetivos` | `POST /api/importacion/objetivos/preview` | admin rrhh | reversible | no | necesita el archivo real de RRHH: el parser depende de los nombres de columna, el encoding y el separador de SU planilla |
| /objetivos | `components/features/objetivos/ObjetivoModal.tsx` | `createObjetivo` | `POST /api/objetivos` | admin rrhh | reversible | sí |  |
| /objetivos | `components/features/objetivos/ObjetivoModal.tsx` | `updateObjetivo` | `PUT /api/objetivos/{}` | admin rrhh | reversible | sí |  |
| /offboarding | `components/features/offboarding/EfectivizarBajaButton.tsx` | `efectivizarBaja` | `POST /api/offboarding/{}/efectivizar` | admin rrhh | 🔴 escribe estado='baja' y fecha_egreso en el legajo | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /offboarding | `components/features/offboarding/EntrevistaSalida.tsx` | `registrarEntrevista` | `PUT /api/offboarding/{}/entrevista` | admin rrhh | reversible | sí |  |
| /offboarding | `components/features/offboarding/useOffboardings.ts` | `marcarActivoDevuelto` | `PUT /api/offboarding/{}/activos/{}` | admin rrhh | reversible | sí |  |
| /onboarding | `components/features/onboarding/IniciarOnboardingModal.tsx` | `iniciarOnboarding` | `POST /api/onboarding/{}/iniciar` | admin rrhh | reversible | sí |  |
| /onboarding | `components/features/onboarding/OnboardingChecklist.tsx` | `completarTarea` | `PUT /api/onboarding/{}/tareas/{}/completar` | admin rrhh | reversible | sí |  |
| /onboarding/templates | `app/(dashboard)/onboarding/templates/page.tsx` | `deleteTemplate` | `DELETE /api/onboarding/templates/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /onboarding/templates | `components/features/onboarding/NuevoTemplateModal.tsx` | `createTemplate` | `POST /api/onboarding/templates` | admin rrhh | reversible | sí |  |
| /onboarding/templates/{} | `components/features/onboarding/AddTareaForm.tsx` | `addTarea` | `POST /api/onboarding/templates/{}/tareas` | admin rrhh | reversible | sí |  |
| /onboarding/templates/{} | `components/features/onboarding/VisibilidadToggle.tsx` | `updateTemplate` | `PUT /api/onboarding/templates/{}` | admin rrhh | reversible | sí |  |
| /onboarding/templates/{} | `components/features/onboarding/useTemplateDetalle.ts` | `deleteTarea` | `DELETE /api/onboarding/templates/{}/tareas/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /onboarding/templates/{} | `components/features/onboarding/useTemplateDetalle.ts` | `updateTarea` | `PUT /api/onboarding/templates/{}/tareas/{}` | admin rrhh | reversible | sí |  |
| /onboarding/templates/{} | `components/features/onboarding/useTemplateDetalle.ts` | `updateTemplate` | `PUT /api/onboarding/templates/{}` | admin rrhh | reversible | sí |  |
| /perfiles-puesto | `components/features/perfilesPuesto/guardarPerfil.ts` | `createPerfil` | `POST /api/perfiles-puesto` | admin rrhh | reversible | sí |  |
| /perfiles-puesto | `components/features/perfilesPuesto/guardarPerfil.ts` | `updatePerfil` | `PUT /api/perfiles-puesto/{}` | admin rrhh | reversible | sí |  |
| /perfiles-puesto | `components/features/perfilesPuesto/useAccionesPerfil.ts` | `deletePerfil` | `DELETE /api/perfiles-puesto/{}` | admin rrhh | reversible | sí |  |
| /perfiles-puesto | `components/features/perfilesPuesto/useAccionesPerfil.ts` | `updatePerfil` | `PUT /api/perfiles-puesto/{}` | admin rrhh | reversible | sí |  |
| /periodos | `app/(dashboard)/periodos/page.tsx` | `reabrirPeriodo` | `POST /api/periodos/{}/reabrir` | admin rrhh | reversible | sí |  |
| /periodos | `components/features/periodos/PeriodoForm.tsx` | `cerrarPeriodo` | `POST /api/periodos` | admin rrhh | reversible | sí |  |
| /proyectos | `app/(dashboard)/proyectos/page.tsx` | `createProyecto` | `POST /api/proyectos` | admin rrhh | reversible | sí |  |
| /proyectos | `app/(dashboard)/proyectos/page.tsx` | `updateProyecto` | `PUT /api/proyectos/{}` | admin rrhh | reversible | sí |  |
| /proyectos/{} | `app/(dashboard)/proyectos/[id]/page.tsx` | `updateProyecto` | `PUT /api/proyectos/{}` | admin rrhh | reversible | sí |  |
| /proyectos/{} | `components/features/proyectos/EquipoTab.tsx` | `deleteAsignacion` | `DELETE /api/proyectos/{}/asignaciones/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /proyectos/{} | `components/features/proyectos/EquipoTab.tsx` | `updateAsignacion` | `PUT /api/proyectos/{}/asignaciones/{}` | admin rrhh | reversible | sí |  |
| /proyectos/{} | `components/features/proyectos/HorasTab.tsx` | `createHora` | `POST /api/proyectos/{}/horas` | admin rrhh | reversible | sí |  |
| /proyectos/{} | `components/features/proyectos/HorasTab.tsx` | `deleteHora` | `DELETE /api/proyectos/{}/horas/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /proyectos/{} | `components/features/proyectos/asignarAcciones.ts` | `asignarArea` | `POST /api/proyectos/{}/asignaciones/area` | admin rrhh | reversible | sí |  |
| /proyectos/{} | `components/features/proyectos/asignarAcciones.ts` | `asignarBulk` | `POST /api/proyectos/{}/asignaciones/bulk` | admin rrhh | reversible | sí |  |
| /recategorizaciones | `components/features/recategorizaciones/guardarRecategorizacion.ts` | `createRecategorizacion` | `POST /api/recategorizaciones` | admin rrhh | reversible | sí |  |
| /recategorizaciones | `components/features/recategorizaciones/guardarRecategorizacion.ts` | `updateRecategorizacion` | `PUT /api/recategorizaciones/{}` | admin rrhh | reversible | sí |  |
| /reportes | `components/features/reportes/ReporteCard.tsx` | `generarReporte` | `POST /api/reportes/generar` | admin rrhh | 🔴 llama a Claude y cuesta plata por request | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| /sucesion | `components/features/sucesion/NuevoHitoForm.tsx` | `createHito` | `POST /api/sucesion/planes/{}/hitos` | admin rrhh | reversible | no | pantalla apagada: flag del front (la página redirige a /dashboard). El backend sí responde: lo que queda sin probar es el recorrido por navegador, no el endpoint |
| /sucesion | `components/features/sucesion/NuevoPlanModal.tsx` | `createPlanCarrera` | `POST /api/sucesion/planes` | admin rrhh | reversible | no | pantalla apagada: flag del front (la página redirige a /dashboard). El backend sí responde: lo que queda sin probar es el recorrido por navegador, no el endpoint |
| /sucesion | `components/features/sucesion/usePlanDetalle.ts` | `completarHito` | `PUT /api/sucesion/hitos/{}/completar` | admin rrhh | reversible | no | pantalla apagada: flag del front (la página redirige a /dashboard). El backend sí responde: lo que queda sin probar es el recorrido por navegador, no el endpoint |
| /sucesion | `components/features/sucesion/usePlanDetalle.ts` | `updateReadiness` | `PUT /api/sucesion/planes/{}/readiness` | admin rrhh | reversible | no | pantalla apagada: flag del front (la página redirige a /dashboard). El backend sí responde: lo que queda sin probar es el recorrido por navegador, no el endpoint |
| /usuarios | `app/(dashboard)/usuarios/page.tsx` | `eliminarUsuario` | `DELETE /api/usuarios/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /usuarios | `components/features/usuarios/CrearUsuarioModal.tsx` | `crearUsuario` | `POST /api/usuarios` | admin rrhh | reversible | sí |  |
| /vacaciones | `components/features/vacaciones/PendientesSection.tsx` | `deleteVacacionPendiente` | `DELETE /api/vacaciones-pendientes/{}` | admin rrhh, mandos medios | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /vacaciones | `components/features/vacaciones/PendientesSection.tsx` | `updateVacacionPendiente` | `PUT /api/vacaciones-pendientes/{}` | admin rrhh, mandos medios | reversible | sí |  |
| /vacaciones | `components/features/vacaciones/VacacionesModal.tsx` | `createVacacion` | `POST /api/vacaciones` | admin rrhh, mandos medios | reversible | sí |  |
| /vacaciones | `components/features/vacaciones/VacacionesModal.tsx` | `createVacacionPendiente` | `POST /api/vacaciones-pendientes` | admin rrhh, mandos medios | reversible | sí |  |
| /vacaciones | `components/features/vacaciones/useVacacionesLista.ts` | `cancelarVacacion` | `PUT /api/vacaciones/{}/cancelar` | admin rrhh, mandos medios | reversible | sí |  |
| /vacantes | `components/features/vacantes/MailsPendientes.tsx` | `asignarMail` | `POST /api/vacantes/casilla/asignar` | admin rrhh | reversible | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| /vacantes | `components/features/vacantes/RevisarCasillaButton.tsx` | `revisarCasilla` | `POST /api/vacantes/casilla/revisar` | admin rrhh | 🔴 lee la casilla de Gmail y crea candidatos a partir de lo que encuentre | no | depende de una casilla de Gmail viva y de un token OAuth vigente |
| /vacantes | `components/features/vacantes/VacanteModal.tsx` | `createVacante` | `POST /api/vacantes` | admin rrhh | reversible | sí |  |
| /vacantes/{} | `components/features/screening/ClasificarCvsButton.tsx` | `clasificarPendientes` | `POST /api/screening/vacantes/{}` | admin rrhh | reversible | no | llama a Claude: cuesta plata por request y la respuesta no es determinista, así que la aserción no puede ser sobre el contenido |
| /vacantes/{} | `components/features/vacantes/CandidatoModal.tsx` | `createCandidato` | `POST /api/vacantes/{}/candidatos` | admin rrhh | reversible | sí |  |
| /vacantes/{} | `components/features/vacantes/EliminarVacanteButton.tsx` | `deleteVacante` | `DELETE /api/vacantes/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /vacantes/{} | `components/features/vacantes/InformacionPuestoSection.tsx` | `updateVacante` | `PUT /api/vacantes/{}` | admin rrhh | reversible | sí |  |
| /vacantes/{} | `components/features/vacantes/LinkedinModal.tsx` | `publicarLinkedin` | `POST /api/vacantes/{}/publicar-linkedin` | admin rrhh | 🔴 publica afuera del sistema | no | depende de un servicio externo (LinkedIn / Zernio) |
| /vacantes/{} | `components/features/vacantes/PipelineSeleccion.tsx` | `moverCandidato` | `PUT /api/candidatos/{}/etapa` | admin rrhh | reversible | sí |  |
| /vacantes/{} | `components/features/vacantes/PublicacionSection.tsx` | `updateVacante` | `PUT /api/vacantes/{}` | admin rrhh | reversible | sí |  |
| /vacantes/{} | `components/features/vacantes/VacanteImagenes.tsx` | `eliminarAdjunto` | `DELETE /api/adjuntos/{}` | admin rrhh | 🔴 borra la fila | sí, sólo sobre datos sembrados | sólo sobre las filas sembradas por docs/SEMILLA-SMOKE.md, nunca sobre datos de RRHH |
| /vacantes/{} | `components/features/vacantes/VacanteImagenes.tsx` | `marcarAdjuntoPrincipal` | `PUT /api/adjuntos/{}/principal` | admin rrhh | reversible | sí |  |
| /vacantes/{} | `components/features/vacantes/VacanteImagenes.tsx` | `subirAdjunto` | `POST /api/adjuntos` | admin rrhh | reversible | sí |  |

## 5 — Los casos que ya sabemos que hay que probar

No salen de recorrer la superficie: son **afirmaciones sobre el comportamiento**, y si no están escritas no están. Los conteos se miden contra el código.

| Familia | Qué probar | Origen | Casos | ¿Automatizable? | Reserva |
|---|---|---|---:|---|---|
| **id INEXISTENTE** | todo endpoint que recibe un id, con un uuid que no existe: 404 con el contrato {error,message,code}, nunca 500 | los 24 `maybe_single()` que devolvían 500 (CLAUDE.md · §.single() vs maybe_single). `tests/test_maybe_single_guarda.py` lo vigila por AST desde adentro; nada lo vigila desde afuera | 115 | sí |  |
| **id de OTRA EMPRESA** | el mismo endpoint con un id real de otra empresa: 404 IDÉNTICO al de 'no existe' — mismo status, mismo code, mismo mensaje. Nunca 403 ni 500 | CLAUDE.md · Patrón de barrera de empresa. Es el contrato que el bug de maybe_single rompía: un recurso ajeno salía 500 | 104 | sí, sólo sobre datos sembrados | necesita dos empresas con datos propios; hoy hay 2 empresas cargadas |
| **editar a alguien dado de baja** | PUT /api/empleados/{id} y POST /api/recategorizaciones sobre alguien con estado='baja'. La guarda del egreso rechaza `fecha_efectiva > fecha_egreso` con 422; verificar que lo RETROACTIVO legítimo siga entrando | docs/SEMILLA-SMOKE.md §7 — se descubrió sembrando, con 201 y el legajo pisado | 2 | sí, sólo sobre datos sembrados | escribe sobre un legajo: sólo sobre los SMK-xx |
| **contraseña provisoria que nunca vence** | entrar por API (POST /api/auth/login + cualquier endpoint) con un usuario que tiene must_change_password=true y ver que el sistema LO DEJA HACER TODO. Hoy pasa: el flag lo aplica solo AuthGuard.tsx:29, en el navegador | medido el 23/8/2026 al sembrar los tres usuarios de prueba del smoke. Anotado en docs/DEUDA-TECNICA.md §1-ter | 1 | sí | los tres usuarios de smk.* ya tienen el flag bajo; para probarlo hay que crear uno nuevo y NO cambiarle la contraseña |
| **los tres roles, uno por uno** | el mismo recorrido con smk.admin, smk.gerencia y smk.mando: que gerencia_lectura reciba 403 en TODA escritura, que mandos_medios reciba 403 fuera de vacaciones/ausencias, y que dentro de las suyas vea SOLO a sus subordinados | docs/SMOKE-TEST.md declaraba como su límite más grande que los 4 usuarios de producción son admin_rrhh. Las credenciales las genera la fase `usuarios` de scripts/semilla_smoke.py | 3 | sí, sólo sobre datos sembrados | el corte de ownership depende de los manager_id sembrados sobre SMK-xx |
| **bugs abiertos del recorrido** | clic en el nombre del usuario · los filtros de objetivos salen desalineados · un 404 de la API se muestra como "Algo salió mal" · SENIOR y senior se cuentan como dos categorías en Distribución de plantilla | recorrido manual con Franco (23/8/2026). Es el único origen de este documento que no se deriva del repo | 4 | parcial | el de Distribución es un test de backend; los otros tres son visuales o de interacción y hoy no hay jsdom en la suite del front |
| **sistema de diseño §2 y §3** | las decisiones punto por punto, incluidas las que el barrido declaró no verificables y las DOS que están sin construir (ver la tabla de abajo) | docs/SISTEMA-DE-DISENO.md §2 y §3 + components/ui/decisionesVisuales.test.ts | 23 | parcial | 15 las verifica el barrido por clase CSS; 6 están declaradas no verificables desde el código; 2 no están construidas |

### Los cuatro bugs abiertos del recorrido

| Bug | Dónde mirar |
|---|---|
| clic en el nombre del usuario | components/layout/UserMenu.tsx — verificar qué pasa al hacer clic en el nombre (¿abre el menú, no hace nada, o navega a una ruta que no existe?) |
| los filtros de objetivos salen desalineados | app/(dashboard)/objetivos/ + components/features/objetivos/ — es la única pantalla que no monta `<Pagination>` y su barra de filtros convive con el selector de vista (`TipoObjetivoTabs`), que se agregó el 23/8/2026 |
| un 404 de la API se muestra como "Algo salió mal" | components/ui/ErrorState.tsx y app/error.tsx usan ese literal genérico. El backend distingue 404 de 500 con un `code` propio y la pantalla lo aplana a un solo mensaje |
| SENIOR y senior se cuentan como dos categorías en Distribución de plantilla | services/reportes/_reporte_distribucion.py:33 — `clave = _SIN if ... else crudo` usa el valor CRUDO. El `.upper()` de la línea de al lado sólo decide si el valor está VACÍO; no normaliza la clave de agrupación. Afecta al reporte R3 y al KPI de distribución |

### Sistema de diseño §2 y §3, punto por punto

**15** decisiones las verifica `decisionesVisuales.test.ts` por clase CSS contra el primitivo donde viven, con su cita del documento. Se listan acá para que el recorrido manual no las repita.

| § | Decisión | La cubre un barrido |
|---|---|---|
| §2 | la tarjeta que ES un control se eleva 3px y se le ilumina el borde al apuntarla | sí |
| §2 | los 160ms de la tarjeta, declarados y no heredados del default de Tailwind (150ms) | sí |
| §2 | la tarjeta es opaca: `bg-card` pleno, sin vidrio y sin fondo traslúcido | sí |
| §2 | la FILA se desplaza y NO se eleva: ni translate-y, ni sombra que no sea la marca interior | sí |
| §2 | la fila de datos mide 46px | sí |
| §3 | el encabezado mide 32px (`h-8`), va sobre `--secondary` y en mayúsculas de 10px | sí |
| §3 | la marca de hover son 3px de `--primary` a la izquierda, en 160ms | sí |
| §3 | el chip de filtro activo: relleno `--accent`, borde `--primary` | sí |
| §3 | el selector de la barra de filtros mide 30px de `md` para arriba (44px táctiles abajo) | sí |
| §3 | el monograma de la barra de identidad mide 46px | sí |
| §3 | la grilla etiqueta-valor: filas de 30px y el valor en cifras tabulares | sí |
| §3 | el modal de formulario: blur de 28px, scrim al 35% y tope de 560px | sí |
| §3 | el campo del modal de formulario mide 34px de `md` para arriba | sí |
| §3 | el campo con foco: borde `--ring` y anillo de 3px, de fábrica en el primitivo | sí |
| §3 | el esqueleto usa un shimmer de 1,2s, no el `animate-pulse` de 2s | sí |
| §3 | las acciones por fila siempre visibles | **no — declarada no verificable desde el código** |
| §3 | el chip es el único relleno azul de la pantalla | **no — declarada no verificable desde el código** |
| §2 | el fondo con manchas de color, azul al 9% y verde al 7% | **no — declarada no verificable desde el código** |
| §6 | el KPI que requiere acción se despega con el fondo, no con un número en color | **no — declarada no verificable desde el código** |
| §3 | el título del modal explica la consecuencia, y el error dice qué corregir | **no — declarada no verificable desde el código** |
| §3 | el vacío explica con los valores reales de los filtros | **no — declarada no verificable desde el código** |

#### 🔴 Las dos que NO están construidas

Medidas contra el código en esta corrida. Las dos son **invisibles para el barrido de decisiones visuales**, y por el mismo motivo estructural: ese barrido verifica que una clase esté donde la decisión dice, y prohíbe el vidrio fuera de donde §2 lo permite. Ninguna de sus dos preguntas puede ver una decisión que **no se construyó en ningún lado**.

| Qué falta | Evidencia | Qué dice §2 |
|---|---|---|
| **las manchas de fondo (azul al 9%, verde al 7%) no están construidas** | app/globals.css pinta `body { @apply bg-background }` — un color plano. Los únicos `radial-gradient` del front están en app/utilidades.css y son las sombras de scroll horizontal (negro 0.16 / blanco 0.14), no manchas de color | «Fondo con color, suave. Manchas muy diluidas: azul al 9%, verde al 7%.» |
| **el vidrio del sidebar no está construido** | components/layout/Sidebar.tsx usa `bg-sidebar` opaco y su scrim mobile es `bg-black/50` sin blur. `VIDRIO_PERMITIDO` del barrido lista 4 archivos y el sidebar no es ninguno: el barrido sólo prohíbe vidrio de más, nunca exige el de menos | «Vidrio SOLO en el sidebar y en los modales.» |

## Endpoints declarados sin caller en el front

Importados de `backend/tests/test_callers_huerfanos.py`, no copiados: ese barrido ya los mantiene vivos en las dos direcciones (una excepción que consigue caller da rojo, una que apunta a una ruta borrada también).

| Endpoint | Razón / disparador de salida |
|---|---|
| `GET /api/ausencias/{id}` | completitud REST: el front nunca pide una ausencia sola. |
| `GET /api/capacitaciones/{id}` | completitud REST: el front nunca pide una sola. |
| `GET /api/clientes/{id}` | completitud REST: el modal de edición recibe el objeto entero del listado, así que pedir la fila de vuelta sería una ida a la red por lo que la pantalla ya tiene. Su wrapper `fetchCliente` se borró el 2026-08-10 tras nacer sin caller; este barrido no lo vio porque `updateCliente`/`deleteCliente` escriben el MISMO literal de path. |
| `GET /api/eventos/{id}` | completitud REST: el modal de edición recibe el objeto entero del listado, así que pedir la fila de vuelta sería una ida a la red por lo que la pantalla ya tiene. Es el MISMO caso que /api/clientes/{id}, y por eso services/eventos.ts nace sin su `fetchEvento` en vez de con un wrapper que nadie llama. |
| `GET /api/integraciones/google/callback` | lo invoca el REDIRECT de Google, no el front. Un wrapper en services/ sería incorrecto. |
| `GET /api/objetivos/areas-conocidas` | el pool de áreas ya usadas, para el desplegable del filtro por área. Sigue sin caller: la tanda del selector de vista (23/8/2026) construyó el filtro por `tipo`, no el de área. SALE DE ESTA LISTA cuando `_camposObjetivos.ts` monte el select de área — hoy ese archivo declara en su encabezado por qué NO lo tiene (los objetivos son del equipo de Capital Humano, y sus operadores no tienen área), así que el disparador real es que esa decisión de producto se revierta. Si eso no pasa, lo que corresponde es BORRAR el endpoint, no dejarlo declarado para siempre. |
| `GET /api/perfiles-puesto/{id}` | completitud REST: el LISTADO devuelve el perfil entero —los 12 campos, no una proyección—, así que el modal de edición recibe el objeto que la pantalla ya tiene y pedir la fila de vuelta sería una ida a la red por nada. Es el MISMO caso que /api/clientes/{id} y /api/eventos/{id}, y por eso services/perfilesPuesto.ts nace SIN su `fetchPerfil` en vez de con un wrapper que nadie llama. 🔴 Esta entrada es la única de las 7 del módulo que sobrevivió al cableado del front (20/8/2026). |
| `GET /api/recategorizaciones/{id}` | completitud REST: el LISTADO devuelve la fila entera —incluidos los seis campos de la cadena de valores anteriores—, así que el modal de edición recibe el objeto que la pantalla ya tiene y pedirlo de vuelta sería una ida a la red por nada. Es el MISMO caso que /api/clientes/{id}, /api/eventos/{id} y /api/perfiles-puesto/{id}, y por eso services/recategorizaciones.ts nace SIN su fetch por id. 🔴 Es la única de las 6 del módulo que sobrevivió al cableado del front (20/8/2026). |
| `GET /api/vacaciones-pendientes/empleado/{empleado_id}` | completitud REST: el listado ya acepta `empleado_id` como Query y es el que usa el front. |
| `GET /health` | infraestructura: lo consulta el chequeo post-deploy, no una pantalla. |

## Lo que la generación encontró

| Chequeo | Resultado |
|---|---|
| acciones cuyo componente no cuelga de ninguna pantalla ni layout | **0** — ninguna |
| declaraciones de baja lógica que ya no se sostienen contra el código | **0** — las 3 siguen sanas |
| verbos de escritura sin clasificar (caen en «reversible» por default) | `activa`, `area`, `asignar`, `bulk`, `cambiar-password`, `cancelar`, `certificado`, `clasificacion`, `completar`, `devolver`, `entrevista`, `escala`, `estado`, `etapa`, `hitos`, `horas`, `identificar`, `iniciar`, `licencia`, `login`, `logo`, `logout`, `nomina-empleados`, `parametros`, `preview`, `principal`, `reabrir`, `readiness`, `remitente`, `resolver`, `restaurar`, `resuelta`, `tareas`, `vacante` |
