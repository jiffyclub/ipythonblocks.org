import datetime
import hashlib
import json
import random

import dataset
import tornado.options

from twiggy import log
log = log.name(__name__)

tornado.options.define('db_file',
                       default='/var/ipborgdb/ipborg.db',
                       type=str)

JSONIZE_KEYS = {'python_version', 'code_cells', 'grid_data'}
PUBLIC_TABLE = 'public_grids'
SECRET_TABLE = 'secret_grids'


def make_grid_id(grid_spec):
    """
    Generate a unique ID for a grid.

    Unique ID is generated by hashing the grid spec, the current date,
    and a random number with sha1 and returning the first ten
    characters of the hex digest.

    Parameters
    ----------
    grid_spec : dict

    Returns
    -------
    grid_id : str

    """
    hash_str = (str(grid_spec) +
                str(datetime.datetime.now()) +
                str(random.random()))
    grid_id = hashlib.sha1(hash_str).hexdigest()[:10]

    if get_grid_entry(grid_id, False) or get_grid_entry(grid_id, True):
        # this ID isn't unique, try again.
        return make_grid_id(grid_spec)
    else:
        return grid_id


def get_db():
    """
    Get a pointer to the databse.

    Returns
    -------
    db : dataset.Database

    """
    return dataset.connect('sqlite:///' + tornado.options.options.db_file)


def get_table(secret):
    """
    Return the appropriate dataset.Table instance.

    Parameters
    ----------
    secret : bool
        Whether it's a secret grid.

    Returns
    -------
    table : dataset.Table

    """
    db = get_db()
    return db[PUBLIC_TABLE] if not secret else db[SECRET_TABLE]


def sqlize_grid_spec(grid_spec):
    """
    Not all of grid_spec's fields match sqlite types,
    this will convert them to JSON strings.

    Parameters
    ----------
    grid_spec : dict

    Returns
    -------
    grid_entry : dict

    """
    grid_entry = grid_spec.copy()

    for k in JSONIZE_KEYS:
        grid_entry[k] = json.dumps(grid_entry[k])

    return grid_entry


def desqlize_grid_entry(grid_entry):
    """
    Not all of grid_spec's fields match sqlite types,
    so some of them are stored as JSON strings.
    This will convert them from the strings back to the useful types.

    Parameters
    ----------
    grid_entry : dict

    Returns
    -------
    grid_spec : dict

    """
    grid_spec = grid_entry.copy()

    for k in JSONIZE_KEYS:
        grid_spec[k] = json.loads(grid_spec[k])

    return grid_spec


def store_grid_entry(grid_spec):
    """
    Add a grid spec to the database and return the grid's unique ID.

    Parameters
    ----------
    grid_spec : dict

    Returns
    -------
    grid_id : str

    """
    grid_id = make_grid_id(grid_spec)

    grid_entry = sqlize_grid_spec(grid_spec)
    grid_entry['grid_id'] = grid_id

    llog = log.fields(grid_id=grid_id, secret=grid_entry['secret'])
    llog.debug('storing grid')
    table = get_table(grid_entry['secret'])
    table.insert(grid_entry)
    llog.debug('grid stored')

    return grid_id


def get_grid_entry(grid_id, secret=False):
    """
    Get a specific grid entry.

    Parameters
    ----------
    grid_id : str
    secret : bool, optional
        Whether this is a secret grid.

    Returns
    -------
    grid_spec : dict
        Will be None if no matching grid was found.

    """
    llog = log.fields(grid_id=grid_id, secret=secret)
    llog.debug('looking for grid')

    table = get_table(secret)
    grid_spec = table.find_one(grid_id=grid_id)

    if grid_spec:
        llog.debug('grid found')
        grid_spec = desqlize_grid_entry(grid_spec)

    else:
        llog.debug('grid not found')

    return grid_spec


def get_random_grid_id():
    """
    Get a random, non-secret grid id.

    Returns
    -------
    grid_id : str

    """
    query = ('SELECT grid_id '
             'FROM {} '
             'ORDER BY RANDOM() '
             'LIMIT 1').format(PUBLIC_TABLE)
    db = get_db()
    cursor = db.query(query)
    return tuple(cursor)[0]['grid_id']
