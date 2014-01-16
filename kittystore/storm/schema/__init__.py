# -*- coding: utf-8 -*-


CREATES = {

    "sqlite": [ """
        CREATE TABLE "list" (
            name VARCHAR(255) NOT NULL,
            display_name TEXT,
            description TEXT,
            subject_prefix TEXT,
            archive_policy INTEGER,
            created_at DATETIME,
            PRIMARY KEY (name)
        );""", """
        CREATE TABLE "category" (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR(255) NOT NULL
        );""", """
        CREATE TABLE "thread" (
            list_name VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            date_active DATETIME NOT NULL,
            category_id INTEGER,
            PRIMARY KEY (list_name, thread_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES category(id)
        );""", """
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
        );""", """
        CREATE TABLE "email" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            sender_email VARCHAR(255) NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            date DATETIME NOT NULL,
            timezone INTEGER NOT NULL,
            in_reply_to VARCHAR(255), -- How about replies from another list ?
            message_id_hash VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            thread_order INTEGER NOT NULL DEFAULT 0,
            thread_depth INTEGER NOT NULL DEFAULT 0,
            archived_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (list_name, thread_id)
                REFERENCES thread(list_name, thread_id) ON DELETE CASCADE,
            FOREIGN KEY (sender_email) REFERENCES sender(email)
        );""", """
        CREATE TABLE "email_full" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            "full" BLOB NOT NULL,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
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
            PRIMARY KEY (list_name, message_id, counter),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""", """
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
        'CREATE INDEX "ix_sender_user_id" ON "sender" (user_id);',
        'CREATE INDEX "ix_email_list_name" ON "email" (list_name);',
        'CREATE INDEX "ix_email_date" ON "email" (date);',
        'CREATE UNIQUE INDEX "ix_email_list_name_message_id_hash" ON "email" (list_name, message_id_hash);',
        'CREATE INDEX "ix_email_sender_email" ON "email" (sender_email);',
        'CREATE INDEX "ix_email_subject" ON "email" (subject);',
        'CREATE INDEX "ix_email_thread_id" ON "email" (thread_id);',
        'CREATE INDEX "ix_email_list_name_thread_id" ON "email" (list_name, thread_id);',
        'CREATE INDEX "ix_email_thread_order" ON "email" (thread_order);',
        'CREATE INDEX "ix_email_archived_date" ON "email" (archived_date);',
        'CREATE INDEX "ix_thread_date_active" ON "thread" (date_active);',
        'CREATE INDEX "ix_thread_list_name" ON "thread" (list_name);',
        'CREATE UNIQUE INDEX "ix_category_name" ON "category" (name);',
        'CREATE INDEX "ix_attachment_list_name_message_id" ON "attachment" (list_name, message_id);',
        'CREATE INDEX "ix_vote_list_name_message_id" ON "vote" (list_name, message_id);',
        'CREATE INDEX "ix_vote_user_id" ON "vote" (user_id);',
        'CREATE INDEX "ix_vote_value" ON "vote" (value);',
        ],

    "postgres": [ """
        CREATE TABLE "list" (
            name VARCHAR(255) NOT NULL,
            display_name TEXT,
            description TEXT,
            subject_prefix TEXT,
            archive_policy INTEGER,
            created_at TIMESTAMP WITHOUT TIME ZONE,
            PRIMARY KEY (name)
        );""", """
        CREATE TABLE "category" (
            id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""", """
        CREATE SEQUENCE category_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MAXVALUE
            NO MINVALUE
            CACHE 1
        ;""",
        "ALTER SEQUENCE category_id_seq OWNED BY category.id;",
        "ALTER TABLE ONLY category ALTER COLUMN id SET DEFAULT nextval('category_id_seq'::regclass);",
        """
        CREATE TABLE "thread" (
            list_name VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            date_active TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            category_id INTEGER,
            PRIMARY KEY (list_name, thread_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES category(id)
        );""", """
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
        );""", """
        CREATE TABLE "email" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            sender_email VARCHAR(255) NOT NULL,
            subject TEXT NOT NULL,
            content TEXT NOT NULL,
            date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            timezone INTEGER NOT NULL,
            in_reply_to VARCHAR(255), -- How about replies from another list ?
            message_id_hash VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            thread_order INTEGER NOT NULL DEFAULT 0,
            thread_depth INTEGER NOT NULL DEFAULT 0,
            archived_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (list_name, thread_id)
                REFERENCES thread(list_name, thread_id) ON DELETE CASCADE,
            FOREIGN KEY (sender_email) REFERENCES sender(email)
        );""", """
        CREATE TABLE "email_full" (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            "full" BYTEA NOT NULL,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
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
            PRIMARY KEY (list_name, message_id, counter),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""", """
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
        'CREATE INDEX "ix_sender_user_id" ON "sender" (user_id);',
        'CREATE INDEX "ix_email_list_name" ON "email" (list_name);',
        'CREATE INDEX "ix_email_date" ON "email" (date);',
        'CREATE UNIQUE INDEX "ix_email_list_name_message_id_hash" ON "email" (list_name, message_id_hash);',
        'CREATE INDEX "ix_email_sender_email" ON "email" (sender_email);',
        'CREATE INDEX "ix_email_subject" ON "email" (subject);',
        'CREATE INDEX "ix_email_thread_id" ON "email" (thread_id);',
        'CREATE INDEX "ix_email_list_name_thread_id" ON "email" (list_name, thread_id);',
        'CREATE INDEX "ix_email_thread_order" ON "email" (thread_order);',
        'CREATE INDEX "ix_email_archived_date" ON "email" (archived_date);',
        'CREATE INDEX "ix_thread_date_active" ON "thread" (date_active);',
        'CREATE INDEX "ix_thread_list_name" ON "thread" (list_name);',
        'CREATE UNIQUE INDEX "ix_category_name" ON "category" (name);',
        'CREATE INDEX "ix_attachment_list_name_message_id" ON "attachment" (list_name, message_id);',
        'CREATE INDEX "ix_vote_list_name_message_id" ON "vote" (list_name, message_id);',
        'CREATE INDEX "ix_vote_user_id" ON "vote" (user_id);',
        'CREATE INDEX "ix_vote_value" ON "vote" (value);',
        ],

    "mysql": [ """
        CREATE TABLE `list` (
            name VARCHAR(255) NOT NULL,
            display_name TEXT,
            description TEXT,
            subject_prefix TEXT,
            archive_policy INTEGER,
            created_at DATETIME,
            PRIMARY KEY (name)
        );""", """
        CREATE TABLE `category` (
            id INTEGER NOT NULL AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            PRIMARY KEY (id)
        );""", """
        CREATE TABLE `thread` (
            list_name VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            date_active DATETIME NOT NULL,
            category_id INTEGER,
            PRIMARY KEY (list_name, thread_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES category(id)
        );""", """
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
        );""", """
        CREATE TABLE `email` (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            sender_email VARCHAR(255) NOT NULL,
            subject TEXT NOT NULL COLLATE utf8_general_ci,
            content TEXT NOT NULL COLLATE utf8_general_ci,
            date DATETIME NOT NULL,
            timezone INTEGER NOT NULL,
            in_reply_to VARCHAR(255), -- How about replies from another list ?
            message_id_hash VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            thread_order INTEGER NOT NULL DEFAULT 0,
            thread_depth INTEGER NOT NULL DEFAULT 0,
            archived_date DATETIME,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE,
            FOREIGN KEY (list_name, thread_id)
                REFERENCES thread(list_name, thread_id) ON DELETE CASCADE,
            FOREIGN KEY (sender_email) REFERENCES sender(email)
        );""", """
        CREATE TABLE `email_full` (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            `full` BLOB NOT NULL,
            PRIMARY KEY (list_name, message_id),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""", """
        CREATE TABLE `attachment` (
            list_name VARCHAR(255) NOT NULL,
            message_id VARCHAR(255) NOT NULL,
            counter INTEGER NOT NULL,
            content_type VARCHAR(255) NOT NULL,
            encoding VARCHAR(50),
            name VARCHAR(255),
            size INTEGER NOT NULL,
            content BLOB NOT NULL,
            PRIMARY KEY (list_name, message_id, counter),
            FOREIGN KEY (list_name, message_id)
                REFERENCES email(list_name, message_id) ON DELETE CASCADE
        );""", """
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
        'CREATE INDEX `ix_sender_user_id` ON `sender` (user_id);',
        'CREATE INDEX `ix_email_list_name` ON `email` (list_name);',
        'CREATE INDEX `ix_email_date` ON `email` (date);',
        'CREATE UNIQUE INDEX `ix_email_list_name_message_id_hash` ON `email` (list_name, message_id_hash);',
        'CREATE INDEX `ix_email_sender_email` ON `email` (sender_email(255));',
        'CREATE INDEX `ix_email_subject` ON `email` (subject(255));',
        'CREATE INDEX `ix_email_list_name_thread_id` ON `email` (list_name, thread_id);',
        'CREATE INDEX `ix_email_thread_id` ON `email` (thread_id);',
        'CREATE INDEX `ix_email_thread_order` ON `email` (thread_order);',
        'CREATE INDEX `ix_email_archived_date` ON `email` (archived_date);',
        'CREATE INDEX `ix_thread_date_active` ON `thread` (date_active);',
        'CREATE INDEX `ix_thread_list_name` ON `thread` (list_name);',
        'CREATE UNIQUE INDEX `ix_category_name` ON `category` (name);',
        'CREATE INDEX `ix_attachment_list_name_message_id` ON `attachment` (list_name, message_id);',
        'CREATE INDEX `ix_vote_list_name_message_id` ON `vote` (list_name, message_id);',
        'CREATE INDEX `ix_vote_user_id" ON "vote` (user_id);',
        'CREATE INDEX `ix_vote_value" ON "vote` (value);',
        ],

}
