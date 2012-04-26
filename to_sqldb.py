#!/usr/bin/python -tt

# Import the content of a mbox file into mongodb

import bson
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

from kittystore.kittysamodel import Email, get_class_object
from kittystore.kittysastore import list_to_table_name, KittySAStore
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import OperationalError, InvalidRequestError


TOTALCNT = 0
DB_URL = 'postgres://mm3:mm3@localhost/mm3'
engine = create_engine(DB_URL, echo=False,
    pool_recycle=3600)
store = KittySAStore(DB_URL)
Session = sessionmaker(bind=engine)
session = Session()


def convert_date(date_string):
    """ Convert the string of the date to a datetime object. """
    #print date_string
    date_string = date_string.split('(')[0].strip()
    dt = parse(date_string)
    return dt.astimezone(tz.tzutc())


def to_db(mbfile, list_name):
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
        email = get_class_object(list_to_table_name(list_name), 'email',
                    MetaData(engine), create=True)
        cnt_read = cnt_read + 1
        #print cnt_read
        TOTALCNT = TOTALCNT + 1
        infos = {}
        ## TODO: We need to catch-up Subjects/From which are of a specific
        ## encoding.
        for it in message.keys():
            it2 = it.replace('-', '')
            infos[it2] = message[it]
        keys = infos.keys()
        ## There seem to be a problem to parse some messages
        if not keys:
            print '  Failed: %s keys: "%s"' % (mbfile, keys)
            #print message
            continue
        if 'MessageID' in infos:
            infos['MessageID'] = infos['MessageID'].replace('<', ''
                ).replace('>', '')
        if 'From' in infos:
            regex = '(.*)\((.*)\)'
            match = re.match(regex, infos['From'])
            if match:
                email_add, name = match.groups()
                infos['From'] = name
                email_add = email_add.replace(' at ', '@')
                infos['Email'] = email_add.strip()
        try:
            if not 'MessageID' in infos:
                print '  Failed: No Message-ID for email:'
                print '   Content:', message['Subject'], message['Date'], message['From']
                continue
            if not store.get_email(list_name, infos['MessageID']):
                infos['Date'] = convert_date(infos['Date'])
                infos['Content'] = message.get_payload()
                thread_id = 0
                if not 'References' in infos and not 'InReplyTo' in infos:
                    infos['ThreadID'] = b32encode(sha1(infos['MessageID']).digest())
                else:
                    ref = None
                    if 'References' in infos:
                        ref= infos['References'].split()[0].strip()
                    else:
                        ref= infos['InReplyTo']
                        infos['References'] = infos['InReplyTo']
                        del(infos['InReplyTo'])
                    ref = ref.replace('<', '').replace('>', '')
                    res = store.get_email(list_name, ref)
                    if res and res.thread_id:
                        infos['ThreadID'] = res.thread_id
                    else:
                        infos['ThreadID'] = b32encode(sha1(infos['MessageID']).digest())
                infos['Category'] = 'Question'
                if 'agenda' in infos['Subject'].lower():
                    infos['Category'] = 'Agenda'
                if 'reminder' in infos['Subject'].lower():
                    infos['Category'] = 'Agenda'
                infos['Full'] = message.as_string()

                ## TODO: I'm not sure the TOTALCNT approach is the right one
                ## we should discuss this with the pipermail guys
                infos['LegacyID'] = TOTALCNT
                if not 'References' in infos:
                    infos['References'] = None
                #print infos.keys()
                mail = email(
                    sender=infos['From'],
                    email=infos['Email'],
                    subject=infos['Subject'],
                    content=infos['Content'],
                    date=infos['Date'],
                    message_id=infos['MessageID'],
                    stable_url_id=infos['MessageID'],
                    thread_id=infos['ThreadID'],
                    references=infos['References'],
                    full=infos['Full'])
                mail.save(session)
                cnt = cnt + 1
                session.commit()
        except Exception, err:
            print ' Error: "%s"' % err
            print 'File:',mbfile , 'Content:', message['Subject'], message['Date'], message['From']
            pass
        #else:
            #print '  Failed: %s ID: "%s" ' % (mbfile, infos['MessageID'])
            #print '   Content:', message['Subject'], message['Date'], message['From']
    session.commit()
    print '  %s email read' % cnt_read
    print '  %s email added to the database' % cnt

def get_table_size(list_name):
    """ Return the size of the document in mongodb. """
    email = get_class_object(list_to_table_name(list_name), 'email',
                    MetaData(engine))
    print '  %s emails are stored into the database' % session.query(email).count()


if __name__ == '__main__':
    #sys.argv.extend(['devel', 'lists/devel-2012-03-March.txt'])
    if len(sys.argv) < 2 or '-h' in sys.argv or '--help' in sys.argv:
        print '''USAGE:
python to_sqldb.py list_name mbox_file [mbox_file]'''
    else:
        print 'Adding to database list: %s' % sys.argv[1]
        for mbfile in sys.argv[2:]:
            print mbfile
            if os.path.exists(mbfile):
                to_db(mbfile, sys.argv[1])
                get_table_size(sys.argv[1])
    session.close()

