from twiggy import add_emitters, formats, levels, outputs


def twiggy_setup():
    sout = outputs.StreamOutput(format=formats.line_format)
    add_emitters(('ipborg.std', levels.DEBUG, None, sout))
