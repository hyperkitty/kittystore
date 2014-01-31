# -*- coding: utf-8 -*-
# pylint: disable=R0904,C0103
# - Too many public methods
# - Invalid name XXX (should match YYY)

import unittest
import datetime

from mock import Mock

from kittystore import events


class TestNotify(unittest.TestCase):

    def test_notify(self):
        class Event: pass
        dummy = []
        events.subscribe(dummy.append, Event)
        e = Event()
        events.notify(e)
        self.assertEqual(dummy, [e])

    def test_decorator(self):
        class Event: pass
        dummy = []
        events.subscribe_to(Event)(dummy.append)
        e = Event()
        events.notify(e)
        self.assertEqual(dummy, [e])

    def test_decorator_staticmethod(self):
        class Event: pass
        dummy = []
        class Target:
            @events.subscribe_to(Event)
            def run(e):
                dummy.append(e)
        e = Event()
        events.notify(e)
        self.assertEqual(dummy, [e])


from mailman.email.message import Message
from kittystore.storm import get_storm_store
from kittystore.test import FakeList, SettingsModule

class TestNotifyStore(unittest.TestCase):
    def setUp(self):
        self.store = get_storm_store(SettingsModule(), auto_create=True)
        self.store.db.cache.get_or_create = Mock()
        self.store.db.cache.get_or_create.side_effect = lambda *a: a[1]()
        self.store.db.cache.set = Mock()
        # cache.delete() will be called if the cache is invalidated
        self.store.db.cache.delete = Mock()

    def tearDown(self):
        self.store.close()

    def test_on_new_message_invalidate(self):
        # Check that the cache is invalidated on new message
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        today = datetime.date.today()
        self.store.add_to_list(FakeList("example-list"), msg)
        # calls to cache.delete() -- invalidation
        delete_args = [ call[0][0] for call in
                        self.store.db.cache.delete.call_args_list ]
        #from pprint import pprint; pprint(delete_args)
        self.assertEqual(set(delete_args), set([
            u'list:example-list:recent_participants_count',
            u'list:example-list:recent_threads_count',
            u'list:example-list:participants_count:%d:%d' % (today.year, today.month),
            u'list:example-list:thread:QKODQBCADMDSP5YPOPKECXQWEQAMXZL3:emails_count',
            u'list:example-list:thread:QKODQBCADMDSP5YPOPKECXQWEQAMXZL3:participants_count'
            ]))
        # calls to cache.get_or_create() -- repopulation
        goc_args = [ call[0][0] for call in
                     self.store.db.cache.get_or_create.call_args_list ]
        #from pprint import pprint; pprint(goc_args)
        self.assertEqual(set(goc_args), set([
            u'list:example-list:recent_participants_count',
            u'list:example-list:recent_threads_count',
            u'list:example-list:participants_count:%d:%d' % (today.year, today.month),
            u'list:example-list:threads_count:%d:%d' % (today.year, today.month),
            u'list:example-list:thread:QKODQBCADMDSP5YPOPKECXQWEQAMXZL3:emails_count',
            u'list:example-list:thread:QKODQBCADMDSP5YPOPKECXQWEQAMXZL3:participants_count'
            ]))
        #self.assertEqual(l.recent_participants_count, 1)
        #self.assertEqual(l.recent_threads_count, 1)
        #msg.replace_header("Message-ID", "<dummy2>")
        #self.store.add_to_list(FakeList("example-list"), msg)
        #self.assertEqual(l.recent_participants_count, 1)
        #self.assertEqual(l.recent_threads_count, 2)

    def test_on_new_thread_invalidate(self):
        # Check that the cache is invalidated on new message
        msg = Message()
        msg["From"] = "dummy@example.com"
        msg["Message-ID"] = "<dummy>"
        msg.set_payload("Dummy message")
        self.store.add_to_list(FakeList("example-list"), msg)
        msg.replace_header("Message-ID", "<dummy2>")
        msg["In-Reply-To"] = "<dummy>"
        self.store.add_to_list(FakeList("example-list"), msg)
        call_args = [ call[0][0] for call in self.store.db.cache.set.call_args_list ]
        #from pprint import pprint; pprint(call_args)
        self.assertEqual(call_args,
            [u'list:example-list:thread:QKODQBCADMDSP5YPOPKECXQWEQAMXZL3:subject'])
