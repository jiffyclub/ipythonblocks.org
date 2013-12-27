import json
import logging
import os

import jsonschema
import tornado.ioloop
import tornado.log
import tornado.options
import tornado.web

from twiggy import log

# local imports
from . import postvalidate
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


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{}'.format(os.environ.get('MC_PORT')))


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


application = tornado.web.Application([
    (r'/', MainHandler),
    # (r'/about', AboutHandler),
    # (r'/random', RandomHandler),
    (r'/post', PostHandler),
    # (r'/get/([a-zA-Z0-9]+)', GetGridSpecHandler),
    # (r'/([a-zA-Z0-9]+)', RenderGridHandler)
], **settings)


if __name__ == '__main__':
    configure_tornado_logging()
    twiggy_setup()

    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
