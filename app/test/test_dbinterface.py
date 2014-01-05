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


def setup_function(function):
    _, tornado.options.options.db_file = tempfile.mkstemp()


def teardown_function(function):
    os.remove(tornado.options.options.db_file)


@mock.patch('datetime.datetime', autospec=True)
@mock.patch('random.random', return_value='random')
def test_make_grid_id(rand_mock, dt_mock):
    dt_mock.now.return_value = 'now'

    data = basic_grid(data_2x2())._construct_post_request(None, False)
    test_id = dbi.make_grid_id(data)
    ref_id = hashlib.sha1(str(data) + 'now' + 'random').hexdigest()[:10]

    assert test_id == ref_id
    dt_mock.now.assert_called_once_with()
    rand_mock.assert_called_once_with()


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

    grid_id = dbi.store_grid_entry(data)

    table = dbi.get_table(secret)
    entry = table.find_one(grid_id=grid_id)
    del entry['id']

    data['grid_id'] = grid_id

    assert entry == dbi.sqlize_grid_spec(data)

@pytest.mark.parametrize('secret', [False, True])
def test_get_grid_entry(secret, basic_grid):
    data = basic_grid._construct_post_request(None, secret)
    grid_id = dbi.store_grid_entry(data)

    test_entry = dbi.get_grid_entry(grid_id, secret=secret)
    ref_entry = dbi.get_table(secret).find_one(grid_id=grid_id)
    assert ref_entry

    ref_entry = dbi.desqlize_grid_entry(ref_entry)
    assert test_entry == ref_entry


def test_get_random_grid_entry(basic_grid):
    data = basic_grid._construct_post_request(None, False)
    grid_id = dbi.store_grid_entry(data)
    data['grid_id'] = grid_id

    test_id = dbi.get_random_grid_id()

    assert test_id == grid_id
