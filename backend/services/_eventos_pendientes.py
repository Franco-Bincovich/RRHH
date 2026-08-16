"""
"Qué eventos hay que avisar hoy" — el descarte fino, en Python.

🔴 POR QUÉ ESTO NO ESTÁ EN LA QUERY, que es donde el repo pone todos sus filtros.
La condición es `fecha - dias_aviso <= hoy`, o sea una comparación entre una constante y una
EXPRESIÓN sobre DOS columnas de la misma fila. PostgREST no la puede expresar: sus operadores
comparan una columna contra un valor, no una columna contra otra ni contra una aritmética. Las
alternativas se evaluaron y se descartaron:
  · una columna generada `fecha_aviso` — la agrega una migración, y el lote de migraciones se
    congeló; además duplica un dato derivable de otros dos y hay que mantenerla en sync;
  · una vista o un RPC — mismo costo de migración, y mete lógica de negocio en la base, que es
    justo lo que este repo sacó de ahí cuando dropeó los triggers de auditoría (058);
  · traer todo y filtrar — es esto, pero **acotado**: ver el techo de abajo.

🔑 EL RECORTE DE LA QUERY ES EXACTO, NO UNA HEURÍSTICA. El repo pide
`NOT resuelta AND fecha <= hoy + TECHO_DIAS`, y `TECHO_DIAS` no es un número prudente: es el
MÁXIMO que admite el CHECK `eventos_agenda_dias_aviso_check` (`dias_aviso <= 365`). Un evento
posterior a ese horizonte no puede estar dentro de su ventana de aviso ni con el `dias_aviso` más
grande que la base acepta. O sea: no se descarta ningún candidato posible, y en Python solo se
recorren los que ya son plausibles. Si algún día el CHECK sube, ESTE número tiene que subir con
él — y por eso está escrito acá, con el porqué, y no como un 365 suelto en la query.

⚠️ NO HAY PISO. La lista NO lleva `fecha >= hoy`, y es la otra mitad del diseño: un evento no
desaparece por vencer, desaparece cuando alguien lo marca resuelto. Uno del 1/10 sin resolver
tiene que seguir apareciendo el 15/10 — es el que nadie atendió, o sea el que más importa. Un
aviso que se auto-oculta al vencer es exactamente el que se pierde.
"""
from datetime import date, timedelta
from typing import Iterable, List

from schemas.evento_agenda import EventoResponse

# Espejo de `eventos_agenda_dias_aviso_check`. Ver el encabezado: define el techo EXACTO de la
# query, no un margen elegido a ojo.
TECHO_DIAS = 365


def techo_de_fecha(hoy: date) -> date:
    """La fecha máxima que puede tener un evento y estar todavía dentro de su ventana de aviso."""
    return hoy + timedelta(days=TECHO_DIAS)


def en_ventana(evento: EventoResponse, hoy: date) -> bool:
    """¿Este evento ya entró en su ventana de aviso?

    Args:
        evento: la fila, con su `fecha` y su `dias_aviso` (que puede ser el default de la empresa
            o el override propio — a esta altura ya está resuelto, es una columna).
        hoy: la fecha de referencia. Entra como PARÁMETRO y no se lee de `date.today()` acá
            adentro, que es lo que permite que un test fije el día en vez de depender de cuándo
            corre.

    Returns:
        True si `fecha - dias_aviso <= hoy`. Los vencidos dan True siempre: no hay piso.
    """
    return evento.fecha - timedelta(days=evento.dias_aviso) <= hoy


def filtrar(candidatos: Iterable[EventoResponse], hoy: date) -> List[EventoResponse]:
    """Se queda con los que hay que avisar hoy. Conserva el orden que trajo la query."""
    return [e for e in candidatos if en_ventana(e, hoy)]
