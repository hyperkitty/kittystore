# -*- coding: utf-8 -*-
# pylint: disable=R0904

import unittest
import email
import mailbox
import datetime

from storm.exceptions import IntegrityError
from kittystore.storm import get_storm_store
from kittystore.storm.model import Email
from kittystore.test import get_test_file


class FakeList(object):
    def __init__(self, name):
        self.fqdn_listname = name


class TestSAStore(unittest.TestCase):

    def setUp(self):
        self.store = get_storm_store("sqlite:")

    #def tearDown(self):
    #    self.store.close()

    def test_no_message_id(self):
        msg = email.message.Message()
        self.assertRaises(ValueError, self.store.add_to_list,
                          FakeList("example-list"), msg)

    def test_no_date(self):
        msg = email.message.Message()
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
