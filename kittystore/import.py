"""
Import the content of a mbox file into the database.
"""

import datetime
import mailbox
import os
import re
import sys
import time
import urllib
from base64 import b32encode
from dateutil.parser import parse
from dateutil import tz
from kitchen.text.converters import to_bytes
from hashlib import sha1
from sqlalchemy.exc import OperationalError

from kittystore import get_store

TOTALCNT = 0
#KITTYSTORE_URL = 'postgres://mm3:mm3@localhost/mm3'
#KITTYSTORE_URL = 'postgres://kittystore:kittystore@localhost/kittystore'
KITTYSTORE_URL = 'sqlite:///' + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "kittystore.sqlite"))


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


class DummyMailingList(object):
    def __init__(self, address):
        self.fqdn_listname = unicode(address)
        self.display_name = None


def convert_date(date_string):
    """ Convert the string of the date to a datetime object. """
    #print date_string
    date_string = date_string.split('(')[0].strip()
    dt = parse(date_string)
    return dt.astimezone(tz.tzutc())


def extract_attachments(store, mlist, message):
    """Parse message to search for attachments"""
    has_attach = False
    message_text = message.as_string()
    if "-------------- next part --------------" in message_text:
        has_attach = True
    # Regular attachments
    attachments = ATTACHMENT_RE.findall(message_text)
    for counter, att in enumerate(attachments):
        download_attachment(store, mlist, message["Message-Id"], counter,
                            att[0], att[1], att[2])
    # Embedded messages
    embedded = EMBEDDED_MSG_RE.findall(message_text)
    for counter, att in enumerate(embedded):
        download_attachment(store, mlist, message["Message-Id"], counter,
                            att[0], 'message/rfc822', att[1])
    # HTML attachments
    html_attachments = HTML_ATTACH_RE.findall(message_text)
    for counter, att in enumerate(html_attachments):
        download_attachment(store, mlist, message["Message-Id"], counter,
                            os.path.basename(att), 'text/html', att)
    # Text without charset
    text_no_charset = TEXT_NO_CHARSET_RE.findall(message_text)
    for counter, att in enumerate(text_no_charset):
        download_attachment(store, mlist, message["Message-Id"], counter,
                            att[0], 'text/plain', att[1])
    ## Other, probably inline text/plain
    #if has_attach and not (attachments or embedded
    #                       or html_attachments or text_no_charset):
    #    print message_text


def download_attachment(store, mlist, message_id, counter, name, content_type, url):
    #print "Downloading attachment from", url
    content = urllib.urlopen(url).read()
    store.add_attachment(mlist, message_id, counter, name, content_type,
                         None, content)

def to_db(mbfile, list_name, store):
    """ Upload all the emails in a mbox file into the database using
    kittystore API.

    :arg mbfile, a mailbox file from which the emails are extracted and
    upload to the database.
    :arg list_name, the fully qualified list name.
    """
    global TOTALCNT
    cnt = 0
    cnt_read = 0
    mlist = DummyMailingList(list_name)
    for message in mailbox.mbox(mbfile):
        cnt_read = cnt_read + 1
        #print cnt_read
        TOTALCNT = TOTALCNT + 1
        # Try to find the mailing-list subject prefix in the first email
        if cnt_read == 1:
            subject_prefix = PREFIX_RE.search(message["subject"])
            if subject_prefix:
                mlist.display_name = unicode(subject_prefix.group(1))
        try:
            msg_id_hash = store.add_to_list(mlist, message)
        except ValueError, e:
            if len(e.args) != 2:
                raise # Regular ValueError exception
            print "%s from %s about %s" % (e.args[0],
                    e.args[1].get("From"), e.args[1].get("Subject"))
            continue
        except OperationalError, e:
            print message["From"], message["Subject"], e
            # Database is locked
            time.sleep(1)
            msg_id_hash = store.add_to_list(mlist, message)
        # Parse message to search for attachments
        extract_attachments(store, mlist, message)

        store.flush()
        cnt = cnt + 1
    store.commit()
    print '  %s email read' % cnt_read
    print '  %s email added to the database' % cnt


def main():
    if len(sys.argv) < 2 or '-h' in sys.argv or '--help' in sys.argv:
        print '''USAGE:
python to_sqldb.py list_name mbox_file [mbox_file]'''
    else:
        print 'Adding to database list: %s' % sys.argv[1]

        store = get_store(KITTYSTORE_URL, debug=False)
        for mbfile in sys.argv[2:]:
            print mbfile
            if os.path.exists(mbfile):
                to_db(mbfile, sys.argv[1], store)
                print '  %s emails are stored into the database' % store.get_list_size(sys.argv[1])

