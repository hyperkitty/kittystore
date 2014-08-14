# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

from __future__ import absolute_import, print_function, unicode_literals

import unittest
import tempfile
import os

import sqlalchemy as sa
import alembic
from mock import Mock

from kittystore import SchemaUpgradeNeeded
from kittystore.sa import SchemaManager
from kittystore.sa.model import Base
from kittystore.test import SettingsModule


class TestSAMigrations(unittest.TestCase):

    def setUp(self):
        _fh, self.tmpfile = tempfile.mkstemp(suffix=".sqlite")
        os.close(_fh)
        self.settings = SettingsModule()
        self.settings.KITTYSTORE_URL = "sqlite:///%s" % self.tmpfile
        self.sm = SchemaManager(self.settings)

    def tearDown(self):
        os.remove(self.tmpfile)

    def _get_db_rev(self, engine=None):
        if engine is None:
            engine = self.sm.engine
        tmpmd = sa.MetaData()
        tmpmd.reflect(engine)
        version_table = tmpmd.tables["alembic_version"]
        session = sa.orm.sessionmaker(bind=engine)()
        #print(session.query(version_table.c.version_num).all())
        return session.query(version_table.c.version_num).scalar()

    def assertAllTablesCreated(self, engine=None):
        if engine is None:
            engine = self.sm.engine
        dbmd = sa.MetaData()
        dbmd.reflect(engine)
        dbtables = set(dbmd.tables.keys())
        codetables = set(Base.metadata.tables.keys())
        # add the alembic table, it's not in the code but expected
        codetables.add("alembic_version")
        self.assertEqual(dbtables, codetables)

    def test_no_db_no_auto_create(self):
        self.sm._create = Mock()
        self.sm._upgrade = Mock()
        self.assertRaises(SchemaUpgradeNeeded, self.sm.check)
        self.assertFalse(self.sm._create.called)
        self.assertFalse(self.sm._upgrade.called)
        self.assertEqual(self._get_db_rev(), None)

    def test_no_db_auto_create(self):
        self.sm._upgrade = Mock()
        version = self.sm.setup_db()
        self.assertFalse(self.sm._upgrade.called)
        self.assertEqual(version, self.sm.script.get_current_head())
        self.assertEqual(self._get_db_rev(), version)
        self.assertAllTablesCreated()

    def test_existing_db_from_storm(self):
        Base.metadata.create_all(self.sm.engine)
        # Create a patch table to look like a Storm DB
        tmpmd = sa.MetaData()
        sa.Table("patch", tmpmd, sa.Column("version", sa.Integer))
        tmpmd.create_all(self.sm.engine)
        # Now test
        self.sm._create = Mock()
        version = self.sm.setup_db()
        self.assertFalse(self.sm._create.called)
        self.assertEqual(version, self.sm.script.get_current_head())
        self.assertAllTablesCreated()
        # Check that the patch table is gone
        tmpmd = sa.MetaData()
        tmpmd.reflect(self.sm.engine)
        self.assertFalse("patch" in tmpmd.tables)
        self.assertEqual(self._get_db_rev(), version)

    def test_db_is_up_to_date(self):
        self.sm._create = Mock()
        self.sm._upgrade = Mock()
        # create an up-to-date database
        alembic.command.stamp(self.sm.config, "head")
        version = self.sm.setup_db()
        # check that no method has been run
        self.assertFalse(self.sm._create.called)
        self.assertFalse(self.sm._upgrade.called)
        self.assertEqual(version, self.sm.script.get_current_head())
