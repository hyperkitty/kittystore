# -*- coding: utf-8 -*-

"""
KittyMGStore - an object mapper and interface to the mongo database
                representation of emails for mailman 3.

Copyright (C) 2012 Pierre-Yves Chibon
Author: Pierre-Yves Chibon <pingou@pingoured.fr>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""


import pymongo
import re
from datetime import datetime

from zope.interface import implements
from mailman.interfaces.messages import IMessageStore


class KittyMGStore(object):
    """ Implementation of the store for a MongoDB backend. """

    implements(IMessageStore)

    def __init__(self, host='localhost', port=27017):
        """ Constructor.
        Create the session using the engine defined in the url.

        :arg host, hostname or IP of the database server. Defaults to
        'localhost'
        :arg port, port of the database server. Defaults to '27017'
        :kwarg debug, a boolean to set the debug mode on or off.
        """
        self.connection = pymongo.Connection(host, port)

    def get_archives(self, list_name, start, end):
        """ Return all the thread started emails between two given dates.
        
        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg start, a datetime object representing the starting date of
        the interval to query.
        :arg end, a datetime object representing the ending date of
        the interval to query.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('Date')
        mongodb.mails.ensure_index('Date')
        mongodb.mails.create_index('References')
        mongodb.mails.ensure_index('References')
        # Beginning of thread == No 'References' header
        archives = []
        for email in mongodb.mails.find(
                {'References': {'$exists':False},
                'InReplyTo': {'$exists':False},
                "Date": {"$gt": start, "$lt": end}}, 
                sort=[('Date', pymongo.DESCENDING)]):
            archives.append(email)
        return archives

    def get_archives_length(self, list_name):
        """ Return a dictionnary of years, months for which there are
        potentially archives available for a given list (based on the
        oldest post on the list).

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('Date')
        mongodb.mails.ensure_index('Date')
        archives = {}
        entry = mongodb.mails.find_one(sort=[('Date', pymongo.ASCENDING)])
        date = entry['Date']
        now = datetime.now()
        year = date.year
        month = date.month
        while year < now.year:
            archives[year] = range(1, 13)[(month -1):]
            year = year + 1
            month = 1
        archives[now.year] = range(1, 13)[:now.month]
        return archives

    def get_email(self, list_name, message_id):
        """ Return an Email object found in the database corresponding
        to the Message-ID provided.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg message_id, Message-ID as found in the headers of the email.
        Used here to uniquely identify the email present in the database.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('MessageID')
        mongodb.mails.ensure_index('MessageID')
        return mongodb.mails.find_one({'MessageID': message_id})

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        mongodb = self.connection[list_name]
        return mongodb.mails.count()

    def get_thread_length(self, list_name, thread_id):
        """ Return the number of email present in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('ThreadID')
        mongodb.mails.ensure_index('ThreadID')
        return mongodb.mails.find({'ThreadID': thread_id}).count()

    def get_thread_participants(self, list_name, thread_id):
        """ Return the list of participant in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('ThreadID')
        mongodb.mails.ensure_index('ThreadID')
        authors = set()
        for mail in mongodb.mails.find({'ThreadID': thread_id}):
            authors.add(mail['From'])
        return authors

    def search_content(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the content of the emails.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('Date')
        mongodb.mails.ensure_index('Date')
        mongodb.mails.create_index('Content')
        mongodb.mails.ensure_index('Content')
        regex = '.*%s.*' % keyword
        query_string = {'Content': re.compile(regex, re.IGNORECASE)}
        return list(mongodb.mails.find(query_string, sort=[('Date',
            pymongo.DESCENDING)]))

    def search_content_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content or their subject.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the content or subject of
        the emails.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('Date')
        mongodb.mails.ensure_index('Date')
        mongodb.mails.create_index('Content')
        mongodb.mails.ensure_index('Content')
        mongodb.mails.create_index('Subject')
        mongodb.mails.ensure_index('Subject')
        regex = '.*%s.*' % keyword
        query_string = {'$or' : [
            {'Content': re.compile(regex, re.IGNORECASE)},
            {'Subject': re.compile(regex, re.IGNORECASE)}
            ]}
        return list(mongodb.mails.find(query_string, sort=[('Date',
            pymongo.DESCENDING)]))

    def search_sender(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        the name or email address of the sender of the email.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the database.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('Date')
        mongodb.mails.ensure_index('Date')
        mongodb.mails.create_index('From')
        mongodb.mails.ensure_index('From')
        mongodb.mails.create_index('Email')
        mongodb.mails.ensure_index('Email')
        regex = '.*%s.*' % keyword
        query_string = {'$or' : [
            {'From': re.compile(regex, re.IGNORECASE)},
            {'Email': re.compile(regex, re.IGNORECASE)}
            ]}
        return list(mongodb.mails.find(query_string, sort=[('Date',
            pymongo.DESCENDING)]))
        

    def search_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their subject.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the subject of the emails.
        """
        mongodb = self.connection[list_name]
        mongodb.mails.create_index('Date')
        mongodb.mails.ensure_index('Date')
        mongodb.mails.create_index('Subject')
        mongodb.mails.ensure_index('Subject')
        regex = '.*%s.*' % keyword
        query_string = {'Subject': re.compile(regex, re.IGNORECASE)}
        return list(mongodb.mails.find(query_string, sort=[('Date',
            pymongo.DESCENDING)]))
