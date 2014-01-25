import hashlib
import json
import tempfile
import os

import dataset
import ipythonblocks as ipb
import tornado.options

import mock
import pytest

from .. import dbinterface as dbi


@pytest.fixture
def data_2x2():
    return [[(1, 2, 3, 4), (5, 6, 7, 8)],
            [(9, 10, 11, 12), (13, 14, 15, 16)]]

@pytest.fixture
def basic_grid(data_2x2):
    grid = ipb.BlockGrid(2, 2)
    grid._load_simple_grid(data_2x2)
    return grid


def setup_module(module):
    tornado.options.options.public_salt = 'public'
    tornado.options.options.secret_salt = 'secret'


def setup_function(function):
    _, tornado.options.options.db_file = tempfile.mkstemp()


def teardown_function(function):
    os.remove(tornado.options.options.db_file)


@pytest.mark.parametrize('secret, salt',
    [(False, 'public'), (True, 'secret')])
def test_get_hashids(secret, salt):
    hashids = dbi.get_hashids(secret)
    assert hashids._salt == salt


@pytest.mark.parametrize('secret, hash_id',
    [(False, 'bizkiL'), (True, 'MiXoi4')])
def test_encode_grid_id(secret, hash_id):
    assert dbi.encode_grid_id(1, secret) == hash_id


@pytest.mark.parametrize('secret, hash_id',
    [(False, 'bizkiL'), (True, 'MiXoi4')])
def test_decode_hash_id(secret, hash_id):
    assert dbi.decode_hash_id(hash_id, secret) == 1


def test_sqlize_grid_spec(basic_grid):
    data = basic_grid._construct_post_request(None, False)
    entry = dbi.sqlize_grid_spec(data)

    for k in dbi.JSONIZE_KEYS:
        assert isinstance(entry[k], str)


def test_desqlize_grid_entry(basic_grid):
    data = basic_grid._construct_post_request(None, False)
    entry = dbi.sqlize_grid_spec(data)
    spec = dbi.desqlize_grid_entry(entry)

    for k in dbi.JSONIZE_KEYS:
        assert not isinstance(spec[k], str)


@pytest.mark.parametrize('secret, table_name',
    [(False, dbi.PUBLIC_TABLE),
     (True, dbi.SECRET_TABLE)])
def test_store_grid_entry(secret, table_name, basic_grid):
    data = basic_grid._construct_post_request(None, secret)

    hash_id = dbi.store_grid_entry(data)

    table = dbi.get_table(secret)
    entry = table.find_one(id=1)
    del entry['id']

    assert entry == dbi.sqlize_grid_spec(data)

@pytest.mark.parametrize('secret', [False, True])
def test_get_grid_entry(secret, basic_grid):
    data = basic_grid._construct_post_request(None, secret)
    hash_id = dbi.store_grid_entry(data)

    test_entry = dbi.get_grid_entry(hash_id, secret=secret)
    ref_entry = dbi.get_table(secret).find_one(id=1)
    assert ref_entry

    ref_entry = dbi.desqlize_grid_entry(ref_entry)
    assert test_entry == ref_entry


def test_get_random_grid_entry(basic_grid):
    data = basic_grid._construct_post_request(None, False)
    hash_id = dbi.store_grid_entry(data)

    test_id = dbi.get_random_hash_id()

    assert test_id == hash_id
