# -*- coding: utf-8 -*-

# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""
Import the content of a mbox file into the database.

Author: Aurelien Bompard <abompard@fedoraproject.org>
"""

import mailbox
import os
import re
import urllib
from dateutil.parser import parse
from dateutil import tz
from optparse import OptionParser
from random import randint
from email.utils import unquote

from kittystore import get_store


#KITTYSTORE_URL = 'postgres://mm3:mm3@localhost/mm3'
#KITTYSTORE_URL = 'postgres://kittystore:kittystore@localhost/kittystore'
KITTYSTORE_URL = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "kittystore.sqlite"))


PREFIX_RE = re.compile("^\[([\w\s_-]+)\] ")

ATTACHMENT_RE = re.compile(r"""
--------------[ ]next[ ]part[ ]--------------\n
A[ ]non-text[ ]attachment[ ]was[ ]scrubbed\.\.\.\n
Name:[ ]([^\n]+)\n
Type:[ ]([^\n]+)\n
Size:[ ]\d+[ ]bytes\n
Desc:[ ].+?\n
Url[ ]:[ ]([^\s]+)\s*\n
""", re.X | re.S)

EMBEDDED_MSG_RE = re.compile(r"""
--------------[ ]next[ ]part[ ]--------------\n
An[ ]embedded[ ]message[ ]was[ ]scrubbed\.\.\.\n
From:[ ].+?\n
Subject:[ ](.+?)\n
Date:[ ][^\n]+\n
Size:[ ]\d+\n
Url:[ ]([^\s]+)\s*\n
""", re.X | re.S)

HTML_ATTACH_RE = re.compile(r"""
--------------[ ]next[ ]part[ ]--------------\n
An[ ]HTML[ ]attachment[ ]was[ ]scrubbed\.\.\.\n
URL:[ ]([^\s]+)\s*\n
""", re.X)

TEXT_NO_CHARSET_RE = re.compile(r"""
--------------[ ]next[ ]part[ ]--------------\n
An[ ]embedded[ ]and[ ]charset-unspecified[ ]text[ ]was[ ]scrubbed\.\.\.\n
Name:[ ]([^\n]+)\n
Url:[ ]([^\s]+)\s*\n
""", re.X | re.S)


def convert_date(date_string):
    """ Convert the string of the date to a datetime object. """
    #print date_string
    date_string = date_string.split('(')[0].strip()
    dt = parse(date_string)
    return dt.astimezone(tz.tzutc())


class DummyMailingList(object):
    # pylint: disable=R0903
    # (Too few public methods)
    def __init__(self, address):
        self.fqdn_listname = unicode(address)
        self.display_name = None


class DbImporter(object):
    """
    Import email messages into the KittyStore database using its API.
    """

    def __init__(self, mlist, store, opts):
        self.mlist = mlist
        self.store = store
        self.total_imported = 0
        self.force_import = opts.duplicates
        self.no_download = opts.no_download

    def from_mbox(self, mbfile):
        """ Upload all the emails in a mbox file into the database using
        kittystore API.

        :arg mbfile, a mailbox file from which the emails are extracted and
        upload to the database.
        :arg list_name, the fully qualified list name.
        """
        cnt_imported = 0
        cnt_read = 0
        for message in mailbox.mbox(mbfile):
            cnt_read = cnt_read + 1
            self.total_imported += 1
            # Try to find the mailing-list subject prefix in the first email
            if cnt_read == 1:
                subject_prefix = PREFIX_RE.search(message["subject"])
                if subject_prefix:
                    self.mlist.display_name = unicode(subject_prefix.group(1))
            if self.force_import:
                while self.store.is_message_in_list(
                            self.mlist.fqdn_listname, unquote(message["Message-Id"])):
                    print "Found duplicate, changing message id from", message["Message-Id"], "to",
                    message.replace_header("Message-Id",
                            "<%s-%s>" % (unquote(message["Message-Id"]),
                                         str(randint(0, 100))))
                    print message["Message-Id"]
            try:
                self.store.add_to_list(self.mlist, message)
            except ValueError, e:
                if len(e.args) != 2:
                    raise # Regular ValueError exception
                print "%s from %s about %s" % (e.args[0],
                        e.args[1].get("From"), e.args[1].get("Subject"))
                continue
            # Parse message to search for attachments
            self.extract_attachments(message)

            self.store.flush()
            cnt_imported += 1
        self.store.commit()
        print '  %s email read' % cnt_read
        print '  %s email added to the database' % cnt_imported

    def extract_attachments(self, message):
        """Parse message to search for attachments"""
        message_text = message.as_string()
        #has_attach = False
        #if "-------------- next part --------------" in message_text:
        #    has_attach = True
        # Regular attachments
        attachments = ATTACHMENT_RE.findall(message_text)
        for counter, att in enumerate(attachments):
            self.download_attachment(message["Message-Id"], counter,
                                     att[0], att[1], att[2])
        # Embedded messages
        embedded = EMBEDDED_MSG_RE.findall(message_text)
        for counter, att in enumerate(embedded):
            self.download_attachment(message["Message-Id"], counter,
                                     att[0], 'message/rfc822', att[1])
        # HTML attachments
        html_attachments = HTML_ATTACH_RE.findall(message_text)
        for counter, att in enumerate(html_attachments):
            self.download_attachment(message["Message-Id"], counter,
                                     os.path.basename(att), 'text/html', att)
        # Text without charset
        text_no_charset = TEXT_NO_CHARSET_RE.findall(message_text)
        for counter, att in enumerate(text_no_charset):
            self.download_attachment(message["Message-Id"], counter,
                                     att[0], 'text/plain', att[1])
        ## Other, probably inline text/plain
        #if has_attach and not (attachments or embedded
        #                       or html_attachments or text_no_charset):
        #    print message_text

    def download_attachment(self, message_id, counter, name, ctype, url):
        #print "Downloading attachment from", url
        if self.no_download:
            content = ""
        else:
            content = urllib.urlopen(url).read()
        self.store.add_attachment(self.mlist, message_id, counter, name,
                                  ctype, None, content)


def parse_args():
    usage = "%prog -l list_name mbox_file [mbox_file ...]"
    parser = OptionParser(usage=usage)
    parser.add_option("-l", "--list-name", help="the fully-qualified list "
            "name (including the '@' symbol and the domain name")
    parser.add_option("-v", "--verbose", action="store_true",
            help="show more output")
    parser.add_option("-d", "--debug", action="store_true",
            help="show a whole lot more of output")
    parser.add_option("--no-download", action="store_true",
            help="don't download attachments")
    parser.add_option("-D", "--duplicates", action="store_true",
            help="do not skip duplicate emails (same Message-ID header), "
                 "import them with a different Message-ID")
    opts, args = parser.parse_args()
    if opts.list_name is None:
        parser.error("the list name must be given on the command-line.")
    if not args:
        parser.error("no mbox file selected.")
    if "@" not in opts.list_name:
        parser.error("the list name must be fully-qualified, including "
                     "the '@' symbol and the domain name.")
    for mbfile in args:
        if not os.path.exists(mbfile):
            parser.error("No such mbox file: %s" % mbfile)
    return opts, args


def main():
    opts, args = parse_args()
    print 'Importing messages from %s to database...' % opts.list_name
    store = get_store(KITTYSTORE_URL, debug=opts.debug)
    mlist = DummyMailingList(opts.list_name)
    importer = DbImporter(mlist, store, opts)
    for mbfile in args:
        print "Importing from mbox file %s" % mbfile
        importer.from_mbox(mbfile)
        print '  %s emails are stored into the database' \
              % store.get_list_size(opts.list_name)
