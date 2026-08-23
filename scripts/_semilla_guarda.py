"""
LA RED DE SEGURIDAD de la semilla: nada que MODIFIQUE un legajo puede apuntar a alguien real.

🔴 POR QUÉ ESTO ES UN ARCHIVO Y NO TRES LÍNEAS ADENTRO DE UNA FASE. De las cuatro fases que
tocan personas, DOS modifican el legajo de la persona a la que apuntan: recategorizar pisa
rol/seniority/categoría (`_recategorizaciones_write.aplicar_al_empleado`) y efectivizar una baja
escribe `estado='baja'` con su `fecha_egreso`. Ninguna de las dos se deshace con un DELETE, y
`empleados` no tiene endpoint de borrado. O sea que un error de puntería acá no es un dato de
prueba mal cargado: es un colaborador de Karstec dado de baja en producción.

⚠️ EL CRITERIO ES EL MAIL Y NO EL LEGAJO. `@semilla.hrkarstec.site` es único en TODO el sistema;
el legajo es único **por empresa**, así que dos sociedades podrían tener cada una un `SMK-05`.
"""

from _semilla_padron import DOMINIO


class ColaboradorReal(Exception):
    """Se iba a escribir sobre alguien que NO sembró este script. Corta la corrida."""


def es_sembrado(cli, empleado_id: str, empresa: str) -> bool:
    """🔴 LA RED DE SEGURIDAD. Verifica CONTRA EL SISTEMA que ese id es de la semilla.

    POR QUÉ NO ALCANZA CON "está en mi diccionario de sembrados". El diccionario puede venir del
    MANIFIESTO de otra corrida —o de otra base—, y un uuid que allá era `SMK-05` acá puede ser
    cualquiera. Las dos operaciones que llaman a esto (recategorizar y dar de baja) MODIFICAN el
    legajo: la recategorización pisa rol/seniority/categoría y la baja escribe `estado='baja'`
    con su `fecha_egreso`. Sobre una persona real eso no se deshace con un DELETE.

    Por eso la comprobación es una LECTURA del sistema vivo y el criterio es el mail: el dominio
    `@semilla.hrkarstec.site` no lo puede tener ningún colaborador de Karstec, y a diferencia del
    legajo es único en TODO el sistema y no por empresa.
    """
    ficha = cli.get(f"/api/empleados/{empleado_id}", empresa=empresa)
    return DOMINIO in (ficha.get("email_corporativo") or "")


def exigir_sembrado(cli, persona: dict, operacion: str) -> None:
    """Corta con `ColaboradorReal` si el objetivo no lleva la marca de la semilla."""
    if not es_sembrado(cli, persona["id"], persona["empresa_id"]):
        raise ColaboradorReal(
            f"ABORTADO antes de {operacion}: el id {persona['id']} (esperado {persona['legajo']}) "
            f"NO tiene el dominio @{DOMINIO}, o sea que es un colaborador REAL. "
            "Casi con seguridad el manifiesto viene de otra base. Borralo y volvé a sembrar.")

