import hashlib
import json
import tempfile
import os

import ipythonblocks as ipb
import pytest
import sqlalchemy as sa
import testing.postgresql
from sqlalchemy.orm import sessionmaker

from .. import dbinterface as dbi
from .. import models


@pytest.fixture(scope='module')
def pg_engine():
    with testing.postgresql.Postgresql() as postgresql:
        engine = sa.create_engine(postgresql.url())
        models.Base.metadata.create_all(bind=engine)

        yield engine

        engine.dispose()


@pytest.fixture
def session(pg_engine):
    conn = pg_engine.connect()
    transaction = conn.begin()

    Session = sessionmaker(bind=conn)
    session = Session()

    yield session

    session.rollback()
    session.close()
    Session.close_all()
    transaction.rollback()
    conn.close()


@pytest.fixture
def data_2x2():
    return [[(1, 2, 3, 4), (5, 6, 7, 8)],
            [(9, 10, 11, 12), (13, 14, 15, 16)]]


@pytest.fixture
def basic_grid(data_2x2):
    grid = ipb.BlockGrid(2, 2)
    grid._load_simple_grid(data_2x2)
    return grid


@pytest.fixture(autouse=True)
def set_salts(monkeypatch):
    monkeypatch.setenv('HASHIDS_PUBLIC_SALT', 'public')
    monkeypatch.setenv('HASHIDS_SECRET_SALT', 'secret')


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


@pytest.mark.parametrize('secret', [False, True])
def test_get_store_grid_entry(secret, basic_grid, session):
    data = basic_grid._construct_post_request(None, secret)

    # hack to normalize tuples to lists in the data dict so it matches JSON
    comp_data = json.loads(json.dumps(data))

    hash_id = dbi.store_grid_entry(session, data)

    grid_id = dbi.decode_hash_id(hash_id, secret)
    assert grid_id == 1

    grid_inst = dbi.get_grid_entry(session, hash_id, secret=secret)
    assert grid_inst.id == 1
    for key, value in comp_data.items():
        assert getattr(grid_inst, key) == value


def test_get_random_grid_entry(basic_grid, session):
    data = basic_grid._construct_post_request(None, False)
    hash_id = dbi.store_grid_entry(session, data)
    test_id = dbi.get_random_hash_id(session)

    assert test_id == hash_id
