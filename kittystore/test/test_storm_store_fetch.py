# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103

import unittest

from mailman.email.message import Message

from kittystore.storm import get_storm_store

from kittystore.test import FakeList


class TestStormStoreFetch(unittest.TestCase):

    def setUp(self):
        self.store = get_storm_store("sqlite:")
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

    def test_search_list_for_sender(self):
        """Search for a Message in a List by Sender """
        email = self.store.search_list_for_sender(self.listname, "dummy@example").one()
        self.assertIsNotNone(email)
        self.assertEqual(email.sender_email, "dummy@example.com")

    def test_search_list_for_content(self):
        """Search for a Message in a List by Content """
        email = self.store.search_list_for_content(self.listname, "Message").one()
        self.assertIsNotNone(email)
        self.assertEqual(email.sender_email, "dummy@example.com")

    def test_search_list_for_content_case_false(self):
        """Search for a Message in a List by Content (case insensitive)"""
        email = self.store.search_list_for_content(self.listname, "MESSAGE").one()
        self.assertIsNotNone(email)
        self.assertEqual(email.sender_email, "dummy@example.com")

    def test_search_list_for_subject(self):
        """Search for a Message in a List by Subject """
        email = self.store.search_list_for_subject(self.listname, "Subject").one()
        self.assertIsNotNone(email)
        self.assertEqual(email.sender_email, "dummy@example.com")

    def test_search_list_for_content_subject_subject(self):
        """Search for a Message in a List by Content or Subject. Match for Subject """
        email = self.store.search_list_for_content_subject(self.listname, "Subject").one()
        self.assertIsNotNone(email)
        self.assertEqual(email.sender_email, "dummy@example.com")

    def test_search_list_for_content_subject_content(self):
        """Search for a Message in a List by Content or Subject. Match for Content"""
        email = self.store.search_list_for_content_subject(self.listname, "Message").one()
        self.assertIsNotNone(email)
        self.assertEqual(email.sender_email, "dummy@example.com")
