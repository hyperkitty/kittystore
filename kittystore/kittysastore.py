# -*- coding: utf-8 -*-

"""
KittySAStore - an object mapper and interface to a SQL database
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

import datetime

from kittystore import KittyStore
from kittystore.kittysamodel import get_class_object


from sqlalchemy import create_engine, distinct, MetaData, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


def list_to_table_name(list_name):
    """ For a given fully qualified list name, return the table name.
    What the method does is to transform the special characters from the
    list name to underscore ('_') and append the 'KS_' prefix in front.
    (KS stands for KittyStore).

    Characters replaced: -.@

    :arg list_name, the fully qualified list name to be transformed to
    the table name.
    """
    for char in ['-', '.', '@']:
        list_name = list_name.replace(char, '_')
    return 'HK_%s' % list_name


class KittySAStore(KittyStore):
    """ SQL-Alchemy powered interface to query emails from the database.
    """

    def __init__(self, url, debug=False):
        """ Constructor.
        Create the session using the engine defined in the url.

        :arg url, URL used to connect to the database. The URL contains
        information with regards to the database engine, the host to connect
        to, the user and password and the database name.
          ie: <engine>://<user>:<password>@<host>/<dbname>
          ie: mysql://mm3_user:mm3_password@localhost/mm3
        :kwarg debug, a boolean to set the debug mode on or off.
        """
        self.engine = create_engine(url, echo=debug)
        self.metadata = MetaData(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def get_archives(self, list_name, start, end):
        """ Return all the thread started emails between two given dates.
        
        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg start, a datetime object representing the starting date of
        the interval to query.
        :arg end, a datetime object representing the ending date of
        the interval to query.
        """
        # Beginning of thread == No 'References' header
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(email).filter(
            and_(
                email.date >= start,
                email.date <= end,
                email.references == None)
                ).all()

    def get_archives_length(self, list_name):
        """ Return a dictionnary of years, months for which there are
        potentially archives available for a given list (based on the
        oldest post on the list).

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        archives = {}
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        entry = self.session.query(email).order_by(
                    email.date).limit(1).all()[0]
        now = datetime.datetime.now()
        year = entry.date.year
        month = entry.date.month
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
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mail = None
        try:
            mail = self.session.query(email).filter_by(
                message_id=message_id).one()
        except NoResultFound:
            pass
        return mail

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(email).count()

    def get_thread(self, list_name, thread_id):
        """ Return all the emails present in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, thread_id as used in the web-pages.
        Used here to uniquely identify the thread in the database.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mail = None
        try:
            mail = self.session.query(email).filter_by(
                thread_id=thread_id).all()
        except NoResultFound:
            pass
        return mail

    def get_thread_length(self, list_name, thread_id):
        """ Return the number of email present in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(email).filter_by(
                    thread_id=thread_id).count()

    def get_thread_participants(self, list_name, thread_id):
        """ Return the list of participant in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(distinct(email.sender)).filter(
                email.thread_id == thread_id).all()

    def search_content(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the content of the emails.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(email).filter(
                email.content.like('%{0}%'.format(keyword))
                ).all()

    def search_content_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content or their subject.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the content or subject of
        the emails.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mails = self.session.query(email).filter(
                email.content.like('%{0}%'.format(keyword))
                ).all()
        mails.extend(self.session.query(email).filter(
                email.subject.like('%{0}%'.format(keyword))
                ).all())
        return mails

    def search_sender(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        the name or email address of the sender of the email.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the database.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mails = self.session.query(email).filter(
                email.sender.like('%{0}%'.format(keyword))
                ).all()
        mails.extend(self.session.query(email).filter(
                email.email.like('%{0}%'.format(keyword))
                ).all())
        return mails

    def search_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their subject.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the subject of the emails.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(email).filter(
                email.subject.like('%{0}%'.format(keyword))
                ).all()
