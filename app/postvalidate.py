schema = {
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'title': 'Grid Post Schema',
    'description': 'Used to validate incoming posts of new grids.',
    'type': 'object',
    'properties': {
        'python_version': {
            'description': 'Version of Python from which post originated.',
            'type': 'array',
            'minItems': 5,
            'maxItems': 5
        },
        'ipb_version': {
            'description': 'Version of ipythonblocks from which post originated.',
            'type': 'string',
            'pattern': r'\d+\.\d+(?:\.\d+)?.*'
        },
        'ipb_class': {
            'description': 'Grid class from which post originated.',
            'type': 'string',
            'enum': ['BlockGrid', 'ImageGrid']
        },
        'code_cells': {
            'description': 'Any code cells sent from notebook.',
            'type': ['array', 'null'],
            'minItems': 1
        },
        'secret': {
            'description': 'Whether this post should be secret.',
            'type': 'boolean'
        },
        'grid_data': {
            'description': 'Spec of the grid itself.',
            'type': 'object',
            'properties': {
                'lines_on': {
                    'description': 'Are lines on for this grid.',
                    'type': 'boolean'
                },
                'width': {
                    'description': 'Number of columns in grid.',
                    'type': 'integer',
                    'minimum': 1
                },
                'height': {
                    'description': 'Number of rows in grid.',
                    'type': 'integer',
                    'minimum': 1
                },
                'blocks': {
                    'description': 'Block colors and sizes in nested lists.',
                    'type': 'array',
                    'minItems': 1,
                    'items': {
                        'description': 'Grid row.',
                        'type': 'array',
                        'minItems': 1,
                        'items': {
                            'description': 'Individual block.',
                            'type': 'array',
                            'minItems': 4,
                            'maxItems': 4,
                            'items': {
                                'description': 'Block descriptor.',
                                'type': 'integer',
                                'minimum': 0
                            }
                        }
                    }
                }
            },
            'required': ['lines_on', 'width', 'height', 'blocks']
        }
    },
    'required': ['python_version', 'ipb_version', 'ipb_class', 'code_cells',
                 'secret', 'grid_data']
}
