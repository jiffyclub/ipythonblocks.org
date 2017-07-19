"""Script for migrating ipythonblocks grid data from SQLite to Postgres"""
import json
import os
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

# The module in the ipythonblocks.org application code that contains
# table definitions
from app import models

# SQLite DB related variables
SQLITEDB = 'sqlite:///' + str(Path.home() / 'ipborg.db')
SQLITE_ENGINE = sa.create_engine(str(SQLITEDB))
SQLITE_META = sa.MetaData(bind=SQLITE_ENGINE)

# Postgres DB related variables
DBURL = os.environ['DATABASE_URL']  # could be local or remote server
PSQL_ENGINE = sa.create_engine(DBURL)
SESSION = sessionmaker(bind=PSQL_ENGINE)

# columns that are serialized JSON in the SQLite DB
JSONIZE_KEYS = {'python_version', 'code_cells', 'grid_data'}

# drop and recreate tables in the destination DB so we're always
# starting fresh
models.Base.metadata.drop_all(bind=PSQL_ENGINE)
models.Base.metadata.create_all(bind=PSQL_ENGINE)


def sqlite_row_to_sa_row(row, sa_cls):
    """
    Convert a row from the SQLite DB (a SQLAlchemy RowProxy instance)
    into an ORM instance such as PublicGrid or SecretGrid
    (exact class provided by the sa_cls argument). This takes care of
    de-serializing the JSON data stored in the SQLite DB.

    """
    d = dict(row)
    for key in JSONIZE_KEYS:
        d[key] = json.loads(d[key]) if d[key] else None

    return sa_cls(**d)


def sqlite_table_to_sa_rows(table_name, sa_cls):
    """
    Yields SQLAlchemy ORM instances of sa_cls from a SQLite table
    specified by table_name.

    """
    table = sa.Table(table_name, SQLITE_META, autoload=True)
    results = SQLITE_ENGINE.execute(table.select())
    for row in results:
        yield sqlite_row_to_sa_row(row, sa_cls)


def migrate():
    """
    Trigger the reading from SQLite, transformation of JSON data,
    and writing to Postgres.

    """
    session = SESSION()
    session.add_all(sqlite_table_to_sa_rows('public_grids', models.PublicGrid))
    session.add_all(sqlite_table_to_sa_rows('secret_grids', models.SecretGrid))
    session.commit()


if __name__ == '__main__':
    migrate()
