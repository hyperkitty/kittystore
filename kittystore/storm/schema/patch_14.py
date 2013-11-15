# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type


SQL = {
    "sqlite": ["""
        CREATE TABLE "list_month_activity" (
            list_name VARCHAR(255) NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            participants_count INTEGER,
            threads_count INTEGER,
            PRIMARY KEY (list_name, year, month),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE
        );""",
        # No alter table add constraint in SQLite: http://www.sqlite.org/omitted.html
        'CREATE INDEX "ix_email_archived_date" ON "email" (archived_date);',
        'ALTER TABLE "list" ADD COLUMN created_at DATETIME;',
        ],
    "postgres": ["""
        CREATE TABLE "list_month_activity" (
            list_name VARCHAR(255) NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            participants_count INTEGER,
            threads_count INTEGER,
            PRIMARY KEY (list_name, year, month),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE
        );""",
        'ALTER TABLE "thread" ADD CONSTRAINT fk_thread_list FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE;',
        'ALTER TABLE "email" ADD CONSTRAINT fk_email_list FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE;',
        'CREATE INDEX "ix_email_archived_date" ON "email" (archived_date);',
        'ALTER TABLE "list" ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE;',
        ],
    "mysql": ["""
        CREATE TABLE `list_month_activity` (
            list_name VARCHAR(255) NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            participants_count INTEGER,
            threads_count INTEGER,
            PRIMARY KEY (list_name, year, month),
            FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE
        );""",
        'ALTER TABLE `thread` ADD CONSTRAINT fk_thread_list FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE;',
        'ALTER TABLE `email` ADD CONSTRAINT fk_email_list FOREIGN KEY (list_name) REFERENCES list(name) ON DELETE CASCADE;',
        'CREATE INDEX `ix_email_archived_date` ON `email` (archived_date);',
        'ALTER TABLE `list` ADD COLUMN created_at DATETIME;',
        ],
    }


def apply(store):
    """Add the category table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    store.commit()
