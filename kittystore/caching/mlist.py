# -*- coding: utf-8 -*-
"""
Cached values concerning mailing-lists
"""

from urllib2 import HTTPError

import mailmanclient
from dateutil.parser import parse as date_parse
from mailman.interfaces.archiver import ArchivePolicy

from kittystore import events
from kittystore.utils import get_mailman_client


class CompatibleMList(object):
    """
    Convert the List object returned by mailmanclient to an
    IMailingList-compatible object
    """
    converters = {
        "created_at": date_parse,
        "archive_policy": lambda p: getattr(ArchivePolicy, p),
    }
    def __init__(self, mlist, props):
        for prop in props:
            try:
                value = getattr(mlist, prop)
            except AttributeError:
                value = mlist.settings[prop]
            if prop in self.converters:
                value = self.converters[prop](value)
            setattr(self, prop, value)


def update_props(store, mlist):
    l = store.get_list(mlist.fqdn_listname)
    if isinstance(mlist, mailmanclient._client._List):
        mlist = CompatibleMList(mlist, l.mailman_props)
    for propname in l.mailman_props:
        setattr(l, propname, getattr(mlist, propname))


@events.subscribe_to(events.NewMessage)
def on_new_message(event):
    update_props(event.store, event.mlist)


def sync_list_properties(store):
    """Sync the list properties from Mailman"""
    try:
        mm_client = get_mailman_client(store.settings)
    except HTTPError:
        return # Can't refresh at this time
    for list_name in store.get_list_names():
        try:
            mm_mlist = mm_client.get_list(list_name)
        except (HTTPError, mailmanclient.MailmanConnectionError):
            continue
        if mm_mlist:
            update_props(store, mm_mlist)
