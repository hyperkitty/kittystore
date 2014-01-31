# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

import unittest
import email
import datetime
from shutil import rmtree
from tempfile import mkdtemp
#from traceback import format_exc

from storm.exceptions import IntegrityError
#from storm.exceptions import DatabaseError
from mailman.email.message import Message
from mailman.interfaces.archiver import ArchivePolicy

from kittystore import get_store
from kittystore.storm import get_storm_store
from kittystore.storm.model import Email, Attachment, Thread
from kittystore.utils import get_message_id_hash

from kittystore.test import get_test_file, FakeList, SettingsModule


class TestStormStore(unittest.TestCase):

    def setUp(self):
        self.store = get_storm_store(SettingsModule(), auto_create=True)

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
        now = datetime.datetime.utcnow()
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
        self.assertEqual(stored_msg.timezone, 0)

    def test_date_aware(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["Date"] = "Fri, 02 Nov 2012 16:07:54 +0100"
        msg.set_payload("Dummy message")
        try:
            self.store.add_to_list(FakeList("example-list"), msg)
        except IntegrityError, e:
            self.fail(e)
        stored_msg = self.store.db.find(Email).one()
        expected = datetime.datetime(2012, 11, 2, 15, 7, 54)
        self.assertEqual(stored_msg.date, expected)
        self.assertEqual(stored_msg.timezone, 60)

    def test_attachment_insert_order(self):
        """Attachments must not be inserted in the DB before the email"""
        # Re-activate foreign key support in sqlite
        if SettingsModule.KITTYSTORE_URL.startswith("sqlite:"):
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

    def test_long_message_id(self):
        # Some message-ids are more than 255 chars long
        # Check with assert here because SQLite will not enforce the limit
        # (http://www.sqlite.org/faq.html#q9)
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "X" * 260
        msg.set_payload("Dummy message")
        try:
            self.store.add_to_list(FakeList("example-list"), msg)
        except IntegrityError, e:
            self.fail(e)
        stored_msg = self.store.db.find(Email).one()
        self.assertTrue(len(stored_msg.message_id) <= 255,
                "Very long message-id headers are not truncated")

    def test_long_message_id_reply(self):
        # Some message-ids are more than 255 chars long, we'll truncate them
        # but check that references are preserved
        msg1 = Message()
        msg1["From"] = "dummy@example.com"
        msg1["Message-ID"] = "<" + ("X" * 260) + ">"
        msg1.set_payload("Dummy message")
        msg2 = Message()
        msg2["From"] = "dummy@example.com"
        msg2["Message-ID"] = "<Y>"
        msg2["References"] = "<" + ("X" * 260) + ">"
        msg2.set_payload("Dummy message")
        try:
            self.store.add_to_list(FakeList("example-list"), msg1)
            self.store.add_to_list(FakeList("example-list"), msg2)
        except IntegrityError, e:
            self.fail(e)
        stored_msg2 = self.store.db.find(Email, Email.message_id == u"Y").one()
        self.assertEqual(stored_msg2.in_reply_to, "X" * 254)
        self.assertEqual(stored_msg2.thread_order, 1)
        self.assertEqual(stored_msg2.thread_depth, 1)
        thread = self.store.db.find(Thread).one()
        self.assertTrue(thread is not None)
        self.assertEqual(len(thread), 2)


    #def test_payload_invalid_unicode(self):
    #    # Python2 won't mind, but PostgreSQL will refuse the data
    #    # http://bugs.python.org/issue9133
    #    msg = Message()
    #    msg["Message-ID"] = "<dummy>"
    #    msg.set_payload("\xed\xa1\xbc") # This is invalid UTF-8
    #    try:
    #        self.store.add_to_list(FakeList("example-list"), msg)
    #    except DatabaseError, e:
    #        print type(e)
    #        print format_exc()
    #        self.fail("Failed to add the message")
    #    self.fail("WIP")


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


class TestStormStoreWithSearch(unittest.TestCase):

    def setUp(self):
        self.tmpdir = mkdtemp(prefix="kittystore-testing-")
        settings = SettingsModule()
        settings.KITTYSTORE_SEARCH_INDEX = self.tmpdir
        self.store = get_store(settings, auto_create=True)

    def tearDown(self):
        self.store.close()
        rmtree(self.tmpdir)

    def test_private_list(self):
        # emails on private lists must not be found by a search on all lists
        ml = FakeList("example-list")
        ml.archive_policy = ArchivePolicy.private
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        self.store.add_to_list(ml, msg)
        result = self.store.search("dummy")
        self.assertEqual(result["total"], 0)
