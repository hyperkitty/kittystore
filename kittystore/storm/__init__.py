# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement

import sys

import storm.tracer
from storm.locals import create_database, Store
from storm.schema.schema import Schema

from .model import List, Email
from . import schema
from .store import StormStore


def get_storm_store(url, debug=False):
    if debug:
        storm.tracer.debug(True, stream=sys.stdout)
    database = create_database(url)
    store = Store(database)
    dbtype = url.partition(":")[0]
    dbschema = Schema(schema.CREATES[dbtype], [], [], schema)
    dbschema.upgrade(store)
    return StormStore(store, debug)
