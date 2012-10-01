# -*- coding: utf-8 -*-

import unittest
import email

from mock import Mock

from kittystore.scrub import Scrubber
from kittystore.test import get_test_file


class TestScrubber(unittest.TestCase):

    def test_attachment_1(self):
        with open(get_test_file("attachment-1.txt")) as email_file:
            msg = email.message_from_file(email_file)
        store = Mock()
        scrubber = Scrubber("testlist@example.com", msg, store)
        contents = scrubber.scrub()
        self.assertEqual(store.add_attachment.call_count, 1)
        store.add_attachment.assert_called_with(
                'testlist@example.com', '505E5185.5040208@libero.it', 2,
                'puntogil.vcf', 'text/x-vcard',
                'begin:vcard\r\nfn:gil\r\nn:;gil\r\nversion:2.1\r\n'
                'end:vcard\r\n\r\n')
        self.assertEqual(contents,
                "This is a test message.\r\n\r\n"
                "\n-- \ndevel mailing list\ndevel@lists.fedoraproject.org\n"
                "https://admin.fedoraproject.org/mailman/listinfo/devel\n"
                )

    def test_attachment_2(self):
        with open(get_test_file("attachment-2.txt")) as email_file:
            msg = email.message_from_file(email_file)
        store = Mock()
        scrubber = Scrubber("testlist@example.com", msg, store)
        contents = scrubber.scrub()
        self.assertEqual(store.add_attachment.call_count, 1)
        store.add_attachment.assert_called_with(
                'testlist@example.com', '50619B7A.2030404@thelounge.net', 3,
                'signature.asc', 'application/pgp-signature',
                '-----BEGIN PGP SIGNATURE-----\r\nVersion: GnuPG v1.4.12 '
                '(GNU/Linux)\r\nComment: Using GnuPG with Mozilla - '
                'http://www.enigmail.net/\r\n\r\niEYEARECAAYFAlBhm3oACgkQhmBj'
                'z394AnmMnQCcC+6tWcqE1dPQmIdRbLXgKGVp\r\nEeUAn2OqtaXaXaQV7rx+'
                'SmOldmSzcFw4\r\n=OEJv\r\n-----END PGP SIGNATURE-----\r\n')
        self.assertEqual(contents,
                u"This is a test message\r\nNon-ascii chars: Hofm\xfchlgasse\r\n"
                u"\n-- \ndevel mailing list\ndevel@lists.fedoraproject.org\n"
                u"https://admin.fedoraproject.org/mailman/listinfo/devel\n"
                )

    def test_attachment_3(self):
        with open(get_test_file("attachment-3.txt")) as email_file:
            msg = email.message_from_file(email_file)
        store = Mock()
        scrubber = Scrubber("testlist@example.com", msg, store)
        contents = scrubber.scrub()
        self.assertEqual(store.add_attachment.call_count, 2)
        args_1, args_2 = store.add_attachment.call_args_list
        # HTML part
        self.assertEqual(args_1[0][0:5], ("testlist@example.com",
                "CACec3Lup8apbhUMcm_Ktn1dPxx4eWr2y1RV7ZSYhy0tzmjSrgQ@mail.gmail.com",
                3, "attachment.html", "text/html"))
        self.assertEqual(len(args_1[0][5]), 3134)
        # Image attachment
        self.assertEqual(args_2[0][0:5], ("testlist@example.com",
                "CACec3Lup8apbhUMcm_Ktn1dPxx4eWr2y1RV7ZSYhy0tzmjSrgQ@mail.gmail.com",
                4, "GeoffreyRoucourt.jpg", "image/jpeg"))
        self.assertEqual(len(args_2[0][5]), 282180)
        # Scrubbed content
        self.assertEqual(contents, u"This is a test message\r\n")

    def test_html_email_1(self):
        with open(get_test_file("html-email-1.txt")) as email_file:
            msg = email.message_from_file(email_file)
        store = Mock()
        scrubber = Scrubber("testlist@example.com", msg, store)
        contents = scrubber.scrub()
        self.assertEqual(store.add_attachment.call_count, 1)
        args = store.add_attachment.call_args[0]
        # HTML part
        self.assertEqual(args[0:5], ("testlist@example.com",
                "016001cd9b3b$b71efed0$255cfc70$@fr",
                2, "attachment.html", "text/html"))
        self.assertEqual(len(args[5]), 2723)
        # Scrubbed content
        self.assertEqual(contents,
                u"This is a test message\r\n"
                u"Non-ASCII chars: r\xe9ponse fran\xe7ais \n")

