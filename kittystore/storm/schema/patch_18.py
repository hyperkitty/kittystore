# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": ["""
        CREATE TABLE "vote" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            value TINYINT NOT NULL,
            PRIMARY KEY (list_name, message_id, user_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES user(id)
        );""",
        'CREATE INDEX "ix_vote_list_name_message_id" ON "vote" (list_name, message_id);',
        'CREATE INDEX "ix_vote_user_id" ON "vote" (user_id);',
        'CREATE INDEX "ix_vote_value" ON "vote" (value);',
        ],
    "postgres": ["""
        CREATE TABLE "vote" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            value SMALLINT NOT NULL,
            PRIMARY KEY (list_name, message_id, user_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES "user"(id)
        );""",
        'CREATE INDEX "ix_vote_list_name_message_id" ON "vote" (list_name, message_id);',
        'CREATE INDEX "ix_vote_user_id" ON "vote" (user_id);',
        'CREATE INDEX "ix_vote_value" ON "vote" (value);',
        ],
    "mysql": ["""
        CREATE TABLE `vote` (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            value TINYINT NOT NULL,
            PRIMARY KEY (list_name, message_id, user_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES `user`(id)
        );""",
        'CREATE INDEX `ix_vote_list_name_message_id` ON `vote` (list_name, message_id);',
        'CREATE INDEX `ix_vote_user_id" ON "vote` (user_id);',
        'CREATE INDEX `ix_vote_value" ON "vote` (value);',
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

