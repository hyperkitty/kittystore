# -*- coding: utf-8 -*-

"""
This module mainly contains stored requests that are used in different places,
the aim is to follow the DRY principle.

Copyright (C) 2012 Aurelien Bompard <abompard@fedoraproject.org>
Author: Aurelien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

from __future__ import absolute_import

from sqlalchemy import and_
from dogpile.cache import make_region


def get_participants_count_between(session, list_name, begin_date, end_date):
        from .model import Email
        # We filter on emails dates instead of threads dates because that would
        # also include last month's participants when threads carry from one
        # month to the next
        result = session.query(Email.sender_email).filter(and_(
                        Email.list_name == list_name,
                        Email.date >= begin_date,
                        Email.date < end_date,
                        )).distinct()
        return result.count()
        # TODO: check that ------v
        #return result.count() # generates a sub-query
        return len(list(result))

def get_threads_between(session, list_name, begin_date, end_date):
        from .model import Thread
        return session.query(Thread).filter(and_(
                    Thread.list_name == list_name,
                    Thread.date_active >= begin_date,
                    Thread.date_active < end_date,
                ))
