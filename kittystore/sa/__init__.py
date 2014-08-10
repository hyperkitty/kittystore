# -*- coding: utf-8 -*-

from __future__ import absolute_import, with_statement

from dogpile.cache import make_region
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .model import Base


def get_sa_store(settings, search_index=None, debug=False, auto_create=False):
    engine = create_engine(settings.KITTYSTORE_URL, echo=debug)
    if auto_create or True:
        Base.metadata.create_all(engine)
    cache = make_region()
    Session = sessionmaker(bind=engine)
    Session.cache = cache
    session = Session()
    return
