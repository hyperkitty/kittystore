#!/usr/bin/python -tt

# Import the content of a mbox file into mongodb

import bson
from bson.errors import InvalidStringData
import datetime
import mailbox
import os
import pymongo
import re
import sys
import time
from base64 import b32encode
from dateutil.parser import parse
from kitchen.text.converters import to_bytes
from hashlib import sha1

connection = pymongo.Connection('localhost', 27017)

TOTALCNT = 0

def convert_date(date_string):
    """ Convert the string of the date to a datetime object. """
    date_string = date_string.strip()
    dt = parse(date_string)
    return dt


def to_mongo(mbfile, database):
    """ Upload all the emails in a mbox file into a mongo database. """
    global TOTALCNT
    db = connection[database]
    cnt = 0
    cnt_read = 0
    for message in mailbox.mbox(mbfile):
        cnt_read = cnt_read + 1
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
                email, name = match.groups()
                infos['From'] = name
                email = email.replace(' at ', '@')
                infos['Email'] = email.strip()
        try:
            if db.mails.find({'MessageID': infos['MessageID']}).count() == 0:
                infos['Date'] = convert_date(infos['Date'])
                infos['Content'] = message.get_payload()
                try:
                    bson.BSON.encode({'content' : infos['Content']})
                except InvalidStringData:
                    ## TODO: Do something about this encoding issue
                    raise InvalidStringData('Email has invalid content')
                thread_id = 0
                db.mails.create_index('MessageID')
                db.mails.ensure_index('MessageID')
                db.mails.create_index('ThreadID')
                db.mails.ensure_index('ThreadID')
                if not 'References' in infos and not 'InReplyTo' in infos:
                    infos['ThreadID'] = b32encode(sha1(infos['MessageID']).digest())
                else:
                    ref = None
                    if 'References' in infos:
                        ref= infos['References'].split()[0].strip()
                    else:
                        ref= infos['InReplyTo']
                    ref = ref.replace('<', '').replace('>', '')
                    res = db.mails.find_one({'MessageID': ref})
                    if res and 'ThreadID' in res:
                        infos['ThreadID'] = res['ThreadID']
                    else:
                        infos['ThreadID'] = b32encode(sha1(infos['MessageID']).digest())
#                infos['Category'] = 'Question'
#                if 'agenda' in infos['Subject'].lower():
#                    infos['Category'] = 'Agenda'
#                if 'reminder' in infos['Subject'].lower():
#                    infos['Category'] = 'Agenda'
#                infos['Full'] = message.as_string()
#                try:
#                    bson.BSON.encode({'content' : infos['Full']})
#                except InvalidStringData:
#                    ## TODO: Do something about this encoding issue
#                    raise InvalidStringData('Email has invalid full version')

                ## TODO: I'm not sure the TOTALCNT approach is the right one
                ## we should discuss this with the pipermail guys
#                infos['LegacyID'] = TOTALCNT
                db.mails.insert(infos)
                cnt = cnt + 1
        except Exception, err:
            print '  Failed: %s error: "%s"' % (mbfile, err)
            print '  Failed:', message['Subject'], message['Date'], message['From']
    print '  %s email read' % cnt_read
    print '  %s email added to the database' % cnt

def get_document_size(database):
    """ Return the size of the document in mongodb. """
    db = connection[database]
    print '  %s emails are stored into the database' % db.mails.count()


if __name__ == '__main__':
    #sys.argv.extend(['devel', 'lists/devel-2012-03-March.txt'])
    if len(sys.argv) < 2 or '-h' in sys.argv or '--help' in sys.argv:
        print '''USAGE:
python mbox_to_mongo.py db_name mbox_file [mbox_file]'''
    else:
        print 'Adding to database: %s' % sys.argv[1]
        for mbfile in sys.argv[2:]:
            print mbfile
            if os.path.exists(mbfile):
                print mbfile
                to_mongo(mbfile, sys.argv[1])
                get_document_size(sys.argv[1])

"""
## Test command-line:
$ mongo
use fedora-devel
db.mails.find()
db.mails.count()
"""
