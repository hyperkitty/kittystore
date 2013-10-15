# -*- coding: utf-8 -*-

def apply(store):
    """Add the list.archive_policy column"""
    store.execute('ALTER TABLE list ADD COLUMN archive_policy INTEGER;')
    store.commit()
