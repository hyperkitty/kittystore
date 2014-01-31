# -*- coding: utf-8 -*-

"""
Copyright (C) 2012 Aurélien Bompard <abompard@fedoraproject.org>
Author: Aurélien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import

import os
import shutil

from whoosh.index import create_in, exists_in, open_dir
from whoosh.fields import Schema, ID, TEXT, DATETIME, KEYWORD, BOOLEAN
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import MultifieldParser
from whoosh.query import Term
from mailman.interfaces.archiver import ArchivePolicy
from mailman.interfaces.messages import IMessage

import logging
logger = logging.getLogger(__name__)


def email_to_search_doc(email):
    if not IMessage.providedBy(email):
        raise ValueError("not an instance of the Email class")
    private_list = (email.mlist.archive_policy == ArchivePolicy.private)
    search_doc = {
            "list_name": email.list_name,
            "message_id": email.message_id,
            "sender": u"%s %s" % (email.sender_name, email.sender_email),
            "user_id": email.user_id,
            "subject": email.subject,
            "content": email.content,
            "date": email.date, # UTC
            "private_list": private_list,
    }
    attachments = [a.name for a in email.attachments]
    if attachments:
        search_doc["attachments"] = " ".join(attachments)
    return search_doc


class SearchEngine(object):

    def __init__(self, location):
        self.location = location
        self._index = None

    def _get_schema(self):
        stem_ana = StemmingAnalyzer()
        return Schema(
                list_name=ID(stored=True),
                message_id=ID(stored=True, unique=True),
                sender=TEXT(field_boost=1.5),
                user_id=TEXT,
                subject=TEXT(field_boost=2.0, analyzer=stem_ana),
                content=TEXT(analyzer=stem_ana),
                date=DATETIME(),
                attachments=TEXT,
                tags=KEYWORD(commas=True, scorable=True),
                private_list=BOOLEAN(),
            )

    @property
    def index(self):
        if self._index is None:
            self._index = open_dir(self.location)
        return self._index

    def add(self, doc):
        writer = self.index.writer()
        if IMessage.providedBy(doc):
            doc = email_to_search_doc(doc)
        try:
            writer.add_document(**doc)
        except Exception:
            writer.cancel()
            raise
        else:
            writer.commit()

    def search(self, query, list_name=None, page=None, limit=10,
               sortedby=None, reverse=False):
        """
        TODO: Should the searcher be shared?
        http://pythonhosted.org/Whoosh/threads.html#concurrency
        """
        query = MultifieldParser(
                ["sender", "subject", "content", "attachments"],
                self.index.schema).parse(query)
        if list_name:
            results_filter = Term("list_name", list_name)
        else:
            # When searching all lists, only the public lists are searched
            results_filter = Term("private_list", False)
        return_value = {"total": 0, "results": []}
        with self.index.searcher() as searcher:
            if page:
                results = searcher.search_page(
                        query, page, pagelen=limit, sortedby=sortedby,
                        reverse=reverse, filter=results_filter)
                return_value["total"] = results.total
            else:
                results = searcher.search(
                        query, limit=limit, sortedby=sortedby,
                        reverse=reverse, filter=results_filter)
                # http://pythonhosted.org/Whoosh/searching.html#results-object
                if results.has_exact_length():
                    return_value["total"] = len(results)
                else:
                    return_value["total"] = results.estimated_length()
            return_value["results"] = [ dict(r) for r in results ]
        return return_value

    def optimize(self):
        return self.index.optimize()

    def add_batch(self, documents):
        """
        See http://pythonhosted.org/Whoosh/batch.html
        """
        logger.info("Indexing all messages")
        # Don't use optimizations below, it will eat up lots of memory and can
        # go as far as preventing forking (OSError), tested on a 3GB VM with
        # the Fedora archives
        #writer = self.index.writer(limitmb=256, procs=4, multisegment=True)
        writer = self.index.writer(multisegment=True)
        # remove the LRU cache limit from the stemanalyzer
        for component in writer.schema["content"].analyzer:
            try:
                component.cachesize = -1
                component.clear()
            except AttributeError:
                continue
        try:
            for num, doc in enumerate(documents):
                if IMessage.providedBy(doc):
                    doc = email_to_search_doc(doc)
                writer.add_document(**doc)
                if num % 1000 == 0:
                    logger.info("...still indexing (%d/%d)..."
                                 % (num, len(documents)))
        except Exception:
            writer.cancel()
            raise
        else:
            writer.commit()

    def initialize_with(self, store):
        """Create and populate the index with the contents of a Store"""
        if not os.path.isdir(self.location):
            os.makedirs(self.location)
        self._index = create_in(self.location, self._get_schema())
        self.add_batch(store.get_all_messages())

    def needs_upgrade(self):
        if not exists_in(self.location):
            return True
        if "user_id" not in self.index.schema:
            return True
        new_schema = self._get_schema()
        for field_name, field_type in new_schema.items():
            if field_name not in self.index.schema:
                return True
        return False

    def upgrade(self, store):
        """Upgrade the schema"""
        if not exists_in(self.location):
            self.initialize_with(store)
        if "user_id" not in self.index.schema:
            logger.info("Rebuilding the search index to include the new user_id field...")
            shutil.rmtree(self.location)
            self.initialize_with(store)
        new_schema = self._get_schema()
        writer = self.index.writer()
        for field_name, field_type in new_schema.items():
            if field_name not in self.index.schema:
                logger.info("Adding field %s to the search index" % field_name)
                writer.add_field(field_name, field_type)
        writer.commit(optimize=True)



class DelayedSearchEngine(SearchEngine):

    def __init__(self, *args, **kw):
        super(DelayedSearchEngine, self).__init__(*args, **kw)
        self._add_buffer = []

    def add(self, doc):
        self._add_buffer.append(doc)

    def flush(self):
        self.add_batch(self._add_buffer)
        self._add_buffer = []


def make_delayed(engine):
    return DelayedSearchEngine(engine.location)
