# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103

import unittest

from mailman.email.message import Message

from kittystore.storm import get_storm_store

from kittystore.test import FakeList, SettingsModule


class TestStormStoreFetch(unittest.TestCase):

    def setUp(self):
        self.store = get_storm_store(SettingsModule(), auto_create=True)
        self.listname, self.m_hash = self.add_fetch_data()

    def tearDown(self):
        self.store.close()

    def add_fetch_data(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Subject"] = "Fake Subject"
        msg["Message-ID"] = "<dummy>"
        msg["Date"] = "Fri, 02 Nov 2012 16:07:54"
        msg.set_payload("Fake Message")

        ml = FakeList("example-list")
        ml.display_name = u"name 1"
        ml.subject_prefix = u"[prefix 1]"

        return ml.fqdn_listname, self.store.add_to_list(ml, msg)

    def test_get_message_by_id_from_list(self):
        """Get a Message in a List by Message-ID """
        m = self.store.get_message_by_id_from_list(self.listname, "dummy")
        self.assertIsNotNone(m)
        self.assertEqual(m.sender_email, "dummy@example.com")

    def test_get_thread(self):
        """Get a Thread in a List by Thread-ID """
        # Test assumes message_id_hash == thread_id
        m = self.store.get_message_by_hash_from_list(self.listname, self.m_hash)
        self.assertIsNotNone(m)
        t = self.store.get_thread(self.listname, m.thread_id)
        self.assertIsNotNone(t)
        self.assertEqual(t.thread_id, m.thread_id)
        self.assertEqual(t.list_name, self.listname)
