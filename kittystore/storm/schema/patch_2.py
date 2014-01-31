# -*- coding: utf-8 -*-

from __future__ import absolute_import

from storm.expr import And

from .utils import get_db_type
from kittystore.storm.model import Thread, Email


SQL = {
    "sqlite": [ """
        CREATE TABLE "thread" (
            list_name VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            date_active DATETIME NOT NULL,
            PRIMARY KEY (list_name, thread_id)
        );""",
        'CREATE INDEX "ix_thread_date_active" ON "thread" (date_active);',
        'ALTER TABLE "list" ADD COLUMN "display_name" TEXT;',
        ],
    "postgres": [ """
        CREATE TABLE "thread" (
            list_name VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            date_active TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (list_name, thread_id)
        );""",
        'CREATE INDEX "ix_thread_date_active" ON "thread" (date_active);',
        'ALTER TABLE "list" ADD COLUMN "display_name" TEXT;',
        ],
    "mysql": [],
    }


def apply(store):
    """Add the thread table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    for email in store.find(Email, Email.in_reply_to == None
            ).values(Email.list_name, Email.thread_id):
        list_name, thread_id = email
        thread = Thread(list_name, thread_id)
        store.add(thread)
        store.flush()
    for email in store.find(Email).values(Email.list_name, Email.thread_id):
        # in case of partial imports, some threads are missing their original
        # email (the one without an in-reply-to header)
        list_name, thread_id = email
        thread_count = store.find(Thread, And(
                            Thread.list_name == list_name,
                            Thread.thread_id == thread_id,
                        )).count()
        if thread_count == 0:
            # this email has no associated thread, create it
            thread = Thread(list_name, thread_id)
            store.add(thread)
            store.flush()
    if dbtype == "postgres":
        store.execute('ALTER TABLE email '
                'ADD FOREIGN KEY (list_name, thread_id) '
                'REFERENCES thread(list_name, thread_id) ON DELETE CASCADE;')
        store.execute('ALTER TABLE attachment '
            'ADD FOREIGN KEY (list_name, message_id) '
            'REFERENCES email(list_name, message_id) ON DELETE CASCADE;')
    store.commit()
