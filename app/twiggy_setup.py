import tornado.options
from twiggy import *


def twiggy_setup():
    fout = outputs.FileOutput(
        tornado.options.options.app_log_file, format=formats.line_format)
    sout = outputs.StreamOutput(format=formats.line_format)

    addEmitters(
        ('ipborg.file', levels.DEBUG, None, fout),
        ('ipborg.std', levels.DEBUG, None, sout))
