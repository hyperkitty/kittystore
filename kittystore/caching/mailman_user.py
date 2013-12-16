# -*- coding: utf-8 -*-
"""
Cached values concerning emails
"""

import datetime
from urllib2 import HTTPError
import mailmanclient

from kittystore import events
from kittystore.utils import get_mailman_client

import logging
logger = logging.getLogger(__name__)


_MAILMAN_CLIENT = None
_USER_ID_CACHE = {}


def get_user_id(store, message):
    global _MAILMAN_CLIENT, _USER_ID_CACHE
    address = message.sender_email
    if address not in _USER_ID_CACHE:
        if _MAILMAN_CLIENT is None:
            _MAILMAN_CLIENT = get_mailman_client(store.settings)
        try:
            mm_user = _MAILMAN_CLIENT.get_user(address)
        except HTTPError, e:
            if e.code == 404:
                _USER_ID_CACHE[address] = None
            else:
                raise
        else:
            _USER_ID_CACHE[address] = unicode(mm_user.user_id)
    return _USER_ID_CACHE[address]


@events.subscribe_to(events.NewMessage)
def on_new_message(event):
    try:
        event.message.user_id = get_user_id(event.store, event.message)
    except (HTTPError, mailmanclient.MailmanConnectionError):
        return # Can't refresh at this time


def sync_mailman_user(store):
    """Sync the user ID from Mailman"""
    # There can be millions of emails, break into smaller chuncks to avoid
    # hogging up the memory
    buffer_size = 50000
    # XXX: Storm-specific
    from kittystore.storm.model import Email
    prev_count = store.db.find(Email, Email.user_id == None).count()
    try:
        while True:
            for message in store.db.find(Email,
                        Email.user_id == None)[:buffer_size]:
                message.user_id = get_user_id(store, message)
            store.commit()
            count = store.db.find(Email, Email.user_id == None).count()
            if count == 0 or count == prev_count:
                break # done, or no improvement (former members)
            prev_count = count
            logger.info("%d emails left to refresh" % count)
    except (HTTPError, mailmanclient.MailmanConnectionError):
        return # Can't refresh at this time
