# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        'CREATE INDEX "ix_thread_subject" ON "thread" (subject);',
        ],
    "postgres": [
        'CREATE INDEX "ix_thread_subject" ON "thread" (subject);',
        ],
    "mysql": [
        'CREATE INDEX `ix_thread_subject` ON `thread` (subject);',
        ],
    }


def apply(store):
    """Add indexes on thread.subject"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
