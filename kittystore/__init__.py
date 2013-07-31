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


def get_store(settings, debug=None):
    """Factory for a KittyStore subclass"""
    required_keys = ("KITTYSTORE_URL", "KITTYSTORE_SEARCH_INDEX",
                     "MAILMAN_REST_SERVER", "MAILMAN_API_USER",
                     "MAILMAN_API_PASS")
    for req_key in required_keys:
        try:
            getattr(settings, req_key)
        except AttributeError:
            raise AttributeError("The settings file is missing the \"%s\" key" % req_key)
    if debug is None:
        debug = getattr(settings, "KITTYSTORE_DEBUG", False)
    if settings.KITTYSTORE_URL.startswith("mongo://"):
        raise NotImplementedError
    #else:
    #    from kittystore.sa import KittySAStore
    #    return KittySAStore(url, debug)
    else:
        from kittystore.storm import get_storm_store
        store = get_storm_store(settings, debug)
    if settings.KITTYSTORE_SEARCH_INDEX is not None:
        store.search_index.initialize_with(store)
    return store


class MessageNotFound(Exception):
    pass
