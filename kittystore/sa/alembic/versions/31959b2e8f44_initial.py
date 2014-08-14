"""Initial migration (empty)

This empty migration file makes sure there is always an alembic_version in the
database. As a consequence, if the DB version is reported as None, it means the
database needs to be created from scratch with SQLAlchemy itself.

It also removes the "patch" table left over from Storm (if it exists).

Revision ID: 31959b2e8f44
Revises: None
Create Date: 2014-08-13 15:07:09.282855

"""

# revision identifiers, used by Alembic.
revision = '31959b2e8f44'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_table('patch') # Storm migration versionning table

def downgrade():
    pass
