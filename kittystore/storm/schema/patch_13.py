# -*- coding: utf-8 -*-

from __future__ import absolute_import

from . import get_db_type


SQL = {
    "sqlite": [
        'ALTER TABLE "list" ADD COLUMN description TEXT;',
        'ALTER TABLE "list" ADD COLUMN recent_participants_count INTEGER;',
        'ALTER TABLE "list" ADD COLUMN recent_threads_count INTEGER;',
        ],
    "postgres": [
        'ALTER TABLE "list" ADD COLUMN description TEXT;',
        'ALTER TABLE "list" ADD COLUMN recent_participants_count INTEGER;',
        'ALTER TABLE "list" ADD COLUMN recent_threads_count INTEGER;',
        ],
    "mysql": [
        'ALTER TABLE `list` ADD COLUMN description TEXT;',
        'ALTER TABLE `list` ADD COLUMN recent_participants_count INTEGER;',
        'ALTER TABLE `list` ADD COLUMN recent_threads_count INTEGER;',
        ],
    }


def apply(store):
    """
    Add the description, recent_participants_count and recent_threads_count
    columns.
    """
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
