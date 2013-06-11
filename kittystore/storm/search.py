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

from whoosh.index import create_in, exists_in, open_dir
from whoosh.fields import Schema, ID, TEXT, DATETIME, KEYWORD
from whoosh.analysis import StemmingAnalyzer
from whoosh.qparser import MultifieldParser

from .model import Email


def email_to_search_doc(email):
    if not isinstance(email, Email):
        raise ValueError("not an instance of the Email class")
    search_doc = {
            "list_name": email.list_name,
            "message_id": email.message_id,
            "sender": u"%s %s" % (email.sender_name, email.sender_email),
            "subject": email.subject,
            "content": email.content,
            "date": email.date, # UTC
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
                message_id=ID(stored=True),
                sender=TEXT(field_boost=1.5),
                subject=TEXT(field_boost=2.0, analyzer=stem_ana),
                content=TEXT(analyzer=stem_ana),
                date=DATETIME(),
                attachments=TEXT,
                tags=KEYWORD(commas=True, scorable=True),
            )

    @property
    def index(self):
        if self._index is None:
            if not os.path.isdir(self.location):
                os.makedirs(self.location)
            if exists_in(self.location):
                self._index = open_dir(self.location)
            else:
                self._index = create_in(self.location, self._get_schema())
        return self._index

    def add(self, doc):
        writer = self.index.writer()
        if isinstance(doc, Email):
            doc = email_to_search_doc(doc)
        try:
            writer.add_document(**doc)
        except Exception:
            writer.cancel()
            raise
        else:
            writer.commit()

    def search(self, query, page=None, limit=10, sortedby=None, reverse=False):
        """
        TODO: Should the searcher be shared?
        http://pythonhosted.org/Whoosh/threads.html#concurrency
        """
        query = MultifieldParser(
                ["sender", "subject", "content", "attachments"],
                self.index.schema).parse(query)
        return_value = {"total": 0, "results": []}
        with self.index.searcher() as searcher:
            if page:
                results = searcher.search_page(
                        query, page, pagelen=limit, sortedby=sortedby,
                        reverse=reverse)
                return_value["total"] = results.total
            else:
                results = searcher.search(
                        query, limit=limit, sortedby=sortedby, reverse=reverse)
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
        writer = self.index.writer(limitmb=256, procs=4, multisegment=True)
        # remove the LRU cache limit from the stemanalyzer
        for component in writer.schema["content"].analyzer:
            try:
                component.cachesize = -1
                component.clear()
            except AttributeError:
                continue
        try:
            for doc in documents:
                if isinstance(doc, Email):
                    doc = email_to_search_doc(doc)
                writer.add_document(**doc)
        except Exception:
            writer.cancel()
            raise
        else:
            writer.commit()

    def initialize_with(self, store):
        """Create and populate the index with the contents of a Store"""
        if exists_in(self.location):
            return # index already exists
        messages = store.db.find(Email).order_by(Email.archived_date)
        self.add_batch(messages)
