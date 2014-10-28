"""The User.id field is now a proper UUID

Also add ONUPDATE=CASCADE to some foreign keys.

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


FKEYS_CASCADE = ( # Foreign keys to add ONUPDATE=CASCADE to.
    {"from_t": "email", "from_c": ["list_name"],
     "to_t": "list", "to_c": ["name"]},
    {"from_t": "email", "from_c": ["list_name", "thread_id"],
     "to_t": "thread", "to_c": ["list_name", "thread_id"]},
    {"from_t": "email_full", "from_c": ["list_name", "message_id"],
     "to_t": "email", "to_c": ["list_name", "message_id"]},
    {"from_t": "sender", "from_c": ["user_id"],
     "to_t": "user", "to_c": ["id"]},
    {"from_t": "vote", "from_c": ["user_id"],
     "to_t": "user", "to_c": ["id"]},
)


def drop_user_id_fkeys():
    op.drop_constraint("sender_user_id_fkey", "sender")
    op.drop_constraint("vote_user_id_fkey", "vote")

def create_user_id_fkeys(cascade):
    op.create_foreign_key("sender_user_id_fkey",
        "sender", "user", ["user_id"], ["id"],
        onupdate=cascade, ondelete=cascade)
    op.create_foreign_key("vote_user_id_fkey",
        "vote", "user", ["user_id"], ["id"],
        onupdate=cascade, ondelete=cascade)

def rebuild_fkeys(cascade):
    # Add or remove onupdate=CASCADE on some foreign keys.
    # We need to be online or we can't reflect the constraint names.
    if (context.is_offline_mode()
        or op.get_context().dialect.name != 'postgresql'):
        return
    connection = op.get_bind()
    md = sa.MetaData()
    md.reflect(bind=connection)
    for fkey in FKEYS_CASCADE:
        keyname = None
        for existing_fk in md.tables[fkey["from_t"]].foreign_keys:
            if existing_fk.constraint.columns == fkey["from_c"]:
                keyname = existing_fk.name
        assert keyname is not None
        op.drop_constraint(keyname, fkey["from_t"])
        op.create_foreign_key(keyname,
            fkey["from_t"], fkey["to_t"], fkey["from_c"], fkey["to_c"],
            onupdate=cascade, ondelete=cascade)


def upgrade():
    # Convert existing data into UUID strings
    if not context.is_offline_mode():
        connection = op.get_bind()
        # Create a new MetaData instance here because the data is not proper
        # UUIDs yet so it'll error out.
        metadata = sa.MetaData()
        metadata.bind = connection
        User = Base.metadata.tables["user"].tometadata(metadata)
        User = sa.Table("user", metadata,
            sa.Column("id", sa.Unicode(255), primary_key=True),
            extend_existing=True)
        if connection.dialect.name != "sqlite":
            drop_user_id_fkeys()
            create_user_id_fkeys("CASCADE")
        transaction = connection.begin()
        for user in User.select().execute():
            try:
                new_user_id = unicode(UUID(int=int(user.id)))
            except ValueError:
                continue # Already converted
            User.update().where(
                User.c.id == user.id
            ).values(id=new_user_id).execute()
        transaction.commit()
    # Convert to UUID for PostreSQL or to CHAR(32) for others
    if op.get_context().dialect.name == 'sqlite':
        pass # No difference between varchar and char in SQLite
    elif op.get_context().dialect.name == 'postgresql':
        drop_user_id_fkeys()
        for table, col in ( ("user", "id"),
                            ("sender", "user_id"),
                            ("vote", "user_id") ):
            op.execute('''
                ALTER TABLE "{table}"
                    ALTER COLUMN {col} TYPE UUID USING {col}::uuid
                '''.format(table=table, col=col))
        create_user_id_fkeys("CASCADE")
    else:
        # Untested on other engines
        for table, col in ( ("user", "id"),
                            ("sender", "user_id"),
                            ("vote", "user_id") ):
            op.alter_column(table, col, type_=types.UUID,
                            existing_type=sa.Unicode(255),
                            existing_nullable=False)
    # Now add onupdate=CASCADE to some foreign keys.
    rebuild_fkeys("CASCADE")


def downgrade():
    # Convert to UUID for PostreSQL or to CHAR(32) for others
    if op.get_context().dialect.name == 'sqlite':
        pass # No difference between varchar and char in SQLite
    elif op.get_context().dialect.name == 'postgresql':
        drop_user_id_fkeys()
        for table, col in ( ("user", "id"),
                            ("sender", "user_id"),
                            ("vote", "user_id") ):
            op.alter_column(table, col, type_=sa.Unicode(255),
                            existing_type=types.UUID,
                            existing_nullable=False)
        # Need cascade for data conversion below, it will be removed by the
        # last operation (or the loop on FKEYS_CASCADE if offline).
        create_user_id_fkeys("CASCADE")
    else:
        # Untested on other engines
        for table, col in ( ("user", "id"),
                            ("sender", "user_id"),
                            ("vote", "user_id") ):
            op.alter_column(table, col, type_=sa.Unicode(255),
                            existing_type=types.UUID,
                            existing_nullable=False)
    if not context.is_offline_mode():
        connection = op.get_bind()
        # Create a new MetaData instance here because the data is UUIDs and we
        # want to convert to simple strings
        metadata = sa.MetaData()
        metadata.bind = connection
        User = Base.metadata.tables["user"].tometadata(metadata)
        User = sa.Table("user", metadata,
            sa.Column("id", sa.Unicode(255), primary_key=True),
            extend_existing=True)
        transaction = connection.begin()
        for user in User.select().execute():
            try:
                new_user_id = UUID(user.id).int
            except ValueError:
                continue # Already converted
            User.update().where(
                User.c.id == user.id
            ).values(id=new_user_id).execute()
        transaction.commit()
        if connection.dialect.name != "sqlite":
            drop_user_id_fkeys()
            create_user_id_fkeys(None)
    # Now remove onupdate=CASCADE from some foreign keys
    rebuild_fkeys(None)
