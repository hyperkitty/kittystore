# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": [
        'ALTER TABLE "email" ADD COLUMN user_id VARCHAR(255);',
        'CREATE INDEX "ix_email_user_id" ON "email" (user_id);',
        ],
    "postgres": [
        'ALTER TABLE "email" ADD COLUMN user_id VARCHAR(255);',
        'CREATE INDEX "ix_email_user_id" ON "email" (user_id);',
        ],
    "mysql": [
        'ALTER TABLE `email` ADD COLUMN user_id VARCHAR(255);',
        'CREATE INDEX `ix_email_user_id` ON `email` (user_id(255));',
        ],
    }


def apply(store):
    """Add the user_address table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
