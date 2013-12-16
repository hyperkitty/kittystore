# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

import unittest
import datetime

from mock import Mock
from mailman.email.message import Message
from mailman.interfaces.archiver import ArchivePolicy

from kittystore import get_store
from kittystore.test import get_test_file, FakeList, SettingsModule


class ListCacheTestCase(unittest.TestCase):

    def setUp(self):
        self.store = get_store(SettingsModule(), auto_create=True)

    def tearDown(self):
        self.store.close()

    def test_properties_on_new_message(self):
        ml = FakeList("example-list")
        ml.display_name = u"name 1"
        ml.subject_prefix = u"[prefix 1]"
        ml.description = u"desc 1"
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        self.store.add_to_list(ml, msg)
        ml_db = self.store.get_lists()[0]
        self.assertEqual(ml_db.display_name, "name 1")
        self.assertEqual(ml_db.subject_prefix, "[prefix 1]")
        ml.display_name = u"name 2"
        ml.subject_prefix = u"[prefix 2]"
        ml.description = u"desc 2"
        ml.archive_policy = ArchivePolicy.private
        msg.replace_header("Message-ID", "<dummy2>")
        self.store.add_to_list(ml, msg)
        ml_db = self.store.get_lists()[0]
        #ml_db = self.store.db.find(List).one()
        self.assertEqual(ml_db.display_name, "name 2")
        self.assertEqual(ml_db.subject_prefix, "[prefix 2]")
        self.assertEqual(ml_db.description, "desc 2")
        self.assertEqual(ml_db.archive_policy, ArchivePolicy.private)

    def test_on_old_message(self):
        olddate = datetime.datetime.utcnow() - datetime.timedelta(days=40)
        ml = FakeList("example-list")
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["Date"] = olddate.isoformat()
        msg.set_payload("Dummy message")
        self.store.add_to_list(ml, msg)
        ml_db = self.store.get_lists()[0]
        self.assertEqual(ml_db.recent_participants_count, 0)
        self.assertEqual(ml_db.recent_threads_count, 0)
