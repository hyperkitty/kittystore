# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .utils import get_db_type
from kittystore.storm.model import Thread
from kittystore.analysis import compute_thread_order_and_depth


SQL = {
    "sqlite": [
        'ALTER TABLE "email" ADD COLUMN "thread_order" INTEGER NOT NULL DEFAULT 0;',
        'ALTER TABLE "email" ADD COLUMN "thread_depth" INTEGER NOT NULL DEFAULT 0;',
        'CREATE INDEX "ix_email_thread_order" ON "email" (thread_order);',
        ],
    "postgres": [
        'ALTER TABLE "email" ADD COLUMN "thread_order" INTEGER NOT NULL DEFAULT 0;',
        'ALTER TABLE "email" ADD COLUMN "thread_depth" INTEGER NOT NULL DEFAULT 0;',
        'CREATE INDEX "ix_email_thread_order" ON "email" (thread_order);',
        ],
    "mysql": [
        'ALTER TABLE `email` ADD COLUMN `thread_order` INTEGER NOT NULL DEFAULT 0;',
        'ALTER TABLE `email` ADD COLUMN `thread_depth` INTEGER NOT NULL DEFAULT 0;',
        'CREATE INDEX `ix_email_thread_order` ON `email` (thread_order);',
        ],
    }


def apply(store):
    """Add the thread_order and thread_depth columns and populate them"""
    dbtype = get_db_type(store)
    for statement in SQL[dbtype]:
        store.execute(statement)
    for thread in store.find(Thread):
        compute_thread_order_and_depth(thread)
        store.add(thread)
    store.commit()
