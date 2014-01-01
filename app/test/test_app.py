import json
import os
import tempfile

import dataset
import tornado.options
import tornado.testing

import mock

from .. import app
from .. import dbinterface as dbi


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
        'code_cells': None,
        'secret': False,
        'grid_data': {
            'lines_on': True,
            'width': 2,
            'height': 2,
            'blocks': data_2x2()
        }
    }


class TestPostGrid(tornado.testing.AsyncHTTPTestCase):
    def setup_method(self, method):
        _, tornado.options.options.db_file = tempfile.mkstemp()

    def teardown_method(self, method):
        os.remove(tornado.options.options.db_file)

    def get_app(self):
        return app.application

    def get_response(self, body):
        self.http_client.fetch(
            self.get_url('/post'), self.stop, method='POST', body=body)
        return self.wait()

    def test_json_failure(self):
        response = self.get_response('{"asdf"}')
        assert response.code == 400

    def test_validation_failure(self):
        response = self.get_response('{"asdf": 5}')
        assert response.code == 400

    @mock.patch.object(dbi, 'make_grid_id', return_value='test_id')
    def test_returns_url(self, id_mock):
        req = request()
        response = self.get_response(json.dumps(req))

        assert response.code == 200
        assert 'application/json' in response.headers['Content-Type']

        body = json.loads(response.body)
        assert body['url'] == 'http://ipythonblocks.org/test_id'

    @mock.patch.object(dbi, 'make_grid_id', return_value='test_id')
    def test_returns_url_secret(self, id_mock):
        req = request()
        req['secret'] = True
        response = self.get_response(json.dumps(req))

        assert response.code == 200
        assert 'application/json' in response.headers['Content-Type']

        body = json.loads(response.body)
        assert body['url'] == 'http://ipythonblocks.org/secret/test_id'

    def test_stores_data(self):
        req = request()
        response = self.get_response(json.dumps(req))

        assert response.code == 200

        body = json.loads(response.body)
        grid_id = body['url'].split('/')[-1]
        grid_spec = dbi.get_grid_entry(grid_id)
        req['grid_id'] = grid_id
        del grid_spec['id']
        assert grid_spec == json.loads(json.dumps(req))
