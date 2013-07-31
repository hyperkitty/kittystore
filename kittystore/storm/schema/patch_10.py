# -*- coding: utf-8 -*-

from __future__ import absolute_import

from . import get_db_type


SQL = {
    "sqlite": ["""
        CREATE TABLE "user_address" (
            user_id VARCHAR(255) NOT NULL,
            address VARCHAR(255) NOT NULL,
            PRIMARY KEY (user_id, address)
        );""",
        'CREATE INDEX "ix_user_address_user_id" ON "user_address" (user_id);',
        'CREATE UNIQUE INDEX "ix_user_address_address" ON "user_address" (address);',
        ],
    "postgres": ["""
        CREATE TABLE "user_address" (
            user_id VARCHAR(255) NOT NULL,
            address VARCHAR(255) NOT NULL,
            PRIMARY KEY (user_id, address)
        );""",
        'CREATE INDEX "ix_user_address_user_id" ON "user_address" USING btree (user_id);',
        'CREATE UNIQUE INDEX "ix_user_address_address" ON "user_address" USING btree (address);',
        ],
    "mysql": ["""
        CREATE TABLE `user_address` (
            user_id VARCHAR(255) NOT NULL,
            address VARCHAR(255) NOT NULL,
            PRIMARY KEY (user_id, address)
        );""",
        'CREATE INDEX `ix_user_address_user_id` ON `user_address` (user_id);',
        'CREATE UNIQUE INDEX `ix_user_address_address` ON `user_address` (address);',
        ],
    }


def apply(store):
    """Add the user_address table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
