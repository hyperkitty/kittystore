# -*- coding: utf-8 -*-

"""
Copyright (C) 2012 Aurelien Bompard <abompard@fedoraproject.org>
Author: Aurelien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

import datetime

from storm.locals import *
from .hack_datetime import DateTime

from kittystore.utils import get_message_id_hash


__all__ = ("List", "Email",)

class List(object):

    __storm_table__ = "list"

    name = Unicode(primary=True)

    def __init__(self, name):
        self.name = unicode(name)


class Email(object):

    __storm_table__ = "email"
    __storm_primary__ = "list_name", "message_id"

    list_name = Unicode()
    message_id = Unicode()
    sender_name = Unicode()
    sender_email = Unicode()
    subject = Unicode()
    content = Unicode()
    date = DateTime()
    in_reply_to = Unicode()
    hash_id = Unicode()
    thread_id = Unicode()
    full = RawStr()
    archived_date = DateTime(default_factory=datetime.datetime.now)

    def __init__(self, list_name, message_id):
        self.list_name = unicode(list_name)
        self.message_id = unicode(message_id)
        self.hash_id = unicode(get_message_id_hash(self.message_id))
