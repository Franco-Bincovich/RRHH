"""
Markdown MÍNIMO a HTML, escapando todo lo demás. Sin dependencias.

🔴 EXISTE PARA QUE NO HAYA HTML EDITABLE POR EL USUARIO. Un mail de RRHH con formato es
esperable, pero si RRHH escribiera HTML, ese HTML llegaría al buzón del destinatario sin que
nadie lo revise — y este repo NO tiene ninguna dependencia de sanitización (verificado: cero
`bleach`, cero `dangerouslySetInnerHTML` en el front). Sumar una y mantenerla al día es un
trabajo permanente; sanitizar HTML bien es notoriamente difícil.

Con Markdown el problema no se acota: DESAPARECE. El conjunto de HTML posible lo genera este
archivo, no el usuario. Lo que RRHH escribe es texto, y todo lo que parezca markup se escapa.

⚠️ EL ORDEN IMPORTA Y NO SE PUEDE INVERTIR: primero se ESCAPA todo el texto, y recién sobre el
texto ya escapado se aplican las marcas. Al revés, un `<b>` escrito por el usuario sobreviviría
al escapado porque ya sería parte del HTML generado.

🔴 Y LAS VARIABLES SE INTERPOLAN ANTES DE PASAR POR ACÁ (ver `_render`), justamente para que sus
valores también se escapen. Ese es el vector real: el texto de la plantilla lo escribe RRHH, pero
el valor de `{{nombre_empleado}}` sale de la base, y un empleado llamado `Ana <script>` no puede
convertirse en markup.

Lo que se soporta, y nada más: **negrita**, *itálica*, `[texto](url)`, listas con `- `, y saltos
de párrafo. Alcanza para lo que un mail de RRHH necesita.
"""
import html
import re

_NEGRITA = re.compile(r"\*\*(.+?)\*\*")
_ITALICA = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
# Solo http/https en el destino: un `[click](javascript:...)` es un link ejecutable, y el escapado
# no lo frena porque el esquema viaja en un atributo, no en el texto.
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def a_html(texto: str) -> str:
    """Convierte el Markdown mínimo de una plantilla a HTML seguro.

    Args:
        texto: el cuerpo de la plantilla, con las variables YA sustituidas.

    Returns:
        HTML listo para el cuerpo del mail.
    """
    partes = []
    for bloque in re.split(r"\n\s*\n", texto.strip()):
        lineas = [ln.strip() for ln in bloque.splitlines() if ln.strip()]
        if lineas and all(ln.startswith("- ") for ln in lineas):
            items = "".join(f"<li>{_marcas(ln[2:])}</li>" for ln in lineas)
            partes.append(f"<ul>{items}</ul>")
        elif lineas:
            partes.append("<p>" + "<br>".join(_marcas(ln) for ln in lineas) + "</p>")
    return "".join(partes)


def _marcas(linea: str) -> str:
    """Escapa la línea ENTERA y recién después aplica las marcas. El orden es la seguridad."""
    seguro = html.escape(linea, quote=True)
    seguro = _LINK.sub(r'<a href="\2">\1</a>', seguro)
    seguro = _NEGRITA.sub(r"<strong>\1</strong>", seguro)
    return _ITALICA.sub(r"<em>\1</em>", seguro)
