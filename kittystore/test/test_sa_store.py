# -*- coding: utf-8 -*-

import unittest
import email
import mailbox
from mock import Mock

from kittystore.sa.store import KittySAStore, list_to_table_name
from kittystore.sa.kittysamodel import get_class_object
from sqlalchemy.exc import ProgrammingError
from kittystore.test import get_test_file

class TestSAStore(unittest.TestCase):

    def setUp(self):
        self.store = KittySAStore("sqlite:///:memory:")

    def tearDown(self):
        self.store.session.close()

    def test_non_ascii_payload(self):
        """add_to_list must handle non-ascii messages"""
        with open(get_test_file("non-ascii-payload.txt")) as email_file:
            msg = email.message_from_file(email_file)
        self.store.add_to_list("example-list", msg)
        try:
            self.store.session.flush()
        except ProgrammingError, e:
            self.fail(e)

    def test_non_ascii_headers(self):
        """add_to_list must handle non-ascii headers"""
        mbox = mailbox.mbox(get_test_file("non-ascii-headers.txt"))
        for msg in mbox:
            self.store.add_to_list("example-list", msg)
        self.store.session.flush()
        email = get_class_object(list_to_table_name("example-list"), 'email',
            self.store.metadata)
        for msg in self.store.session.query(email).all():
            print repr(msg.sender)
            self.failIf("=?" in msg.sender,
                    "header not decoded: %s" % msg.sender)
