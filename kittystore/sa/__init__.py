# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement, unicode_literals, print_function

import os

from pkg_resources import resource_filename
from dogpile.cache import make_region
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

import alembic
import alembic.config
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext

from kittystore import SchemaUpgradeNeeded
from kittystore.caching import setup_cache
from .model import Base
from .store import SAStore



class SchemaManager(object):

    def __init__(self, settings, engine=None, debug=False):
        self.settings = settings
        if engine is None:
            engine = create_engine(settings.KITTYSTORE_URL, echo=debug)
        self.engine = engine
        self.debug = debug
        self._config = None
        self._script = None

    @property
    def config(self):
        if self._config is None:
            self._config = alembic.config.Config(resource_filename(
                    "kittystore.sa", "alembic.ini"))
            self._config.set_main_option(
                    "sqlalchemy.url", self.settings.KITTYSTORE_URL)
        return self._config

    @property
    def script(self):
        if self._script is None:
            self._script = ScriptDirectory.from_config(self.config)
        return self._script

    def check(self):
        def _do_check(db_rev, context):
            head_rev = self.script.get_current_head()
            if db_rev == head_rev:
                return [] # already at the head revision
            raise SchemaUpgradeNeeded("version of the database: %s. Version of the code: %s" % (db_rev, head_rev))
        with EnvironmentContext(self.config, self.script, fn=_do_check):
            self.script.run_env()
        return self.script.get_current_head()

    def _db_is_storm(self):
        md = MetaData()
        md.reflect(bind=self.engine)
        return "patch" in md.tables

    def _create(self):
        Base.metadata.create_all(self.engine)
        alembic.command.stamp(self.config, "head")

    def _upgrade(self):
        alembic.command.upgrade(self.config, "head")

    def setup_db(self):
        # Alembic commands can't be run within the EnvironmentContext (they
        # create their own), so we store the commands to run in this list and
        # run them afterwards.
        to_run = []
        def _find_cmds(db_rev, context):
            head_rev = self.script.get_current_head()
            if db_rev == None:
                if self._db_is_storm():
                    # DB from a previous version, run migrations to remove
                    # Storm-specific tables and upgrade to SQLAlchemy & Alembic
                    to_run.append(self._upgrade)
                else:
                    # initial DB creation
                    to_run.append(self._create)
            elif db_rev != head_rev:
                to_run.append(self._upgrade)
            # db_rev == head_rev: already at the latest revision, nothing to do
            return []
        with EnvironmentContext(self.config, self.script, fn=_find_cmds):
            self.script.run_env()
        for cmd in to_run:
            cmd()
        return self.script.get_current_head()



def create_sa_db(settings, debug=False):
    engine = create_engine(settings.KITTYSTORE_URL, echo=debug)
    schema_mgr = SchemaManager(settings, engine, debug)
    return schema_mgr.setup_db()



def get_sa_store(settings, search_index=None, debug=False, auto_create=False):
    engine = create_engine(settings.KITTYSTORE_URL, echo=debug)
    schema_mgr = SchemaManager(settings, engine, debug)
    try:
        schema_mgr.check()
    except SchemaUpgradeNeeded:
        if not auto_create:
            raise
        schema_mgr.setup_db()
    Session = sessionmaker(bind=engine)
    session = Session()
    cache = make_region()
    setup_cache(cache, settings)
    session.cache = cache
    return SAStore(session, search_index, settings, debug)
