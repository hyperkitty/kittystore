# -*- coding: utf-8 -*-
"""
Cached values concerning threads
"""

from kittystore.caching import CachedValue


class ThreadStats(CachedValue):
    """Number of emails and number of participants"""

    def on_new_message(self, store, mlist, message):
        if message.thread.emails_count is None:
            message.thread.emails_count = 1
        else:
            message.thread.emails_count += 1
        message.thread.participants_count = \
            len(message.thread.participants)

    def refresh(self, store):
        # XXX: Storm-specific
        from kittystore.storm.model import Thread
        for num, thread in enumerate(store.db.find(Thread)):
            thread.emails_count = None # reset it
            len(thread) # this will refill the cached value
            thread.participants_count = len(thread.participants)
            if num % 1000 == 0:
                store.commit() # otherwise we'll blow up the memory


class ThreadSubject(CachedValue):

    def on_new_thread(self, store, mlist, thread):
        thread.subject = thread.starting_email.subject

    def refresh(self, store):
        # XXX: Storm-specific
        from kittystore.storm.model import Thread
        for thread in store.db.find(Thread, Thread.subject == None):
            self.on_new_thread(store, None, thread)
