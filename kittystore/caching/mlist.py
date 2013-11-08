# -*- coding: utf-8 -*-
"""
Cached values concerning mailing-lists
"""

import datetime
from urllib2 import HTTPError

import mailmanclient

from kittystore.caching import CachedValue
from kittystore.utils import daterange


class ListPropertiesCache(CachedValue):

    props = ("display_name", "description", "subject_prefix", "archive_policy")

    def on_new_message(self, store, mlist, message):
        l = store.get_list(mlist.fqdn_listname)
        for propname in self.props:
            setattr(l, propname, getattr(mlist, propname))

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


class ListActivityCache(CachedValue):
    """
    Refresh the recent_participants_count and recent_threads_count properties.
    """

    def _refresh_list(self, store, mlist):
        # Get stats for last 30 days
        today = datetime.datetime.utcnow()
        #today -= datetime.timedelta(days=400) #debug
        # the upper boundary is excluded in the search, add one day
        end_date = today + datetime.timedelta(days=1)
        begin_date = end_date - datetime.timedelta(days=32)
        days = daterange(begin_date, end_date)
        # now compute the values
        threads = store.get_threads(list_name=mlist.name,
                                    start=begin_date, end=end_date)
        participants = set()
        for thread in threads:
            participants.update(thread.participants)
        mlist.recent_participants_count = len(participants)
        mlist.recent_threads_count = len(threads)

    def on_new_message(self, store, mlist, message):
        l = store.get_list(mlist.fqdn_listname)
        self._refresh_list(store, l)

    def refresh(self, store):
        for mlist in store.get_lists():
            self._refresh_list(store, mlist)
