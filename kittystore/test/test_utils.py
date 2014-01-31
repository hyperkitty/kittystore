# -*- coding: utf-8 -*-
# pylint: disable=R0904

import unittest
import email
import datetime
import dateutil

from mailman.email.message import Message

import kittystore.utils
from kittystore.test import get_test_file


class TestUtils(unittest.TestCase):

    def test_ref_parsing(self):
        with open(get_test_file("strange-in-reply-to-header.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        ref_id = kittystore.utils.get_ref(msg)
        self.assertEqual(ref_id, "200704070053.46646.other.person@example.com")

    def test_wrong_reply_to_format(self):
        with open(get_test_file("wrong-in-reply-to-header.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        ref_id = kittystore.utils.get_ref(msg)
        self.assertEqual(ref_id, None)

    def test_in_reply_to(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["In-Reply-To"] = " <ref-1> "
        msg.set_payload("Dummy message")
        ref_id = kittystore.utils.get_ref(msg)
        self.assertEqual(ref_id, "ref-1")

    def test_in_reply_to_and_reference(self):
        """The In-Reply-To header should win over References"""
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["In-Reply-To"] = " <ref-1> "
        msg["References"] = " <ref-2> "
        msg.set_payload("Dummy message")
        ref_id = kittystore.utils.get_ref(msg)
        self.assertEqual(ref_id, "ref-1")

    def test_single_reference(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["References"] = " <ref-1> "
        msg.set_payload("Dummy message")
        ref_id = kittystore.utils.get_ref(msg)
        self.assertEqual(ref_id, "ref-1")

    def test_multiple_reference(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["References"] = " <ref-1> <ref-2> "
        msg.set_payload("Dummy message")
        ref_id = kittystore.utils.get_ref(msg)
        self.assertEqual(ref_id, "ref-2")

    def test_empty_reference(self):
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg["References"] = " "
        msg.set_payload("Dummy message")
        try:
            kittystore.utils.get_ref(msg)
        except IndexError:
            self.fail("Empty 'References' tag should be handled")

    def test_non_ascii_headers(self):
        """utils.header_to_unicode must handle non-ascii headers"""
        testdata = [
                ("=?ISO-8859-2?Q?V=EDt_Ondruch?=", u'V\xedt Ondruch'),
                ("=?UTF-8?B?VsOtdCBPbmRydWNo?=", u'V\xedt Ondruch'),
                ("=?iso-8859-1?q?Bj=F6rn_Persson?=", u'Bj\xf6rn Persson'),
                ("=?UTF-8?B?TWFyY2VsYSBNYcWhbMOhxYhvdsOh?=", u'Marcela Ma\u0161l\xe1\u0148ov\xe1'),
                ("Dan =?ISO-8859-1?Q?Hor=E1k?=", u'Dan Hor\xe1k'),
                ("=?ISO-8859-1?Q?Bj=F6rn?= Persson", u'Bj\xf6rn Persson'),
                ("=?UTF-8?Q?Re=3A_=5BFedora=2Dfr=2Dlist=5D_Compte=2Drendu_de_la_r=C3=A9union_du_?= =?UTF-8?Q?1_novembre_2009?=", u"Re: [Fedora-fr-list] Compte-rendu de la r\xe9union du 1 novembre 2009"),
                ("=?iso-8859-1?q?Compte-rendu_de_la_r=E9union_du_?= =?iso-8859-1?q?1_novembre_2009?=", u"Compte-rendu de la r\xe9union du 1 novembre 2009"),
                ]
        for h_in, h_expected in testdata:
            h_out = kittystore.utils.header_to_unicode(h_in)
            self.assertEqual(h_out, h_expected)
            self.assertTrue(isinstance(h_out, unicode))

    def test_bad_header(self):
        """
        utils.header_to_unicode must handle badly encoded non-ascii headers
        """
        testdata = [
            ("Guillermo G\xf3mez", u"Guillermo G\ufffdmez"),
            ("=?gb2312?B?UmU6IFJlOl9bQW1iYXNzYWRvcnNdX01hdGVyaWFfc29icmVfb19DRVNvTF8oRGnhcmlvX2RlX2JvcmRvKQ==?=",
                u"Re: Re:_[Ambassadors]_Materia_sobre_o_CESoL_(Di\ufffdrio_de_bordo)"),
        ]
        for h_in, h_expected in testdata:
            try:
                h_out = kittystore.utils.header_to_unicode(h_in)
            except UnicodeDecodeError, e:
                self.fail(e)
            self.assertEqual(h_out, h_expected)
            self.assertTrue(isinstance(h_out, unicode))

    def test_wrong_datestring(self):
        datestring = "Fri, 5 Dec 2003 11:41 +0000 (GMT Standard Time)"
        parsed = kittystore.utils.parsedate(datestring)
        self.assertEqual(parsed, None)

    def test_very_large_timezone(self):
        """
        Timezone displacements must not be greater than 14 hours
        Or PostgreSQL won't accept them.
        """
        datestrings = ["Wed, 1 Nov 2006 23:50:26 +1800",
                       "Wed, 1 Nov 2006 23:50:26 -1800"]
        for datestring in datestrings:
            parsed = kittystore.utils.parsedate(datestring)
            self.assertEqual(parsed, dateutil.parser.parse(datestring))
            self.assertTrue(parsed.utcoffset() <= datetime.timedelta(hours=13),
                            "UTC offset %s for datetime %s is too large"
                            % (parsed.utcoffset(), parsed))

    def test_datestring_no_timezone(self):
        datestring = "Sun, 12 Dec 2004 19:11:28"
        parsed = kittystore.utils.parsedate(datestring)
        self.assertEqual(parsed, datetime.datetime(2004, 12, 12, 19, 11, 28))

    def test_unknown_encoding(self):
        """Unknown encodings should just replace unknown characters"""
        header = "=?x-gbk?Q?Frank_B=A8=B9ttner?="
        decoded = kittystore.utils.header_to_unicode(header)
        self.assertEqual(decoded, u'Frank B\ufffd\ufffdttner')

    def test_no_from(self):
        msg = Message()
        msg.set_payload("Dummy message")
        try:
            name, email = kittystore.utils.parseaddr(msg["From"])
        except AttributeError, e:
            self.fail(e)
        self.assertEqual(name, '')
        self.assertEqual(email, '')
