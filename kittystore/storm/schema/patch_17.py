# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL_step_1 = {
    "sqlite": ["""
        CREATE TABLE "user" (
            id VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""", """
        CREATE TABLE "sender" (
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            user_id VARCHAR(255),
            PRIMARY KEY (email),
            FOREIGN KEY (user_id) REFERENCES user(id)
        );""",
        'CREATE INDEX "ix_sender_user_id" ON "sender" (user_id);',
        'CREATE INDEX "ix_email_list_name_thread_id" ON "email" (list_name, thread_id);',
        'CREATE INDEX "ix_attachment_list_name_message_id" ON "attachment" (list_name, message_id);',
        ],
    "postgres": ["""
        CREATE TABLE "user" (
            id VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""", """
        CREATE TABLE "sender" (
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            user_id VARCHAR(255),
            PRIMARY KEY (email),
            FOREIGN KEY (user_id) REFERENCES "user"(id)
        );""",
        'CREATE INDEX "ix_sender_user_id" ON "sender" (user_id);',
        'CREATE INDEX "ix_email_list_name_thread_id" ON "email" (list_name, thread_id);',
        'CREATE INDEX "ix_attachment_list_name_message_id" ON "attachment" (list_name, message_id);',
        ],
    "mysql": ["""
        CREATE TABLE `user` (
            id VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""", """
        CREATE TABLE `sender` (
            email VARCHAR(255) NOT NULL,
            name VARCHAR(255) COLLATE utf8_general_ci,
            user_id VARCHAR(255),
            PRIMARY KEY (email),
            FOREIGN KEY (user_id) REFERENCES `user`(id)
        );""",
        'CREATE INDEX `ix_sender_user_id` ON `sender` (user_id);',
        'CREATE INDEX `ix_email_list_name_thread_id` ON `email` (list_name, thread_id);',
        'CREATE INDEX `ix_attachment_list_name_message_id` ON `attachment` (list_name, message_id);',
        ],
    }

SQL_step_2 = {
    "sqlite": [
        'DROP INDEX "ix_email_user_id"',
        # No 'ALTER TABLE DROP COLUMN' or 'ALTER TABLE ADD constraint' in SQLite
        ],
    "postgres": [
        'DROP INDEX "ix_email_user_id"',
        'ALTER TABLE "email" DROP COLUMN "sender_name"',
        'ALTER TABLE "email" DROP COLUMN "user_id"',
        'ALTER TABLE "email" ADD FOREIGN KEY (sender_email) REFERENCES sender(email)',
        ],
    "mysql": [
        'DROP INDEX `ix_email_user_id`',
        'ALTER TABLE `email` DROP COLUMN `sender_name`',
        'ALTER TABLE `email` DROP COLUMN `user_id`',
        'ALTER TABLE `email` ADD FOREIGN KEY (sender_email) REFERENCES sender(email)',
        ],
    }


def apply(store):
    """
    Remove the database-based cache.
    """
    dbtype = get_db_type(store)
    # create the new tables
    for statement in SQL_step_1[dbtype]:
        store.execute(statement)
    # escape the user table name, it's usually a reserved sql word
    if dbtype == "mysql":
        user_table_name = '`user`'
    else:
        user_table_name = '"user"'
    # migrate the data
    store.execute("INSERT INTO sender(email) SELECT DISTINCT sender_email FROM email")
    for addr in store.execute("SELECT email FROM sender"):
        addr = addr[0]
        name_and_userid = store.execute(
                "SELECT sender_name, user_id FROM email "
                "WHERE sender_email = ? LIMIT 1", [addr]).get_one()
        if name_and_userid is None:
            continue
        name, user_id = name_and_userid
        if name is not None:
            store.execute("UPDATE sender SET name = ? WHERE email = ?", (name, addr))
        if user_id is not None:
            if store.execute("SELECT COUNT(*) FROM %s WHERE id = ?" % user_table_name,
                             [user_id]).get_one()[0] == 0:
                store.execute("INSERT INTO %s VALUES (?)" % user_table_name, [user_id])
            store.execute("UPDATE sender SET user_id = ? WHERE email = ?", (user_id, addr))
    # drop the old columns
    for statement in SQL_step_2[dbtype]:
        store.execute(statement)
    store.commit()

