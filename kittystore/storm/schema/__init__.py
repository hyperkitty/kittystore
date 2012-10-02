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
            message_id_hash VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            "full" BLOB NOT NULL,
            archived_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (list_name, message_id)
        );""", """
        CREATE TABLE "attachment" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            counter INTEGER NOT NULL,
            content_type VARCHAR(255) NOT NULL,
            encoding VARCHAR(50),
            name VARCHAR(255),
            size INTEGER NOT NULL,
            content BLOB NOT NULL,
            PRIMARY KEY (list_name, message_id, counter)
        );""",
        'CREATE INDEX "ix_email_list_name" ON "email" (list_name);',
        'CREATE INDEX "ix_email_date" ON "email" (date);',
        'CREATE UNIQUE INDEX "ix_email_list_name_message_id_hash" ON "email" (list_name, message_id_hash);',
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
            message_id_hash VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            "full" BYTEA NOT NULL,
            archived_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (list_name, message_id)
        );""", """
        CREATE TABLE "attachment" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            counter INTEGER NOT NULL,
            content_type VARCHAR(255) NOT NULL,
            encoding VARCHAR(50),
            name VARCHAR(255),
            size INTEGER NOT NULL,
            content BYTEA NOT NULL,
            PRIMARY KEY (list_name, message_id, counter)
        );""",
        'CREATE INDEX "ix_email_list_name" ON "email" USING btree (list_name);',
        'CREATE INDEX "ix_email_date" ON "email" USING btree (date);',
        'CREATE UNIQUE INDEX "ix_email_list_name_message_id_hash" ON "email" USING btree (list_name, message_id_hash);',
        'CREATE INDEX "ix_email_subject" ON "email" USING btree (subject);',
        'CREATE INDEX "ix_email_thread_id" ON "email" USING btree (thread_id);',
        ],

}


def get_db_type(store):
    database = store.get_database()
    return database.__class__.__module__.split(".")[-1]
