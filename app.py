import logging
import os

import tornado.ioloop
import tornado.log
import tornado.options
import tornado.web


tornado.options.define('tornado_log_file',
                       default='/var/log/ipborg/torando.log',
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
configure_tornado_logging()


settings = {
    'static_path': os.path.join(os.path.dirname(__file__), 'static'),
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'debug': True,
    'gzip': True
}


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{}'.format(os.environ.get('MC_PORT')))


application = tornado.web.Application([
    (r"/", MainHandler),
], **settings)


if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
