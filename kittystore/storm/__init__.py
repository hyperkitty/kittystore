# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement

import sys
import threading

import storm.tracer
from storm.locals import create_database, Store
from storm.schema.schema import Schema

from .model import List, Email
from . import schema
from .store import StormStore


class ThreadSafeStorePool(object):
    """
    Storm does not have a thread pool, like SQLAlchemy. Solve the threading
    problem by keeping the store in a thread-local object.

    http://unpythonic.blogspot.fr/2007/11/using-storm-and-sqlite-in-multithreaded.html
    """

    def __init__(self, url, debug):
        self.url = url
        self.debug = debug
        self._local = threading.local()

    def get(self):
        try:
            return self._local.store
        except AttributeError:
            self._local.store = create_store(self.url, self.debug)
            return self._local.store


def create_store(url, debug):
    if debug:
        storm.tracer.debug(True, stream=sys.stdout)
    database = create_database(url)
    dbtype = url.partition(":")[0]
    store = Store(database)
    dbschema = Schema(schema.CREATES[dbtype], [], [], schema)
    dbschema.upgrade(store)
    return StormStore(store, debug)


def get_storm_store(url, debug=False):
    # Thread safety is managed by the middleware
    #store_pool = ThreadSafeStorePool(url, debug)
    #return store_pool.get()
    return create_store(url, debug)
