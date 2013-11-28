# -*- coding: utf-8 -*-
"""
Cached values concerning mailing-lists
"""

import datetime
from urllib2 import HTTPError

import mailmanclient
from dateutil.parser import parse as date_parse
from mailman.interfaces.archiver import ArchivePolicy

from kittystore.caching import CachedValue


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


class ListProperties(CachedValue):

    start_msg = "Refreshing list properties from Mailman"

    def on_new_message(self, store, mlist, message):
        l = store.get_list(mlist.fqdn_listname)
        if isinstance(mlist, mailmanclient._client._List):
            mlist = CompatibleMList(mlist, l.mailman_props)
        for propname in l.mailman_props:
            setattr(l, propname, getattr(mlist, propname))

    def daily(self, store):
        return self.refresh(store)

    def refresh(self, store):
        try:
            mm_client = self._get_mailman_client(store.settings)
        except HTTPError:
            return # Can't refresh at this time
        for list_name in store.get_list_names():
            try:
                mm_mlist = mm_client.get_list(list_name)
            except (HTTPError, mailmanclient.MailmanConnectionError):
                continue
            if mm_mlist:
                self.on_new_message(store, mm_mlist, None)


class RecentListActivity(CachedValue):
    """
    Refresh the recent_participants_count and recent_threads_count properties.
    """

    start_msg = "Computing recent list activity"

    def on_new_message(self, store, mlist, message):
        l = store.get_list(mlist.fqdn_listname)
        begin_date = l.get_recent_dates()[0]
        if message.date >= begin_date:
            l.refresh_cache()

    def daily(self, store):
        return self.refresh(store)

    def refresh(self, store):
        for mlist in store.get_lists():
            mlist.refresh_cache()


class MonthlyListActivity(CachedValue):
    """
    Refresh the monthly participants_count and threads_count values.
    """

    def on_new_message(self, store, mlist, message):
        l = store.get_list(mlist.fqdn_listname)
        activity = l.get_month_activity(message.date.year, message.date.month)
        activity.refresh()

    def refresh(self, store):
        for mlist in store.get_lists():
            mlist.clear_month_activity()
