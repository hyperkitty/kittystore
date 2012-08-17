# -*- coding: utf-8 -*-

"""
Misc helper functions.

Copyright (C) 2012 Aurelien Bompard
Author: Aurelien Bompard <abompard@fedoraproject.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or (at
your option) any later version.
See http://www.gnu.org/copyleft/gpl.html  for the full text of the
license.
"""

import email.utils
import time
import re
from datetime import datetime, tzinfo
from base64 import b32encode
from hashlib import sha1

import dateutil.parser


__all__ = ("get_message_id_hash", "parseaddr", "parsedate",
           "get_ref_and_thread_id",
           )


IN_BRACKETS_RE = re.compile("[^<]*<([^>]+)>.*")


def get_message_id_hash(msg_id):
    """
    Returns the X-Message-ID-Hash header for the provided Message-ID header.

    See <http://wiki.list.org/display/DEV/Stable+URLs#StableURLs-Headers> for
    details. Example:

    >>> get_message_id_hash('<87myycy5eh.fsf@uwakimon.sk.tsukuba.ac.jp>')
    'AGDWSNXXKCWEILKKNYTBOHRDQGOX3Y35'

    """
    msg_id = msg_id.strip("<>")
    return b32encode(sha1(msg_id).digest())


def parseaddr(address):
    """
    Wrapper around email.utils.parseaddr to also handle Mailman's generated
    mbox archives.
    """
    address = address.replace(" at ", "@")
    return email.utils.parseaddr(address)

def parsedate(datestring):
    if datestring is None:
        return None
    return dateutil.parser.parse(datestring)
    #date_tuple = email.utils.parsedate_tz(datestring)
    #timestamp = email.utils.mktime_tz(date_tuple)
    #return datetime.fromtimestamp(timestamp)

def get_ref_and_thread_id(message, list_name, store):
    """
    Returns the thread ID and the message-id of the reference email for a given
    message.
    """
    if (not message.has_key("References")
            and not message.has_key("In-Reply-To")):
        return None, None
    # It's a reply, use the thread_id from the parent email
    ref_id = message.get("References")
    if ref_id is not None:
        # There can be multiple references, use the first one
        ref_id = ref_id.split()[0].strip()
    else:
        ref_id = message.get("In-Reply-To")
    ref_id = IN_BRACKETS_RE.match(ref_id).group(1)
    # It's a reply, use the thread_id from the parent email
    ref_msg = store.get_message_by_id_from_list(list_name, ref_id)
    if ref_msg is None:
        thread_id = None
    else:
        # re-use parent's thread-id
        thread_id = ref_msg.thread_id
    return ref_id, thread_id

