# -*- coding: utf-8 -*-

from __future__ import absolute_import

from storm.expr import And
from storm.locals import Desc

from . import get_db_type
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
        ],
    "postgres": [ """
        CREATE TABLE "thread" (
            list_name VARCHAR(255) NOT NULL,
            thread_id VARCHAR(255) NOT NULL,
            date_active TIMESTAMP WITH TIME ZONE NOT NULL,
            PRIMARY KEY (list_name, thread_id)
        );""",
        'CREATE INDEX "ix_thread_date_active" ON "thread" USING btree (date_active);',
        ],
    "mysql": [],
    }


def apply(store):
    """Add the thread table"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    for email in store.find(Email, Email.in_reply_to == None):
        thread = Thread(email.list_name, email.thread_id)
        store.add(thread)
        store.flush()
    for email in store.find(Email):
        # in case of partial imports, some threads are missing their original
        # email (the one without an in-reply-to header)
        thread_count = store.find(Thread, And(
                            Thread.list_name == email.list_name,
                            Thread.thread_id == email.thread_id,
                        )).count()
        if thread_count == 0:
            # this email has no associated thread, create it
            thread = Thread(email.list_name, email.thread_id)
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
