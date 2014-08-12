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


from zope.interface import implements
from mailman.interfaces.messages import IMessageStore

from kittystore.analysis import compute_thread_order_and_depth

import logging
logger = logging.getLogger(__name__)


class Store(object):
    """
    Abstract interface to query emails from the database.
    """

    implements(IMessageStore)

    def __init__(self, db, search_index, settings, debug=False):
        """ Constructor.
        Create the session using the engine defined in the url.

        :param db: the Storm store object
        :param debug: a boolean to set the debug mode on or off.
        """
        self.db = db
        self.debug = debug
        self.search_index = search_index
        self.settings = settings


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
        raise NotImplementedError

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
        raise NotImplementedError

    def get_list_size(self, list_name):
        """ Return the number of emails stored for a given mailing list.

        :arg list_name, name of the mailing list in which this email
        should be searched.
        """
        raise NotImplementedError

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
        raise NotImplementedError

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
        raise NotImplementedError

    @property
    def messages(self):
        """An iterator over all messages in this message store."""
        raise NotImplementedError

    # Other methods (not in IMessageStore)

    def attach_to_thread(self, email, thread):
        """Attach an email to an existing thread"""
        if email.date <= thread.starting_email.date:
            raise ValueError("Can't attach emails older than the first "
                             "email in a thread")
        email.thread_id = thread.thread_id
        email.in_reply_to = thread.starting_email.message_id
        if email.date > thread.date_active:
            thread.date_active = email.date
        compute_thread_order_and_depth(thread)
        self.flush()


    def search(self, query, list_name=None, page=None, limit=10,
               sortedby=None, reverse=False):
        """
        Returns a list of email corresponding to the query string. The
        sender, subject, content and attachment names are searched. If
        list_name is None, all public lists are searched.

        :param query: the query string to execute.
        :param list_name: name of the mailing list in which this email
            should be searched. If None or not specified, all lists are
            searched.
        :param page: the page number to return. If None, don't paginate.
        :param limit: the number of results per page.
        :param sortedby: the field to sort by. If None or not specified, sort
            by match score.
        :param reverse: reverse the order of the results.
        """
        results = self.search_index.search(
                query, list_name, page, limit, sortedby=sortedby,
                reverse=reverse)
        results["results"] = [ self.get_message_by_id_from_list(
                                    r["list_name"], r["message_id"])
                               for r in results["results"] ]
        return results

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
