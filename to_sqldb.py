#!/usr/bin/python -tt

# Import the content of a mbox file into SQL

import datetime
import mailbox
import os
import re
import sys
import time
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


def convert_date(date_string):
    """ Convert the string of the date to a datetime object. """
    #print date_string
    date_string = date_string.split('(')[0].strip()
    dt = parse(date_string)
    return dt.astimezone(tz.tzutc())


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
    for message in mailbox.mbox(mbfile):
        cnt_read = cnt_read + 1
        #print cnt_read
        TOTALCNT = TOTALCNT + 1
        try:
            msg_id_hash = store.add_to_list(list_name, message)
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
            msg_id_hash = store.add_to_list(list_name, message)
        store.flush()
        cnt = cnt + 1
    store.commit()
    print '  %s email read' % cnt_read
    print '  %s email added to the database' % cnt


if __name__ == '__main__':
    #sys.argv.extend(['devel', 'lists/devel-2012-03-March.txt'])
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
