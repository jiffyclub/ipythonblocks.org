import json
import os
import tempfile

import dataset
import tornado.options
import tornado.testing

import mock

from .. import app
from .. import dbinterface as dbi


def setup_module(module):
    tornado.options.options.public_salt = 'public'
    tornado.options.options.secret_salt = 'secret'
    dbi.get_memcached().flush_all()


def teardown_module(module):
    dbi.get_memcached().flush_all()


def setup_function(function):
    _, tornado.options.options.db_file = tempfile.mkstemp()


def teardown_function(function):
    os.remove(tornado.options.options.db_file)


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
        _, tornado.options.options.db_file = tempfile.mkstemp()

    def teardown_method(self, method):
        os.remove(tornado.options.options.db_file)

    def get_app(self):
        return app.application

    def get_response(self, body=None):
        self.http_client.fetch(
            self.get_url(self.app_url), self.stop,
            method=self.method, body=body)
        return self.wait()

    def save_grid(self, secret):
        req = request()
        req['secret'] = secret
        hash_id = dbi.store_grid_entry(req)
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
        assert body['url'] == 'http://ipythonblocks.org/bizkiL'

    def test_returns_url_secret(self):
        req = request()
        req['secret'] = True
        response = self.get_response(json.dumps(req))

        assert response.code == 200
        assert 'application/json' in response.headers['Content-Type']

        body = json.loads(response.body)
        assert body['url'] == 'http://ipythonblocks.org/secret/MiXoi4'

    def test_stores_data(self):
        req = request()
        response = self.get_response(json.dumps(req))

        assert response.code == 200

        body = json.loads(response.body)
        hash_id = body['url'].split('/')[-1]
        grid_spec = dbi.get_grid_entry(hash_id)
        del grid_spec['id']
        assert grid_spec == json.loads(json.dumps(req))


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
        assert '<table' in response.body
        assert 'asdf' in response.body

    def test_render_secret(self):
        hash_id = self.save_grid(True)
        self.app_url = '/secret/{}'.format(hash_id)

        response = self.get_response()
        assert response.code == 200
        assert '<table' in response.body
        assert 'asdf' in response.body
