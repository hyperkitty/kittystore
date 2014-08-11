# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement

from dogpile.cache import make_region
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kittystore.caching import setup_cache
from .model import Base
from .store import SAStore


def get_sa_store(settings, search_index=None, debug=False, auto_create=False):
    engine = create_engine(settings.KITTYSTORE_URL, echo=debug)
    if auto_create or True:
        Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    cache = make_region()
    setup_cache(cache, settings)
    session.cache = cache
    return SAStore(session, search_index, settings, debug)
