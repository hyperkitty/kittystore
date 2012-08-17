# -*- coding: utf-8 -*-

import unittest
import email
from mock import Mock

from kittystore.sa import KittySAStore
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

