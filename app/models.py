"""Definition of SQL tables used to store ipythonblocks grid data"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CommonColumnsMixin:
    """Columns common to both public and secret grids"""
    __table_args__ = {'schema': 'public'}  # "public" is postgres' default schema

    id = sa.Column(sa.Integer, primary_key=True)
    ipb_version = sa.Column(sa.Text, nullable=False)
    python_version = sa.Column(pg.JSONB, nullable=False)
    grid_data = sa.Column(pg.JSONB, nullable=False)
    code_cells = sa.Column(pg.JSONB)
    ipb_class = sa.Column(sa.Text, nullable=False)
    created_at = sa.Column(
        sa.DateTime(timezone=True), nullable=False,
        server_default=sa.text('NOW()'))


class PublicGrid(CommonColumnsMixin, Base):
    """Table to hold public grids (discoverable via "random")"""
    __tablename__ = 'public_grids'

    # no-op column, but put it here anyway
    secret = sa.Column(sa.Boolean, nullable=False, default=False)


class SecretGrid(CommonColumnsMixin, Base):
    """Table to hold secret grids"""
    __tablename__ = 'secret_grids'

    # no-op column, but put it here anyway
    secret = sa.Column(sa.Boolean, nullable=False, default=True)
