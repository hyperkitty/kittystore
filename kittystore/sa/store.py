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

from kittystore import MessageNotFound
from kittystore.utils import get_message_id_hash, parseaddr, parsedate
from kittystore.utils import header_to_unicode
from kittystore.scrub import Scrubber
from kittystore.utils import get_ref_and_thread_id
from kittystore.sa.kittysamodel import get_class_object

from zope.interface import implements
from mailman.interfaces.messages import IMessageStore

from sqlalchemy import create_engine, distinct, MetaData, and_, desc, or_
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


class KittySAStore(object):
    """
    SQL-Alchemy powered interface to query emails from the database.
    """

    implements(IMessageStore)

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
        connect_args = {}
        if url.startswith('sqlite://'):
            connect_args["check_same_thread"] = False
        self.engine = create_engine(url, echo=debug, connect_args=connect_args)
        self.metadata = MetaData(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

    def add(self, message):
        """Add the message to the store.

        :param message: An email.message.Message instance containing at
            least a unique Message-ID header.  The message will be given
            an X-Message-ID-Hash header, overriding any existing such
            header.
        :returns: The calculated X-Message-ID-Hash header.
        :raises ValueError: if the message is missing a Message-ID 
            header.
            The storage service is also allowed to raise this exception
            if it find, but disallows collisions.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def add_to_list(self, list_name, message):
        """Add the message to a specific list of the store.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message: An email.message.Message instance containing at
            least a unique Message-ID header.  The message will be given
            an X-Message-ID-Hash header, overriding any existing such
            header.
        :returns: The calculated X-Message-ID-Hash header.
        :raises ValueError: if the message is missing a Message-ID 
            header.
            The storage service is also allowed to raise this exception
            if it find, but disallows collisions.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
                        MetaData(self.engine), create=True)
        if not message.has_key("Message-Id"):
            raise ValueError("No 'Message-Id' header in email", message)
        msg_id = message['Message-Id'].strip("<>")
        msg_id_hash = get_message_id_hash(msg_id)
        if self.get_message_by_id_from_list(list_name, msg_id) is not None:
            print ("Duplicate email from %s: %s" %
                   (message['From'], message.get('Subject', '""')))
            return msg_id_hash

        # Find thread id
        ref, thread_id = get_ref_and_thread_id(message, list_name, self)
        if thread_id is None:
            # make up the thread_id if not found
            thread_id = msg_id_hash

        from_name, from_email = parseaddr(message['From'])
        from_name = header_to_unicode(from_name)
        full = message.as_string()
        scrubber = Scrubber(list_name, message, self)
        payload = scrubber.scrub() # modifies the message in-place

        #category = 'Question' # TODO: enum + i18n ?
        #if ('agenda' in message.get('Subject', '').lower() or
        #        'reminder' in message.get('Subject', '').lower()):
        #    # i18n!
        #    category = 'Agenda'

        mail = email(
            sender=from_name,
            email=from_email,
            subject=header_to_unicode(message.get('Subject')),
            content=payload.encode("utf-8"),
            date=parsedate(message.get("Date")),
            message_id=msg_id,
            stable_url_id=msg_id_hash,
            thread_id=thread_id,
            references=ref,
            full=full,
            )
        self.session.add(mail)
        return msg_id_hash

    def delete_message(self, message_id):
        """Remove the given message from the store.

        :param message: The Message-ID of the mesage to delete from the
            store.
        :raises LookupError: if there is no such message.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def delete_message_from_list(self, list_name, message_id):
        """Remove the given message for a specific list from the store.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message: The Message-ID of the mesage to delete from the
            store.
        :raises LookupError: if there is no such message.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
                                 self.metadata, create=False)
        msg = self.get_message_by_id_from_list(list_name, message_id)
        if msg is None:
            raise MessageNotFound(list_name, message_id)
        self.session.delete(msg)

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        return self.session.query(email).count()


    def get_message_by_hash(self, message_id_hash):
        """Return the message with the matching X-Message-ID-Hash.

        :param message_id_hash: The X-Message-ID-Hash header contents to
            search for.
        :returns: The message, or None if no matching message was found.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def get_message_by_hash_from_list(self, list_name, message_id_hash):
        """Return the message with the matching X-Message-ID-Hash.

        :param message_id_hash: The X-Message-ID-Hash header contents to
            search for.
        :returns: The message, or None if no matching message was found.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
                                 self.metadata)
        try:
            return self.session.query(email).filter_by(
                    stable_url_id=message_id_hash).one()
        except NoResultFound:
            return None

    def get_message_by_id(self, message_id):
        """Return the message with a matching Message-ID.

        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """
        # Not sure this is useful: a message should always be in a list
        raise NotImplementedError

    def get_message_by_id_from_list(self, list_name, message_id):
        """Return the message with a matching Message-ID.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
                                 self.metadata)
        try:
            return self.session.query(email).filter_by(
                    message_id=message_id).one()
        except NoResultFound:
            return None

    def search_list_for_content(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content.

        :param list_name: name of the mailing list in which this email
        should be searched.
        :param keyword: keyword to search in the content of the emails.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mails = self.session.query(email).filter(
                email.content.ilike('%{0}%'.format(keyword))
                ).order_by(email.date).all()
        mails.reverse() # TODO: change the SQL order above
        return mails

    def search_list_for_content_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content or their subject.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the content or subject of
            the emails.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mails = self.session.query(email).filter(or_(
                email.content.ilike('%{0}%'.format(keyword)),
                email.subject.ilike('%{0}%'.format(keyword))
                )).order_by(email.date).all()
        mails.reverse() # TODO: change the SQL order above
        return mails

    def search_list_for_sender(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        the name or email address of the sender of the email.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the database.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mails = self.session.query(email).filter(or_(
                email.sender.ilike('%{0}%'.format(keyword)),
                email.email.ilike('%{0}%'.format(keyword))
                )).order_by(email.date).all()
        mails.reverse() # TODO: change the SQL order above
        return mails


    def search_list_for_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their subject.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the subject of the emails.
        """
        email = get_class_object(list_to_table_name(list_name), 'email',
            self.metadata)
        mails = self.session.query(email).filter(
                email.subject.ilike('%{0}%'.format(keyword))
                ).order_by(email.date).all()
        mails.reverse() # TODO: change the SQL order above
        return mails

    @property
    def messages(self):
        """An iterator over all messages in this message store."""
        raise NotImplementedError






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
        mails = self.session.query(email).filter(
            and_(
                email.date >= start,
                email.date <= end,
                email.references == None)
                ).order_by(email.date).all()
        mails.reverse()
        return mails

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
        try:
            return self.session.query(email).filter_by(
                thread_id=thread_id).order_by(email.date).all()
        except NoResultFound:
            return None

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

    def flush(self):
        self.session.flush()

    def commit(self):
        self.session.commit()
