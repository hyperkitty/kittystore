# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

import unittest
import email
import datetime

from storm.exceptions import IntegrityError
from mailman.email.message import Message

from kittystore.storm import get_storm_store
from kittystore.storm.model import Email, Attachment, List
from kittystore.utils import get_message_id_hash

from kittystore.test import get_test_file, FakeList


class TestStormStore(unittest.TestCase):

    def setUp(self):
        self.store = get_storm_store("sqlite:")

    def tearDown(self):
        self.store.close()

    def test_no_message_id(self):
        msg = Message()
        self.assertRaises(ValueError, self.store.add_to_list,
                          FakeList("example-list"), msg)

    def test_no_date(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        now = datetime.datetime.now()
        try:
            self.store.add_to_list(FakeList("example-list"), msg)
        except IntegrityError, e:
            self.fail(e)
        stored_msg = self.store.db.find(Email).one()
        self.assertTrue(stored_msg.date >= now)

    def test_date_naive(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["Date"] = "Fri, 02 Nov 2012 16:07:54"
        msg.set_payload("Dummy message")
        try:
            self.store.add_to_list(FakeList("example-list"), msg)
        except IntegrityError, e:
            self.fail(e)
        stored_msg = self.store.db.find(Email).one()
        expected = datetime.datetime(2012, 11, 2, 16, 7, 54)
        self.assertEqual(stored_msg.date, expected)

    def test_attachment_insert_order(self):
        """Attachments must not be inserted in the DB before the email"""
        # Re-activate foreign key support in sqlite
        self.store.db._connection._raw_connection.isolation_level = 'IMMEDIATE'
        self.store.db.execute("PRAGMA foreign_keys = ON")
        self.store.db._connection._raw_connection.execute("PRAGMA foreign_keys = ON")
        #print "*"*10, list(self.store.db.execute("PRAGMA foreign_keys"))
        #self.store = get_storm_store("postgres://kittystore:kittystore@localhost/kittystore_test")
        with open(get_test_file("attachment-1.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        try:
            self.store.add_to_list(FakeList("example-list"), msg)
        except IntegrityError, e:
            self.fail(e)
        self.assertEqual(self.store.db.find(Email).count(), 1)
        self.assertEqual(self.store.db.find(Attachment).count(), 1)

    def test_update_list(self):
        """List records must be updated when changed in Mailman"""
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        ml = FakeList("example-list")
        ml.display_name = u"name 1"
        ml.subject_prefix = u"[prefix 1]"
        self.store.add_to_list(ml, msg)
        ml_db = self.store.db.find(List).one()
        self.assertEqual(ml_db.display_name, "name 1")
        self.assertEqual(ml_db.subject_prefix, "[prefix 1]")
        ml.display_name = u"name 2"
        ml.subject_prefix = u"[prefix 2]"
        self.store.add_to_list(ml, msg)
        ml_db = self.store.db.find(List).one()
        self.assertEqual(ml_db.display_name, "name 2")
        self.assertEqual(ml_db.subject_prefix, "[prefix 2]")


    def test_thread_neighbors(self):
        ml = FakeList("example-list")
        # Create 3 threads
        msg_t1_1 = Message()
        msg_t1_1["From"] = "dummy@example.com"
        msg_t1_1["Message-ID"] = "<id1_1>"
        msg_t1_1.set_payload("Dummy message")
        self.store.add_to_list(ml, msg_t1_1)
        msg_t2_1 = Message()
        msg_t2_1["From"] = "dummy@example.com"
        msg_t2_1["Message-ID"] = "<id2_1>"
        msg_t2_1.set_payload("Dummy message")
        self.store.add_to_list(ml, msg_t2_1)
        msg_t3_1 = Message()
        msg_t3_1["From"] = "dummy@example.com"
        msg_t3_1["Message-ID"] = "<id3_1>"
        msg_t3_1.set_payload("Dummy message")
        self.store.add_to_list(ml, msg_t3_1)
        # Check the neighbors
        def check_neighbors(thread, expected_prev, expected_next):
            thread_id = get_message_id_hash("<id%s_1>" % thread)
            prev_th, next_th = self.store.get_thread_neighbors(
                    "example-list", thread_id)
            # convert to something I can compare
            prev_th = prev_th and prev_th.thread_id
            expected_prev = expected_prev and \
                    get_message_id_hash("<id%s_1>" % expected_prev)
            next_th = next_th and next_th.thread_id
            expected_next = expected_next and \
                    get_message_id_hash("<id%s_1>" % expected_next)
            # compare
            self.assertEqual(prev_th, expected_prev)
            self.assertEqual(next_th, expected_next)
        # Order should be: 1, 2, 3
        check_neighbors(1, None, 2)
        check_neighbors(2, 1, 3)
        check_neighbors(3, 2, None)
        # now add a new message in thread 1, which becomes the most recently
        # active
        msg_t1_2 = Message()
        msg_t1_2["From"] = "dummy@example.com"
        msg_t1_2["Message-ID"] = "<id1_2>"
        msg_t1_2["In-Reply-To"] = "<id1_1>"
        msg_t1_2.set_payload("Dummy message")
        self.store.add_to_list(ml, msg_t1_2)
        # Order should be: 2, 3, 1
        check_neighbors(2, None, 3)
        check_neighbors(3, 2, 1)
        check_neighbors(1, 3, None)


    #def test_non_ascii_payload(self):
    #    """add_to_list must handle non-ascii messages"""
    #    with open(get_test_file("non-ascii-payload.txt")) as email_file:
    #        msg = email.message_from_file(email_file)
    #    self.store.add_to_list("example-list", msg)
    #    try:
    #        self.store.session.flush()
    #    except ProgrammingError, e:
    #        self.fail(e)
    #    print msg.items()
    #    email_table = get_class_object(list_to_table_name("example-list"), 'email',
    #        self.store.metadata)
    #    emails = self.store.session.query(email_table).all()
    #    for e in emails:
    #        print e.content

    #def test_non_ascii_headers(self):
    #    """add_to_list must handle non-ascii headers"""
    #    mbox = mailbox.mbox(get_test_file("non-ascii-headers.txt"))
    #    for msg in mbox:
    #        self.store.add_to_list("example-list", msg)
    #    self.store.session.flush()
    #    email_table = get_class_object(list_to_table_name("example-list"), 'email',
    #        self.store.metadata)
    #    for msg in self.store.session.query(email_table).all():
    #        print repr(msg.sender), repr(msg.subject)
    #        self.failIf("=?" in msg.sender,
    #                "From header not decoded: %s" % msg.sender)
    #        self.failIf("=?" in msg.subject,
    #                "Subject header not decoded: %s" % msg.sender)
