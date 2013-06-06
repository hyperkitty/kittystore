# -*- coding: utf-8 -*-

"""
Module entry point: call get_store() to instanciate a KittyStore
implementation.

Copyright (C) 2012 Aurelien Bompard
Author: Aurelien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

__all__ = ("get_store", "MessageNotFound", )


def get_store(url, search=None, debug=False):
    """Factory for a KittyStore subclass"""
    if url.startswith("mongo://"):
        raise NotImplementedError
    #else:
    #    from kittystore.sa import KittySAStore
    #    return KittySAStore(url, debug)
    else:
        from kittystore.storm import get_storm_store
        store = get_storm_store(url, search, debug)
    if search is not None:
        store.search_index.initialize_with(store)
    return store


class MessageNotFound(Exception):
    pass
