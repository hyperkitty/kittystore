# -*- coding: utf-8 -*-

"""
Copyright (C) 2012-2014 Aurélien Bompard <abompard@fedoraproject.org>
Author: Aurélien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import, print_function, unicode_literals

import datetime
from email.utils import unquote

from mailman.interfaces.archiver import ArchivePolicy
from sqlalchemy import desc, and_
from sqlalchemy.sql import func
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from dateutil.tz import tzutc

from kittystore import MessageNotFound, events
from kittystore.store import Store
from kittystore.utils import parseaddr, parsedate
from kittystore.utils import header_to_unicode
from kittystore.scrub import Scrubber
from kittystore.utils import get_ref_and_thread_id
from kittystore.analysis import compute_thread_order_and_depth

from .model import List, Email, Attachment, Thread, Category
from .model import Sender, User

import logging
logger = logging.getLogger(__name__)


class SAStore(Store):
    """
    SQLAlchemy-powered interface to query emails from the database.
    """

    def add_to_list(self, mlist, message):
        list_name = mlist.fqdn_listname
        # Create the list if it does not exist
        l = self.db.query(List).get(list_name)
        if l is None:
            l = List(name=list_name)
            # Don't wait for the cache to set those properties
            for propname in l.mailman_props:
                setattr(l, propname, getattr(mlist, propname))
            self.db.add(l)
        if mlist.archive_policy == ArchivePolicy.never:
            logger.info("Archiving disabled by list policy for %s" % list_name)
            return None
        if not message.has_key("Message-Id"):
            raise ValueError("No 'Message-Id' header in email", message)
        msg_id = unicode(unquote(message['Message-Id']))
        # Protect against extremely long Message-Ids (there is no limit in the
        # email spec), it's set to VARCHAR(255) in the database
        if len(msg_id) >= 255:
            msg_id = msg_id[:254]
        email = Email(list_name=list_name, message_id=msg_id)
        if self.is_message_in_list(list_name, email.message_id):
            logger.info("Duplicate email from %s: %s" %
                   (message['From'], message.get('Subject', '""')))
            return email.message_id_hash

        #if not getattr(settings.KITTYSTORE_FULL_EMAIL):
        #    # If it's a valid value, leave it to the "prototype" archiver
        #    # Note: the message.as_string() call must be done before scrubbing
        #    email_full = EmailFull(list_name, msg_id, message.as_string())
        #    self.db.add(email_full)

        # Find thread id
        new_thread = False
        ref, thread_id = get_ref_and_thread_id(message, list_name, self)
        if thread_id is None:
            new_thread = True
            # make up the thread_id if not found
            thread_id = email.message_id_hash
        email.thread_id = thread_id
        email.in_reply_to = ref

        try:
            from_name, from_email = parseaddr(message['From'])
            from_name = header_to_unicode(from_name).strip()
            email.sender_email = unicode(from_email).strip()
        except (UnicodeDecodeError, UnicodeEncodeError):
            raise ValueError("Non-ascii sender address", message)
        sender = self.db.query(Sender).get(email.sender_email)
        if sender is None:
            sender = Sender(email=email.sender_email, name=from_name)
            self.db.add(sender)
        else:
            sender.name = from_name # update the name if needed
        email.subject = header_to_unicode(message.get('Subject'))
        if email.subject is not None:
            # limit subject size to 2000 chars or PostgreSQL may complain
            email.subject = email.subject[:2000]
        msg_date = parsedate(message.get("Date"))
        if msg_date is None:
            # Absent or unparseable date
            msg_date = datetime.datetime.utcnow()
        utcoffset = msg_date.utcoffset()
        if msg_date.tzinfo is not None:
            msg_date = msg_date.astimezone(tzutc()).replace(tzinfo=None)
        email.date = msg_date
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
            thread = Thread(list_name=list_name, thread_id=thread_id)
            self.db.add(thread)
        else:
            thread = self.db.query(Thread).get((list_name, thread_id))
        thread.date_active = email.date

        thread.emails.append(email)
        compute_thread_order_and_depth(thread)
        for attachment in attachments:
            self.add_attachment(list_name, msg_id, *attachment)
        self.flush()
        # invalidate the cache
        events.notify(events.NewMessage(self, mlist, email))
        if new_thread:
            events.notify(events.NewThread(self, mlist, thread))
        # search indexing
        # do it after caching because we need some list properties (like
        # archive_policy)
        if self.search_index is not None:
            self.search_index.add(email)

        return email.message_id_hash


    def delete_message_from_list(self, list_name, message_id):
        msg = self.get_message_by_id_from_list(list_name, message_id)
        if msg is None:
            raise MessageNotFound(list_name, message_id)
        self.db.delete(msg)
        # Remove the thread if necessary
        if msg.thread.emails_count == 0:
            self.db.delete(msg.thread)
        self.flush()

    def get_list_size(self, list_name):
        return self.db.query(Email).filter(
                Email.list_name == list_name).count()


    def get_message_by_hash_from_list(self, list_name, message_id_hash):
        return self.db.query(Email).filter(and_(
                    Email.list_name == list_name,
                    Email.message_id_hash == message_id_hash,
                )).first()

    def get_message_by_id_from_list(self, list_name, message_id):
        return self.db.query(Email).get((list_name, message_id[:254]))

    # Other methods (not in IMessageStore)

    def is_message_in_list(self, list_name, message_id):
        """Checks if a message is in the list.

        :param list_name: The fully qualified list name in which the
            message should be searched.
        :param message_id: The Message-ID header contents to search for.
        :returns: True of False
        """
        return self.db.query(Email).get(
                    (list_name, message_id[:254])) is not None

    def get_list_names(self):
        """Return the names of the archived lists.

        :returns: A list containing the names of the archived mailing-lists.
        """
        return self.db.query(List.name).order_by(List.name).all()

    def get_lists(self):
        """Return the archived lists.

        :returns: A list containing the archived mailing-lists.
        """
        return self.db.query(List).order_by(List.name).all()

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
        return self.db.query(Email).filter(and_(
                    Email.list_name == list_name,
                    Email.date >= start,
                    Email.date < end,
                )).order_by(desc(Email.date)).all()

    def get_thread(self, list_name, thread_id):
        """ Return the specified thread.

        :param list_name: The name of the mailing list in which this email
            should be searched.
        :param thread_id: The thread_id as used in the web-pages. Used here to
            uniquely identify the thread in the database.
        :returns: The thread object.
        """
        return self.db.query(Thread).get((list_name, thread_id))

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
        return self.db.query(Thread).filter(and_(
                    Thread.list_name == list_name,
                    Thread.date_active >= start,
                    Thread.date_active < end,
                )).order_by(desc(Thread.date_active))

    def get_start_date(self, list_name):
        """ Get the date of the first archived email in a list.

        :param list_name: The fully qualified list name to search
        :returns: The datetime of the first message, or None if no message have
            been archived yet.
        """
        return self.db.query(Email.date).filter(
                Email.list_name == list_name
                ).order_by(Email.date).limit(1).scalar()

    def get_last_date(self, list_name):
        """ Get the date of the last archived email in a list.

        :param list_name: The fully qualified list name to search
        :returns: The datetime of the last message, or None if no message have
            been archived yet.
        """
        return self.db.query(Email.date).filter(
                Email.list_name == list_name
                ).order_by(desc(Email.date)).limit(1).scalar()

    def get_thread_neighbors(self, list_name, thread_id):
        """ Return the previous and the next threads of the specified thread,
        in date order.

        :param list_name: The name of the mailing list to query.
        :param thread_id: The unique identifier of the thread as specified in
            the database.
        :returns: A couple formed of the older thread and the newer thread, in
            this order.
        :rtype: tuple
        """
        thread = self.get_thread(list_name, thread_id)
        threads_query = self.db.query(Thread).filter(
                    Thread.list_name == list_name)
        next_thread = threads_query.filter(
                    Thread.date_active > thread.date_active
                ).order_by(Thread.date_active).first()
        prev_thread = threads_query.filter(
                    Thread.date_active < thread.date_active
                ).order_by(desc(Thread.date_active)).first()
        return (prev_thread, next_thread)

    def delete_thread(self, list_name, thread_id):
        """ Delete the specified thread.

        :param list_name: The name of the mailing list containing this thread
        :param thread_id: The thread_id as used in the web-pages. Used here to
            uniquely identify the thread in the database.
        """
        self.db.delete(self.get_thread(list_name, thread_id))

    def get_list(self, list_name):
        """ Return the list object for a mailing list name.

        :arg list_name, name of the mailing list to retrieve.
        """
        return self.db.query(List).get(list_name)

    def get_message_by_number(self, list_name, num):
        """ Return the n-th email for the specified list.

        :param list_name: The name of the mailing list in which this email
            should be searched.
        :param num: The email number in order received.
        :returns: The email message.
        """
        return self.db.query(Email).filter_by(list_name=list_name)\
                    .order_by(Email.archived_date).offset(num).first()

    def get_top_participants(self, list_name, start, end, limit=None):
        """ Return all the participants between two given dates.

        :param list_name: The name of the mailing list in which this email
            should be searched.
        :param start: A datetime object representing the starting date of
            the interval to query.
        :param end: A datetime object representing the ending date of
            the interval to query.
        :param limit: Limit the number of participants to return. If None or
            not supplied, return them all.
        :returns: The list of thread-starting messages.
        """
        part = self.db.query(Sender.name, Email.sender_email,
                             func.count(Email.sender_email)
                ).join(Email
                ).filter(and_(
                    Email.list_name == list_name,
                    Email.date >= start,
                    Email.date < end,
                )).group_by(Email.sender_email, Sender.name
                ).order_by(desc(func.count(Email.sender_email)))
        if limit is not None:
            part = part.limit(limit)
        return part.all()


    def get_categories(self):
        """ Return the list of available categories
        """
        return self.db.query(Category.name).order_by(Category.name).all()


    def get_first_post(self, list_name, user_id):
        """ Returns a user's first post on a list """
        return self.db.query(Email).filter(and_(
                    Email.list_name == list_name,
                    Email.sender_email == Sender.email,
                    Sender.user_id == user_id,
                )).order_by(Email.archived_date).first()

    def get_user(self, user_id):
        """ Returns a user given his user_id """
        return self.db.query(User).get(user_id)

    def get_users_count(self):
        return self.db.query(User).count()

    def create_user(self, email, user_id, name=None):
        """
        Create a user with the given user_id.
        """
        user = User(id=user_id)
        self.db.add(user)
        sender = self.db.query(Sender).get(email)
        if sender is None:
            sender = Sender(email=email, name=name)
            self.db.add(sender)
        sender.user_id = user_id

    def get_sender_name(self, user_id):
        """ Returns a user's fullname when given his user_id """
        return self.db.query(Sender.name).filter(
                              Sender.user_id == user_id).first()

    def get_senders_without_user(self, limit=None):
        q = self.db.query(Sender).filter(Sender.user_id == None)
        if limit:
            q = q.limit(limit)
        return q

    def _get_messages_by_user_id(self, user_id, list_name=None):
        """ Returns a user's email hashes """
        req = self.db.query(Email).filter(and_(
                    Email.sender_email == Sender.email,
                    Sender.user_id == user_id))
        if list_name is not None:
            req = req.filter(Email.list_name == list_name)
        return req

    def get_message_hashes_by_user_id(self, user_id, list_name=None):
        query = self._get_messages_by_user_id(user_id, list_name)
        return query.with_entities(Email.message_id_hash).all()

    def get_message_count_by_user_id(self, user_id, list_name=None):
        return self._get_messages_by_user_id(user_id, list_name).count()

    def get_messages_by_user_id(self, user_id, list_name=None):
        """ Returns a user's emails"""
        query = self._get_messages_by_user_id(user_id, list_name)
        return query.order_by(desc(Email.date)).all()

    def get_threads_user_posted_to(self, user_id, list_name=None):
        req = self.db.query(Thread).join(Email).join(Sender).filter(
                Sender.user_id == user_id)
        if list_name is not None:
            req = req.filter(Thread.list_name == list_name)
        return req.distinct()

    def get_all_messages(self):
        return self.db.query(Email).order_by(Email.archived_date).all()

    def get_message_dates(self, list_name, start, end):
        """ Return all email dates between two given dates.

        :param list_name: The name of the mailing list in which these emails
            should be searched.
        :param start: A datetime object representing the starting date of
            the interval to query.
        :param end: A datetime object representing the ending date of
            the interval to query.
        :returns: The list of messages.
        """
        return [ e.date for e in self.db.query(Email.date).filter(and_(
                    Email.list_name == list_name,
                    Email.date >= start,
                    Email.date < end,
                 )).order_by(desc(Email.date)) ]

    # Attachments

    def add_attachment(self, mlist, msg_id, counter, name, content_type,
                       encoding, content):
        msg_id = msg_id[:254]
        existing = self.db.query(Attachment).filter_by(
                    list_name=mlist,
                    message_id=msg_id,
                    counter=counter,
                ).count()
        if existing:
            return
        attachment = Attachment(list_name=mlist,
                                message_id=msg_id,
                                counter=counter,
                                name=name,
                                content_type=content_type,
                                content=content,
                                size=len(content))
        attachment.encoding = encoding if encoding is not None else None
        self.db.add(attachment)
        self.flush()

    def get_attachments(self, list_name, message_id):
        """Return the message's attachments

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :returns: A list of attachments
        """
        return self.db.query(Attachment).filter(and_(
                    Attachment.list_name == list_name,
                    Attachment.message_id == message_id[:254]
                )).order_by(Attachment.counter).all()

    def get_attachment_by_counter(self, list_name, message_id, counter):
        """Return the message's attachment at 'counter' position.

        :param list_name: The fully qualified list name to which the
            message should be added.
        :param message_id: The Message-ID header contents to search for.
        :param counter: The position in the MIME-multipart email.
        :returns: The corresponding attachment
        """
        return self.db.query(Attachment).get(
                    (list_name, message_id[:254], counter))
