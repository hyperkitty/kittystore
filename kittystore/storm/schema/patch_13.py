# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        'ALTER TABLE "list" ADD COLUMN description TEXT;',
        'ALTER TABLE "list" ADD COLUMN recent_participants_count INTEGER;',
        'ALTER TABLE "list" ADD COLUMN recent_threads_count INTEGER;',
        'ALTER TABLE "thread" ADD COLUMN emails_count INTEGER;',
        'ALTER TABLE "thread" ADD COLUMN participants_count INTEGER;',
        'ALTER TABLE "thread" ADD COLUMN subject TEXT;',
        ],
    "postgres": [
        'ALTER TABLE "list" ADD COLUMN description TEXT;',
        'ALTER TABLE "list" ADD COLUMN recent_participants_count INTEGER;',
        'ALTER TABLE "list" ADD COLUMN recent_threads_count INTEGER;',
        'ALTER TABLE "thread" ADD COLUMN emails_count INTEGER;',
        'ALTER TABLE "thread" ADD COLUMN participants_count INTEGER;',
        'ALTER TABLE "thread" ADD COLUMN subject TEXT;',
        ],
    "mysql": [
        'ALTER TABLE `list` ADD COLUMN description TEXT;',
        'ALTER TABLE `list` ADD COLUMN recent_participants_count INTEGER;',
        'ALTER TABLE `list` ADD COLUMN recent_threads_count INTEGER;',
        'ALTER TABLE `thread` ADD COLUMN emails_count INTEGER;',
        'ALTER TABLE `thread` ADD COLUMN participants_count INTEGER;',
        'ALTER TABLE `thread` ADD COLUMN subject TEXT COLLATE utf8_general_ci;',
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
