# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        # No 'ALTER TABLE DROP COLUMN' in SQLite
        'DROP TABLE list_month_activity;',
        ],
    "postgres": [
        'ALTER TABLE "list" DROP COLUMN recent_participants_count;',
        'ALTER TABLE "list" DROP COLUMN recent_threads_count;',
        'ALTER TABLE "thread" DROP COLUMN emails_count;',
        'ALTER TABLE "thread" DROP COLUMN participants_count;',
        'ALTER TABLE "thread" DROP COLUMN subject;',
        'DROP TABLE list_month_activity;',
        ],
    "mysql": [
        'ALTER TABLE `list` DROP COLUMN recent_participants_count;',
        'ALTER TABLE `list` DROP COLUMN recent_threads_count;',
        'ALTER TABLE `thread` DROP COLUMN emails_count;',
        'ALTER TABLE `thread` DROP COLUMN participants_count;',
        'ALTER TABLE `thread` DROP COLUMN subject;',
        'DROP TABLE list_month_activity;',
        ],
    }


def apply(store):
    """
    Remove the database-based cache.
    """
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()

