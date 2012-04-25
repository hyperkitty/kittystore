# -*- coding: utf-8 -*-

"""
sastore - an object mapper and interface to a SQL database
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

from sqlalchemy import (
    create_engine,
    distinct,
    Column,
    Integer,
    DateTime,
    String,
    Text,
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Email(Base):
    """ Email table.

    Define the fields of the table and their types.
    """

    __tablename__ = 'email'
    id = Column(Integer, primary_key=True)
    list_name = Column(String(50), nullable=False)
    sender = Column(String(100), nullable=False)
    email = Column(String(75), nullable=False)
    subject = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    date = Column(DateTime)
    message_id = Column(String(150), unique=True, nullable=False)
    stable_url_id = Column(String(250), unique=True, nullable=False)
    thread_id = Column(String(150), nullable=False)
    references = Column(Text)
    full = Column(Text)

    def __init__(self, list_name, sender, email, subject, content,
        date, message_id, stable_url_id, thread_id, references, full):
        """ Constructor instanciating the defaults values. """
        self.list_name = list_name
        self.sender = sender
        self.email = email
        self.subject = subject
        self.content = content
        self.date = date
        self.message_id = message_id
        self.stable_url_id = stable_url_id
        self.thread_id = thread_id
        self.references = references
        self.full = full

    def __repr__(self):
        """ Representation of the Email object when printed. """
        return "<Email('%s', '%s','%s', '%s', '%s')>" % (self.list_name,
            self.sender, self.email, self.date, self.subject)

    def save(self, session):
        """ Save the object into the database. """
        session.add(self)


def create(url):
    """ Create the tables in the database using the information from the
    url obtained.

    :arg url, URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
      ie: mysql://mm3_user:mm3_password@localhost/mm3
    """
    engine = create_engine(url, echo=True)
    Base.metadata.create_all(engine)


class MMEmail(object):
    """ Interface to query emails from the database. """

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
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

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
        archives = []
        for el in self.session.query(Email).filter(
                Email.list_name == list_name,
                Email.date >= start,
                Email.date <= end,
                Email.references == None,
                ).order_by(Email.date):
            archives.append(el)
        return archives

    def get_archives_length(self, list_name):
        """ Return a dictionnary of years, months for which there are
        potentially archives available for a given list (based on the
        oldest post on the list).

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        archives = {}
        entry = self.session.query(Email).filter(
                Email.list_name == list_name
                ).order_by(Email.date).limit(1).one()
        now = datetime.datetime.now()
        year = entry.date.year
        month = entry.date.month
        while year < now.year:
            archives[year] = range(1,13)[(month -1):]
            year = year + 1
            month = 1
        archives[now.year] = range(1,13)[:now.month]
        return archives

    def get_email(self, list_name, message_id):
        """ Return an Email object found in the database corresponding
        to the Message-ID provided.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg message_id, Message-ID as found in the headers of the email.
        Used here to uniquely identify the email present in the database.
        """
        return self.session.query(Email).filter_by(list_name=list_name,
            message_id=message_id).one()

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        return self.session.query(Email).filter_by(list_name=list_name
            ).count()

    def get_thread_length(self, list_name, thread_id):
        """ Return the number of email present in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """

        return self.session.query(Email).filter(
                Email.list_name == list_name,
                Email.thread_id == thread_id).count()

    def get_thread_participants(self, list_name, thread_id):
        """ Return the list of participant in a thread. This thread
        is uniquely identified by its thread_id.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg thread_id, unique identifier of the thread as specified in
        the database.
        """
        return self.session.query(distinct(Email.sender)).filter(
                Email.list_name == list_name,
                Email.thread_id == thread_id).all()

    def search_content(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the content of the emails.
        """
        return self.session.query(Email).filter(
                Email.content.like('%{0}%'.format(keyword))
                ).all()

    def search_content_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content or their subject.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the content or subject of
        the emails.
        """
        mails = self.session.query(Email).filter(
                Email.content.like('%{0}%'.format(keyword))
                ).all()
        mails.extend(self.session.query(Email).filter(
                Email.subject.like('%{0}%'.format(keyword))
                ).all())
        return mails

    def search_sender(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        the name or email address of the sender of the email.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the database.
        """
        mails = self.session.query(Email).filter(
                Email.list_name == list_name,
                Email.sender.like('%{0}%'.format(keyword))
                ).all()
        mails.extend(self.session.query(Email).filter(
                Email.list_name == list_name,
                Email.email.like('%{0}%'.format(keyword))
                ).all())
        return mails

    def search_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their subject.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        :arg keyword, keyword to search in the subject of the emails.
        """
        return self.session.query(Email).filter(
                Email.subject.like('%{0}%'.format(keyword))
                ).all()


if __name__ == '__main__':
    import datetime
    url = 'postgresql://mm3:mm3@localhost/mm3'
    #create(url)
    mmemail = MMEmail(url)#, debug=True)
    print mmemail.get_email('devel',
        'Pine.LNX.4.55.0307210822320.19648@verdande.oobleck.net')
    start = datetime.datetime(2012, 3, 1)
    end = datetime.datetime(2012, 3, 30)
    print len(mmemail.get_archives('devel', start, end))
    print mmemail.get_thread_length('devel',
        '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
    print mmemail.get_thread_participants('devel',
        '4FCWUV6BCP3A5PASNFX6L5JOAE4GJ7F2')
    print mmemail.get_archives_length('devel')
    print 'Subject', len(mmemail.search_subject('devel', 'rawhid'))
    print 'Content', len(mmemail.search_content('devel', 'rawhid'))
    print 'Content-Subject', len(
        mmemail.search_content_subject('devel', 'rawhid'))
    print 'Sender', len(mmemail.search_sender('devel', 'pingou'))
    print mmemail.get_list_size('devel')
