# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

import unittest
from datetime import datetime

from mailman.email.message import Message

from kittystore.storm import get_storm_store
from kittystore.storm.model import Email, Thread
from kittystore.analysis import compute_thread_order_and_depth

from kittystore.test import FakeList, SettingsModule


def make_fake_email(num=1, list_name="example-list", date=None):
    msg = Email(list_name, "<msg%d>" % num)
    msg.thread_id = u"<msg%d>" % num
    msg.sender_email = u"sender%d@example.com" % num
    msg.subject = u"subject %d" % num
    msg.content = u"message %d" % num
    if date is None:
        msg.date = datetime.now()
    else:
        msg.date = date
    msg.timezone = 0
    return msg


class TestThreadOrderDepth(unittest.TestCase):

    def setUp(self):
        self.store = get_storm_store(SettingsModule(), auto_create=True)

    def tearDown(self):
        self.store.flush()
        self.store.rollback()
        self.store.close()

    def test_simple_thread(self):
        # A basic thread: msg2 replies to msg1
        thread = Thread("example-list", "<msg1>")
        self.store.db.add(thread)
        msg1 = make_fake_email(1)
        msg1.thread_order = msg1.thread_depth = 42
        self.store.db.add(msg1)
        msg2 = make_fake_email(2)
        msg2.thread_id = u"<msg1>"
        msg2.in_reply_to = u"<msg1>"
        msg2.thread_order = msg2.thread_depth = 42
        self.store.db.add(msg2)
        self.store.flush()
        compute_thread_order_and_depth(thread)
        self.assertEqual(msg1.thread_order, 0)
        self.assertEqual(msg1.thread_depth, 0)
        self.assertEqual(msg2.thread_order, 1)
        self.assertEqual(msg2.thread_depth, 1)

    def test_classical_thread(self):
        # msg1
        # |-msg2
        # | `-msg4
        # `-msg3
        thread = Thread("example-list", "<msg1>")
        self.store.db.add(thread)
        msg1 = make_fake_email(1)
        msg2 = make_fake_email(2)
        msg3 = make_fake_email(3)
        msg4 = make_fake_email(4)
        # All in the same thread
        msg2.thread_id = msg3.thread_id = msg4.thread_id = u"<msg1>"
        # Set up the reply tree
        msg2.in_reply_to = msg3.in_reply_to = u"<msg1>"
        msg4.in_reply_to = u"<msg2>"
        # Init with false values
        msg1.thread_order = msg1.thread_depth = \
                msg2.thread_order = msg2.thread_depth = \
                msg3.thread_order = msg3.thread_depth = \
                msg4.thread_order = msg4.thread_depth = 42
        self.store.db.add(msg1)
        self.store.db.add(msg2)
        self.store.db.add(msg3)
        self.store.db.add(msg4)
        self.store.flush()
        compute_thread_order_and_depth(thread)
        self.assertEqual(msg1.thread_order, 0)
        self.assertEqual(msg1.thread_depth, 0)
        self.assertEqual(msg2.thread_order, 1)
        self.assertEqual(msg2.thread_depth, 1)
        self.assertEqual(msg3.thread_order, 3)
        self.assertEqual(msg3.thread_depth, 1)
        self.assertEqual(msg4.thread_order, 2)
        self.assertEqual(msg4.thread_depth, 2)

    def test_add_in_classical_thread(self):
        # msg1
        # |-msg2
        # | `-msg4
        # `-msg3
        ml = FakeList("example-list")
        msgs = []
        for num in range(1, 5):
            msg = Message()
            msg["From"] = "sender%d@example.com" % num
            msg["Message-ID"] = "<msg%d>" % num
            msg.set_payload("message %d" % num)
            msgs.append(msg)
        msgs[1]["In-Reply-To"] = "<msg1>"
        msgs[2]["In-Reply-To"] = "<msg1>"
        msgs[3]["In-Reply-To"] = "<msg2>"
        for msg in msgs:
            self.store.add_to_list(ml, msg)
        msgs = []
        for num in range(1, 5):
            msg = self.store.get_message_by_id_from_list(
                    "example-list", "msg%d" % num)
            msgs.append(msg)
        msg1, msg2, msg3, msg4 = msgs
        self.assertEqual(msg1.thread_order, 0)
        self.assertEqual(msg1.thread_depth, 0)
        self.assertEqual(msg2.thread_order, 1)
        self.assertEqual(msg2.thread_depth, 1)
        self.assertEqual(msg3.thread_order, 3)
        self.assertEqual(msg3.thread_depth, 1)
        self.assertEqual(msg4.thread_order, 2)
        self.assertEqual(msg4.thread_depth, 2)

    def test_reply_to_oneself(self):
        # A message replying to itself (yes, it's been spotted in the wild)
        thread = Thread("example-list", "<msg1>")
        self.store.db.add(thread)
        msg1 = make_fake_email(1)
        msg1.in_reply_to = u"<msg1>"
        msg1.thread_order = msg1.thread_depth = 42
        self.store.db.add(msg1)
        self.store.flush()
        compute_thread_order_and_depth(thread)
        # Don't traceback with a "maximum recursion depth exceeded" error
        self.assertEqual(msg1.thread_order, 0)
        self.assertEqual(msg1.thread_depth, 0)

    def test_reply_loops(self):
        """Loops in message replies"""
        # This implies that someone replies to a message not yet sent, but you
        # never know, Dr Who can be on your mailing-list.
        thread = Thread("example-list", "<msg1>")
        self.store.db.add(thread)
        msg1 = make_fake_email(1)
        msg1.in_reply_to = u"<msg2>"
        self.store.db.add(msg1)
        msg2 = make_fake_email(2)
        msg2.thread_id = u"<msg1>"
        msg2.in_reply_to = u"<msg1>"
        self.store.db.add(msg2)
        self.store.flush()
        compute_thread_order_and_depth(thread)
        # Don't traceback with a "maximum recursion depth exceeded" error
