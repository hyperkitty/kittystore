# -*- coding: utf-8 -*-
"""
Cached values concerning emails
"""

from urllib2 import HTTPError
from uuid import UUID
import mailmanclient

from kittystore import events
from kittystore.utils import get_mailman_client

import logging
logger = logging.getLogger(__name__)


_MAILMAN_CLIENT = None


def get_user_id(store, sender):
    global _MAILMAN_CLIENT
    if _MAILMAN_CLIENT is None:
        _MAILMAN_CLIENT = get_mailman_client(store.settings)
    try:
        mm_user = _MAILMAN_CLIENT.get_user(sender.email)
    except HTTPError, e:
        if e.code == 404:
            return None
        else:
            raise
    except ValueError:
        return None
    else:
        user_id = mm_user.user_id
        if user_id is None:
            return None
        else:
            return UUID(int=user_id)


@events.subscribe_to(events.NewMessage)
def on_new_message(event):
    if event.message.sender.user_id is not None:
        return
    try:
        user_id = get_user_id(event.store, event.message.sender)
    except (HTTPError, mailmanclient.MailmanConnectionError):
        return # Can't refresh at this time
    if user_id is None:
        return
    user = event.store.get_user(user_id)
    if user is None:
        event.store.create_user(event.message.sender_email, user_id)
    event.message.sender.user_id = user_id


def sync_mailman_user(store):
    """Sync the user ID from Mailman"""
    # There can be thousands of senders, break into smaller chuncks to avoid
    # hogging up the memory
    buffer_size = 1000
    prev_count = store.get_senders_without_user().count()
    try:
        while True:
            for sender in store.get_senders_without_user(limit=buffer_size):
                user_id = get_user_id(store, sender)
                if user_id is None:
                    continue
                user = store.get_user(user_id)
                if user is None:
                    store.create_user(sender.email, user_id)
            store.commit()
            count = store.get_senders_without_user().count()
            if count == 0 or count == prev_count:
                break # done, or no improvement (former members)
            prev_count = count
            logger.info("%d emails left to refresh" % count)
    except (HTTPError, mailmanclient.MailmanConnectionError):
        return # Can't refresh at this time
