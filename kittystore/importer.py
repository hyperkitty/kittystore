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

from __future__ import absolute_import

import mailbox
import os
import re
import urllib
import sys
import logging
from dateutil.parser import parse
from dateutil import tz
from optparse import OptionParser
from random import randint
from email.utils import unquote
from urllib2 import HTTPError
from traceback import print_exc

from mailman.interfaces.archiver import ArchivePolicy
from storm.exceptions import DatabaseError
from mailmanclient import MailmanConnectionError
from kittystore import SchemaUpgradeNeeded
from kittystore.scripts import get_store_from_options, StoreFromOptionsError
from kittystore.utils import get_mailman_client
from kittystore.caching import sync_mailman
from kittystore.search import make_delayed
from kittystore.test import FakeList


PREFIX_RE = re.compile("^\[([\w\s_-]+)\] ")

ATTACHMENT_RE = re.compile(r"""
--------------[ ]next[ ]part[ ]--------------\n
A[ ]non-text[ ]attachment[ ]was[ ]scrubbed\.\.\.\n
Name:[ ]([^\n]+)\n
Type:[ ]([^\n]+)\n
Size:[ ]\d+[ ]bytes\n
Desc:[ ].+?\n
U(?:rl|RL)[ ]?:[ ]([^\s]+)\s*\n
""", re.X | re.S)

EMBEDDED_MSG_RE = re.compile(r"""
--------------[ ]next[ ]part[ ]--------------\n
An[ ]embedded[ ]message[ ]was[ ]scrubbed\.\.\.\n
From:[ ].+?\n
Subject:[ ](.+?)\n
Date:[ ][^\n]+\n
Size:[ ]\d+\n
U(?:rl|RL)[ ]?:[ ]([^\s]+)\s*\n
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
U(?:rl|RL)[ ]?:[ ]([^\s]+)\s*\n
""", re.X | re.S)

TEXTWRAP_RE = re.compile("\n\s*")


def awarify(date):
    if date.tzinfo is None or date.tzinfo.utcoffset(date) is None:
        return date.replace(tzinfo=tz.tzutc())
    return date


class DownloadError(Exception): pass


def get_mailinglist(list_name, settings, opts):
    mlist = FakeList(list_name)
    try:
        mm_client = get_mailman_client(settings)
        mm_list = mm_client.get_list(list_name)
    except (HTTPError, MailmanConnectionError), e:
        if opts.debug:
            print "Can't get the mailing-list from Mailman: %s" % e
    else:
        mlist_settings = mm_list.settings
        mlist.display_name = mlist_settings["display_name"]
        mlist.subject_prefix = mlist_settings["subject_prefix"]
        mlist.archive_policy = getattr(ArchivePolicy, mlist_settings["archive_policy"])
    return mlist


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
        self.verbose = opts.verbose
        self.since = opts.since
        if opts.cont:
            self.since = store.get_last_date(self.mlist.fqdn_listname)
        if self.since is not None:
            self.since = awarify(self.since)
            if self.verbose:
                print "Only emails after %s will be imported" % self.since

    def from_mbox(self, mbfile):
        """ Upload all the emails in a mbox file into the database using
        kittystore API.

        :arg mbfile, a mailbox file from which the emails are extracted and
        upload to the database.
        :arg list_name, the fully qualified list name.
        """
        self.store.search_index = make_delayed(self.store.search_index)
        cnt_imported = 0
        cnt_read = 0
        for message in mailbox.mbox(mbfile):
            if self.since:
                date = message["date"]
                if date:
                    try:
                        date = awarify(parse(date))
                    except ValueError, e:
                        print "Can't parse date string in message %s: %s" \
                              % (message["message-id"], date)
                        print e
                        continue
                    if date < self.since:
                        continue
            cnt_read = cnt_read + 1
            self.total_imported += 1
            if self.verbose:
                print "%s (%d)" % (message["Message-Id"], self.total_imported)
            # Un-wrap the subject line if necessary
            if message["subject"]:
                message.replace_header("subject",
                        TEXTWRAP_RE.sub(" ", message["subject"]))
            # Try to find the mailing-list subject prefix in the first email
            if not self.mlist.subject_prefix and message["subject"]:
                subject_prefix = PREFIX_RE.search(message["subject"])
                if subject_prefix:
                    self.mlist.subject_prefix = unicode(subject_prefix.group(1))
            if self.force_import:
                while self.store.is_message_in_list(
                            self.mlist.fqdn_listname,
                            unquote(message["Message-Id"])):
                    oldmsgid = message["Message-Id"]
                    message.replace_header("Message-Id",
                            "<%s-%s>" % (unquote(message["Message-Id"]),
                                         str(randint(0, 100))))
                    print("Found duplicate, changing message id from %s to %s"
                          % (oldmsgid, message["Message-Id"]))
            # Parse message to search for attachments
            try:
                attachments = self.extract_attachments(message)
            except DownloadError, e:
                print ("Could not download one of the attachments! "
                       "Skipping this message. Error: %s" % e.args[0])
                continue
            # Now insert the message
            try:
                self.store.add_to_list(self.mlist, message)
            except ValueError, e:
                if len(e.args) != 2:
                    raise # Regular ValueError exception
                print "%s from %s about %s" % (e.args[0],
                        e.args[1].get("From"), e.args[1].get("Subject"))
                continue
            except DatabaseError:
                print_exc()
                print ("Message %s failed to import, skipping"
                       % unquote(message["Message-Id"]))
                self.store.rollback()
                continue
            # And insert the attachments
            for counter, att in enumerate(attachments):
                self.store.add_attachment(
                        self.mlist.fqdn_listname,
                        message["Message-Id"].strip(" <>"),
                        counter, att[0], att[1], None, att[2])

            self.store.flush()
            cnt_imported += 1
            # Commit every time to be able to rollback on error
            self.store.commit()
        self.store.search_index.flush() # Now commit to the search index
        if self.verbose:
            print '  %s email read' % cnt_read
            print '  %s email added to the database' % cnt_imported

    def extract_attachments(self, message):
        """Parse message to search for attachments"""
        all_attachments = []
        message_text = message.as_string()
        #has_attach = False
        #if "-------------- next part --------------" in message_text:
        #    has_attach = True
        # Regular attachments
        attachments = ATTACHMENT_RE.findall(message_text)
        for att in attachments:
            all_attachments.append( (att[0], att[1],
                    self.download_attachment(att[2])) )
        # Embedded messages
        embedded = EMBEDDED_MSG_RE.findall(message_text)
        for att in embedded:
            all_attachments.append( (att[0], 'message/rfc822',
                    self.download_attachment(att[1])) )
        # HTML attachments
        html_attachments = HTML_ATTACH_RE.findall(message_text)
        for att in html_attachments:
            url = att.strip("<>")
            all_attachments.append( (os.path.basename(url), 'text/html',
                    self.download_attachment(url)) )
        # Text without charset
        text_no_charset = TEXT_NO_CHARSET_RE.findall(message_text)
        for att in text_no_charset:
            all_attachments.append( (att[0], 'text/plain',
                    self.download_attachment(att[1])) )
        ## Other, probably inline text/plain
        #if has_attach and not (attachments or embedded
        #                       or html_attachments or text_no_charset):
        #    print message_text
        return all_attachments

    def download_attachment(self, url):
        url = url.strip(" <>")
        if self.no_download:
            if self.verbose:
                print "NOT downloading attachment from %s" % url
            content = ""
        else:
            if self.verbose:
                print "Downloading attachment from %s" % url
            try:
                content = urllib.urlopen(url).read()
            except IOError, e:
                raise DownloadError(e)
        return content


