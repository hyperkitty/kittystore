# -*- coding: utf-8 -*-

"""
Some data is cached in the database for faster access. This module re-computes
these values, for example in a periodic manner.
"""

import datetime
from urllib2 import HTTPError
from pkg_resources import resource_listdir
import mailmanclient


class CachedValue(object):

    def on_new_message(self, store, mlist, message):
        pass

    def on_new_thread(self, store, mlist, thread):
        pass

    def refresh(self, store):
        pass

    def _get_mailman_client(self, settings):
        try:
            mm_client = mailmanclient.Client('%s/3.0' %
                            settings.MAILMAN_REST_SERVER,
                            settings.MAILMAN_API_USER,
                            settings.MAILMAN_API_PASS)
        except (HTTPError, mailmanclient.MailmanConnectionError):
            raise HTTPError
        return mm_client


class CacheManager(object):

    _cached_values = []
    auto_refresh = True
    _last_refresh = None

    def discover(self):
        """
        Discover subclasses of CachedValue. This only search direct submodules
        of kittystore.caching.
        """
        submodules = [ f[:-3] for f in resource_listdir("kittystore.caching", "")
                       if f.endswith(".py") and f != "__init__.py" ]
        for submod_name in submodules:
            __import__("kittystore.caching.%s" % submod_name)
        self._cached_values = [ C() for C in CachedValue.__subclasses__() ]

    def on_new_message(self, store, mlist, message):
        if self.auto_refresh and datetime.date.today() != self._last_refresh:
            return self.refresh(store) # Refresh at least once a day
        for cval in self._cached_values:
            cval.on_new_message(store, mlist, message)

    def on_new_thread(self, store, mlist, thread):
        for cval in self._cached_values:
            cval.on_new_thread(store, mlist, thread)

    def refresh(self, store):
        for cval in self._cached_values:
            cval.refresh(store)
        self._last_refresh = datetime.date.today()
