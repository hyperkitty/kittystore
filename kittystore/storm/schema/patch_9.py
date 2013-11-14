# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        'CREATE INDEX "ix_sender_email" ON "email" (sender_email);',
        ],
    "postgres": [
        'CREATE INDEX "ix_sender_email" ON "email" (sender_email);',
        ],
    "mysql": [
        'CREATE INDEX `ix_sender_email` ON `email` (sender_email);',
        ],
    }


def apply(store):
    """Add indexes on email.sender_email"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
