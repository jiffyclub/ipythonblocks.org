import contextlib
import json
import logging
import os

import jsonschema
import sqlalchemy as sa
import tornado.ioloop
import tornado.log
import tornado.options
import tornado.web

from ipythonblocks import BlockGrid
from sqlalchemy.orm import sessionmaker
from twiggy import log

# local imports
from . import dbinterface as dbi
from . import postvalidate
from .colorize import colorize
from .twiggy_setup import twiggy_setup

tornado.options.define('port', default=80, type=int)
tornado.options.define('db_url', type=str)
log = log.name(__name__)


def configure_tornado_logging():
    fh = logging.StreamHandler()

    fmt = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    fh.setFormatter(fmt)

    logger = logging.getLogger('tornado')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    tornado.log.enable_pretty_logging(logger=logger)


class MainHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        return 'main.html'


class AboutHandler(tornado.web.StaticFileHandler):
    def parse_url_path(self, url_path):
        return 'about.html'


class DBAccessHandler(tornado.web.RequestHandler):
    @contextlib.contextmanager
    def session_context(self):
        session = self.application.session_factory()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


class PostHandler(DBAccessHandler):
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

        with self.session_context() as session:
            hash_id = dbi.store_grid_entry(session, req_data)

        if req_data['secret']:
            url = 'http://www.ipythonblocks.org/secret/{}'
        else:
            url = 'http://www.ipythonblocks.org/{}'

        url = url.format(hash_id)

        self.write({'url': url})


class GetGridSpecHandler(DBAccessHandler):
    def initialize(self, secret):
        self.secret = secret

    def get(self, hash_id):
        with self.session_context() as session:
            grid_spec = dbi.get_grid_entry(session, hash_id, self.secret)

            if not grid_spec:
                raise tornado.web.HTTPError(404, 'Grid not found.')

            self.write(grid_spec.grid_data)


class RandomHandler(DBAccessHandler):
    def get(self):
        with self.session_context() as session:
            hash_id = dbi.get_random_hash_id(session)
        log.info('redirecting to url /{0}', hash_id)
        self.redirect('/' + hash_id, status=303)


class ErrorHandler(DBAccessHandler):
    def get(self):
        self.send_error(404)

    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.render('404.html')
        else:
            super().send_error(status_code, **kwargs)


class RenderGridHandler(ErrorHandler):
    def initialize(self, secret):
        self.secret = secret

    @tornado.web.removeslash
    def get(self, hash_id):
        with self.session_context() as session:
            grid_spec = dbi.get_grid_entry(session, hash_id, secret=self.secret)

            if not grid_spec:
                self.send_error(404)
                return

            gd = grid_spec.grid_data
            grid = BlockGrid(gd['width'], gd['height'], lines_on=gd['lines_on'])
            grid._load_simple_grid(gd['blocks'])
            grid_html = grid._repr_html_()

            code_cells = grid_spec.code_cells or []
            code_cells = [colorize(c) for c in code_cells]

            self.render('grid.html', grid_html=grid_html, code_cells=code_cells)


class AppWithSession(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = sa.create_engine(tornado.options.options.db_url)
        self.session_factory = sessionmaker(bind=self.engine)


SETTINGS = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'debug': True,
    'gzip': True
}


def make_application():
    return AppWithSession(handlers=[
        (r'/()', MainHandler, {'path': SETTINGS['template_path']}),
        (r'/(about)', AboutHandler, {'path': SETTINGS['template_path']}),
        (r'/random', RandomHandler),
        (r'/post', PostHandler),
        (r'/get/(\w{6}\w*)', GetGridSpecHandler, {'secret': False}),
        (r'/get/secret/(\w{6}\w*)', GetGridSpecHandler, {'secret': True}),
        (r'/(\w{6}\w*)/*', RenderGridHandler, {'secret': False}),
        (r'/secret/(\w{6}\w*)/*', RenderGridHandler, {'secret': True}),
        (r'/.*', ErrorHandler)
    ], **SETTINGS)


if __name__ == '__main__':
    tornado.options.parse_command_line()
    configure_tornado_logging()
    twiggy_setup()

    log.fields(port=tornado.options.options.port).info('starting server')
    application = make_application()
    application.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
