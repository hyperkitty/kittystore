# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        'CREATE INDEX "ix_thread_list_name" ON "thread" (list_name);',
        ],
    "postgres": [
        'CREATE INDEX "ix_thread_list_name" ON "thread" (list_name);',
        ],
    "mysql": [
        'CREATE INDEX `ix_thread_list_name` ON `thread` (list_name);',
        ],
    }


def apply(store):
    """Add indexes on thread.list_name"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()

