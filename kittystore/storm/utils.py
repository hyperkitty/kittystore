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

import datetime

from storm.locals import And


def get_participants_count_between(store, list_name, begin_date, end_date):
        from .model import Email
        # We count emails instead of thread participants because that would
        # also include last month's participants when threads carry from one
        # month to the next
        result = store.find(Email, And(
                        Email.list_name == list_name,
                        Email.date >= begin_date,
                        Email.date < end_date,
                        )).config(distinct=True
                        ).values(Email.sender_name, Email.sender_email)
        return len(list(result))

def get_threads_between(store, list_name, begin_date, end_date):
        from .model import Thread
        return store.find(Thread, And(
                    Thread.list_name == list_name,
                    Thread.date_active >= begin_date,
                    Thread.date_active < end_date,
                ))
