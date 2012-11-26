# -*- coding: utf-8 -*-

from __future__ import absolute_import

from . import get_db_type


SQL = {
    "sqlite": [ """
        CREATE TABLE "email_full" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            "full" BLOB NOT NULL,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""",
        'INSERT INTO "email_full" SELECT list_name, message_id, "full" FROM "email";'
        # No 'ALTER TABLE DROP COLUMN' in SQLite
        ],
    "postgres": [ """
        CREATE TABLE "email_full" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            "full" BYTEA NOT NULL,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""",
        'INSERT INTO "email_full" SELECT list_name, message_id, "full" FROM "email";'
        'ALTER TABLE "email" DROP COLUMN "full";',
        ],
    "mysql": [ """
        CREATE TABLE `email_full` (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            `full` BLOB NOT NULL,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""",
        'INSERT INTO `email_full` SELECT list_name, message_id, `full` FROM `email`;'
        ],
    }


def apply(store):
    """Add the thread table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()

