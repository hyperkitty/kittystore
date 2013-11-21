# -*- coding: utf-8 -*-

from storm.locals import StormError
from storm.schema.schema import Schema as StormSchema
from storm.schema.patch import PatchApplier


def get_db_type(store):
    database = store.get_database()
    return database.__class__.__module__.split(".")[-1]


class CheckingSchema(StormSchema):

    def has_pending_patches(self, store):
        """Check if the C{store} needs a schema upgrade.

        Nothing will be committed to the database. Run C{upgrade()} to apply
        the unapplied schema patches.

        Returns True if the schema needs an upgrade, False otherwise.
        """
        try:
            store.execute("SELECT * FROM patch WHERE version=0")
        except StormError:
            return True
        else:
            patch_applier = PatchApplier(store, self._patch_package)
            return patch_applier.has_pending_patches()
