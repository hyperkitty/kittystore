# -*- coding: utf-8 -*-

# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""
Misc helper functions.

Author: Aurelien Bompard <abompard@fedoraproject.org>
"""

import email.utils
import re
from email.header import decode_header
from datetime import timedelta
from base64 import b32encode
from hashlib import sha1 # pylint: disable-msg=E0611

import dateutil.parser, dateutil.tz


__all__ = ("get_message_id_hash", "parseaddr", "parsedate",
           "header_to_unicode", "payload_to_unicode",
           "get_ref_and_thread_id",
           )


IN_BRACKETS_RE = re.compile("[^<]*<([^>]+)>.*")


def get_message_id_hash(msg_id):
    """
    Returns the X-Message-ID-Hash header for the provided Message-ID header.

    See <http://wiki.list.org/display/DEV/Stable+URLs#StableURLs-Headers> for
    details. Example:

    >>> get_message_id_hash('<87myycy5eh.fsf@uwakimon.sk.tsukuba.ac.jp>')
    'JJIGKPKB6CVDX6B2CUG4IHAJRIQIOUTP'

    """
    msg_id = email.utils.unquote(msg_id)
    return b32encode(sha1(msg_id).digest())


def parseaddr(address):
    """
    Wrapper around email.utils.parseaddr to also handle Mailman's generated
    mbox archives.
    """
    address = address.replace(" at ", "@")
    from_name, from_email = email.utils.parseaddr(address)
    if not from_name:
        from_name = from_email
    return from_name, from_email


def header_to_unicode(header):
    """
    See also: http://ginstrom.com/scribbles/2007/11/19/parsing-multilingual-email-with-python/
    """
    h_decoded = []
    for text, charset in decode_header(header):
        if charset is None:
            h_decoded.append(unicode(text))
        else:
            try:
                h_decoded.append(text.decode(charset))
            except LookupError:
                # Unknown encoding
                h_decoded.append(text.decode("ascii", "replace"))
    return u" ".join(h_decoded)


def parsedate(datestring):
    if datestring is None:
        return None
    try:
        parsed = dateutil.parser.parse(datestring)
    except ValueError:
        return None
    if parsed.utcoffset() is not None and \
            abs(parsed.utcoffset()) > timedelta(hours=13):
        parsed = parsed.astimezone(dateutil.tz.tzutc())
    return parsed
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
    ref_id = IN_BRACKETS_RE.match(ref_id)
    if ref_id is None:
        # Can't parse the reference
        return None, None
    ref_id = ref_id.group(1)
    # It's a reply, use the thread_id from the parent email
    ref_msg = store.get_message_by_id_from_list(list_name, ref_id)
    if ref_msg is None:
        thread_id = None
    else:
        # re-use parent's thread-id
        thread_id = unicode(ref_msg.thread_id)
    return unicode(ref_id), thread_id

