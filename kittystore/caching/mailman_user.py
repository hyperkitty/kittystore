# -*- coding: utf-8 -*-
"""
Cached values concerning emails
"""

from urllib2 import HTTPError
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
    else:
        if mm_user.user_id is None:
            return None
        else:
            return unicode(mm_user.user_id)


@events.subscribe_to(events.NewMessage)
def on_new_message(event):
    if event.message.user_id is not None:
        return
    try:
        user_id = get_user_id(event.store, event.message.sender)
    except (HTTPError, mailmanclient.MailmanConnectionError):
        return # Can't refresh at this time
    if user_id is None:
        return
    # XXX: Storm-specific
    from kittystore.storm.model import User
    user = event.store.db.get(User, user_id)
    if user is None:
        event.store.db.add(User(user_id))
    event.message.user_id = user_id


def sync_mailman_user(store):
    """Sync the user ID from Mailman"""
    # There can be thousands of senders, break into smaller chuncks to avoid
    # hogging up the memory
    buffer_size = 1000
    # XXX: Storm-specific
    from kittystore.storm.model import Sender, User
    prev_count = store.db.find(Sender, Sender.user_id == None).count()
    try:
        while True:
            for sender in store.db.find(Sender,
                        Sender.user_id == None)[:buffer_size]:
                user_id = get_user_id(store, sender)
                if user_id is None:
                    continue
                sender.user_id = user_id
                user = store.db.find(User, User.id == user_id).one()
                if user is None:
                    store.db.add(User(user_id))
            store.commit()
            count = store.db.find(Sender, Sender.user_id == None).count()
            if count == 0 or count == prev_count:
                break # done, or no improvement (former members)
            prev_count = count
            logger.info("%d emails left to refresh" % count)
    except (HTTPError, mailmanclient.MailmanConnectionError):
        return # Can't refresh at this time
