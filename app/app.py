import json
import logging
import os

import jsonschema
import tornado.ioloop
import tornado.log
import tornado.options
import tornado.web

from ipythonblocks import BlockGrid
from twiggy import log

# local imports
from . import dbinterface as dbi
from . import postvalidate
from .colorize import colorize
from .twiggy_setup import twiggy_setup

tornado.options.define('tornado_log_file',
                       default='/var/log/ipborg/tornado.log',
                       type=str)
tornado.options.define('app_log_file',
                       default='/var/log/ipborg/app.log',
                       type=str)
tornado.options.parse_command_line()


def configure_tornado_logging():
    fh = logging.handlers.RotatingFileHandler(
        tornado.options.options.tornado_log_file,
        maxBytes=2**29, backupCount=10)

    fmt = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    fh.setFormatter(fmt)

    logger = logging.getLogger('tornado')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    tornado.log.enable_pretty_logging(logger=logger)


settings = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'debug': True,
    'gzip': True
}


class MainHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        return 'main.html'


class AboutHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        return 'about.html'


class PostHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            req_data = json.loads(self.request.body)
        except ValueError:
            log.debug('Unable to load request JSON.')
            raise tornado.web.HTTPError(400, 'Unable to load request JSON.')

        try:
            jsonschema.validate(req_data, postvalidate.schema)
        except jsonschema.ValidationError:
            log.debug('Post JSON validation failed.')
            raise tornado.web.HTTPError(400, 'Post JSON validation failed.')

        hash_id = dbi.store_grid_entry(req_data)

        if req_data['secret']:
            url = 'http://ipythonblocks.org/secret/{}'
        else:
            url = 'http://ipythonblocks.org/{}'

        url = url.format(hash_id)

        self.write({'url': url})


class GetGridSpecHandler(tornado.web.RequestHandler):
    def initialize(self, secret):
        self.secret = secret

    def get(self, hash_id):
        grid_spec = dbi.get_grid_entry(hash_id, self.secret)
        if not grid_spec:
            raise tornado.web.HTTPError(404, 'Grid not found.')

        self.write(grid_spec['grid_data'])


class RandomHandler(tornado.web.RequestHandler):
    def get(self):
        hash_id = dbi.get_random_hash_id()
        self.redirect('/' + hash_id, status=303)


class RenderGridHandler(tornado.web.RequestHandler):
    def initialize(self, secret):
        self.secret = secret

    @tornado.web.removeslash
    def get(self, hash_id):
        grid_spec = dbi.get_grid_entry(hash_id, secret=self.secret)
        if not grid_spec:
            self.send_error(404)
            return

        gd = grid_spec['grid_data']
        grid = BlockGrid(gd['width'], gd['height'], lines_on=gd['lines_on'])
        grid._load_simple_grid(gd['blocks'])
        grid_html = grid._repr_html_()

        code_cells = grid_spec['code_cells'] or []
        code_cells = [colorize(c) for c in code_cells]

        self.render('grid.html', grid_html=grid_html, code_cells=code_cells)


application = tornado.web.Application([
    (r'/()', MainHandler, {'path': settings['template_path']}),
    (r'/(about)', AboutHandler, {'path': settings['template_path']}),
    (r'/random', RandomHandler),
    (r'/post', PostHandler),
    (r'/get/(\w{6}\w*)', GetGridSpecHandler, {'secret': False}),
    (r'/get/secret/(\w{6}\w*)', GetGridSpecHandler, {'secret': True}),
    (r'/(\w{6}\w*)/*', RenderGridHandler, {'secret': False}),
    (r'/secret/(\w{6}\w*)/*', RenderGridHandler, {'secret': True})
], **settings)


if __name__ == '__main__':
    configure_tornado_logging()
    twiggy_setup()

    application.listen(8877)
    tornado.ioloop.IOLoop.instance().start()
