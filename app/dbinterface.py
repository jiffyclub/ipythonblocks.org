import functools
import os
import random

import sqlalchemy as sa
from hashids import Hashids
from twiggy import log

from . import models

log = log.name(__name__)

HASH_MIN_LENGTH = 6


@functools.lru_cache(maxsize=2)
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
    salt = (
        os.environ['HASHIDS_SECRET_SALT']
        if secret
        else os.environ['HASHIDS_PUBLIC_SALT'])
    return Hashids(salt=salt, min_length=HASH_MIN_LENGTH)


@functools.lru_cache()
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


@functools.lru_cache()
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


def store_grid_entry(session, grid_spec):
    """
    Add a grid spec to the database and return the grid's unique ID.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
    grid_spec : dict

    Returns
    -------
    hash_id : str

    """
    llog = log.fields(secret=grid_spec['secret'])
    llog.debug('storing grid')

    table = models.SecretGrid if grid_spec['secret'] else models.PublicGrid
    new_grid = table(**grid_spec)
    session.add(new_grid)
    session.flush()
    hash_id = encode_grid_id(new_grid.id, grid_spec['secret'])

    llog.fields(grid_id=new_grid.id, hash_id=hash_id).debug('grid stored')

    return hash_id


def get_grid_entry(session, hash_id, secret=False):
    """
    Get a specific grid entry.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session
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

    llog.debug('pulling grid from database')
    table = models.SecretGrid if secret else models.PublicGrid
    grid_spec = session.query(table).filter(table.id == grid_id).one_or_none()

    return grid_spec


def get_random_hash_id(session):
    """
    Get a random, non-secret grid id.

    Parameters
    ----------
    session : sqlalchemy.orm.session.Session

    Returns
    -------
    hash_id : str

    """
    grid = session.query(models.PublicGrid).order_by(sa.func.random()).one()
    return encode_grid_id(grid.id, secret=False)
