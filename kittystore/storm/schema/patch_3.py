# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        'ALTER TABLE "email" ADD COLUMN "timezone" INTEGER NOT NULL DEFAULT 0;',
        ],
    "postgres": [
        'ALTER TABLE "email" ADD COLUMN "timezone" INTEGER;',
        'UPDATE "email" SET "timezone" = EXTRACT(TIMEZONE_MINUTE FROM date)',
        'UPDATE "email" SET date = date AT TIME ZONE \'UTC\';',
        'ALTER TABLE "email" ALTER COLUMN "date" TYPE TIMESTAMP WITHOUT TIME ZONE;',
        'ALTER TABLE "email" ALTER COLUMN "timezone" SET NOT NULL;',
        'ALTER TABLE "thread" ALTER COLUMN "date_active" TYPE TIMESTAMP WITHOUT TIME ZONE;',
        ],
    "mysql": [],
    }


def apply(store):
    """Add the thread table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
