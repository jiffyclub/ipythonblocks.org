"""Script for migrating ipythonblocks grid data from SQLite to Postgres"""
import contextlib
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


@contextlib.contextmanager
def session_context():
    session = SESSION()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def migrate():
    """
    Trigger the reading from SQLite, transformation of JSON data,
    and writing to Postgres.

    """
    with session_context() as session:
        session.add_all(sqlite_table_to_sa_rows('public_grids', models.PublicGrid))
        session.add_all(sqlite_table_to_sa_rows('secret_grids', models.SecretGrid))

        # Because all the grids added so far already had IDs, the sequences
        # backing the id columns in the grid tables haven't been advanced
        # at all. When trying to add a new table the sequence would provide
        # a key of 1, which would then collide with the existing grids.
        # We need to manually set the sequences behind the table primary keys
        # so that when new grids are added with no IDs the automatically
        # generated IDs are actually available.
        max_public_id = session.query(sa.func.max(models.PublicGrid.id)).scalar()
        max_secret_id = session.query(sa.func.max(models.SecretGrid.id)).scalar()

        session.execute(sa.text(
            f'select setval(\'public_grids_id_seq\', {max_public_id})'))
        session.execute(sa.text(
            f'select setval(\'secret_grids_id_seq\', {max_secret_id})'))


if __name__ == '__main__':
    migrate()
