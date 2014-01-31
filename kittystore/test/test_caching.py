# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

import unittest
import datetime
from urllib2 import HTTPError

from mock import Mock
from mailman.email.message import Message
from mailman.interfaces.archiver import ArchivePolicy

from kittystore import get_store
from kittystore.caching import mailman_user
from kittystore.test import FakeList, SettingsModule


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



class FakeMMUser(object):
    user_id = None

class UserIdCacheTestCase(unittest.TestCase):

    def setUp(self):
        self.store = get_store(SettingsModule(), auto_create=True)
        self.mm_client = Mock()
        mailman_user._MAILMAN_CLIENT = self.mm_client
        self.mm_client.get_user.side_effect = HTTPError(
                None, 404, "dummy", {}, None)

    def tearDown(self):
        self.store.close()
        mailman_user._MAILMAN_CLIENT = None

    def test_on_new_message_userid(self):
        # Check that the user_id is set on a new message
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        # setup Mailman's reply
        new_user_id = FakeMMUser()
        new_user_id.user_id = "DUMMY-USER-ID"
        self.mm_client.get_user.side_effect = lambda addr: new_user_id
        # check the User does not exist yet
        self.assertEqual(0,
                self.store.get_message_count_by_user_id("DUMMY-USER-ID"))
        # do the test and check
        self.store.add_to_list(FakeList("example-list"), msg)
        dbmsg = self.store.get_message_by_id_from_list(
                "example-list", "dummy")
        self.assertEqual(dbmsg.sender.user_id, "DUMMY-USER-ID")
        self.assertTrue(dbmsg.sender.user is not None,
                "A 'User' instance was not created")
        self.assertEqual(dbmsg.sender.user.id, "DUMMY-USER-ID")
        self.assertEqual(1,
                self.store.get_message_count_by_user_id("DUMMY-USER-ID"))
        # XXX: Storm-specific
        from kittystore.storm.model import User
        self.assertEqual(self.store.db.find(User).count(), 1)

    def test_on_new_message_no_reply_from_mailman(self):
        # Check that the user_id is set on a new message
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        self.store.add_to_list(FakeList("example-list"), msg)
        dbmsg = self.store.get_message_by_id_from_list(
                "example-list", "dummy")
        self.assertEqual(dbmsg.sender.user_id, None)

    def test_sync_mailman_user(self):
        # Check that the user_id is set when sync_mailman_user is run
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        self.store.add_to_list(FakeList("example-list"), msg)
        dbmsg = self.store.get_message_by_id_from_list(
                "example-list", "dummy")
        self.assertEqual(dbmsg.sender.user_id, None)
        # setup Mailman's reply
        new_user_id = FakeMMUser()
        new_user_id.user_id = "DUMMY-USER-ID"
        self.mm_client.get_user.side_effect = lambda addr: new_user_id
        # do the test and check
        mailman_user.sync_mailman_user(self.store)
        #dbmsg = self.store.get_message_by_id_from_list(
        #        "example-list", "dummy")
        self.assertEqual(dbmsg.sender.user_id, "DUMMY-USER-ID")
        self.assertTrue(dbmsg.sender.user is not None,
                "A 'User' instance was not created")
        self.assertEqual(dbmsg.sender.user.id, "DUMMY-USER-ID")
        self.assertEqual(1,
                self.store.get_message_count_by_user_id("DUMMY-USER-ID"))
