import datetime
import json
import os
import random

import dataset
import pylibmc
import tornado.options

from hashids import Hashids
from twiggy import log
log = log.name(__name__)

tornado.options.define('db_file',
                       default='/var/ipborgdb/ipborg.db',
                       type=str)
tornado.options.define('secret_salt', type=str)
tornado.options.define('public_salt', type=str)

JSONIZE_KEYS = {'python_version', 'code_cells', 'grid_data'}
PUBLIC_TABLE = 'public_grids'
SECRET_TABLE = 'secret_grids'
HASH_MIN_LENGTH = 6


def get_memcached():
    host = os.environ['MC_PORT']
    return pylibmc.Client([host], binary=True)


def get_hashids(secret):
    """
    Return the appropriate Hashids instance depending whether it's
    for a secret or public grid.

    Parameters
    ----------
    secret : bool

    Returns
    -------
    hashids : hashids.Hashids instance

    """
    opts = tornado.options.options
    salt = opts.secret_salt if secret else opts.public_salt
    return Hashids(salt=salt, min_length=HASH_MIN_LENGTH)


def encode_grid_id(grid_id, secret):
    """
    Turn an integer grid ID into a hash ID to be used in a URL.

    Parameters
    ----------
    grid_id : int
    secret : bool

    Returns
    -------
    hash_id : str

    """
    hashids = get_hashids(secret)
    return hashids.encrypt(grid_id)


def decode_hash_id(hash_id, secret):
    """
    Turn a hash ID from a URL into an integer grid ID for database lookup.
    Returns None if the decryption was unsuccesful (e.g. not a valid Hashid).

    Parameters
    ----------
    hash_id : str
    secret : bool

    Returns
    -------
    grid_id : int

    """
    hashids = get_hashids(secret)
    dec = hashids.decrypt(hash_id)
    if dec:
        return dec[0]


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
    hash_id : str

    """
    grid_entry = sqlize_grid_spec(grid_spec)

    llog = log.fields(secret=grid_entry['secret'])
    llog.debug('storing grid')
    table = get_table(grid_entry['secret'])
    grid_id = table.insert(grid_entry)
    llog.fields(grid_id=grid_id).debug('grid stored')

    return encode_grid_id(grid_id, grid_entry['secret'])


def get_grid_entry(hash_id, secret=False):
    """
    Get a specific grid entry.

    Parameters
    ----------
    hash_id : str
    secret : bool, optional
        Whether this is a secret grid.

    Returns
    -------
    grid_spec : dict
        Will be None if no matching grid was found.

    """
    grid_id = decode_hash_id(hash_id, secret)
    llog = log.fields(grid_id=grid_id, hash_id=hash_id, secret=secret)
    if not grid_id:
        # couldn't do the conversion from hash to database ID
        llog.debug('cannot decrypt hash')
        return

    llog.debug('looking for grid')

    mc = get_memcached()
    mc_key = str((grid_id, secret))
    if mc_key in mc:
        llog.debug('pulling grid from memcached')
        return mc[mc_key]

    llog.debug('pulling grid from database')
    table = get_table(secret)
    grid_spec = table.find_one(id=grid_id)

    if grid_spec:
        llog.debug('grid found')
        grid_spec = desqlize_grid_entry(grid_spec)
        mc[mc_key] = grid_spec

    else:
        llog.debug('grid not found')
        return

    return grid_spec


def get_random_hash_id():
    """
    Get a random, non-secret grid id.

    Returns
    -------
    hash_id : str

    """
    query = ('SELECT id '
             'FROM {} '
             'ORDER BY RANDOM() '
             'LIMIT 1').format(PUBLIC_TABLE)
    db = get_db()
    cursor = db.query(query)
    return encode_grid_id(tuple(cursor)[0]['id'], secret=False)
