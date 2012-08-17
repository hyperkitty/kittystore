# -*- coding: utf-8 -*-

import unittest
import email
from mock import Mock

import kittystore.utils
from kittystore.test import get_test_file

class TestUtils(unittest.TestCase):

    def test_ref_parsing(self):
        with open(get_test_file("strange-in-reply-to-header.txt")) as email_file:
            msg = email.message_from_file(email_file)
        store = Mock()
        store.get_message_by_id_from_list.return_value = None
        ref_id, thread_id = kittystore.utils.get_ref_and_thread_id(
                msg, "example-list", store)
        self.assertEqual(ref_id, "200704070053.46646.other.person@example.com")
