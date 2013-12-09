import logging
import os

import tornado.ioloop
import tornado.log
import tornado.web


def configure_tornado_logging():
    fh = logging.handlers.RotatingFileHandler(
        '/var/log/ipborg/tornado.log', maxBytes=2**29, backupCount=10)

    fmt = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    fh.setFormatter(fmt)

    logger = logging.getLogger('tornado')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    tornado.log.enable_pretty_logging(logger=logger)
configure_tornado_logging()


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{}'.format(os.environ.get('MC_PORT')))

application = tornado.web.Application([
    (r"/", MainHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
