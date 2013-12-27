#!/usr/bin/env sh

python -m app.app \
    --tornado_log_file=./tornado.log \
    --app_log_file=./app.log \
    --db_file=./ipborg.db
