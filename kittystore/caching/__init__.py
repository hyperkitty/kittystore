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

from pkg_resources import resource_listdir

import logging
logger = logging.getLogger(__name__)


def sync_mailman(store):
    from kittystore.caching.mailman_user import sync_mailman_user
    from kittystore.caching.mlist import sync_list_properties
    for sync_fn in (sync_mailman_user, sync_list_properties):
        if sync_fn.__doc__:
            logger.info(sync_fn.__doc__)
        sync_fn(store)


def setup_cache(cache, settings):
    def find_backend():
        default_backend = "dogpile.cache.memory"
        default_args = {}
        try:
            django_backend = settings.CACHES["default"]["BACKEND"]
            django_location = settings.CACHES["default"]["LOCATION"]
        except (KeyError, AttributeError):
            return default_backend, default_args
        if django_backend == \
                "django.core.cache.backends.memcached.PyLibMCCache":
            backend = 'dogpile.cache.pylibmc'
        elif django_backend == \
                "django.core.cache.backends.memcached.MemcachedCache":
            backend = 'dogpile.cache.memcached'
        else:
            return default_backend, default_args
        if isinstance(django_location, basestring):
            django_location = [django_location]
        arguments = { 'url': django_location, }
        return backend, arguments
    backend, arguments = find_backend()
    cache.configure(backend, arguments=arguments)


def register_events():
    """Register event subscriptions"""
    submodules = [ f[:-3] for f in resource_listdir("kittystore.caching", "")
                   if f.endswith(".py") and f != "__init__.py" ]
    for submod_name in submodules:
        # import the modules, decorators are used to register the right event
        __import__("kittystore.caching.%s" % submod_name)
