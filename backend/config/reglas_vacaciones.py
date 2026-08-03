"""
Parámetros de la política de vacaciones de RRHH. SOLO DATOS — ni una línea de cálculo.

🔴 POR QUÉ ACÁ Y NO EN `settings.py`
`settings` es CONFIGURACIÓN DE ENTORNO: cosas que cambian entre local, Vercel y AWS sin que
cambie el producto (URLs, claves, cuántos proxies hay adelante). Esto es lo contrario: es una
DECISIÓN DE NEGOCIO que vale igual en los tres entornos y que tiene que quedar versionada en
git, revisable en un diff, y con el porqué escrito al lado. Meterla en el entorno significaría
que dos deploys de la misma versión del código pueden calcular saldos distintos, y que nadie
puede reconstruir por qué un empleado tuvo 21 días en marzo. Mismo criterio que
`LIMITE_FILAS_EXPORT` en `services/_limite_export.py`, que también es constante de módulo y no
variable de entorno.

🔴 POR QUÉ ES UN DATACLASS Y NO UN PUÑADO DE CONSTANTES SUELTAS
El panel de configuración está en el plan de trabajo y no existe todavía. El día que exista,
las reglas van a salir de la base y a ser POR EMPRESA. Que ya hoy sean un objeto que se pasa
como parámetro es lo que hace que ese día no haya que tocar el cálculo: cambia de dónde sale
la instancia, no quién la usa. Con constantes de módulo leídas directamente desde las
funciones, en cambio, habría que reescribir cada función y cada test.
Efecto secundario que se cobra desde el primer día: los tests pasan reglas distintas sin
monkeypatchear nada.

⚠️ NINGÚN VALOR DE ACÁ ES UNA SUPOSICIÓN NUESTRA: los cuatro salen de lo que RRHH confirmó.
Los dos puntos que RRHH TODAVÍA NO CERRÓ están marcados abajo con 🚩 y tienen su propio
comentario explicando qué cambia según la respuesta.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ReglasVacaciones:
    """Política de vacaciones. Inmutable: una regla que se puede mutar en runtime es una regla
    que puede cambiar entre dos llamadas del mismo request y dar dos saldos distintos."""

    #: Días por año según antigüedad, como tramos (años_cumplidos_minimos, dias).
    #: ORDENADO DE MAYOR A MENOR y recorrido con el primer match: agregar un tramo nuevo es
    #: UN RENGLÓN, no una cadena de `if` que hay que releer entera para saber qué gana.
    escala_antiguedad: tuple[tuple[int, int], ...] = ((15, 28), (5, 21), (0, 14))

    #: Cuántos años se pueden acumular. Un período P se puede gozar hasta el 31/12 de
    #: P + anios_acumulacion; pasado eso vence. Confirmado con RRHH: "acumulables 4 años,
    #: después vencen de atrás para adelante".
    anios_acumulacion: int = 4

    #: 🚩 ABIERTO CON RRHH — el borde exacto del año de ingreso.
    #: Corte (mes, día) del año de ingreso: quien ingresa ANTES de esta fecha se lleva el cupo
    #: completo del tramo que le toque; quien ingresa en esa fecha o después se lleva
    #: `dias_ingreso_tardio`. No es proporcional día por día: es un corte.
    #: La pregunta abierta es dónde cae exactamente "julio" — (7, 1) trata a todo julio como
    #: tardío, (8, 1) lo trata como completo, (7, 15) parte el mes al medio. Está como par
    #: (mes, día) y NO como `if fecha.month <= 7` justamente para que las tres respuestas sean
    #: un cambio de constante y no un cambio de código.
    corte_ingreso: tuple[int, int] = (7, 1)

    #: Días que corresponden por el período del año de ingreso cuando se ingresa a partir del
    #: corte de arriba.
    dias_ingreso_tardio: int = 5

    #: 🚩 ABIERTO CON RRHH — "la antigüedad se mide de octubre a octubre".
    #: Mes en el que se cumple la antigüedad a efectos del cupo: para el período P, los años
    #: cumplidos se miden al día 1 de este mes del año P. O sea que alguien que cumple 5 años
    #: en noviembre de 2026 recién cobra 21 días en el período 2027.
    #: ⚠️ ESTO INTERPRETA "octubre a octubre" COMO *CUÁNDO SE MIDE LA ANTIGÜEDAD*, dejando el
    #: PERÍODO como año calendario. Si RRHH aclara que lo que va de octubre a septiembre es el
    #: período en sí, lo único que cambia es `periodo_de(fecha)` en `_vacaciones_cupos.py` —
    #: está aislada ahí por eso. El modelo apoya esta lectura: `solicitudes_vacaciones.periodo`
    #: es un SMALLINT con CHECK 2000–2100, o sea un AÑO; cuando en este repo hizo falta
    #: representar un rango (`evaluacion_lotes.periodo`) se usó TEXT.
    mes_cierre_antiguedad: int = 10


#: Instancia única que usa la aplicación. Las funciones de cálculo la reciben como parámetro
#: con este valor por default, así que el día que las reglas vengan de la base (por empresa)
#: no hay que tocar ninguna de ellas: se les pasa otra instancia.
REGLAS = ReglasVacaciones()
