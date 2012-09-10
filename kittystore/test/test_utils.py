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

    def test_wrong_reply_to_format(self):
        with open(get_test_file("wrong-in-reply-to-header.txt")) as email_file:
            msg = email.message_from_file(email_file)
        store = Mock()
        store.get_message_by_id_from_list.return_value = None
        ref_id, thread_id = kittystore.utils.get_ref_and_thread_id(
                msg, "example-list", store)
        self.assertEqual(ref_id, None)

    def test_non_ascii_payload(self):
        """utils.payload_to_unicode must handle non-ascii messages"""
        for enc in ["utf8", "iso8859"]:
            with open(get_test_file("payload-%s.txt" % enc)) as email_file:
                msg = email.message_from_file(email_file)
            payload = kittystore.utils.payload_to_unicode(msg)
            print enc, repr(payload)
            self.assertTrue(isinstance(payload, unicode))
            self.assertEqual(payload, u'This message contains non-ascii '
                    u'characters:\n\xe9 \xe8 \xe7 \xe0 \xee \xef \xeb \u20ac\n')

    def test_non_ascii_headers(self):
        """utils.header_to_unicode must handle non-ascii headers"""
        testdata = [
                ("=?ISO-8859-2?Q?V=EDt_Ondruch?=", u'V\xedt Ondruch'),
                ("=?UTF-8?B?VsOtdCBPbmRydWNo?=", u'V\xedt Ondruch'),
                ("=?iso-8859-1?q?Bj=F6rn_Persson?=", u'Bj\xf6rn Persson'),
                ("=?UTF-8?B?TWFyY2VsYSBNYcWhbMOhxYhvdsOh?=", u'Marcela Ma\u0161l\xe1\u0148ov\xe1'),
                ("Dan =?ISO-8859-1?Q?Hor=E1k?=", u'Dan Hor\xe1k'),
                ("=?ISO-8859-1?Q?Bj=F6rn?= Persson", u'Bj\xf6rnPersson'),
                ("=?UTF-8?Q?Re=3A_=5BFedora=2Dfr=2Dlist=5D_Compte=2Drendu_de_la_r=C3=A9union_du_?= =?UTF-8?Q?1_novembre_2009?=", u"Re: [Fedora-fr-list] Compte-rendu de la r\xe9union du 1 novembre 2009"),
                ("=?iso-8859-1?q?Compte-rendu_de_la_r=E9union_du_?= =?iso-8859-1?q?1_novembre_2009?=", u"Compte-rendu de la r\xe9union du 1 novembre 2009"),
                ]
        for h_in, h_expected in testdata:
            h_out = kittystore.utils.header_to_unicode(h_in)
            self.assertEqual(h_out, h_expected)
            self.assertTrue(isinstance(h_out, unicode))
