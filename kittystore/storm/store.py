# -*- coding: utf-8 -*-

"""
Copyright (C) 2012 Aurélien Bompard <abompard@fedoraproject.org>
Author: Aurélien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import

import datetime
from email.utils import unquote

from zope.interface import implements
from mailman.interfaces.messages import IMessageStore
from storm.locals import Desc
from storm.expr import And, Or
from dateutil.tz import tzutc

from kittystore import MessageNotFound
from kittystore.utils import parseaddr, parsedate
from kittystore.utils import header_to_unicode
from kittystore.scrub import Scrubber
from kittystore.utils import get_ref_and_thread_id

from .model import List, Email, Attachment, Thread, EmailFull


class StormStore(object):
    """
    Storm-powered interface to query emails from the database.
    """

    implements(IMessageStore)

    def __init__(self, db, debug=False):
        """ Constructor.
        Create the session using the engine defined in the url.

        :param db: the Storm store object
        :param debug: a boolean to set the debug mode on or off.
        """
        self.db = db
        self.debug = debug

    # IMessageStore methods

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

    def add_to_list(self, mlist, message):
        """Add the message to a specific list of the store.

        :param mlist: The mailing-list object, implementing
            mailman.interfaces.mailinglist.IMailingList.
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
        list_name = unicode(mlist.fqdn_listname)
        # Create the list if it does not exist
        list_is_in_db = self.db.find(List,
                List.name == list_name).count()
        if not list_is_in_db:
            l = List(list_name)
            l.display_name = mlist.display_name
            self.db.add(l)
        if not message.has_key("Message-Id"):
            raise ValueError("No 'Message-Id' header in email", message)
        msg_id = unicode(unquote(message['Message-Id']))
        email = Email(list_name, msg_id)
        if self.is_message_in_list(list_name, email.message_id):
            print ("Duplicate email from %s: %s" %
                   (message['From'], message.get('Subject', '""')))
            return email.message_id_hash

        # the message.as_string() call must be done before scrubbing
        email_full = EmailFull(list_name, msg_id, message.as_string())
        # Find thread id
        new_thread = False
        ref, thread_id = get_ref_and_thread_id(message, list_name, self)
        if thread_id is None:
            new_thread = True
            # make up the thread_id if not found
            thread_id = email.message_id_hash
        email.thread_id = thread_id
        email.in_reply_to = ref

        from_name, from_email = parseaddr(message['From'])
        from_name = header_to_unicode(from_name)
        email.sender_name = from_name.strip()
        email.sender_email = unicode(from_email).strip()
        email.subject = header_to_unicode(message.get('Subject'))
        msg_date = parsedate(message.get("Date"))
        if msg_date is None:
            # Absent or unparseable date
            msg_date = datetime.datetime.now()
        if msg_date.tzinfo is not None:
            msg_date = msg_date.astimezone(tzutc()).replace(tzinfo=None)
        email.date = msg_date
        utcoffset = msg_date.utcoffset()
        if utcoffset is None:
            email.timezone = 0
        else:
            # in minutes
            email.timezone = ( (utcoffset.days * 24 * 60 * 60)
                               + utcoffset.seconds) / 60

        scrubber = Scrubber(list_name, message)
        # warning: scrubbing modifies the msg in-place
        email.content, attachments = scrubber.scrub()

        #category = 'Question' # TODO: enum + i18n ?
        #if ('agenda' in message.get('Subject', '').lower() or
        #        'reminder' in message.get('Subject', '').lower()):
        #    # i18n!
        #    category = 'Agenda'

        if new_thread:
            thread = Thread(list_name, thread_id, email.date)
        else:
            thread = self.db.find(Thread, And(
                            Thread.list_name == list_name,
                            Thread.thread_id == thread_id,
                            )).one()
        thread.date_active = email.date
        self.db.add(thread)

        self.db.add(email)
        self.db.add(email_full)
        self.flush()
        for attachment in attachments:
            self.add_attachment(list_name, msg_id, *attachment)
        return email.message_id_hash

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
        msg = self.get_message_by_id_from_list(list_name, message_id)
        if msg is None:
            raise MessageNotFound(list_name, message_id)
        self.db.delete(msg)
        # Remove the thread if necessary
        thread = self.db.find(Thread, And(
                        Thread.list_name == msg.list_name,
                        Thread.thread_id == msg.thread_id,
                        )).one()
        if len(thread.emails) == 0:
            self.db.delete(thread)
        self.flush()

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        return self.db.find(Email,
                Email.list_name == unicode(list_name)).count()


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
        return self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.message_id_hash == unicode(message_id_hash)
                )).one()

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
        msg = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.message_id == unicode(message_id)
                )).one()
        return msg

    def search_list_for_content(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content.

        :param list_name: name of the mailing list in which this email
        should be searched.
        :param keyword: keyword to search in the content of the emails.
        """
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.content.ilike(u'%{0}%'.format(keyword))
                )).order_by(Desc(Email.date))
        return emails

    def search_list_for_content_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their content or their subject.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the content or subject of
            the emails.
        """
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Or(
                        Email.content.ilike(u'%{0}%'.format(keyword)),
                        Email.subject.ilike(u'%{0}%'.format(keyword)),
                ))).order_by(Desc(Email.date))
        return emails

    def search_list_for_sender(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        the name or email address of the sender of the email.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the database.
        """
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Or(
                        Email.sender_name.ilike(u'%{0}%'.format(keyword)),
                        Email.sender_email.ilike(u'%{0}%'.format(keyword)),
                ))).order_by(Desc(Email.date))
        return emails

    def search_list_for_subject(self, list_name, keyword):
        """ Returns a list of email containing the specified keyword in
        their subject.

        :param list_name: name of the mailing list in which this email
            should be searched.
        :param keyword: keyword to search in the subject of the emails.
        """
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.subject.ilike(u'%{0}%'.format(keyword)),
                )).order_by(Desc(Email.date))
        return emails

    @property
    def messages(self):
        """An iterator over all messages in this message store."""
        raise NotImplementedError

    # Other methods (not in IMessageStore)

    def is_message_in_list(self, list_name, message_id):
        """Return the number of messages with a matching Message-ID in the list.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :returns: The message, or None if no matching message was found.
        """
        return self.db.find(Email.message_id, And(
                    Email.list_name == unicode(list_name),
                    Email.message_id == unicode(message_id)
                )).count()

    def get_list_names(self):
        """Return the names of the archived lists.

        :returns: A list containing the names of the archived mailing-lists.
        """
        return list(self.db.find(List.name).order_by(List.name))

    def get_messages(self, list_name, start, end):
        """ Return all emails between two given dates.

        :param list_name: The name of the mailing list in which these emails
            should be searched.
        :param start: A datetime object representing the starting date of
            the interval to query.
        :param end: A datetime object representing the ending date of
            the interval to query.
        :returns: The list of messages.
        """
        emails = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.date >= start,
                    Email.date < end,
                )).order_by(Desc(Email.date))
        return list(emails)

    def get_thread(self, list_name, thread_id):
        """ Return the specified thread.

        :param list_name: The name of the mailing list in which this email
            should be searched.
        :param thread_id: The thread_id as used in the web-pages. Used here to
            uniquely identify the thread in the database.
        :returns: The thread object.
        """
        return self.db.find(Thread, And(
                    Thread.list_name == unicode(list_name),
                    Thread.thread_id == unicode(thread_id)
                    )).one()

    def get_threads(self, list_name, start, end):
        """ Return all the threads active between two given dates.

        :param list_name: The name of the mailing list in which this email
            should be searched.
        :param start: A datetime object representing the starting date of
            the interval to query.
        :param end: A datetime object representing the ending date of
            the interval to query.
        :returns: The list of thread-starting messages.
        """
        threads = self.db.find(Thread, And(
                    Thread.list_name == unicode(list_name),
                    Thread.date_active >= start,
                    Thread.date_active < end,
                )).order_by(Desc(Thread.date_active))
        return list(threads)

    def get_start_date(self, list_name):
        """ Get the date of the first archived email in a list.

        :param list_name: The fully qualified list name to search
        :returns: The datetime of the first message, or None if no message have
            been archived yet.
        """
        date = self.db.find(Email.date,
                Email.list_name == unicode(list_name)
                ).order_by(Email.date)[:1]
        if date:
            return date.one()
        else:
            return None

    def get_thread_neighbors(self, list_name, thread_id):
        """ Return the previous and the next threads of the specified thread,
        in date order. The returned objects are the emails starting the
        threads.

        :param list_name: The name of the mailing list to query.
        :param thread_id: The unique identifier of the thread as specified in
            the database.
        :returns: A couple formed of the older thread and the newer thread, in
            this order.
        :rtype: tuple
        """
        current_email = self.get_message_by_hash_from_list(list_name, thread_id)
        next_email = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.in_reply_to == None,
                    Email.date > current_email.date,
                )).order_by(Email.date)
        try:
            next_email = next_email[0]
        except IndexError:
            next_email = None
        prev_email = self.db.find(Email, And(
                    Email.list_name == unicode(list_name),
                    Email.in_reply_to == None,
                    Email.date < current_email.date,
                )).order_by(Desc(Email.date))
        try:
            prev_email = prev_email[0]
        except IndexError:
            prev_email = None
        return (prev_email, next_email)

    def get_list(self, list_name):
        """ Return the list object for a mailing list name.

        :arg list_name, name of the mailing list to retrieve.
        """
        return self.db.find(List, List.name == unicode(list_name)).one()

    def get_message_by_number(self, list_name, num):
        """ Return the n-th email for the specified list.

        :param list_name: The name of the mailing list in which this email
            should be searched.
        :param num: The email number in order received.
        :returns: The email message.
        """
        result = self.db.find(Email, Email.list_name == unicode(list_name)
                    ).order_by(Email.archived_date
                    )[num:num+1].one()
        return result


    # Attachments

    def add_attachment(self, mlist, msg_id, counter, name, content_type,
                       encoding, content):
        existing = self.db.find(Attachment.message_id, And(
                    Attachment.list_name == unicode(mlist),
                    Attachment.message_id == unicode(msg_id),
                    Attachment.counter == counter,
                )).count()
        if existing:
            return
        attachment = Attachment()
        attachment.list_name = unicode(mlist)
        attachment.message_id = unicode(msg_id)
        attachment.counter = counter
        attachment.name = unicode(name)
        attachment.content_type = unicode(content_type)
        attachment.encoding = unicode(encoding) if encoding is not None else None
        attachment.content = content
        attachment.size = len(content)
        self.db.add(attachment)
        self.flush()

    def get_attachments(self, list_name, message_id):
        """Return the message's attachments

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :returns: A list of attachments
        """
        att = self.db.find(Attachment, And(
                    Attachment.list_name == unicode(list_name),
                    Attachment.message_id == unicode(message_id)
                )).order_by(Attachment.counter)
        return list(att)

    def get_attachment_by_counter(self, list_name, message_id, counter):
        """Return the message's attachment at 'counter' position.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :param counter: The position in the MIME-multipart email.
        :returns: The corresponding attachment
        """
        return self.db.find(Attachment, And(
                    Attachment.list_name == unicode(list_name),
                    Attachment.message_id == unicode(message_id),
                    Attachment.counter == counter
                )).one()

    # Generic database operations

    def flush(self):
        """Flush pending database operations."""
        self.db.flush()

    def commit(self):
        """Commit transaction to the database."""
        self.db.commit()

    def close(self):
        """Close the connection."""
        self.db.close()

    def rollback(self):
        self.db.rollback()
