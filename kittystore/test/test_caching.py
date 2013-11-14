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
from kittystore.caching import CacheManager
from kittystore.test import get_test_file, FakeList, SettingsModule


class CacheManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.cm = CacheManager()

    def test_discover(self):
        self.cm.discover()
        self.assertNotEqual(len(self.cm._cached_values), 0)

    def test_old_daily(self):
        cv = Mock()
        self.cm._cached_values = [cv]
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        self.cm._last_daily = yesterday
        self.cm.on_new_message(None, None, None)
        self.assertEqual(self.cm._last_daily, datetime.date.today())
        self.assertTrue(cv.daily.called)
        self.assertTrue(cv.on_new_message.called) # called anyway

    def test_on_new_message(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        ml = FakeList("example-list")
        self.cm.on_new_message = Mock()
        self.cm.on_new_thread = Mock()
        store = get_store(SettingsModule(), auto_create=True)
        store._cache_manager = self.cm
        try:
            store.add_to_list(ml, msg)
        finally:
            store.close()
        self.assertTrue(self.cm.on_new_message.called)
        self.assertTrue(self.cm.on_new_thread.called)

    def test_no_new_thread(self):
        ml = FakeList("example-list")
        msg1 = Message()
        msg1["From"] = "dummy@example.com"
        msg1["Message-ID"] = "<dummy1>"
        msg1.set_payload("Dummy message")
        msg2 = Message()
        msg2["From"] = "dummy@example.com"
        msg2["Message-ID"] = "<dummy2>"
        msg2["In-Reply-To"] = "<dummy1>"
        msg2.set_payload("Dummy message")
        self.cm.on_new_message = Mock()
        self.cm.on_new_thread = Mock()
        store = get_store(SettingsModule(), auto_create=True)
        store._cache_manager = self.cm
        try:
            store.add_to_list(ml, msg1)
            store.add_to_list(ml, msg2)
        finally:
            store.close()
        self.assertEqual(self.cm.on_new_message.call_count, 2)
        self.assertEqual(self.cm.on_new_thread.call_count, 1)


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
