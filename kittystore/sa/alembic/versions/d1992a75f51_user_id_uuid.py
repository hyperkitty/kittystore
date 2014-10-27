"""The User.id field is now a proper UUID

Revision ID: d1992a75f51
Revises: 31959b2e8f44
Create Date: 2014-10-27 19:01:30.222710

"""

# revision identifiers, used by Alembic.
revision = 'd1992a75f51'
down_revision = '31959b2e8f44'

from uuid import UUID
from alembic import op, context
import sqlalchemy as sa
from mailman.database import types
from kittystore.sa.model import Base


def upgrade():
    # Convert existing data into UUID strings
    if not context.is_offline_mode():
        connection = op.get_bind()
        # Create a new MetaData instance here because the data is not proper
        # UUIDs yet so it'll error out.
        metadata = sa.MetaData()
        metadata.bind = connection
        User = Base.metadata.tables["user"].tometadata(metadata)
        Sender = Base.metadata.tables["sender"].tometadata(metadata)
        Vote = Base.metadata.tables["vote"].tometadata(metadata)
        User = sa.Table("user", metadata, sa.Column("id", sa.Unicode(255), primary_key=True), extend_existing=True)
        Sender = sa.Table("sender", metadata, sa.Column("user_id", sa.Unicode(255)), extend_existing=True)
        Vote = sa.Table("vote", metadata, sa.Column("user_id", sa.Unicode(255), primary_key=True), extend_existing=True)
        transaction = connection.begin()
        for user in User.select().execute():
            try:
                new_user_id = str(UUID(int=int(user.id)))
            except ValueError:
                continue # Already converted
            Sender.update().where(
                Sender.c.user_id == user.id
            ).values(user_id=new_user_id).execute()
            Vote.update().where(
                Vote.c.user_id == user.id
            ).values(user_id=new_user_id).execute()
            User.update().where(
                User.c.id == user.id
            ).values(id=new_user_id).execute()
        transaction.commit()
    # Convert to UUID for PostreSQL or to CHAR(32) for others
    if op.get_context().dialect.name == 'sqlite':
        pass # No difference between varchar and char in SQLite
    else:
        # This fails on PostgreSQL because it requires a 'USING' clause, and I
        # can't find a way to generate the correct SQL statement that will not
        # violate the foreign key constraints.
        #for table, col in ( ("user", "id"),
        #                    ("sender", "user_id"),
        #                    ("votes", "user_id") ):
        #    op.alter_column(table, col, type_=types.UUID,
        #                    existing_type=sa.Unicode(255),
        #                    existing_nullable=False)
        pass


def downgrade():
    raise RuntimeError("Downgrades are unsupported")
