from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

CSS_CLASS = 'ipb-code'


def colorize(code):
    """
    Turn a code block into HTML.

    """
    return highlight(code, PythonLexer(), HtmlFormatter(cssclass=CSS_CLASS))
