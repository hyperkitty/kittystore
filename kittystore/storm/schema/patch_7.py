# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        # No 'ALTER TABLE DROP COLUMN' in SQLite
        'ALTER TABLE "list" ADD COLUMN subject_prefix TEXT;',
        'UPDATE "list" SET subject_prefix = \'[\' || display_name || \']\';'
        ],
    "postgres": [
        'ALTER TABLE "list" DROP COLUMN "description";',
        'ALTER TABLE "list" ADD COLUMN subject_prefix TEXT;',
        'UPDATE "list" SET subject_prefix = \'[\' || display_name || \']\';',
        ],
    "mysql": [
        'ALTER TABLE `list` DROP COLUMN `description`;',
        'ALTER TABLE `list` ADD COLUMN subject_prefix TEXT;',
        'UPDATE `list`" SET subject_prefix = CONCAT(\'[\', display_name, \']\');',
        ],
    }


def apply(store):
    """Add the subject_prefix column and delete the description column"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
