import tornado.testing


from .. import app


class TestPostGrid(tornado.testing.AsyncHTTPTestCase):
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
