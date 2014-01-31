# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement

import sys

import storm.tracer
from storm.locals import create_database

from . import schema
from .store import StormStore
from .schema.utils import CheckingSchema
from .utils import StoreWithCache
from kittystore import SchemaUpgradeNeeded
from kittystore.caching import setup_cache


def _get_native_store(settings):
    database = create_database(settings.KITTYSTORE_URL)
    return StoreWithCache(database)

def _get_schema(settings):
    dbtype = settings.KITTYSTORE_URL.partition(":")[0]
    return CheckingSchema(schema.CREATES[dbtype], [], [], schema)


def create_storm_store(settings, debug=False):
    if debug:
        storm.tracer.debug(True, stream=sys.stdout)
    store = _get_native_store(settings)
    dbschema = _get_schema(settings)
    dbschema.upgrade(store)


def get_storm_store(settings, search_index=None, debug=False, auto_create=False):
    if debug:
        storm.tracer.debug(True, stream=sys.stdout)
    store = _get_native_store(settings)
    dbschema = _get_schema(settings)
    if dbschema.has_pending_patches(store):
        if auto_create:
            dbschema.upgrade(store)
        else:
            store.close()
            raise SchemaUpgradeNeeded()
    setup_cache(store.cache, settings)
    return StormStore(store, search_index, settings, debug=debug)
