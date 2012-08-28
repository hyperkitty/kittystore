# -*- coding: utf-8 -*-


CREATES = {

    "sqlite": [ """
        CREATE TABLE "list" (
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (name)
        );""", """
        CREATE TABLE "email" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            sender_name VARCHAR(255) NOT NULL,
            sender_email VARCHAR(255) NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            date DATETIME NOT NULL,
            in_reply_to VARCHAR(255), -- How about replies from another list ?
            hash_id VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            "full" BLOB NOT NULL,
            archived_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (list_name, message_id)
        );""",
        'CREATE INDEX "ix_email_list_name" ON "email" (list_name);',
        'CREATE UNIQUE INDEX "ix_email_message_id" ON "email" (message_id);',
        'CREATE INDEX "ix_email_date" ON "email" (date);',
        'CREATE UNIQUE INDEX "ix_email_hash_id" ON "email" (hash_id);',
        'CREATE INDEX "ix_email_subject" ON "email" (subject);',
        'CREATE INDEX "ix_email_thread_id" ON "email" (thread_id);',
        ],

    "postgres": [ """
        CREATE TABLE "list" (
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (name)
        );""", """
        CREATE TABLE "email" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            sender_name VARCHAR(255) NOT NULL,
            sender_email VARCHAR(255) NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            date TIMESTAMP WITH TIME ZONE NOT NULL,
            in_reply_to VARCHAR(255), -- How about replies from another list ?
            hash_id VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            "full" BYTEA NOT NULL,
            archived_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (list_name, message_id)
        );""",
        'CREATE INDEX "ix_email_list_name" ON "email" USING btree (list_name);',
        'CREATE UNIQUE INDEX "ix_email_message_id" ON "email" USING btree (message_id);',
        'CREATE INDEX "ix_email_date" ON "email" USING btree (date);',
        'CREATE UNIQUE INDEX "ix_email_hash_id" ON "email" USING btree (hash_id);',
        'CREATE INDEX "ix_email_subject" ON "email" USING btree (subject);',
        'CREATE INDEX "ix_email_thread_id" ON "email" USING btree (thread_id);',
        ],

}


def get_db_type(store):
    database = store.get_database()
    return database.__class__.__module__.split(".")[-1]
