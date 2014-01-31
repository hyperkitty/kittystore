# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# R0904: Too many public methods (X/20)
# C0103: Invalid name "xX" (should match [a-z_][a-z0-9_]{2,30}$)

import unittest
import email
from traceback import format_exc

from mailman.email.message import Message

from kittystore.scrub import Scrubber
from kittystore.test import get_test_file


class TestScrubber(unittest.TestCase):

    def test_attachment_1(self):
        with open(get_test_file("attachment-1.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0], (
                2, 'puntogil.vcf', 'text/x-vcard', "utf-8",
                'begin:vcard\r\nfn:gil\r\nn:;gil\r\nversion:2.1\r\n'
                'end:vcard\r\n\r\n'))
        self.assertEqual(contents,
                "This is a test message.\r\n\r\n"
                "\n-- \ndevel mailing list\ndevel@lists.fedoraproject.org\n"
                "https://admin.fedoraproject.org/mailman/listinfo/devel\n"
                )

    def test_attachment_2(self):
        with open(get_test_file("attachment-2.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0], (
                3, 'signature.asc', 'application/pgp-signature', None,
                '-----BEGIN PGP SIGNATURE-----\r\nVersion: GnuPG v1.4.12 '
                '(GNU/Linux)\r\nComment: Using GnuPG with Mozilla - '
                'http://www.enigmail.net/\r\n\r\niEYEARECAAYFAlBhm3oACgkQhmBj'
                'z394AnmMnQCcC+6tWcqE1dPQmIdRbLXgKGVp\r\nEeUAn2OqtaXaXaQV7rx+'
                'SmOldmSzcFw4\r\n=OEJv\r\n-----END PGP SIGNATURE-----\r\n'))
        self.assertEqual(contents,
                u"This is a test message\r\nNon-ascii chars: Hofm\xfchlgasse\r\n"
                u"\n-- \ndevel mailing list\ndevel@lists.fedoraproject.org\n"
                u"https://admin.fedoraproject.org/mailman/listinfo/devel\n"
                )

    def test_attachment_3(self):
        with open(get_test_file("attachment-3.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertEqual(len(attachments), 2)
        # HTML part
        self.assertEqual(attachments[0][0:4],
                (3, "attachment.html", "text/html", "iso-8859-1"))
        self.assertEqual(len(attachments[0][4]), 3134)
        # Image attachment
        self.assertEqual(attachments[1][0:4],
                (4, "GeoffreyRoucourt.jpg", "image/jpeg", None))
        self.assertEqual(len(attachments[1][4]), 282180)
        # Scrubbed content
        self.assertEqual(contents, u"This is a test message\r\n")

    def test_html_email_1(self):
        with open(get_test_file("html-email-1.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertEqual(len(attachments), 1)
        # HTML part
        self.assertEqual(attachments[0][0:4],
                (2, "attachment.html", "text/html", "iso-8859-1"))
        self.assertEqual(len(attachments[0][4]), 2723)
        # Scrubbed content
        self.assertEqual(contents,
                u"This is a test message\r\n"
                u"Non-ASCII chars: r\xe9ponse fran\xe7ais \n")

    def test_html_only_email(self):
        # This email only has an HTML part, thus the scrubbed content will be
        # empty. It should be an unicode empty string, not str.
        with open(get_test_file("html-email-2.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertTrue(isinstance(contents, unicode),
            u"Scrubbed content should always be unicode")

    def test_non_ascii_payload(self):
        """Scrubber must handle non-ascii messages"""
        for enc in ["utf8", "iso8859"]:
            with open(get_test_file("payload-%s.txt" % enc)) as email_file:
                msg = email.message_from_file(email_file, _class=Message)
            scrubber = Scrubber("testlist@example.com", msg)
            contents, attachments = scrubber.scrub()
            self.assertTrue(isinstance(contents, unicode))
            self.assertEqual(contents, u'This message contains non-ascii '
                    u'characters:\n\xe9 \xe8 \xe7 \xe0 \xee \xef \xeb \u20ac\n')

    def test_bad_content_type(self):
        """Scrubber must handle unknown content-types"""
        with open(get_test_file("payload-unknown.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        try:
            contents, attachments = scrubber.scrub()
        except LookupError, e:
            import traceback;
            print traceback.format_exc()
            self.fail(e) # codec not found
        self.assertTrue(isinstance(contents, unicode))

    def test_attachment_4(self):
        with open(get_test_file("attachment-4.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertEqual(len(attachments), 2)
        # HTML part
        self.assertEqual(attachments[0][0:4],
                (3, "attachment.html", "text/html", "iso-8859-1"))
        self.assertEqual(len(attachments[0][4]), 114)
        # text attachment
        self.assertEqual(attachments[1][0:4],
                #(4, u"todo-déjeuner.txt", "text/plain", "utf-8"))
                (4, u"todo-djeuner.txt", "text/plain", "utf-8"))
        self.assertEqual(len(attachments[1][4]), 112)
        # Scrubbed content
        self.assertEqual(contents, u'This is a test, HTML message with '
                u'accented letters : \xe9 \xe8 \xe7 \xe0.\r\nAnd an '
                u'attachment with an accented filename\r\n')

    def test_attachment_5(self):
        with open(get_test_file("attachment-5.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()
        self.assertEqual(len(attachments), 1)
        # text attachment
        self.assertEqual(attachments[0][0:4],
                #(2, u"todo-déjeuner.txt", "text/plain", "utf-8"))
                (2, u"attachment.bin", "text/plain", "utf-8"))
        self.assertEqual(len(attachments[0][4]), 112)
        # Scrubbed content
        self.assertEqual(contents, u'This is a test, HTML message with '
                u'accented letters : \xe9 \xe8 \xe7 \xe0.\r\nAnd an '
                u'attachment with an accented filename\r\n\r\n\r\n\r\n')

    def test_attachment_name_badly_encoded(self):
        msg = email.message.Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy content")
        msg.add_header('Content-Disposition', 'attachment', filename='non-ascii-\xb8\xb1\xb1\xbe.jpg')
        scrubber = Scrubber("testlist@example.com", msg)
        try:
            contents, attachments = scrubber.scrub()
        except UnicodeDecodeError:
            print format_exc()
            self.fail("Could not decode the filename")
        self.assertEqual(attachments,
                [(0, 'attachment.bin', 'text/plain', None, 'Dummy content')])

    def test_remove_next_part_from_content(self):
        with open(get_test_file("pipermail_nextpart.txt")) as email_file:
            msg = email.message_from_file(email_file, _class=Message)
        scrubber = Scrubber("testlist@example.com", msg)
        contents, attachments = scrubber.scrub()

        self.failIf("-------------- next part --------------" in contents)
