# -*- coding: utf-8 -*-

def apply(store):
    """Add the description column"""
    store.execute('ALTER TABLE "list" ADD COLUMN "description" TEXT;')
    store.commit()
