import json
import os
import tempfile

import pytest
import sqlalchemy as sa
import testing.postgresql
import tornado.options
import tornado.testing
from sqlalchemy.orm import sessionmaker

from .. import app
from .. import dbinterface as dbi
from .. import models


def setup_module(module):
    module.PG_FACTORY = testing.postgresql.PostgresqlFactory(
        cache_initialized_db=True)

def teardown_module(module):
    module.PG_FACTORY.clear_cache()


@pytest.fixture(autouse=True)
def set_salts(monkeypatch):
    monkeypatch.setenv('HASHIDS_PUBLIC_SALT', 'public')
    monkeypatch.setenv('HASHIDS_SECRET_SALT', 'secret')


def data_2x2():
    return [[(1, 2, 3, 4), (5, 6, 7, 8)],
            [(9, 10, 11, 12), (13, 14, 15, 16)]]


def request():
    return {
        'python_version': (2, 7, 6, 'final', 0),
        'ipb_version': '1.6',
        'ipb_class': 'BlockGrid',
        'code_cells': ['asdf', 'jkl;'],
        'secret': False,
        'grid_data': {
            'lines_on': True,
            'width': 2,
            'height': 2,
            'blocks': data_2x2()
        }
    }


class UtilBase(tornado.testing.AsyncHTTPTestCase):
    def setup_method(self, method):
        self.postgresql = PG_FACTORY()
        self.engine = sa.create_engine(self.postgresql.url())
        models.Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        tornado.options.options.db_url = self.postgresql.url()

    def teardown_method(self, method):
        self.session.close()
        self.Session.close_all()
        self.engine.dispose()
        self.postgresql.stop()

    def get_app(self):
        return app.make_application()

    def get_response(self, body=None):
        return self.fetch(self.app_url, method=self.method, body=body)

    def save_grid(self, secret):
        req = request()
        req['secret'] = secret
        hash_id = dbi.store_grid_entry(self.session, req)
        self.session.commit()
        return hash_id


class TestPostGrid(UtilBase):
    app_url = '/post'
    method = 'POST'

    def test_json_failure(self):
        response = self.get_response('{"asdf"}')
        assert response.code == 400

    def test_validation_failure(self):
        response = self.get_response('{"asdf": 5}')
        assert response.code == 400

    def test_returns_url(self):
        req = request()
        response = self.get_response(json.dumps(req))

        assert response.code == 200
        assert 'application/json' in response.headers['Content-Type']

        body = json.loads(response.body)
        assert body['url'] == 'http://www.ipythonblocks.org/bizkiL'

    def test_returns_url_secret(self):
        req = request()
        req['secret'] = True
        response = self.get_response(json.dumps(req))

        assert response.code == 200
        assert 'application/json' in response.headers['Content-Type']

        body = json.loads(response.body)
        assert body['url'] == 'http://www.ipythonblocks.org/secret/MiXoi4'

    def test_stores_data(self):
        req = request()
        response = self.get_response(json.dumps(req))

        assert response.code == 200

        body = json.loads(response.body)
        hash_id = body['url'].split('/')[-1]
        grid_spec = dbi.get_grid_entry(self.session, hash_id)
        assert grid_spec.id == 1

        comp_data= json.loads(json.dumps(req))

        for key, value in comp_data.items():
            assert getattr(grid_spec, key) == value


class TestGetGrid(UtilBase):
    method = 'GET'

    def test_returns_404(self):
        self.app_url = '/get/asdf'
        response = self.get_response()
        assert response.code == 404

    def test_get_grid(self):
        grid_id = self.save_grid(False)
        self.app_url = '/get/{}'.format(grid_id)

        response = self.get_response()
        assert response.code == 200

        body = json.loads(response.body)
        req = request()

        assert body == json.loads(json.dumps(req['grid_data']))

    def test_get_grid_secret(self):
        grid_id = self.save_grid(True)
        self.app_url = '/get/secret/{}'.format(grid_id)

        response = self.get_response()
        assert response.code == 200

        body = json.loads(response.body)
        req = request()

        assert body == json.loads(json.dumps(req['grid_data']))


class TestRandomHandler(UtilBase):
    def test_random(self):
        grid_id = self.save_grid(False)

        self.http_client.fetch(
            self.get_url('/random'), self.stop,
            method='GET', follow_redirects=False)
        response = self.wait()

        assert response.code == 303
        assert response.headers['Location'] == '/{}'.format(grid_id)


class TestRenderGrid(UtilBase):
    method = 'GET'

    def test_render(self):
        hash_id = self.save_grid(False)
        self.app_url = '/{}'.format(hash_id)

        response = self.get_response()
        assert response.code == 200
        assert b'<table' in response.body
        assert b'asdf' in response.body

    def test_render_secret(self):
        hash_id = self.save_grid(True)
        self.app_url = '/secret/{}'.format(hash_id)

        response = self.get_response()
        assert response.code == 200
        assert b'<table' in response.body
        assert b'asdf' in response.body