def parse_args():
    usage = "%prog -s store_url -l list_name mbox_file [mbox_file ...]"
    parser = OptionParser(usage=usage)
    parser.add_option("-l", "--list-name", help="the fully-qualified list "
            "name (including the '@' symbol and the domain name")
    parser.add_option("-s", "--settings", default="settings",
                      help="the Python path to a Django settings module")
    parser.add_option("-p", "--pythonpath",
                      help="a directory to add to the Python path")
    parser.add_option("-c", "--continue", action="store_true", dest="cont",
                      help="only import newer emails")
    parser.add_option("--since", help="only import emails after this date")
    parser.add_option("-v", "--verbose", action="store_true",
            help="show more output")
    parser.add_option("-d", "--debug", action="store_true",
            help="show a whole lot more of output")
    parser.add_option("--no-download", action="store_true",
            help="don't download attachments")
    parser.add_option("-D", "--duplicates", action="store_true",
            help="do not skip duplicate emails (same Message-ID header), "
                 "import them with a different Message-ID")
    parser.add_option("--no-sync-mailman", action="store_true",
            help="don't sync with Mailman after importing")
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
    if opts.since is not None:
        if opts.cont:
            parser.error("--since and --continue are mutually exclusive")
        try:
            opts.since = parse(opts.since)
        except ValueError, e:
            parser.error("invalid value for '--since': %s" % e)
    try:
        store = get_store_from_options(opts)
    except StoreFromOptionsError, e:
        parser.error(e.args[0])
    except SchemaUpgradeNeeded:
        print >>sys.stderr, ("The database schema needs to be upgraded, "
                             "please run kittystore-updatedb first")
        sys.exit(1)
    return store, opts, args


def main():
    store, opts, args = parse_args()
    if opts.debug:
        debuglevel = logging.DEBUG
    else:
        debuglevel = logging.INFO
    logging.basicConfig(format='%(message)s', level=debuglevel)
    print 'Importing messages from %s to database...' % opts.list_name
    mlist = get_mailinglist(opts.list_name, store.settings, opts)
    importer = DbImporter(mlist, store, opts)
    for mbfile in args:
        print "Importing from mbox file %s" % mbfile
        importer.from_mbox(mbfile)
        if opts.verbose:
            print '  %s emails are stored into the database' \
                  % store.get_list_size(opts.list_name)
    if not opts.no_sync_mailman:
        sync_mailman(store)
    store.commit()
