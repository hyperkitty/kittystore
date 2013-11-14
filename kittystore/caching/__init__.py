# -*- coding: utf-8 -*-

"""
Some data is cached in the database for faster access. This module re-computes
these values, for example in a periodic manner, but also on specific events
like addition of a new message or creation of a new thread.

The cached values are mostly very small results of computation, thus a simple
database store is preferred to a more complex Memcached-based cache.

The computation is done in this module instead of in the model because it is
(mostly) ORM-agnostic.
"""

import datetime
from urllib2 import HTTPError
from pkg_resources import resource_listdir
import mailmanclient


class CachedValue(object):

    def on_new_message(self, store, mlist, message):
        """A new message has been added to the list"""
        pass

    def on_new_thread(self, store, mlist, thread):
        """A new thread has been created in the list"""
        pass

    def daily(self, store):
        """Executed once a day"""
        pass

    def refresh(self, store):
        """Rebuild the cache entirely"""
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
    _last_daily = None

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
        for cval in self._cached_values:
            cval.on_new_message(store, mlist, message)
        if datetime.date.today() != self._last_daily:
            self.daily(store)

    def on_new_thread(self, store, mlist, thread):
        for cval in self._cached_values:
            cval.on_new_thread(store, mlist, thread)

    def daily(self, store):
        for cval in self._cached_values:
            cval.daily(store)
        self._last_daily = datetime.date.today()

    def refresh(self, store):
        for cval in self._cached_values:
            cval.refresh(store)
